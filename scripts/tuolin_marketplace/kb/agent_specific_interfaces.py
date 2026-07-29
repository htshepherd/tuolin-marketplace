from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..shared.project_layout import ProjectPaths
from .video_audio_policy import build_downstream_audio_summary, redact_transcript_for_downstream
from .video_test_evidence import build_downstream_test_summary
from .video_usage_policy import evaluate_video_usage_policy


VIDEO_PLANNER_AGENT_ID = "tuolin-video-planner"
VIDEO_PLANNER_CARD_TYPES = (
    "product",
    "application_scenario",
    "content_asset",
    "evidence",
    "review_item",
    "video_profile",
)
VIDEO_PLANNER_ALLOWED_SCOPES = {"external_allowed", "review_before_external", "evidence_only"}


@dataclass(frozen=True)
class AgentInterfaceRegistration:
    agent_id: str
    builder: Any
    verifier: Any


REGISTERED_AGENT_INTERFACES: tuple[AgentInterfaceRegistration, ...]


def agent_interface_root(paths: ProjectPaths, agent_id: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]+", agent_id):
        raise ValueError("agent_id must use lowercase letters, digits, and hyphens")
    return paths.generated_dir / "agent-interfaces" / agent_id


def refresh_registered_agent_interfaces(
    paths: ProjectPaths,
    *,
    source_interface_revision: str,
    action: str,
    expected_card_ids: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    results = []
    for registration in REGISTERED_AGENT_INTERFACES:
        built = registration.builder(
            paths,
            source_interface_revision=source_interface_revision,
            action=action,
            expected_card_ids=expected_card_ids,
        )
        verification = registration.verifier(paths, built)
        results.append({**built, "verification": verification})
    if not all(item.get("verified") for item in results):
        failed = [str(item.get("agent_id")) for item in results if not item.get("verified")]
        raise RuntimeError("Agent-specific interface refresh verification failed: " + ", ".join(failed))
    return {
        "verified": True,
        "action": action,
        "registered_interface_count": len(results),
        "interfaces": results,
        "legacy_shared_interface_migration_complete": False,
    }


def rebuild_video_planner_interface(
    paths: ProjectPaths,
    *,
    source_interface_revision: str,
    action: str,
    expected_card_ids: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    source_cards = _read_json(paths.generated_dir / "indexes" / "cards.json")
    selected = [_project_card(card) for card in source_cards if _planner_card_allowed(card)]
    selected.sort(key=lambda item: (str(item.get("type")), str(item.get("id"))))
    selected_ids = {str(card["id"]) for card in selected}
    root = agent_interface_root(paths, VIDEO_PLANNER_AGENT_ID)
    root.parent.mkdir(parents=True, exist_ok=True)
    staging_root = root.parent / f".{VIDEO_PLANNER_AGENT_ID}.staging-{uuid.uuid4().hex}"
    generated_at = datetime.now(timezone.utc).isoformat()
    profiles = _load_selected_profiles(paths, selected)
    interface_revision = _projection_revision(selected, profiles)

    try:
        cards_dir = staging_root / "cards"
        cards_dir.mkdir(parents=True, exist_ok=False)
        by_type = {card_type: [] for card_type in VIDEO_PLANNER_CARD_TYPES}
        for card in selected:
            by_type[str(card["type"])].append(card)
        for card_type, cards in by_type.items():
            _write_json(cards_dir / f"{card_type}.json", cards)

        products = [
            {
                "id": card["id"],
                "title": card["title"],
                "aliases": card.get("aliases", []),
                "tags": card.get("tags", []),
                "projection_fingerprint": card["projection_fingerprint"],
            }
            for card in by_type["product"]
        ]
        _write_json(staging_root / "products.json", products)
        _write_json(staging_root / "search_index.json", _build_search_index(selected))
        video_summary = _write_video_profile_projection(
            paths,
            root=staging_root,
            profiles=profiles,
            interface_revision=interface_revision,
            generated_at=generated_at,
        )
        expected = tuple(dict.fromkeys(str(item) for item in expected_card_ids))
        eligible_expected = [
            str(card["id"])
            for card in source_cards
            if str(card.get("id")) in expected and _planner_card_allowed(card)
        ]
        missing_expected = [card_id for card_id in eligible_expected if card_id not in selected_ids]
        if missing_expected:
            raise RuntimeError(
                "Video-planner interface refresh verification failed after "
                f"{action}: missing expected cards: {', '.join(missing_expected)}"
            )
        manifest = {
        "schema_version": "tuolin-agent-interface-v1",
        "agent_id": VIDEO_PLANNER_AGENT_ID,
        "generated_at": generated_at,
        "interface_revision": interface_revision,
        "source_knowledge_revision": source_interface_revision,
        "raw_access": False,
        "cards": "cards/",
        "products": "products.json",
        "search_index": "search_index.json",
        "video_profiles": "video-profiles/",
        "card_types": list(VIDEO_PLANNER_CARD_TYPES),
        "policy": {
            "supported_platforms": ["youtube_shorts", "tiktok"],
            "supported_languages": ["zh", "en"],
            "duration_seconds": {"minimum": 15, "maximum": 90, "recommended": 30},
            "aspect_ratio": "9:16",
            "public_trend_search": False,
            "source_video_audio": False,
            "review_before_external_is_draft_only": True,
        },
        "counts": {
            "cards": len(selected),
            "products": len(products),
            "video_profiles": video_summary["profile_count"],
        },
        "verification": {
            "verified": True,
            "action": action,
            "eligible_expected_card_ids": eligible_expected,
            "excluded_expected_card_ids": [item for item in expected if item not in eligible_expected],
        },
        }
        _write_json(staging_root / "manifest.json", manifest)
        staged_manifest = _read_json(staging_root / "manifest.json")
        staged_products = _read_json(staging_root / "products.json")
        if staged_manifest.get("interface_revision") != interface_revision:
            raise RuntimeError("Video-planner staged manifest revision mismatch")
        if len(staged_products) != len(products):
            raise RuntimeError("Video-planner staged product verification mismatch")
        _promote_interface_snapshot(root, staging_root)
    except Exception:
        if staging_root.exists():
            shutil.rmtree(staging_root)
        raise
    persisted = read_video_planner_manifest(paths)
    if persisted.get("interface_revision") != interface_revision:
        raise RuntimeError("Video-planner interface persisted revision mismatch")
    return {
        "agent_id": VIDEO_PLANNER_AGENT_ID,
        "verified": True,
        "interface_revision": interface_revision,
        "source_knowledge_revision": source_interface_revision,
        "generated_at": generated_at,
        "card_count": len(selected),
        "product_count": len(products),
        "video_profile_count": video_summary["profile_count"],
        "verified_card_ids": eligible_expected,
    }


def verify_video_planner_interface(paths: ProjectPaths, built: dict[str, Any]) -> dict[str, Any]:
    manifest = read_video_planner_manifest(paths)
    products = read_video_planner_products(paths)
    if manifest.get("interface_revision") != built.get("interface_revision"):
        raise RuntimeError("Video-planner verifier found a manifest revision mismatch")
    if len(products) != int(manifest.get("counts", {}).get("products", -1)):
        raise RuntimeError("Video-planner verifier found a product count mismatch")
    persisted_ids = {
        str(card.get("id"))
        for card_type in VIDEO_PLANNER_CARD_TYPES
        for card in read_video_planner_cards(paths, card_type)
    }
    missing = [card_id for card_id in built.get("verified_card_ids", []) if card_id not in persisted_ids]
    if missing:
        raise RuntimeError("Video-planner verifier is missing expected cards: " + ", ".join(missing))
    return {
        "verified": True,
        "agent_id": VIDEO_PLANNER_AGENT_ID,
        "interface_revision": manifest["interface_revision"],
        "verified_card_ids": list(built.get("verified_card_ids", [])),
    }


REGISTERED_AGENT_INTERFACES = (
    AgentInterfaceRegistration(
        agent_id=VIDEO_PLANNER_AGENT_ID,
        builder=rebuild_video_planner_interface,
        verifier=verify_video_planner_interface,
    ),
)


def read_video_planner_manifest(paths: ProjectPaths) -> dict[str, Any]:
    return _read_json(agent_interface_root(paths, VIDEO_PLANNER_AGENT_ID) / "manifest.json")


def read_video_planner_products(paths: ProjectPaths) -> list[dict[str, Any]]:
    return _read_json(agent_interface_root(paths, VIDEO_PLANNER_AGENT_ID) / "products.json")


def read_video_planner_cards(paths: ProjectPaths, card_type: str) -> list[dict[str, Any]]:
    if card_type not in VIDEO_PLANNER_CARD_TYPES:
        raise ValueError(f"Unsupported video-planner card type: {card_type}")
    return _read_json(agent_interface_root(paths, VIDEO_PLANNER_AGENT_ID) / "cards" / f"{card_type}.json")


def read_video_planner_card(paths: ProjectPaths, card_id: str) -> dict[str, Any]:
    for card_type in VIDEO_PLANNER_CARD_TYPES:
        for card in read_video_planner_cards(paths, card_type):
            if card.get("id") == card_id:
                return card
    raise KeyError(f"video-planner card not found: {card_id}")


def search_video_planner_cards(
    paths: ProjectPaths,
    query: str,
    *,
    product_id: str | None = None,
    card_types: tuple[str, ...] | list[str] = (),
    limit: int = 30,
) -> list[dict[str, Any]]:
    terms = [item.casefold() for item in re.split(r"[\s，。；、,.!?！？:：]+", query) if item]
    required_types = set(card_types)
    results: list[tuple[int, str, dict[str, Any]]] = []
    for item in _read_json(agent_interface_root(paths, VIDEO_PLANNER_AGENT_ID) / "search_index.json"):
        if required_types and item.get("type") not in required_types:
            continue
        if product_id and product_id not in item.get("related_product_ids", []):
            continue
        text = str(item.get("text") or "").casefold()
        if terms and not all(term in text for term in terms):
            continue
        results.append((sum(text.count(term) for term in terms), str(item.get("id")), item))
    results.sort(key=lambda row: (-row[0], row[1]))
    return [row[2] for row in results[:limit]]


def read_video_planner_video_catalog(paths: ProjectPaths) -> list[dict[str, Any]]:
    return _read_json(agent_interface_root(paths, VIDEO_PLANNER_AGENT_ID) / "video-profiles" / "catalog.json")


def search_video_planner_video_catalog(
    paths: ProjectPaths,
    *,
    query: str = "",
    product_id: str | None = None,
    use_capabilities: tuple[str, ...] | list[str] = (),
) -> list[dict[str, Any]]:
    terms = [item.casefold() for item in query.split() if item.strip()]
    required = set(use_capabilities)
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for entry in read_video_planner_video_catalog(paths):
        if product_id and entry.get("product_id") != product_id:
            continue
        if not required.issubset(set(entry.get("use_capabilities", []))):
            continue
        text = " ".join(
            str(value)
            for value in (
                entry.get("title", ""),
                entry.get("summary", ""),
                *entry.get("source_classification", []),
                *entry.get("observed_classifications", []),
                *entry.get("use_capabilities", []),
            )
        ).casefold()
        if terms and not all(term in text for term in terms):
            continue
        ranked.append((sum(text.count(term) for term in terms), str(entry.get("profile_id")), entry))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [row[2] for row in ranked]


def read_video_planner_video_detail(paths: ProjectPaths, profile_id: str) -> dict[str, Any]:
    entry = next(
        (item for item in read_video_planner_video_catalog(paths) if item.get("profile_id") == profile_id),
        None,
    )
    if entry is None:
        raise KeyError(f"video-planner profile not found: {profile_id}")
    path = agent_interface_root(paths, VIDEO_PLANNER_AGENT_ID) / "video-profiles" / "details" / f"{entry['video_asset_id']}.json"
    detail = _read_json(path)
    if detail.get("profile_revision") != entry.get("profile_revision"):
        raise ValueError("video-planner profile detail revision mismatch")
    return detail


def resolve_video_planner_representative_media(paths: ProjectPaths, profile_id: str, media_ref: str) -> Path:
    detail = read_video_planner_video_detail(paths, profile_id)
    if media_ref not in {str(item.get("media_ref")) for item in detail.get("representative_frames", [])}:
        raise PermissionError("representative media is not in the active video-planner profile")
    index = _read_json(agent_interface_root(paths, VIDEO_PLANNER_AGENT_ID) / ".private-media-index.json")
    item = next(
        (
            candidate
            for candidate in index.get("media", [])
            if candidate.get("profile_id") == profile_id
            and candidate.get("profile_revision") == detail.get("profile_revision")
            and candidate.get("media_ref") == media_ref
        ),
        None,
    )
    if item is None:
        raise PermissionError("representative media mapping is stale")
    path = (paths.generated_dir / str(item.get("generated_ref") or "")).resolve()
    try:
        path.relative_to(paths.generated_dir.resolve())
    except ValueError as exc:
        raise PermissionError("representative media escapes generated_dir") from exc
    if not path.is_file() or _file_sha256(path) != item.get("content_fingerprint"):
        raise ValueError("representative media is missing or changed")
    return path


def _planner_card_allowed(card: dict[str, Any]) -> bool:
    if card.get("type") not in VIDEO_PLANNER_CARD_TYPES:
        return False
    if card.get("type") == "review_item":
        return card.get("status") != "archived"
    return card.get("status") == "official" and card.get("usage_scope") in VIDEO_PLANNER_ALLOWED_SCOPES


def _project_card(card: dict[str, Any]) -> dict[str, Any]:
    projected = dict(card)
    projected["projection_fingerprint"] = _json_digest(
        {
            "id": card.get("id"),
            "status": card.get("status"),
            "usage_scope": card.get("usage_scope"),
            "frontmatter": card.get("frontmatter"),
            "body_markdown": card.get("body_markdown"),
        }
    )
    projected["draft_only"] = card.get("usage_scope") == "review_before_external"
    return projected


def _load_selected_profiles(paths: ProjectPaths, cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    profiles = []
    for card in cards:
        if card.get("type") != "video_profile":
            continue
        json_path = (paths.knowledge_dir / str(card["path"])).with_suffix(".json")
        if json_path.is_file():
            profiles.append(_read_json(json_path))
    return profiles


def _write_video_profile_projection(
    paths: ProjectPaths,
    *,
    root: Path,
    profiles: list[dict[str, Any]],
    interface_revision: str,
    generated_at: str,
) -> dict[str, int]:
    video_root = root / "video-profiles"
    details_dir = video_root / "details"
    details_dir.mkdir(parents=True, exist_ok=True)
    for stale in details_dir.glob("*.json"):
        stale.unlink()
    registry_available, active_revisions = _active_video_revisions(paths)
    catalog = []
    private_media = []
    for profile in sorted(profiles, key=lambda item: str(item.get("profile_id") or "")):
        if profile.get("processing_state") == "revoked":
            continue
        asset_id = str(profile.get("video_asset_id") or "")
        if registry_available and active_revisions.get(asset_id) != profile.get("source_revision"):
            continue
        revision = str(profile.get("profile_revision") or "")
        representatives = []
        detail_frames = []
        for index, frame in enumerate(profile.get("representative_frames", []), start=1):
            media_ref = f"video-planner-media://{revision}/{index:02d}"
            generated_ref = str(frame.get("generated_ref") or "")
            media_path = (paths.generated_dir / generated_ref).resolve()
            try:
                normalized_ref = media_path.relative_to(paths.generated_dir.resolve())
            except ValueError as exc:
                raise ValueError("video-planner representative media escapes generated_dir") from exc
            if not media_path.is_file():
                raise FileNotFoundError(media_path)
            fingerprint = _file_sha256(media_path)
            representatives.append(
                {
                    "media_ref": media_ref,
                    "timestamp_seconds": frame.get("timestamp_seconds"),
                    "description": frame.get("description", ""),
                }
            )
            detail_frames.append(
                {
                    **{key: value for key, value in frame.items() if key != "generated_ref"},
                    "media_ref": media_ref,
                    "content_fingerprint": fingerprint,
                }
            )
            private_media.append(
                {
                    "profile_id": profile.get("profile_id"),
                    "profile_revision": revision,
                    "media_ref": media_ref,
                    "generated_ref": normalized_ref.as_posix(),
                    "content_fingerprint": fingerprint,
                }
            )
        usage_policy = evaluate_video_usage_policy(profile)
        detail = {
            **profile,
            "transcript_detail": redact_transcript_for_downstream(dict(profile.get("transcript_detail") or {})),
            "representative_frames": detail_frames,
            "interface_revision": interface_revision,
            "interface_state": "video_planner_active",
            "usage_policy": usage_policy,
        }
        _write_json(details_dir / f"{asset_id}.json", detail)
        catalog.append(
            {
                "profile_id": profile.get("profile_id"),
                "video_asset_id": asset_id,
                "product_id": profile.get("product_id"),
                "profile_revision": revision,
                "title": profile.get("title", ""),
                "summary": profile.get("summary", ""),
                "source_classification": profile.get("source_classification", []),
                "observed_classifications": profile.get("observed_classifications", []),
                "use_capabilities": profile.get("use_capabilities", []),
                "product_visibility": profile.get("product_visibility"),
                "reuse_modes": sorted(
                    {
                        str(segment.get("reuse_mode"))
                        for segment in profile.get("key_segments", [])
                        if segment.get("reuse_mode") and segment.get("use_exclusion", {}).get("status") != "excluded"
                    }
                ),
                "risk_summary": profile.get("risk_summary", []),
                "processing_state": profile.get("processing_state"),
                "representative_frames": representatives,
                "audio_summary": build_downstream_audio_summary(profile),
                "test_summary": build_downstream_test_summary(profile),
                "usage_policy": usage_policy,
            }
        )
    _write_json(video_root / "catalog.json", catalog)
    _write_json(
        video_root / "manifest.json",
        {
            "schema_version": "video-planner-profile-interface-v1",
            "interface_revision": interface_revision,
            "generated_at": generated_at,
            "catalog": "catalog.json",
            "details": "details/",
            "raw_access": False,
        },
    )
    _write_json(
        root / ".private-media-index.json",
        {
            "schema_version": "video-planner-private-media-index-v1",
            "interface_revision": interface_revision,
            "media": private_media,
        },
    )
    return {"profile_count": len(catalog), "representative_media_count": len(private_media)}


def _promote_interface_snapshot(active_root: Path, staging_root: Path) -> None:
    backup_root = active_root.parent / f".{active_root.name}.backup-{uuid.uuid4().hex}"
    had_active = active_root.exists()
    if had_active:
        active_root.replace(backup_root)
    try:
        staging_root.replace(active_root)
    except Exception:
        if had_active and backup_root.exists():
            backup_root.replace(active_root)
        raise
    if backup_root.exists():
        shutil.rmtree(backup_root)


def _build_search_index(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for card in cards:
        frontmatter = card.get("frontmatter", {})
        related = sorted(
            {
                *[str(item) for item in frontmatter.get("related_products", [])],
                *([str(card["id"])] if card.get("type") == "product" else []),
                *([str(frontmatter.get("product_id"))] if frontmatter.get("product_id") else []),
            }
        )
        result.append(
            {
                "id": card.get("id"),
                "type": card.get("type"),
                "title": card.get("title"),
                "related_product_ids": related,
                "projection_fingerprint": card.get("projection_fingerprint"),
                "text": " ".join(
                    str(value)
                    for value in (
                        card.get("title", ""),
                        *card.get("aliases", []),
                        *card.get("tags", []),
                        card.get("body_excerpt", ""),
                        *related,
                    )
                ),
            }
        )
    return result


def _projection_revision(cards: list[dict[str, Any]], profiles: list[dict[str, Any]]) -> str:
    return "video_planner_" + _json_digest(
        {
            "cards": [(item.get("id"), item.get("projection_fingerprint")) for item in cards],
            "profiles": [
                (item.get("profile_id"), item.get("profile_revision"), item.get("content_digest"))
                for item in profiles
            ],
        }
    )[:20]


def _active_video_revisions(paths: ProjectPaths) -> tuple[bool, dict[str, str]]:
    path = paths.generated_dir / "cache" / "video-assets" / "registry.json"
    if not path.is_file():
        return False, {}
    registry = _read_json(path)
    return True, {
        str(item.get("asset_id")): str(item.get("source_fingerprint"))
        for item in registry.get("assets", [])
        if item.get("asset_id") and item.get("source_fingerprint")
    }


def _json_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)

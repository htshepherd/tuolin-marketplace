from __future__ import annotations

import json
import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .card_validator import PROFILE, parse_frontmatter, validate_card_file
from .video_audio_policy import (
    build_downstream_audio_summary,
    redact_transcript_for_downstream,
)
from .video_test_evidence import build_downstream_test_summary
from .partitions import scan_all_partitions, summaries_to_json
from ..shared.project_layout import ProjectPaths


def rebuild_generated_indexes(paths: ProjectPaths) -> dict[str, Any]:
    cards = []
    video_profiles = []
    validation_errors = []
    for card_path in sorted(paths.knowledge_dir.rglob("*.md")):
        result = validate_card_file(card_path)
        if result.skipped:
            continue
        if not result.valid:
            validation_errors.append({"path": str(card_path), "errors": list(result.errors)})
            continue
        frontmatter = parse_frontmatter(card_path.read_text(encoding="utf-8"))
        relative_path = card_path.relative_to(paths.knowledge_dir).as_posix()
        body = _card_body(card_path)
        if frontmatter["type"] == "video_profile":
            video_profiles.append(
                json.loads(card_path.with_suffix(".json").read_text(encoding="utf-8"))
            )
        cards.append(
            {
                "id": frontmatter["id"],
                "type": frontmatter["type"],
                "title": frontmatter["title"],
                "aliases": frontmatter.get("aliases", []),
                "status": frontmatter["status"],
                "usage_scope": frontmatter["usage_scope"],
                "tags": frontmatter.get("tags", []),
                "path": relative_path,
                "raw_partitions": frontmatter.get("raw_partitions", []),
                "evidence_refs": frontmatter.get("evidence_refs", []),
                "review_refs": frontmatter.get("review_refs", []),
                "frontmatter": frontmatter,
                "body_excerpt": body[:500],
                "body_markdown": body,
            }
        )

    cards.sort(key=lambda item: (item["type"], item["id"]))
    generated_at = datetime.now(timezone.utc).isoformat()
    partition_summaries = summaries_to_json(scan_all_partitions(paths))
    interface_revision = _interface_revision(cards, partition_summaries)
    context_state = _invalidate_contexts(paths, interface_revision)
    links = _build_links(cards)
    search_index = _build_search_index(cards)
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for card in cards:
        by_type[card["type"]].append(card)

    _write_json(paths.generated_dir / "indexes" / "cards.json", cards)
    _write_json(paths.generated_dir / "indexes" / "links.json", links)
    _write_json(paths.generated_dir / "indexes" / "search_index.json", search_index)

    cards_dir = paths.generated_dir / "agent-interface" / "cards"
    for card_type in sorted(PROFILE["card_types"]):
        _write_json(cards_dir / f"{card_type}.json", by_type.get(card_type, []))

    counts_by_type = Counter(card["type"] for card in cards)
    counts_by_status = Counter(card["status"] for card in cards)
    complete_counts_by_type = {card_type: counts_by_type.get(card_type, 0) for card_type in sorted(PROFILE["card_types"])}
    complete_counts_by_status = {
        status: counts_by_status.get(status, 0) for status in sorted(PROFILE["card_statuses"])
    }
    partition_totals = _partition_totals(partition_summaries)
    manifest_summary = {
        "generated_at": generated_at,
        "interface_revision": interface_revision,
        "card_count": len(cards),
        "counts_by_type": complete_counts_by_type,
        "counts_by_status": complete_counts_by_status,
        "partition_totals": partition_totals,
        "open_review_count": _open_review_count(cards),
        "validation_error_count": len(validation_errors),
    }
    _write_json(paths.generated_dir / "agent-interface" / "manifest_summary.json", manifest_summary)
    _write_json(
        paths.generated_dir / "agent-interface" / "manifest.json",
        {
            "schema_version": "2.0",
            "generated_at": generated_at,
            "interface_revision": interface_revision,
            "cards": "cards/",
            "contexts": "contexts/",
            "indexes": "../indexes/",
            "reports": "../reports/",
            "manifest_summary": "manifest_summary.json",
            "card_types": sorted(PROFILE["card_types"]),
            "partitions": partition_summaries,
            "partition_totals": partition_totals,
            "context_state": context_state,
            "capabilities": [
                "knowledge_status",
                "read_cards_by_type",
                "search",
                "evidence_lookup",
                "review_queue",
                "task_context",
                "video_profile_catalog",
                "video_profile_detail",
                "visual_vector_index_unavailable",
                "codex_visual_rerank_available",
            ],
        },
    )
    _write_video_profile_interface(
        paths,
        video_profiles,
        interface_revision,
        generated_at,
    )
    _write_build_report(paths, manifest_summary, validation_errors)
    _write_review_report(paths, cards, generated_at)
    return manifest_summary


def _build_links(cards: list[dict[str, Any]]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for card in cards:
        for evidence_ref in card.get("evidence_refs", []):
            links.append({"source": card["id"], "target": evidence_ref, "type": "evidence"})
        for review_ref in card.get("review_refs", []):
            links.append({"source": card["id"], "target": review_ref, "type": "review"})
    return links


def _build_search_index(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index = []
    for card in cards:
        frontmatter = card.get("frontmatter", {})
        text_parts = [
            card["title"],
            *card.get("aliases", []),
            *card.get("tags", []),
            *frontmatter.get("raw_partitions", []),
            *frontmatter.get("evidence_refs", []),
            *frontmatter.get("review_refs", []),
            *frontmatter.get("related_products", []),
            *frontmatter.get("source_paths", []),
            *frontmatter.get("affected_cards", []),
        ]
        index.append(
            {
                "id": card["id"],
                "type": card["type"],
                "title": card["title"],
                "status": card["status"],
                "usage_scope": card["usage_scope"],
                "path": card["path"],
                "evidence_refs": card.get("evidence_refs", []),
                "review_refs": card.get("review_refs", []),
                "text": " ".join(str(part) for part in text_parts if part),
            }
        )
    return index


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_build_report(paths: ProjectPaths, manifest_summary: dict[str, Any], validation_errors: list[dict[str, Any]]) -> None:
    lines = [
        "# BUILD_REPORT",
        "",
        f"- generated_at: {manifest_summary['generated_at']}",
        f"- card_count: {manifest_summary['card_count']}",
        f"- validation_error_count: {manifest_summary['validation_error_count']}",
        "",
        "## Counts By Type",
        "",
    ]
    for card_type, count in manifest_summary["counts_by_type"].items():
        lines.append(f"- {card_type}: {count}")
    lines.extend(["", "## Partition Totals", ""])
    for key, value in manifest_summary["partition_totals"].items():
        lines.append(f"- {key}: {value}")
    if validation_errors:
        lines.extend(["", "## Validation Errors", ""])
        for item in validation_errors:
            lines.append(f"- {item['path']}: {'; '.join(item['errors'])}")
    report_path = paths.generated_dir / "reports" / "BUILD_REPORT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_review_report(paths: ProjectPaths, cards: list[dict[str, Any]], generated_at: str) -> None:
    open_reviews = [
        card
        for card in cards
        if card["type"] == "review_item" and card["status"] not in {"archived"}
    ]
    lines = [
        "# REVIEW_REPORT",
        "",
        f"- generated_at: {generated_at}",
        f"- open_review_count: {len(open_reviews)}",
        "",
        "## Open Reviews",
        "",
    ]
    if not open_reviews:
        lines.append("- none")
    for card in open_reviews:
        frontmatter = card.get("frontmatter", {})
        lines.append(f"- {card['id']}: {card['title']}")
        lines.append(f"  - reason: {frontmatter.get('review_reason', '')}")
        lines.append(f"  - affected_cards: {', '.join(frontmatter.get('affected_cards', []))}")
    report_path = paths.generated_dir / "reports" / "REVIEW_REPORT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _card_body(card_path: Path) -> str:
    text = card_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    closing_index = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    return "\n".join(lines[closing_index + 1 :]).strip()


def _partition_totals(partitions: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "pending_material_count": sum(item["pending_material_count"] for item in partitions),
        "pending_processing_count": sum(item.get("pending_processing_count", 0) for item in partitions),
        "product_pending_registration_count": sum(item.get("product_pending_registration_count", 0) for item in partitions),
        "product_pending_subfolder_count": sum(item.get("product_pending_subfolder_count", 0) for item in partitions),
        "pdf_pending_count": sum(item.get("pdf_pending_count", 0) for item in partitions),
        "video_pending_count": sum(item.get("video_pending_count", 0) for item in partitions),
        "recognized_unapplied_count": sum(item["recognized_unapplied_count"] for item in partitions),
        "review_item_count": sum(item["review_item_count"] for item in partitions),
        "needs_update_count": sum(1 for item in partitions if item["status"] == "needs_update"),
        "not_started_count": sum(1 for item in partitions if item["status"] == "not_started"),
    }


def _open_review_count(cards: list[dict[str, Any]]) -> int:
    return sum(1 for card in cards if card["type"] == "review_item" and card["status"] != "archived")


def _interface_revision(cards: list[dict[str, Any]], partition_summaries: list[dict[str, Any]]) -> str:
    payload = {
        "cards": [
            {
                "id": card["id"],
                "status": card["status"],
                "usage_scope": card["usage_scope"],
                "updated_at": card["frontmatter"].get("updated_at"),
                "tags": card.get("tags", []),
                "review_refs": card.get("review_refs", []),
                "evidence_refs": card.get("evidence_refs", []),
                "profile_revision": card["frontmatter"].get("profile_revision"),
                "content_digest": card["frontmatter"].get("content_digest"),
            }
            for card in cards
        ],
        "partitions": [
            {
                "slug": item["slug"],
                "status": item["status"],
                "fingerprint": item["fingerprint"],
                "review_item_count": item["review_item_count"],
                "recognized_unapplied_count": item["recognized_unapplied_count"],
                "product_material_status": item.get("product_material_status"),
                "product_pending_registration_count": item.get("product_pending_registration_count"),
                "product_pending_subfolder_count": item.get("product_pending_subfolder_count"),
            }
            for item in partition_summaries
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_video_profile_interface(
    paths: ProjectPaths,
    profiles: list[dict[str, Any]],
    interface_revision: str,
    generated_at: str,
) -> None:
    root = paths.generated_dir / "agent-interface" / "video-profiles"
    details_dir = root / "details"
    details_dir.mkdir(parents=True, exist_ok=True)
    for stale in details_dir.glob("*.json"):
        stale.unlink()
    catalog = []
    private_media = []
    registry_available, active_source_revisions = (
        _active_video_source_revisions(paths)
    )
    for profile in sorted(profiles, key=lambda item: str(item.get("profile_id") or "")):
        if profile.get("processing_state") == "revoked":
            continue
        if registry_available and active_source_revisions.get(
            str(profile.get("video_asset_id") or "")
        ) != profile.get("source_revision"):
            continue
        profile_revision = str(profile["profile_revision"])
        representative_refs = []
        detail_frames = []
        for index, frame in enumerate(profile.get("representative_frames", []), start=1):
            media_ref = f"video-profile-media://{profile_revision}/{index:02d}"
            generated_ref = str(frame.get("generated_ref") or "")
            media_path = (paths.generated_dir / generated_ref).resolve()
            try:
                normalized_ref = media_path.relative_to(paths.generated_dir.resolve())
            except ValueError as exc:
                raise ValueError("formal video profile media escapes generated_dir") from exc
            if not media_path.is_file():
                raise FileNotFoundError(media_path)
            representative_refs.append(
                {
                    "media_ref": media_ref,
                    "timestamp_seconds": frame["timestamp_seconds"],
                    "description": frame.get("description", ""),
                }
            )
            detail_frames.append(
                {
                    **{
                        key: value
                        for key, value in frame.items()
                        if key != "generated_ref"
                    },
                    "media_ref": media_ref,
                    "content_fingerprint": _file_sha256(media_path),
                }
            )
            private_media.append(
                {
                    "profile_id": profile["profile_id"],
                    "profile_revision": profile_revision,
                    "media_ref": media_ref,
                    "generated_ref": normalized_ref.as_posix(),
                    "content_fingerprint": _file_sha256(media_path),
                }
            )
        detail = {
            **profile,
            "transcript_detail": redact_transcript_for_downstream(
                dict(profile.get("transcript_detail") or {})
            ),
            "representative_frames": detail_frames,
            "interface_revision": interface_revision,
            "interface_state": "formal_active",
        }
        asset_id = str(profile["video_asset_id"])
        _write_json(details_dir / f"{asset_id}.json", detail)
        catalog.append(
            {
                "profile_id": profile["profile_id"],
                "video_asset_id": asset_id,
                "product_id": profile["product_id"],
                "profile_revision": profile_revision,
                "title": profile["title"],
                "summary": profile["summary"],
                "source_classification": profile["source_classification"],
                "observed_classifications": profile["observed_classifications"],
                "use_capabilities": profile["use_capabilities"],
                "product_visibility": profile["product_visibility"],
                "reuse_modes": sorted(
                    {
                        str(segment.get("reuse_mode"))
                        for segment in profile.get("key_segments", [])
                        if segment.get("reuse_mode")
                        and segment.get("use_exclusion", {}).get("status")
                        != "excluded"
                    }
                ),
                "risk_summary": profile["risk_summary"],
                "processing_state": profile["processing_state"],
                "representative_frames": representative_refs,
                "audio_summary": build_downstream_audio_summary(profile),
                "test_summary": build_downstream_test_summary(profile),
            }
        )
    _write_json(root / "catalog.json", catalog)
    _write_json(
        root / "manifest.json",
        {
            "schema_version": "video-profile-interface-v1",
            "interface_revision": interface_revision,
            "generated_at": generated_at,
            "state": "formal_active",
            "catalog": "catalog.json",
            "details": "details/",
            "capabilities": [
                "video_profile_catalog",
                "video_profile_detail",
                "visual_vector_index_unavailable",
                "codex_visual_rerank_available",
            ],
        },
    )
    _write_json(
        paths.generated_dir
        / "cache"
        / "video-profile-interface"
        / "media-index.json",
        {
            "schema_version": "video-profile-private-media-index-v1",
            "interface_revision": interface_revision,
            "media": private_media,
        },
    )


def _active_video_source_revisions(
    paths: ProjectPaths,
) -> tuple[bool, dict[str, str]]:
    registry_path = (
        paths.generated_dir / "cache" / "video-assets" / "registry.json"
    )
    if not registry_path.is_file():
        return False, {}
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    return True, {
        str(item.get("asset_id")): str(item.get("source_fingerprint"))
        for item in registry.get("assets", [])
        if item.get("asset_id") and item.get("source_fingerprint")
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _invalidate_contexts(paths: ProjectPaths, interface_revision: str) -> dict[str, Any]:
    contexts_dir = paths.generated_dir / "agent-interface" / "contexts"
    contexts_dir.mkdir(parents=True, exist_ok=True)
    invalidated = []
    for context_path in sorted(contexts_dir.glob("*.json")):
        if context_path.name == "_context_state.json":
            continue
        try:
            context = json.loads(context_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if context.get("interface_revision") != interface_revision and context.get("valid") is not False:
            context["valid"] = False
            context["invalidated_at"] = datetime.now(timezone.utc).isoformat()
            context["invalidated_reason"] = "agent interface revision changed"
            context_path.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
            invalidated.append(context_path.name)
    state = {
        "interface_revision": interface_revision,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "invalidated_contexts": invalidated,
    }
    _write_json(contexts_dir / "_context_state.json", state)
    return state

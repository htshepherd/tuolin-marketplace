from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import uuid

from ..shared.project_layout import ProjectPaths


PROTECTED_CACHE_STATES = {
    "disputed",
    "failed",
    "review_required",
}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
VIDEO_ASSET_REGISTRY_SCHEMA_VERSION = "1.1"


class ReanalysisRequired(RuntimeError):
    pass


def write_video_cache_manifest(
    paths: ProjectPaths,
    entries: list[dict] | tuple[dict, ...],
) -> Path:
    normalized = [
        _normalize_cache_entry(paths, dict(entry))
        for entry in entries
    ]
    manifest_path = _cache_manifest_path(paths)
    _write_json_atomic(
        manifest_path,
        {
            "schema_version": "video-cache-manifest-v1",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "entries": normalized,
        },
    )
    return manifest_path


def register_video_cache_entry(
    paths: ProjectPaths,
    cache_path: Path,
    *,
    kind: str,
    state: str,
    last_used_at: str,
    profile_revision: str | None = None,
) -> Path:
    source = cache_path.expanduser().resolve()
    entry = _normalize_cache_entry(
        paths,
        {
            "cache_ref": str(source),
            "kind": kind,
            "state": state,
            "last_used_at": last_used_at,
            **(
                {"profile_revision": profile_revision}
                if profile_revision
                else {}
            ),
        },
    )
    manifest_path = _cache_manifest_path(paths)
    entries: list[dict] = []
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = [
            dict(item)
            for item in manifest.get("entries", [])
            if item.get("cache_ref") != entry["cache_ref"]
        ]
    entries.append(entry)
    return write_video_cache_manifest(paths, entries)


def reconcile_video_asset_identity(
    video_path: Path,
    paths: ProjectPaths,
    *,
    product_id: str,
) -> dict:
    source = video_path.expanduser().resolve()
    try:
        source.relative_to(paths.raw_dir.resolve())
    except ValueError as exc:
        raise ValueError("video asset source must stay under raw") from exc
    if not source.is_file() or source.suffix.lower() not in VIDEO_SUFFIXES:
        raise FileNotFoundError(source)
    relative = source.relative_to(paths.raw_dir.resolve()).as_posix()
    registry_path = _video_asset_registry_path(paths)
    if registry_path.is_file():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    else:
        registry = {
            "schema_version": VIDEO_ASSET_REGISTRY_SCHEMA_VERSION,
            "assets": [],
        }
    assets = registry.setdefault("assets", [])
    same_path = [
        item
        for item in assets
        if item.get("product_id") == product_id
        and item.get("source_relative_path") == relative
    ]
    if same_path:
        current = same_path[-1]
        if _verified_quick_signature_matches(current, source):
            return {
                "status": "unchanged",
                **current,
                "registry_path": registry_path,
            }
        fingerprint, signature = _sha256_with_stable_signature(source)
        if current.get("source_fingerprint") == fingerprint:
            _record_verified_quick_signature(current, signature)
            _write_json_atomic(registry_path, registry)
            return {
                "status": "unchanged",
                **current,
                "registry_path": registry_path,
            }
        prior_revision = str(current.get("source_fingerprint") or "")
        history = list(current.get("source_revision_history") or [])
        if prior_revision and prior_revision not in history:
            history.append(prior_revision)
        current["source_fingerprint"] = fingerprint
        current["source_revision_history"] = history
        _record_verified_quick_signature(current, signature)
        current["source_revised_at"] = datetime.now(
            timezone.utc
        ).isoformat()
        _write_json_atomic(registry_path, registry)
        return {
            "status": "source_revised",
            **current,
            "prior_source_revision": prior_revision,
            "registry_path": registry_path,
        }

    fingerprint, signature = _sha256_with_stable_signature(source)
    exact_matches = [
        item
        for item in assets
        if item.get("product_id") == product_id
        and item.get("source_fingerprint") == fingerprint
    ]
    existing_matches = [
        item
        for item in exact_matches
        if (paths.raw_dir / str(item["source_relative_path"])).is_file()
    ]
    missing_matches = [
        item for item in exact_matches if item not in existing_matches
    ]
    if len(exact_matches) == 1 and len(missing_matches) == 1:
        moved = missing_matches[0]
        prior_path = str(moved["source_relative_path"])
        moved["source_relative_path"] = relative
        moved["moved_from"] = prior_path
        moved["moved_at"] = datetime.now(timezone.utc).isoformat()
        _record_verified_quick_signature(moved, signature)
        _write_json_atomic(registry_path, registry)
        return {
            "status": "verified_move",
            **moved,
            "registry_path": registry_path,
        }
    if missing_matches:
        return {
            "status": "review_required",
            "reason": "ambiguous_move_or_copy",
            "source_relative_path": relative,
            "source_fingerprint": fingerprint,
            "candidate_asset_ids": sorted(
                str(item.get("asset_id")) for item in exact_matches
            ),
            "registry_path": registry_path,
        }

    asset_id = f"video_asset_{uuid.uuid4().hex}"
    item = {
        "asset_id": asset_id,
        "product_id": product_id,
        "source_relative_path": relative,
        "source_fingerprint": fingerprint,
        **signature,
        "source_identity_state": "verified",
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    status = "registered"
    if existing_matches:
        family_id = next(
            (
                str(candidate.get("asset_family_id"))
                for candidate in existing_matches
                if candidate.get("asset_family_id")
            ),
            f"video_asset_family_{uuid.uuid4().hex}",
        )
        for candidate in existing_matches:
            candidate["asset_family_id"] = family_id
        item["asset_family_id"] = family_id
        item["duplicate_of_asset_ids"] = sorted(
            str(candidate["asset_id"]) for candidate in existing_matches
        )
        status = "concurrent_copy"
    assets.append(item)
    _write_json_atomic(registry_path, registry)
    return {
        "status": status,
        **item,
        "registry_path": registry_path,
    }


def migrate_video_asset_registry_quick_signatures(
    paths: ProjectPaths,
) -> dict:
    """Upgrade legacy video hashes once without making routine scans read media."""
    registry_path = _video_asset_registry_path(paths)
    if not registry_path.is_file():
        return {
            "status": "no_registry",
            "verified_count": 0,
            "changed_count": 0,
            "missing_count": 0,
            "registry_path": registry_path,
        }
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("schema_version") == VIDEO_ASSET_REGISTRY_SCHEMA_VERSION:
        return {
            "status": "already_current",
            "verified_count": 0,
            "changed_count": 0,
            "missing_count": 0,
            "registry_path": registry_path,
        }

    verified_count = 0
    changed_count = 0
    missing_count = 0
    raw_root = paths.raw_dir.resolve()
    for item in registry.setdefault("assets", []):
        relative = str(item.get("source_relative_path") or "")
        source = (paths.raw_dir / relative).resolve()
        try:
            source.relative_to(raw_root)
        except ValueError:
            item["source_identity_state"] = "invalid_path"
            missing_count += 1
            continue
        if not source.is_file():
            item["source_identity_state"] = "missing"
            missing_count += 1
            continue

        fingerprint, signature = _sha256_with_stable_signature(source)
        if fingerprint == item.get("source_fingerprint"):
            _record_verified_quick_signature(item, signature)
            verified_count += 1
            continue
        item["source_identity_state"] = "source_changed"
        item["observed_source_size_bytes"] = signature["source_size_bytes"]
        item["observed_source_mtime_ns"] = signature["source_mtime_ns"]
        item["source_change_detected_at"] = datetime.now(
            timezone.utc
        ).isoformat()
        changed_count += 1

    registry["schema_version"] = VIDEO_ASSET_REGISTRY_SCHEMA_VERSION
    registry["quick_signature_migrated_at"] = datetime.now(
        timezone.utc
    ).isoformat()
    _write_json_atomic(registry_path, registry)
    return {
        "status": "migrated",
        "verified_count": verified_count,
        "changed_count": changed_count,
        "missing_count": missing_count,
        "registry_path": registry_path,
    }


def verified_video_source_revisions(
    paths: ProjectPaths,
) -> tuple[bool, dict[str, str]]:
    """Return only registry revisions whose local files match cached metadata."""
    registry_path = _video_asset_registry_path(paths)
    if not registry_path.is_file():
        return False, {}
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    revisions: dict[str, str] = {}
    raw_root = paths.raw_dir.resolve()
    for item in registry.get("assets", []):
        asset_id = str(item.get("asset_id") or "")
        fingerprint = str(item.get("source_fingerprint") or "")
        relative = str(item.get("source_relative_path") or "")
        if not asset_id or not fingerprint:
            continue
        source = (paths.raw_dir / relative).resolve()
        try:
            source.relative_to(raw_root)
        except ValueError:
            continue
        if source.is_file() and _verified_quick_signature_matches(item, source):
            revisions[asset_id] = fingerprint
    return True, revisions


def migrate_video_profile_schema(
    profile: dict,
    *,
    target_schema_version: str,
    required_new_semantic_fields: list[str] | tuple[str, ...] = (),
) -> dict:
    target = target_schema_version.strip()
    if not target:
        raise ValueError("target video profile schema version is required")
    semantic_fields = sorted(
        {
            str(field).strip()
            for field in required_new_semantic_fields
            if str(field).strip()
        }
    )
    if semantic_fields:
        raise ReanalysisRequired(
            "video profile schema migration requires reanalysis for semantic fields: "
            + ", ".join(semantic_fields)
        )
    migrated = deepcopy(profile)
    prior = str(migrated.get("schema_version") or "")
    if prior == target:
        return migrated
    migrated["schema_version"] = target
    migrated.setdefault("schema_migrations", []).append(
        {
            "from": prior,
            "to": target,
            "kind": "deterministic_structure_only",
            "migrated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return migrated


def cleanup_video_profile_cache(
    paths: ProjectPaths,
    *,
    now: datetime | None = None,
    retention_days: int = 30,
) -> dict:
    if retention_days < 1:
        raise ValueError("video cache retention must be at least one day")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("cache cleanup time must include a timezone")
    manifest_path = _cache_manifest_path(paths)
    if not manifest_path.is_file():
        return {
            "status": "no_manifest",
            "deleted_refs": [],
            "retained_refs": [],
            "manifest_path": manifest_path,
        }
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "video-cache-manifest-v1":
        raise ValueError("unsupported video cache manifest schema")
    cutoff = current - timedelta(days=retention_days)
    live_refs = _live_video_cache_refs(paths)
    deleted: list[str] = []
    retained: list[str] = []
    updated_entries: list[dict] = []
    for raw_entry in manifest.get("entries", []):
        entry = _normalize_cache_entry(paths, dict(raw_entry))
        cache_ref = entry["cache_ref"]
        cache_path = (paths.generated_dir / cache_ref).resolve()
        last_used = _parse_datetime(entry["last_used_at"])
        if entry.get("state") == "deleted":
            continue
        if (
            cache_ref in live_refs
            or entry.get("state") in PROTECTED_CACHE_STATES
        ):
            retained.append(cache_ref)
        elif last_used < cutoff:
            if cache_path.is_file():
                cache_path.unlink()
            entry["state"] = "deleted"
            entry["deleted_at"] = current.isoformat()
            deleted.append(cache_ref)
        else:
            retained.append(cache_ref)
        updated_entries.append(entry)
    _write_json_atomic(
        manifest_path,
        {
            **manifest,
            "updated_at": current.isoformat(),
            "entries": updated_entries,
        },
    )
    return {
        "status": "cleaned",
        "deleted_refs": deleted,
        "retained_refs": retained,
        "manifest_path": manifest_path,
    }


def _live_video_cache_refs(paths: ProjectPaths) -> set[str]:
    refs: set[str] = set()
    registry_path = (
        paths.generated_dir / "cache" / "video-assets" / "registry.json"
    )
    registry_available = registry_path.is_file()
    active_revisions: dict[str, str] = {}
    if registry_available:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        active_revisions = {
            str(item.get("asset_id")): str(
                item.get("source_fingerprint")
            )
            for item in registry.get("assets", [])
            if item.get("asset_id") and item.get("source_fingerprint")
        }
    profile_root = paths.knowledge_dir / "视频档案"
    if profile_root.is_dir():
        for profile_path in profile_root.rglob("*.json"):
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            if profile.get("processing_state") == "revoked":
                continue
            if registry_available and active_revisions.get(
                str(profile.get("video_asset_id") or "")
            ) != profile.get("source_revision"):
                continue
            for frame in profile.get("representative_frames", []):
                ref = str(frame.get("generated_ref") or "").strip()
                if ref:
                    refs.add(ref)
    media_index_path = (
        paths.generated_dir
        / "cache"
        / "video-profile-interface"
        / "media-index.json"
    )
    if media_index_path.is_file():
        media_index = json.loads(
            media_index_path.read_text(encoding="utf-8")
        )
        for item in media_index.get("media", []):
            ref = str(item.get("generated_ref") or "").strip()
            if ref:
                refs.add(ref)
    return refs


def _normalize_cache_entry(paths: ProjectPaths, entry: dict) -> dict:
    cache_ref = str(entry.get("cache_ref") or "").strip()
    if not cache_ref:
        raise ValueError("video cache entry is missing cache_ref")
    cache_path = (paths.generated_dir / cache_ref).resolve()
    cache_root = (paths.generated_dir / "cache").resolve()
    try:
        cache_path.relative_to(cache_root)
    except ValueError as exc:
        raise ValueError(
            "video cache entries must stay under generated/cache"
        ) from exc
    if not str(entry.get("kind") or "").strip():
        raise ValueError("video cache entry is missing kind")
    if not str(entry.get("state") or "").strip():
        raise ValueError("video cache entry is missing state")
    _parse_datetime(str(entry.get("last_used_at") or ""))
    return {
        **entry,
        "cache_ref": cache_path.relative_to(
            paths.generated_dir.resolve()
        ).as_posix(),
    }


def _cache_manifest_path(paths: ProjectPaths) -> Path:
    return (
        paths.generated_dir
        / "cache"
        / "video-profile-maintenance"
        / "manifest.json"
    )


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("video cache timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise ValueError("video cache timestamp must include a timezone")
    return parsed


def _video_asset_registry_path(paths: ProjectPaths) -> Path:
    return paths.generated_dir / "cache" / "video-assets" / "registry.json"


def _quick_signature(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {
        "source_size_bytes": stat.st_size,
        "source_mtime_ns": stat.st_mtime_ns,
    }


def _verified_quick_signature_matches(item: dict, path: Path) -> bool:
    if item.get("source_identity_state") != "verified":
        return False
    signature = _quick_signature(path)
    return (
        item.get("source_size_bytes") == signature["source_size_bytes"]
        and item.get("source_mtime_ns") == signature["source_mtime_ns"]
        and bool(item.get("source_fingerprint"))
    )


def _record_verified_quick_signature(
    item: dict,
    signature: dict[str, int],
) -> None:
    item["source_size_bytes"] = signature["source_size_bytes"]
    item["source_mtime_ns"] = signature["source_mtime_ns"]
    item["source_identity_state"] = "verified"
    for key in (
        "observed_source_size_bytes",
        "observed_source_mtime_ns",
        "source_change_detected_at",
    ):
        item.pop(key, None)


def _sha256_with_stable_signature(path: Path) -> tuple[str, dict[str, int]]:
    before = _quick_signature(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    after = _quick_signature(path)
    if before != after:
        raise RuntimeError("video source changed while its fingerprint was being calculated")
    return digest.hexdigest(), after


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)

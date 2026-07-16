from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..shared.project_layout import ProjectPaths
from .video_audio_policy import (
    build_downstream_audio_summary,
    redact_transcript_for_downstream,
)
from .video_test_evidence import (
    build_downstream_test_summary,
    validate_test_video_trim,
)


@dataclass(frozen=True)
class VideoProfileInterfaceActivation:
    status: str
    interface_revision: str
    catalog_path: Path
    detail_path: Path


@dataclass(frozen=True)
class VideoProfileRunAuthorization:
    status: str
    run_id: str
    profile_id: str
    interface_revision: str
    authorization_path: Path


@dataclass(frozen=True)
class RuntimeVideoFrameExtraction:
    status: str
    run_id: str
    asset_id: str
    profile_revision: str
    segment_id: str
    timestamp_seconds: float
    frame_path: Path


@dataclass(frozen=True)
class RuntimeVideoClipExtraction:
    status: str
    run_id: str
    asset_id: str
    profile_revision: str
    segment_id: str
    planned_use_id: str
    start_seconds: float
    end_seconds: float
    output_kind: str
    adaptations: dict
    audio_policy: str
    clip_path: Path


def activate_tracer_video_profile_interface(
    staged_profile_path: Path,
    paths: ProjectPaths,
) -> VideoProfileInterfaceActivation:
    source = staged_profile_path.expanduser().resolve()
    staging_root = (
        paths.generated_dir / "staging" / "video-profiles"
    ).resolve()
    try:
        source.relative_to(staging_root)
    except ValueError as exc:
        raise ValueError(f"tracer profile must be under video profile staging: {source}") from exc
    if not source.is_file() or source.suffix.lower() != ".json":
        raise FileNotFoundError(source)
    profile = json.loads(source.read_text(encoding="utf-8"))
    _validate_tracer_profile(profile)
    private_media_index = _build_private_media_index(profile, paths)

    revision_source = (
        f"{profile['profile_id']}:{profile['profile_revision']}:{profile['content_digest']}"
    ).encode("utf-8")
    interface_revision = "video_interface_" + hashlib.sha256(revision_source).hexdigest()[:16]
    root = paths.generated_dir / "agent-interface" / "video-profiles"
    details_dir = root / "details"
    details_dir.mkdir(parents=True, exist_ok=True)
    detail_path = details_dir / f"{profile['video_asset_id']}.json"
    catalog_path = root / "catalog.json"

    representative_refs = [
        {
            "media_ref": (
                f"video-profile-media://{profile['profile_revision']}/"
                f"{index:02d}"
            ),
            "timestamp_seconds": frame["timestamp_seconds"],
            "description": frame.get("description", ""),
        }
        for index, frame in enumerate(profile.get("representative_frames", []), start=1)
    ]
    detail = {
        **profile,
        "transcript_detail": redact_transcript_for_downstream(
            dict(profile.get("transcript_detail") or {})
        ),
        "representative_frames": [
            {
                **{
                    key: value
                    for key, value in frame.items()
                    if key != "generated_ref"
                },
                "media_ref": representative_refs[index]["media_ref"],
            }
            for index, frame in enumerate(profile.get("representative_frames", []))
        ],
        "interface_revision": interface_revision,
        "interface_state": "tracer_active",
    }
    catalog_entry = {
        "profile_id": profile["profile_id"],
        "video_asset_id": profile["video_asset_id"],
        "product_id": profile["product_id"],
        "profile_revision": profile["profile_revision"],
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
    _write_json(detail_path, detail)
    _write_json(catalog_path, [catalog_entry])
    _write_json(
        paths.generated_dir
        / "cache"
        / "video-profile-interface"
        / "media-index.json",
        private_media_index,
    )
    _write_json(
        root / "manifest.json",
        {
            "schema_version": "video-profile-interface-v1",
            "interface_revision": interface_revision,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "state": "tracer_active",
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
    return VideoProfileInterfaceActivation(
        status="active",
        interface_revision=interface_revision,
        catalog_path=catalog_path,
        detail_path=detail_path,
    )


def read_video_profile_catalog(paths: ProjectPaths) -> list[dict]:
    path = paths.generated_dir / "agent-interface" / "video-profiles" / "catalog.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"invalid video profile catalog: {path}")
    return data


def search_video_profile_catalog(
    paths: ProjectPaths,
    *,
    query: str = "",
    product_id: str | None = None,
    source_classifications: tuple[str, ...] | list[str] = (),
    observed_classifications: tuple[str, ...] | list[str] = (),
    use_capabilities: tuple[str, ...] | list[str] = (),
) -> list[dict]:
    required_source = set(source_classifications)
    required_observed = set(observed_classifications)
    required_capabilities = set(use_capabilities)
    terms = [item.casefold() for item in query.split() if item.strip()]
    ranked: list[tuple[int, str, dict]] = []
    for entry in read_video_profile_catalog(paths):
        if product_id is not None and entry.get("product_id") != product_id:
            continue
        if not required_source.issubset(set(entry.get("source_classification", []))):
            continue
        if not required_observed.issubset(set(entry.get("observed_classifications", []))):
            continue
        if not required_capabilities.issubset(set(entry.get("use_capabilities", []))):
            continue
        searchable = " ".join(
            str(value)
            for value in (
                entry.get("title", ""),
                entry.get("summary", ""),
                *entry.get("source_classification", []),
                *entry.get("observed_classifications", []),
                *entry.get("use_capabilities", []),
                *entry.get("risk_summary", []),
            )
        ).casefold()
        if terms and not all(term in searchable for term in terms):
            continue
        score = sum(searchable.count(term) for term in terms)
        ranked.append((score, str(entry.get("profile_id", "")), entry))
    return [
        entry
        for _score, _profile_id, entry in sorted(
            ranked,
            key=lambda item: (-item[0], item[1]),
        )
    ]


def read_video_profile_interface_status(paths: ProjectPaths) -> dict:
    return _read_video_interface_manifest(paths)


def read_video_profile_detail(paths: ProjectPaths, profile_id: str) -> dict:
    catalog = read_video_profile_catalog(paths)
    entry = next(
        (item for item in catalog if item.get("profile_id") == profile_id),
        None,
    )
    if entry is None:
        raise KeyError(f"video profile not found: {profile_id}")
    asset_id = str(entry.get("video_asset_id") or "")
    path = (
        paths.generated_dir
        / "agent-interface"
        / "video-profiles"
        / "details"
        / f"{asset_id}.json"
    )
    if not path.is_file():
        raise FileNotFoundError(path)
    detail = json.loads(path.read_text(encoding="utf-8"))
    if detail.get("profile_id") != profile_id:
        raise ValueError(f"video profile detail identity mismatch: {path}")
    if detail.get("profile_revision") != entry.get("profile_revision"):
        raise ValueError(f"video profile detail revision mismatch: {path}")
    return detail


def resolve_video_profile_media(
    paths: ProjectPaths,
    profile_id: str,
    media_ref: str,
) -> Path:
    detail = read_video_profile_detail(paths, profile_id)
    allowed_refs = {
        str(frame.get("media_ref") or "")
        for frame in detail.get("representative_frames", [])
    }
    if media_ref not in allowed_refs:
        raise PermissionError("representative media is not part of the active video profile")
    index_path = (
        paths.generated_dir
        / "cache"
        / "video-profile-interface"
        / "media-index.json"
    )
    if not index_path.is_file():
        raise FileNotFoundError(index_path)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    item = next(
        (
            candidate
            for candidate in index.get("media", [])
            if candidate.get("media_ref") == media_ref
            and candidate.get("profile_id") == profile_id
            and candidate.get("profile_revision") == detail.get("profile_revision")
        ),
        None,
    )
    if item is None:
        raise PermissionError("representative media revision is not active")
    path = (paths.generated_dir / str(item.get("generated_ref") or "")).resolve()
    try:
        path.relative_to(paths.generated_dir.resolve())
    except ValueError as exc:
        raise PermissionError("representative media mapping escapes generated_dir") from exc
    if not path.is_file():
        raise FileNotFoundError(path)
    if _sha256(path) != item.get("content_fingerprint"):
        raise ValueError("representative media bytes have changed")
    return path


def authorize_video_profile_for_run(
    paths: ProjectPaths,
    run_id: str,
    profile_id: str,
) -> VideoProfileRunAuthorization:
    run_dir = _video_run_dir(paths, run_id)
    if not run_dir.is_dir():
        raise FileNotFoundError(run_dir)
    manifest = _read_video_interface_manifest(paths)
    detail = read_video_profile_detail(paths, profile_id)
    authorization_path = run_dir / "video_profile_authorizations.json"
    authorization = {
        "schema_version": "video-profile-run-authorization-v1",
        "run_id": run_id,
        "interface_revision": manifest["interface_revision"],
        "raw_access": False,
        "authorized_profiles": [
            {
                "profile_id": detail["profile_id"],
                "video_asset_id": detail["video_asset_id"],
                "product_id": detail["product_id"],
                "profile_revision": detail["profile_revision"],
                "source_revision": detail["source_revision"],
                "operations": ["frame", "clip"],
                "revoked": False,
                "segments": [
                    {
                        "segment_id": segment["segment_id"],
                        "start_seconds": segment["start_seconds"],
                        "end_seconds": segment["end_seconds"],
                    }
                    for segment in detail.get("key_segments", [])
                    if segment.get("use_exclusion", {}).get("status")
                    != "excluded"
                ],
            }
        ],
    }
    _write_json(authorization_path, authorization)
    return VideoProfileRunAuthorization(
        status="authorized",
        run_id=run_id,
        profile_id=profile_id,
        interface_revision=manifest["interface_revision"],
        authorization_path=authorization_path,
    )


def extract_runtime_video_frame(
    paths: ProjectPaths,
    *,
    run_id: str,
    interface_revision: str,
    asset_id: str,
    profile_revision: str,
    segment_id: str,
    timestamp_seconds: float,
    ffmpeg_path: str = "ffmpeg",
    runner=subprocess.run,
) -> RuntimeVideoFrameExtraction:
    run_dir = _video_run_dir(paths, run_id)
    if not run_dir.is_dir():
        raise FileNotFoundError(run_dir)
    audit_entry = {
        "attempted_at": datetime.now(timezone.utc).isoformat(),
        "operation": "frame",
        "run_id": run_id,
        "interface_revision": interface_revision,
        "asset_id": asset_id,
        "profile_revision": profile_revision,
        "segment_id": segment_id,
        "timestamp_seconds": float(timestamp_seconds),
    }
    try:
        result = _extract_runtime_video_frame(
            paths,
            run_dir=run_dir,
            run_id=run_id,
            interface_revision=interface_revision,
            asset_id=asset_id,
            profile_revision=profile_revision,
            segment_id=segment_id,
            timestamp_seconds=timestamp_seconds,
            ffmpeg_path=ffmpeg_path,
            runner=runner,
        )
    except Exception as exc:
        _append_runtime_video_audit(
            run_dir,
            {
                **audit_entry,
                "status": "rejected",
                "reason": str(exc),
            },
        )
        raise
    _append_runtime_video_audit(
        run_dir,
        {
            **audit_entry,
            "status": "extracted",
            "output_ref": result.frame_path.relative_to(run_dir).as_posix(),
        },
    )
    return result


def read_runtime_video_audit(paths: ProjectPaths, run_id: str) -> list[dict]:
    run_dir = _video_run_dir(paths, run_id)
    if not run_dir.is_dir():
        raise FileNotFoundError(run_dir)
    path = run_dir / "runtime-video-audit.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"invalid runtime video audit: {path}")
    return data


def extract_runtime_video_clip(
    paths: ProjectPaths,
    *,
    run_id: str,
    interface_revision: str,
    asset_id: str,
    profile_revision: str,
    segment_id: str,
    planned_use_id: str,
    start_seconds: float,
    end_seconds: float,
    output_kind: str,
    adaptations: dict | None = None,
    audio_policy: str = "preserve",
    ffmpeg_path: str = "ffmpeg",
    runner=subprocess.run,
) -> RuntimeVideoClipExtraction:
    run_dir = _video_run_dir(paths, run_id)
    if not run_dir.is_dir():
        raise FileNotFoundError(run_dir)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", planned_use_id):
        raise ValueError("planned_use_id may contain only letters, numbers, underscore, and hyphen")
    start = float(start_seconds)
    end = float(end_seconds)
    audit_entry = {
        "attempted_at": datetime.now(timezone.utc).isoformat(),
        "operation": "clip",
        "run_id": run_id,
        "interface_revision": interface_revision,
        "asset_id": asset_id,
        "profile_revision": profile_revision,
        "segment_id": segment_id,
        "planned_use_id": planned_use_id,
        "start_seconds": start,
        "end_seconds": end,
        "output_kind": output_kind,
    }
    try:
        result = _extract_runtime_video_clip(
            paths,
            run_dir=run_dir,
            run_id=run_id,
            interface_revision=interface_revision,
            asset_id=asset_id,
            profile_revision=profile_revision,
            segment_id=segment_id,
            planned_use_id=planned_use_id,
            start_seconds=start,
            end_seconds=end,
            output_kind=output_kind,
            adaptations=adaptations or {},
            audio_policy=audio_policy,
            ffmpeg_path=ffmpeg_path,
            runner=runner,
        )
    except Exception as exc:
        _append_runtime_video_audit(
            run_dir,
            {
                **audit_entry,
                "status": "rejected",
                "reason": str(exc),
            },
        )
        raise
    _append_runtime_video_audit(
        run_dir,
        {
            **audit_entry,
            "status": "extracted",
            "adaptations": result.adaptations,
            "audio_policy": result.audio_policy,
            "output_ref": result.clip_path.relative_to(run_dir).as_posix(),
        },
    )
    return result


def _extract_runtime_video_clip(
    paths: ProjectPaths,
    *,
    run_dir: Path,
    run_id: str,
    interface_revision: str,
    asset_id: str,
    profile_revision: str,
    segment_id: str,
    planned_use_id: str,
    start_seconds: float,
    end_seconds: float,
    output_kind: str,
    adaptations: dict,
    audio_policy: str,
    ffmpeg_path: str,
    runner,
) -> RuntimeVideoClipExtraction:
    if output_kind not in {"candidate_preview", "task_clip"}:
        raise ValueError("output_kind must be candidate_preview or task_clip")
    normalized_adaptations = _validate_clip_adaptations(adaptations)
    if audio_policy not in {"preserve", "mute_confirmed", "mute_by_profile_policy"}:
        raise ValueError("unsupported runtime clip audio policy")
    if end_seconds <= start_seconds:
        raise ValueError("runtime clip end must be after start")
    if output_kind == "candidate_preview":
        existing = [
            item
            for item in read_runtime_video_audit(paths, run_id)
            if item.get("operation") == "clip"
            and item.get("status") == "extracted"
            and item.get("output_kind") == "candidate_preview"
            and item.get("planned_use_id") == planned_use_id
        ]
        if len(existing) >= 3:
            raise ValueError("a planned use may have at most three candidate previews")

    authorization_path = run_dir / "video_profile_authorizations.json"
    if not authorization_path.is_file():
        raise PermissionError("video run has no profile authorization")
    preliminary_authorization = json.loads(
        authorization_path.read_text(encoding="utf-8")
    )
    preliminary_profile = next(
        (
            item
            for item in preliminary_authorization.get(
                "authorized_profiles",
                [],
            )
            if item.get("video_asset_id") == asset_id
        ),
        None,
    )
    if preliminary_profile is not None and preliminary_profile.get(
        "revoked"
    ):
        raise PermissionError("video asset authorization has been revoked")
    manifest = _read_video_interface_manifest(paths)
    if interface_revision != manifest.get("interface_revision"):
        raise ValueError("video profile interface revision is stale")
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    if authorization.get("interface_revision") != interface_revision:
        raise ValueError("video run authorization is bound to a different interface revision")
    authorized = next(
        (
            item
            for item in authorization.get("authorized_profiles", [])
            if item.get("video_asset_id") == asset_id
        ),
        None,
    )
    if authorized is None or authorized.get("revoked"):
        raise PermissionError("video asset is not authorized for this run")
    if "clip" not in authorized.get("operations", []):
        raise PermissionError("runtime clip extraction is not authorized")
    if authorized.get("profile_revision") != profile_revision:
        raise ValueError("video profile revision is stale")
    segment = next(
        (
            item
            for item in authorized.get("segments", [])
            if item.get("segment_id") == segment_id
        ),
        None,
    )
    if segment is None:
        raise PermissionError("video segment is not authorized for this run")
    if not (
        float(segment["start_seconds"])
        <= start_seconds
        < end_seconds
        <= float(segment["end_seconds"])
    ):
        raise ValueError("runtime clip range is outside the authorized segment")
    detail = read_video_profile_detail(paths, str(authorized["profile_id"]))
    if detail.get("profile_revision") != profile_revision:
        raise ValueError("active video profile revision is stale")
    profile_segment = next(
        (
            item
            for item in detail.get("key_segments", [])
            if item.get("segment_id") == segment_id
        ),
        {},
    )
    test_integrity = dict(profile_segment.get("test_integrity") or {})
    required_test_phases = list(
        test_integrity.get("required_phases") or []
    )
    if required_test_phases:
        validate_test_video_trim(
            required_phases=required_test_phases,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
        )
    required_audio_policy = profile_segment.get(
        "audio_policy",
        detail.get(
            "source_audio_use_policy",
            "human-review-required",
        ),
    )
    if audio_policy == "preserve":
        if required_audio_policy == "mute-required":
            raise PermissionError(
                "original audio is blocked by the active video profile policy"
            )
        if required_audio_policy in {
            "mute-recommended",
            "human-review-required",
        }:
            raise PermissionError(
                "original audio requires review or confirmed muting"
            )
    source = _resolve_authorized_source(paths, authorized)

    sequence = len(
        [
            item
            for item in read_runtime_video_audit(paths, run_id)
            if item.get("operation") == "clip"
            and item.get("status") == "extracted"
            and item.get("output_kind") == output_kind
            and item.get("planned_use_id") == planned_use_id
        ]
    ) + 1
    start_ms = round(start_seconds * 1000)
    end_ms = round(end_seconds * 1000)
    category = "candidates" if output_kind == "candidate_preview" else "tasks"
    clip_path = (
        run_dir
        / "runtime-video-clips"
        / category
        / planned_use_id
        / f"{asset_id}_{segment_id}_{start_ms:010d}_{end_ms:010d}_{sequence:02d}.mp4"
    )
    clip_path.parent.mkdir(parents=True, exist_ok=True)
    filters = _runtime_clip_filters(normalized_adaptations, output_kind)
    command: list[str] = [
        ffmpeg_path,
        "-y",
        "-ss",
        f"{start_seconds:.3f}",
        "-i",
        str(source),
        "-t",
        f"{end_seconds - start_seconds:.3f}",
    ]
    if filters:
        command.extend(["-vf", ",".join(filters)])
    frame_rate = normalized_adaptations.get("frame_rate")
    if frame_rate is not None:
        command.extend(["-r", str(frame_rate)])
    if audio_policy != "preserve":
        command.append("-an")
    command.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast" if output_kind == "candidate_preview" else "medium",
            "-movflags",
            "+faststart",
            str(clip_path),
        ]
    )
    completed = runner(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(
            error or f"runtime clip extraction failed with exit code {completed.returncode}"
        )
    if not clip_path.is_file() or clip_path.stat().st_size == 0:
        raise RuntimeError(f"runtime clip extraction produced no output: {clip_path}")
    return RuntimeVideoClipExtraction(
        status="extracted",
        run_id=run_id,
        asset_id=asset_id,
        profile_revision=profile_revision,
        segment_id=segment_id,
        planned_use_id=planned_use_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        output_kind=output_kind,
        adaptations=normalized_adaptations,
        audio_policy=audio_policy,
        clip_path=clip_path,
    )


def _extract_runtime_video_frame(
    paths: ProjectPaths,
    *,
    run_dir: Path,
    run_id: str,
    interface_revision: str,
    asset_id: str,
    profile_revision: str,
    segment_id: str,
    timestamp_seconds: float,
    ffmpeg_path: str,
    runner,
) -> RuntimeVideoFrameExtraction:
    authorization_path = run_dir / "video_profile_authorizations.json"
    if not authorization_path.is_file():
        raise PermissionError("video run has no profile authorization")
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    authorized = next(
        (
            item
            for item in authorization.get("authorized_profiles", [])
            if item.get("video_asset_id") == asset_id
        ),
        None,
    )
    if authorized is not None and authorized.get("revoked"):
        raise PermissionError("video asset authorization has been revoked")
    manifest = _read_video_interface_manifest(paths)
    if interface_revision != manifest.get("interface_revision"):
        raise ValueError("video profile interface revision is stale")
    if authorization.get("interface_revision") != interface_revision:
        raise ValueError("video run authorization is bound to a different interface revision")
    if authorized is None:
        raise PermissionError("video asset is not authorized for this run")
    if "frame" not in authorized.get("operations", []):
        raise PermissionError("runtime frame extraction is not authorized")
    if authorized.get("profile_revision") != profile_revision:
        raise ValueError("video profile revision is stale")
    segment = next(
        (
            item
            for item in authorized.get("segments", [])
            if item.get("segment_id") == segment_id
        ),
        None,
    )
    if segment is None:
        raise PermissionError("video segment is not authorized for this run")
    timestamp = float(timestamp_seconds)
    if not (
        float(segment["start_seconds"])
        <= timestamp
        <= float(segment["end_seconds"])
    ):
        raise ValueError("runtime frame timestamp is outside the authorized segment")
    detail = read_video_profile_detail(paths, str(authorized["profile_id"]))
    if detail.get("profile_revision") != profile_revision:
        raise ValueError("active video profile revision is stale")
    source = _resolve_authorized_source(paths, authorized)
    milliseconds = round(timestamp * 1000)
    frame_path = (
        run_dir
        / "runtime-video-frames"
        / asset_id
        / f"{segment_id}_{milliseconds:010d}.png"
    )
    frame_path.parent.mkdir(parents=True, exist_ok=True)
    command = (
        ffmpeg_path,
        "-y",
        "-ss",
        f"{timestamp:.3f}",
        "-i",
        str(source),
        "-frames:v",
        "1",
        str(frame_path),
    )
    completed = runner(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(error or f"runtime frame extraction failed with exit code {completed.returncode}")
    if not frame_path.is_file() or frame_path.stat().st_size == 0:
        raise RuntimeError(f"runtime frame extraction produced no output: {frame_path}")
    return RuntimeVideoFrameExtraction(
        status="extracted",
        run_id=run_id,
        asset_id=asset_id,
        profile_revision=profile_revision,
        segment_id=segment_id,
        timestamp_seconds=timestamp,
        frame_path=frame_path,
    )


def _append_runtime_video_audit(run_dir: Path, entry: dict) -> None:
    path = run_dir / "runtime-video-audit.json"
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"invalid runtime video audit: {path}")
    else:
        data = []
    data.append(entry)
    _write_json(path, data)


def _validate_clip_adaptations(adaptations: dict) -> dict:
    allowed = {
        "rotation_degrees",
        "resolution",
        "frame_rate",
        "crop",
        "crop_confirmed",
        "letterbox",
        "letterbox_confirmed",
        "video_codec",
    }
    unsupported = sorted(set(adaptations) - allowed)
    if unsupported:
        raise ValueError(
            "unsupported automatic adaptation: " + ", ".join(unsupported)
        )
    normalized = dict(adaptations)
    rotation = normalized.get("rotation_degrees")
    if rotation is not None and rotation not in {0, 90, 180, 270}:
        raise ValueError("rotation_degrees must be 0, 90, 180, or 270")
    resolution = normalized.get("resolution")
    if resolution is not None and not re.fullmatch(r"[1-9][0-9]{1,4}x[1-9][0-9]{1,4}", str(resolution)):
        raise ValueError("resolution must use WIDTHxHEIGHT")
    frame_rate = normalized.get("frame_rate")
    if frame_rate is not None and not 1 <= int(frame_rate) <= 60:
        raise ValueError("frame_rate must be between 1 and 60")
    if normalized.get("crop") and not normalized.get("crop_confirmed"):
        raise ValueError("crop must be explicitly confirmed")
    if normalized.get("letterbox") and not normalized.get("letterbox_confirmed"):
        raise ValueError("letterbox must be explicitly confirmed")
    codec = normalized.get("video_codec")
    if codec is not None and codec not in {"h264"}:
        raise ValueError("video_codec must be h264")
    return normalized


def _runtime_clip_filters(adaptations: dict, output_kind: str) -> list[str]:
    filters: list[str] = []
    rotation = adaptations.get("rotation_degrees")
    if rotation == 90:
        filters.append("transpose=1")
    elif rotation == 180:
        filters.extend(["hflip", "vflip"])
    elif rotation == 270:
        filters.append("transpose=2")
    crop = adaptations.get("crop")
    if crop:
        filters.append(f"crop={crop}")
    resolution = adaptations.get("resolution")
    if resolution:
        width, height = str(resolution).split("x", 1)
        filters.append(f"scale={width}:{height}")
        if adaptations.get("letterbox"):
            filters.append(f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2")
    elif output_kind == "candidate_preview":
        filters.append("scale=-2:720")
    return filters


def _validate_tracer_profile(profile: dict) -> None:
    required = {
        "profile_id",
        "video_asset_id",
        "product_id",
        "profile_revision",
        "content_digest",
        "title",
        "summary",
        "source_classification",
        "observed_classifications",
        "product_visibility",
        "key_segments",
        "representative_frames",
        "use_capabilities",
        "risk_summary",
        "processing_state",
    }
    missing = sorted(required - set(profile))
    if missing:
        raise ValueError(f"tracer video profile missing fields: {', '.join(missing)}")
    if profile["processing_state"] not in {"review_required", "valid"}:
        raise ValueError("tracer video profile is not interface-readable")


def _build_private_media_index(profile: dict, paths: ProjectPaths) -> dict:
    media: list[dict] = []
    for index, frame in enumerate(profile.get("representative_frames", []), start=1):
        generated_ref = str(frame.get("generated_ref") or "")
        if not generated_ref:
            raise ValueError("representative frame is missing generated_ref")
        path = (paths.generated_dir / generated_ref).resolve()
        try:
            normalized_ref = path.relative_to(paths.generated_dir.resolve())
        except ValueError as exc:
            raise ValueError("representative media must be stored under generated_dir") from exc
        if not path.is_file():
            raise FileNotFoundError(path)
        media.append(
            {
                "profile_id": profile["profile_id"],
                "profile_revision": profile["profile_revision"],
                "media_ref": (
                    f"video-profile-media://{profile['profile_revision']}/"
                    f"{index:02d}"
                ),
                "generated_ref": normalized_ref.as_posix(),
                "content_fingerprint": _sha256(path),
            }
        )
    return {
        "schema_version": "video-profile-private-media-index-v1",
        "profile_id": profile["profile_id"],
        "profile_revision": profile["profile_revision"],
        "media": media,
    }


def _video_run_dir(paths: ProjectPaths, run_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("run_id may contain only letters, numbers, underscore, and hyphen")
    return paths.generated_dir / "reports" / "video-creation" / run_id


def _read_video_interface_manifest(paths: ProjectPaths) -> dict:
    path = paths.generated_dir / "agent-interface" / "video-profiles" / "manifest.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not manifest.get("interface_revision"):
        raise ValueError(f"invalid video profile interface manifest: {path}")
    return manifest


def _resolve_authorized_source(paths: ProjectPaths, authorization: dict) -> Path:
    registry_path = paths.generated_dir / "cache" / "video-assets" / "registry.json"
    if not registry_path.is_file():
        raise FileNotFoundError(registry_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    asset = next(
        (
            item
            for item in registry.get("assets", [])
            if item.get("asset_id") == authorization.get("video_asset_id")
        ),
        None,
    )
    if asset is None:
        raise PermissionError("authorized video asset is missing from the private registry")
    if asset.get("product_id") != authorization.get("product_id"):
        raise PermissionError("authorized video asset product scope no longer matches")
    if asset.get("source_fingerprint") != authorization.get("source_revision"):
        raise ValueError("authorized video source revision is stale")
    source = (paths.raw_dir / str(asset.get("source_relative_path") or "")).resolve()
    try:
        source.relative_to(paths.raw_dir.resolve())
    except ValueError as exc:
        raise PermissionError("private video asset mapping escapes raw_dir") from exc
    if not source.is_file():
        raise FileNotFoundError(source)
    if _sha256(source) != authorization.get("source_revision"):
        raise ValueError("authorized video source bytes have changed")
    return source


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)

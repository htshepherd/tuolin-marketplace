from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .video_profiles import (
    FrameDecoder,
    VIDEO_SUFFIXES,
    VideoAssetRecord,
    inspect_video_candidate,
    register_video_asset,
)
from ..shared.project_layout import ProjectPaths


BatchProcessor = Callable[[Path, VideoAssetRecord, dict], dict]
CHECKPOINT_SCHEMA_VERSION = "video-profile-checkpoint-v1"
ANALYSIS_POLICY_REVISION = "video-analysis-v1"


class SystemicVideoBatchError(RuntimeError):
    """Pause the remaining videos because the shared processing environment failed."""


@dataclass(frozen=True)
class VideoProfileBatchResult:
    status: str
    batch_id: str
    completed_count: int
    skipped_count: int
    failed_count: int
    blockers: tuple[str, ...]
    preflight_path: Path
    manifest_path: Path
    checkpoint_paths: tuple[Path, ...]


def process_video_profile_batch(
    product_video_dir: Path,
    paths: ProjectPaths,
    *,
    product_id: str,
    batch_id: str,
    expected_count: int | None = None,
    ffprobe_path: str = "ffprobe",
    ffmpeg_path: str = "ffmpeg",
    codex_visual_review_available: bool = True,
    optional_asr_available: bool = False,
    runner=subprocess.run,
    frame_decoder: FrameDecoder | None = None,
    processor: BatchProcessor | None = None,
) -> VideoProfileBatchResult:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", batch_id):
        raise ValueError("batch_id may contain only letters, numbers, underscore, and hyphen")
    folder = product_video_dir.expanduser().resolve()
    try:
        source_classification = tuple(folder.relative_to(paths.raw_dir.resolve()).parts)
    except ValueError as exc:
        raise ValueError("video profile batch folder must be under raw_dir") from exc
    if not folder.is_dir():
        raise FileNotFoundError(folder)
    product_slug = product_id.split("/", 1)[-1]
    batch_root = (
        paths.generated_dir
        / "staging"
        / "video-profiles"
        / batch_id
        / product_slug
    )
    checkpoint_root = batch_root / "checkpoints"
    preflight_path = batch_root / "preflight.json"
    manifest_path = batch_root / "batch-manifest.json"
    batch_root.mkdir(parents=True, exist_ok=True)

    preflight = _run_preflight(
        ffprobe_path=ffprobe_path,
        ffmpeg_path=ffmpeg_path,
        codex_visual_review_available=codex_visual_review_available,
        optional_asr_available=optional_asr_available,
        runner=runner,
    )
    _write_json_atomic(preflight_path, preflight)
    blockers = tuple(preflight["blockers"])
    if blockers:
        _write_json_atomic(
            manifest_path,
            _batch_manifest(
                batch_id=batch_id,
                product_id=product_id,
                source_classification=source_classification,
                expected_count=expected_count,
                items=[],
                status="blocked_preflight",
                preflight=preflight,
            ),
        )
        return VideoProfileBatchResult(
            status="blocked_preflight",
            batch_id=batch_id,
            completed_count=0,
            skipped_count=0,
            failed_count=0,
            blockers=blockers,
            preflight_path=preflight_path,
            manifest_path=manifest_path,
            checkpoint_paths=(),
        )

    videos = tuple(
        path
        for path in sorted(folder.rglob("*"))
        if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
    )
    classification_fingerprint = _fingerprint(list(source_classification))
    capability_revision = _fingerprint(
        {
            "required": preflight["required_capabilities"],
            "optional": preflight["optional_capabilities"],
        }
    )
    process = processor or _default_processor
    items: list[dict] = []
    checkpoint_paths: list[Path] = []
    skipped_count = 0
    failed_count = 0
    systemic_error: str | None = None
    for video_index, video in enumerate(videos):
        asset = register_video_asset(video, paths, product_id=product_id)
        checkpoint_path = checkpoint_root / (
            hashlib.sha256(asset.source_relative_path.encode("utf-8")).hexdigest()[:20]
            + ".json"
        )
        bindings = {
            "source_fingerprint": asset.source_fingerprint,
            "classification_fingerprint": classification_fingerprint,
            "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION,
            "analysis_policy_revision": ANALYSIS_POLICY_REVISION,
            "capability_revision": capability_revision,
        }
        existing = _read_json_or_none(checkpoint_path)
        if _checkpoint_is_reusable(existing, bindings):
            skipped_count += 1
            checkpoint_paths.append(checkpoint_path)
            items.append(
                {
                    "source_relative_path": asset.source_relative_path,
                    "asset_id": existing["asset_id"],
                    "status": "valid",
                    "checkpoint": str(checkpoint_path),
                    "resumed": True,
                    "acceptance_facts": existing.get("acceptance_facts", {}),
                }
            )
            _write_json_atomic(
                manifest_path,
                _batch_manifest(
                    batch_id=batch_id,
                    product_id=product_id,
                    source_classification=source_classification,
                    expected_count=expected_count,
                    items=items,
                    status="processing",
                    preflight=preflight,
                ),
            )
            continue
        context = {
            "batch_id": batch_id,
            "checkpoint_root": checkpoint_root,
            "source_classification": source_classification,
            "ffprobe_path": ffprobe_path,
            "ffmpeg_path": ffmpeg_path,
            "runner": runner,
            "frame_decoder": frame_decoder,
            "paths": paths,
            "product_id": product_id,
        }
        try:
            processed = process(video, asset, context)
            if processed.get("status") != "valid":
                raise ValueError("video processor did not return a valid checkpoint state")
            checkpoint = {
                "schema_version": CHECKPOINT_SCHEMA_VERSION,
                "status": "valid",
                "batch_id": batch_id,
                "asset_id": asset.asset_id,
                "product_id": product_id,
                "source_relative_path": asset.source_relative_path,
                **bindings,
                "processor_report": processed.get("report_path"),
                "acceptance_facts": processed.get("acceptance_facts", {}),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            _write_json_atomic(checkpoint_path, checkpoint)
            checkpoint_paths.append(checkpoint_path)
            item_status = "valid"
            error = None
        except SystemicVideoBatchError as exc:
            failed_count += 1
            systemic_error = str(exc)
            failure = {
                "schema_version": CHECKPOINT_SCHEMA_VERSION,
                "status": "systemic_failure",
                "batch_id": batch_id,
                "asset_id": asset.asset_id,
                "product_id": product_id,
                "source_relative_path": asset.source_relative_path,
                **bindings,
                "error": systemic_error,
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }
            _write_json_atomic(checkpoint_path, failure)
            items.append(
                {
                    "source_relative_path": asset.source_relative_path,
                    "asset_id": asset.asset_id,
                    "status": "systemic_failure",
                    "checkpoint": str(checkpoint_path),
                    "resumed": False,
                    "error": systemic_error,
                    "acceptance_facts": {},
                }
            )
            for paused_video in videos[video_index + 1 :]:
                paused_asset = register_video_asset(
                    paused_video,
                    paths,
                    product_id=product_id,
                )
                items.append(
                    {
                        "source_relative_path": paused_asset.source_relative_path,
                        "asset_id": paused_asset.asset_id,
                        "status": "paused",
                        "checkpoint": None,
                        "resumed": False,
                        "error": systemic_error,
                        "acceptance_facts": {},
                    }
                )
            _write_json_atomic(
                manifest_path,
                _batch_manifest(
                    batch_id=batch_id,
                    product_id=product_id,
                    source_classification=source_classification,
                    expected_count=expected_count,
                    items=items,
                    status="paused_systemic_failure",
                    preflight=preflight,
                ),
            )
            break
        except Exception as exc:
            failed_count += 1
            failure = {
                "schema_version": CHECKPOINT_SCHEMA_VERSION,
                "status": "failed",
                "batch_id": batch_id,
                "asset_id": asset.asset_id,
                "product_id": product_id,
                "source_relative_path": asset.source_relative_path,
                **bindings,
                "error": str(exc),
                "failed_at": datetime.now(timezone.utc).isoformat(),
            }
            _write_json_atomic(checkpoint_path, failure)
            item_status = "failed"
            error = str(exc)
        items.append(
            {
                "source_relative_path": asset.source_relative_path,
                "asset_id": asset.asset_id,
                "status": item_status,
                "checkpoint": str(checkpoint_path),
                "resumed": False,
                "error": error,
                "acceptance_facts": (
                    checkpoint.get("acceptance_facts", {})
                    if item_status == "valid"
                    else {}
                ),
            }
        )
        _write_json_atomic(
            manifest_path,
            _batch_manifest(
                batch_id=batch_id,
                product_id=product_id,
                source_classification=source_classification,
                expected_count=expected_count,
                items=items,
                status="processing",
                preflight=preflight,
            ),
        )

    completed_count = sum(item["status"] == "valid" for item in items)
    if systemic_error is not None:
        status = "paused_systemic_failure"
    elif expected_count is not None and len(videos) != expected_count:
        status = "blocked_source_count_mismatch"
    elif failed_count:
        status = "completed_with_failures"
    else:
        status = "completed"
    _write_json_atomic(
        manifest_path,
        _batch_manifest(
            batch_id=batch_id,
            product_id=product_id,
            source_classification=source_classification,
            expected_count=expected_count,
            items=items,
            status=status,
            preflight=preflight,
        ),
    )
    return VideoProfileBatchResult(
        status=status,
        batch_id=batch_id,
        completed_count=completed_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        blockers=(systemic_error,) if systemic_error else (),
        preflight_path=preflight_path,
        manifest_path=manifest_path,
        checkpoint_paths=tuple(checkpoint_paths),
    )


def _run_preflight(
    *,
    ffprobe_path: str,
    ffmpeg_path: str,
    codex_visual_review_available: bool,
    optional_asr_available: bool,
    runner,
) -> dict:
    required = {}
    blockers = []
    for name, command in (("ffprobe", ffprobe_path), ("ffmpeg", ffmpeg_path)):
        try:
            completed = runner(
                (command, "-version"),
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            available = False
        else:
            available = completed.returncode == 0
        required[name] = "available" if available else "unavailable"
        if not available:
            blockers.append(name)
    required["codex_visual_review"] = (
        "available" if codex_visual_review_available else "unavailable"
    )
    if not codex_visual_review_available:
        blockers.append("codex_visual_review")
    return {
        "schema_version": "video-profile-batch-preflight-v1",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "blocked" if blockers else "ready",
        "required_capabilities": required,
        "optional_capabilities": {
            "asr": "available" if optional_asr_available else "unavailable",
            "auxiliary_quality_components": "optional_unchecked",
        },
        "blockers": blockers,
    }


def _default_processor(
    video: Path,
    asset: VideoAssetRecord,
    context: dict,
) -> dict:
    inspection = inspect_video_candidate(
        video,
        context["paths"],
        product_id=context["product_id"],
        source_classification=context["source_classification"],
        ffprobe_path=context["ffprobe_path"],
        ffmpeg_path=context["ffmpeg_path"],
        runner=context["runner"],
        frame_decoder=context.get("frame_decoder"),
    )
    if inspection.status not in {"awaiting_codex_review", "review_required"}:
        raise ValueError(f"unexpected video inspection status: {inspection.status}")
    return {
        "status": "valid",
        "report_path": str(inspection.report_path),
    }


def _checkpoint_is_reusable(checkpoint: dict | None, bindings: dict) -> bool:
    if not checkpoint or checkpoint.get("status") != "valid":
        return False
    return all(checkpoint.get(key) == value for key, value in bindings.items())


def _batch_manifest(
    *,
    batch_id: str,
    product_id: str,
    source_classification: tuple[str, ...],
    expected_count: int | None,
    items: list[dict],
    status: str,
    preflight: dict,
) -> dict:
    return {
        "schema_version": "video-profile-batch-manifest-v1",
        "batch_id": batch_id,
        "product_id": product_id,
        "source_classification": list(source_classification),
        "expected_count": expected_count,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "preflight_status": preflight["status"],
        "items": items,
    }


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json_or_none(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _write_json_atomic(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)

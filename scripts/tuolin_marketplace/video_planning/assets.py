from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..kb.agent_specific_interfaces import read_video_planner_manifest, read_video_planner_video_detail
from ..shared.project_layout import ProjectPaths


@dataclass(frozen=True)
class VideoPlanningPreviewResult:
    status: str
    run_id: str
    profile_id: str
    segment_id: str
    planned_use_id: str
    preview_path: str
    audio_removed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def authorize_video_profile_for_planning_run(paths: ProjectPaths, run_id: str, profile_id: str) -> dict[str, Any]:
    run_dir = _planning_run_dir(paths, run_id)
    state = _read_json(run_dir / "workflow_state.json")
    manifest = read_video_planner_manifest(paths)
    detail = read_video_planner_video_detail(paths, profile_id)
    if state.get("interface", {}).get("interface_revision") != manifest.get("interface_revision"):
        raise ValueError("运行固定的专属接口版本与当前接口不一致；不能新增视频授权。")
    if detail.get("product_id") != state.get("product", {}).get("id"):
        raise PermissionError("视频档案不属于当前策划产品。")
    segments = [
        {key: item[key] for key in ("segment_id", "start_seconds", "end_seconds")}
        for item in detail.get("key_segments", [])
        if item.get("use_exclusion", {}).get("status") != "excluded"
    ]
    if not segments:
        raise PermissionError("视频档案没有可用于策划的片段。")
    path = run_dir / "video_profile_authorizations.json"
    existing = _read_json(path) if path.is_file() else {
        "schema_version": "video-planner-run-authorization-v1",
        "run_id": run_id,
        "interface_revision": manifest["interface_revision"],
        "raw_access": False,
        "authorized_profiles": [],
    }
    entry = {
        "profile_id": profile_id,
        "video_asset_id": detail["video_asset_id"],
        "product_id": detail["product_id"],
        "profile_revision": detail["profile_revision"],
        "source_revision": detail["source_revision"],
        "operations": ["candidate_preview"],
        "segments": segments,
        "authorized_at": datetime.now(timezone.utc).isoformat(),
    }
    existing["authorized_profiles"] = [
        item for item in existing.get("authorized_profiles", []) if item.get("profile_id") != profile_id
    ] + [entry]
    _write_json(path, existing)
    _append_audit(run_dir, {"operation": "authorize_profile", "status": "authorized", **entry})
    return entry


def extract_video_planning_preview(
    paths: ProjectPaths,
    *,
    run_id: str,
    profile_id: str,
    segment_id: str,
    planned_use_id: str,
    start_seconds: float,
    end_seconds: float,
    ffmpeg_path: str = "ffmpeg",
    runner=subprocess.run,
) -> VideoPlanningPreviewResult:
    run_dir = _planning_run_dir(paths, run_id)
    audit = {
        "attempted_at": datetime.now(timezone.utc).isoformat(),
        "operation": "candidate_preview",
        "profile_id": profile_id,
        "segment_id": segment_id,
        "planned_use_id": planned_use_id,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "audio_policy": "removed",
    }
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", planned_use_id):
            raise ValueError("planned_use_id 只能包含字母、数字、下划线和连字符。")
        existing_previews = [
            item for item in _read_audit(run_dir)
            if item.get("operation") == "candidate_preview"
            and item.get("status") == "extracted"
            and item.get("planned_use_id") == planned_use_id
        ]
        if len(existing_previews) >= 3:
            raise ValueError("同一计划用途最多生成三个候选预览。")
        authorization = _authorized_profile(run_dir, profile_id)
        audit["profile_revision"] = authorization["profile_revision"]
        segment = next((item for item in authorization["segments"] if item.get("segment_id") == segment_id), None)
        if segment is None:
            raise PermissionError("片段不在本次运行的授权范围内。")
        start = float(start_seconds)
        end = float(end_seconds)
        audit.update({"start_seconds": start, "end_seconds": end})
        if end <= start or start < float(segment["start_seconds"]) or end > float(segment["end_seconds"]):
            raise ValueError("预览时间范围必须位于已授权片段内。")
        source = _resolve_private_video_source(paths, authorization)
        output_dir = run_dir / "material-previews"
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / f"{planned_use_id}_{len(existing_previews) + 1:02d}.mp4"
        command = [
            ffmpeg_path, "-y", "-ss", f"{start:.3f}", "-i", str(source), "-t", f"{end - start:.3f}",
            "-an", "-vf", "scale=540:960:force_original_aspect_ratio=decrease,pad=540:960:(ow-iw)/2:(oh-ih)/2:black,setsar=1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output),
        ]
        completed = runner(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "ffmpeg 预览截取失败。")
        if not output.is_file() or output.stat().st_size <= 0:
            raise RuntimeError("ffmpeg 未生成有效的视频预览。")
    except Exception as exc:
        _append_audit(run_dir, {**audit, "status": "rejected", "reason": str(exc)})
        raise
    _append_audit(
        run_dir,
        {
            **audit,
            "status": "extracted",
            "preview_path": str(output),
            "preview_fingerprint": _sha256(output),
        },
    )
    return VideoPlanningPreviewResult("extracted", run_id, profile_id, segment_id, planned_use_id, str(output), True)


def read_video_planning_asset_audit(paths: ProjectPaths, run_id: str) -> list[dict[str, Any]]:
    return _read_audit(_planning_run_dir(paths, run_id))


def revalidate_video_planning_material(
    paths: ProjectPaths,
    run_id: str,
    material: dict[str, Any],
) -> None:
    run_dir = _planning_run_dir(paths, run_id)
    authorization = _authorized_profile(run_dir, str(material.get("profile_id") or ""))
    if authorization.get("profile_revision") != material.get("profile_revision"):
        raise ValueError("视频档案授权 revision 已变化。")
    if authorization.get("source_revision") != material.get("source_revision"):
        raise ValueError("视频源授权 revision 已变化。")
    _resolve_private_video_source(paths, authorization)


def _planning_run_dir(paths: ProjectPaths, run_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ValueError("run_id 只能包含字母、数字、下划线和连字符。")
    run_dir = paths.generated_dir / "reports" / "video-planning" / run_id
    if not run_dir.is_dir():
        raise FileNotFoundError(run_dir)
    return run_dir


def _authorized_profile(run_dir: Path, profile_id: str) -> dict[str, Any]:
    path = run_dir / "video_profile_authorizations.json"
    if not path.is_file():
        raise PermissionError("本次策划运行尚未授权任何视频档案。")
    item = next((entry for entry in _read_json(path).get("authorized_profiles", []) if entry.get("profile_id") == profile_id), None)
    if item is None:
        raise PermissionError("视频档案未获本次策划运行授权。")
    return item


def _resolve_private_video_source(paths: ProjectPaths, authorization: dict[str, Any]) -> Path:
    registry = _read_json(paths.generated_dir / "cache" / "video-assets" / "registry.json")
    asset = next((item for item in registry.get("assets", []) if item.get("asset_id") == authorization.get("video_asset_id")), None)
    if asset is None or asset.get("product_id") != authorization.get("product_id"):
        raise PermissionError("私有视频资产映射不存在或产品范围不匹配。")
    if asset.get("source_fingerprint") != authorization.get("source_revision"):
        raise ValueError("视频源版本已变化。")
    source = (paths.raw_dir / str(asset.get("source_relative_path") or "")).resolve()
    try:
        source.relative_to(paths.raw_dir.resolve())
    except ValueError as exc:
        raise PermissionError("私有视频资产路径越过 raw_dir。") from exc
    if not source.is_file() or _sha256(source) != authorization.get("source_revision"):
        raise ValueError("视频源缺失或字节已变化。")
    return source


def _read_audit(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "video_asset_audit.json"
    return _read_json(path) if path.is_file() else []


def _append_audit(run_dir: Path, entry: dict[str, Any]) -> None:
    items = _read_audit(run_dir)
    items.append(entry)
    _write_json(run_dir / "video_asset_audit.json", items)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)

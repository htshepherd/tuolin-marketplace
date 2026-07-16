from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ..shared.project_layout import ProjectPaths
from .video_profile_maintenance import (
    reconcile_video_asset_identity,
    register_video_cache_entry,
)
from .video_test_evidence import validate_test_video_profile_metadata


VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
Runner = Callable[..., subprocess.CompletedProcess[str]]
FrameDecoder = Callable[[Path], bytes]


@dataclass(frozen=True)
class VideoAssetRecord:
    asset_id: str
    product_id: str
    source_relative_path: str
    source_fingerprint: str
    registered_at: str
    registry_path: Path


@dataclass(frozen=True)
class VideoMediaFacts:
    duration_seconds: float
    width: int
    height: int
    frame_rate: float
    video_codec: str
    rotation_degrees: int
    has_audio: bool
    audio_codec: str | None


@dataclass(frozen=True)
class VideoAnalysisSample:
    timestamp_seconds: float
    reason: str


@dataclass(frozen=True)
class VideoAnalysisChange:
    timestamp_seconds: float
    change_type: str


@dataclass(frozen=True)
class VideoAnalysisPlan:
    duration_seconds: float
    max_frames: int
    samples: tuple[VideoAnalysisSample, ...]


@dataclass(frozen=True)
class ExtractedVideoFrame:
    timestamp_seconds: float
    frame_path: Path


@dataclass(frozen=True)
class VideoFrameAssessment:
    frame: ExtractedVideoFrame
    reason: str
    brightness: float
    edge_energy: float


@dataclass(frozen=True)
class VideoFrameFilterResult:
    accepted: tuple[VideoFrameAssessment, ...]
    rejected: tuple[VideoFrameAssessment, ...]


@dataclass(frozen=True)
class VideoCandidateInspection:
    status: str
    asset: VideoAssetRecord
    media_facts: VideoMediaFacts
    source_classification: tuple[str, ...]
    analysis_plan: VideoAnalysisPlan
    accepted_frames: tuple[VideoFrameAssessment, ...]
    rejected_frames: tuple[VideoFrameAssessment, ...]
    representative_candidates: tuple[VideoFrameAssessment, ...]
    report_path: Path


@dataclass(frozen=True)
class VideoCandidateBatchInspection:
    status: str
    product_id: str
    source_classification: tuple[str, ...]
    expected_count: int
    discovered_count: int
    recommendation_allowed: bool
    inspections: tuple[VideoCandidateInspection, ...]
    report_path: Path


@dataclass(frozen=True)
class VideoTracerRecommendation:
    status: str
    recommended_asset_id: str
    reason: str
    report_path: Path


@dataclass(frozen=True)
class CodexVideoCandidateReview:
    title: str
    visual_summary: str
    action_flow: tuple[str, ...]
    product_visibility: str
    observed_classifications: tuple[str, ...]
    audio_observation: str
    risks: tuple[str, ...]
    tracer_suitability: str
    tracer_reason: str
    reviewed_representative_timestamps: tuple[float, ...]


@dataclass(frozen=True)
class CodexVideoCandidateReviewResult:
    status: str
    report_path: Path
    reviewed_at: str


@dataclass(frozen=True)
class VideoTracerConfirmation:
    status: str
    asset_id: str
    report_path: Path
    confirmed_at: str


@dataclass(frozen=True)
class StagedVideoProfileDraft:
    status: str
    profile_id: str
    profile_revision: str
    content_digest: str
    markdown_path: Path
    structured_path: Path


@dataclass(frozen=True)
class VideoAnalysisClip:
    start_seconds: float
    end_seconds: float
    source_fingerprint: str
    clip_path: Path


def register_video_asset(
    video_path: Path,
    paths: ProjectPaths,
    *,
    product_id: str,
) -> VideoAssetRecord:
    source = video_path.expanduser().resolve()
    _require_video_under_raw(source, paths)
    reconciled = reconcile_video_asset_identity(
        source,
        paths,
        product_id=product_id,
    )
    if reconciled.get("status") == "review_required":
        candidates = ", ".join(reconciled.get("candidate_asset_ids", []))
        raise RuntimeError(
            "video asset identity reconciliation requires human review"
            + (f": {candidates}" if candidates else "")
        )
    if reconciled.get("status") == "source_revised":
        from .agent_interface import refresh_agent_interface_after_write

        refresh_agent_interface_after_write(
            paths,
            action="invalidate_replaced_video_source_revision",
        )
    return VideoAssetRecord(
        asset_id=str(reconciled["asset_id"]),
        product_id=str(reconciled["product_id"]),
        source_relative_path=str(reconciled["source_relative_path"]),
        source_fingerprint=str(reconciled["source_fingerprint"]),
        registered_at=str(reconciled["registered_at"]),
        registry_path=Path(reconciled["registry_path"]),
    )


def probe_video_media(
    video_path: Path,
    paths: ProjectPaths,
    *,
    ffprobe_path: str = "ffprobe",
    runner: Runner = subprocess.run,
) -> VideoMediaFacts:
    source = video_path.expanduser().resolve()
    _require_video_under_raw(source, paths)
    command = (
        ffprobe_path,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(source),
    )
    completed = runner(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(error or f"ffprobe failed with exit code {completed.returncode}")

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"ffprobe returned invalid JSON for {source}") from exc
    streams = payload.get("streams", [])
    video_stream = next((item for item in streams if item.get("codec_type") == "video"), None)
    if video_stream is None:
        raise ValueError(f"video stream not found: {source}")
    audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), None)
    duration = _float_value(payload.get("format", {}).get("duration"), field="duration")
    return VideoMediaFacts(
        duration_seconds=duration,
        width=int(video_stream.get("width", 0)),
        height=int(video_stream.get("height", 0)),
        frame_rate=_frame_rate(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")),
        video_codec=str(video_stream.get("codec_name") or "unknown"),
        rotation_degrees=_rotation(video_stream),
        has_audio=audio_stream is not None,
        audio_codec=str(audio_stream.get("codec_name")) if audio_stream else None,
    )


def build_video_analysis_plan(
    media_facts: VideoMediaFacts,
    *,
    detected_change_seconds: tuple[float, ...] = (),
    targeted_changes: tuple[VideoAnalysisChange, ...] = (),
    max_frames: int = 24,
) -> VideoAnalysisPlan:
    if media_facts.duration_seconds <= 0:
        raise ValueError("video duration must be positive")
    if max_frames < 3:
        raise ValueError("video analysis requires at least three frames")

    broad_count = min(max_frames, _broad_sample_count(media_facts.duration_seconds))
    frame_guard = 2.0 / media_facts.frame_rate if media_facts.frame_rate > 0 else 0.1
    tail_guard = min(media_facts.duration_seconds / 2.0, max(0.1, frame_guard))
    end = max(0.0, media_facts.duration_seconds - tail_guard)
    if broad_count == 1:
        broad_timestamps = [0.0]
    else:
        broad_timestamps = [end * index / (broad_count - 1) for index in range(broad_count)]

    samples = [
        VideoAnalysisSample(timestamp_seconds=round(timestamp, 3), reason="uniform_coverage")
        for timestamp in broad_timestamps
    ]
    for change in sorted(detected_change_seconds):
        for timestamp, reason in (
            (change - 0.5, "detected_change_context"),
            (change, "detected_change"),
            (change + 0.5, "detected_change_context"),
        ):
            bounded = min(end, max(0.0, float(timestamp)))
            _add_sample(samples, bounded, reason, max_frames=max_frames)
    allowed_change_types = {
        "scene_change",
        "subject_change",
        "product_visibility_change",
        "action_start",
        "action_peak",
        "action_end",
        "process_state_change",
    }
    for change in sorted(targeted_changes, key=lambda item: item.timestamp_seconds):
        if change.change_type not in allowed_change_types:
            raise ValueError(f"unsupported video analysis change type: {change.change_type}")
        for timestamp, reason in (
            (change.timestamp_seconds - 0.5, f"{change.change_type}_before"),
            (change.timestamp_seconds, change.change_type),
            (change.timestamp_seconds + 0.5, f"{change.change_type}_after"),
        ):
            bounded = min(end, max(0.0, float(timestamp)))
            _add_sample(samples, bounded, reason, max_frames=max_frames)

    samples.sort(key=lambda item: item.timestamp_seconds)
    return VideoAnalysisPlan(
        duration_seconds=media_facts.duration_seconds,
        max_frames=max_frames,
        samples=tuple(samples),
    )


def detect_video_change_candidates(
    video_path: Path,
    paths: ProjectPaths,
    *,
    ffmpeg_path: str = "ffmpeg",
    scene_threshold: float = 0.12,
    max_candidates: int = 12,
    runner: Runner = subprocess.run,
) -> tuple[float, ...]:
    source = video_path.expanduser().resolve()
    _require_video_under_raw(source, paths)
    command = (
        ffmpeg_path,
        "-hide_banner",
        "-i",
        str(source),
        "-vf",
        f"select='gt(scene,{scene_threshold})',showinfo",
        "-fps_mode",
        "vfr",
        "-an",
        "-f",
        "null",
        "-",
    )
    completed = runner(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(error or f"ffmpeg scene detection failed with exit code {completed.returncode}")

    values: list[float] = []
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    for match in re.finditer(r"\bpts_time:([0-9]+(?:\.[0-9]+)?)", output):
        value = round(float(match.group(1)), 3)
        if value not in values:
            values.append(value)
        if len(values) >= max_candidates:
            break
    return tuple(sorted(values))


def filter_video_frame_candidates(
    frames: tuple[ExtractedVideoFrame, ...],
    *,
    decoder: FrameDecoder | None = None,
) -> VideoFrameFilterResult:
    decode = decoder or _decode_frame_luma
    accepted: list[VideoFrameAssessment] = []
    rejected: list[VideoFrameAssessment] = []
    accepted_luma: list[bytes] = []
    for frame in frames:
        luma = decode(frame.frame_path)
        if len(luma) != 256:
            raise ValueError(f"expected 16x16 luma bytes for {frame.frame_path}, got {len(luma)}")
        brightness = sum(luma) / len(luma)
        edge_energy = _edge_energy(luma)
        if brightness <= 10.0:
            reason = "black"
        elif edge_energy < 2.0:
            reason = "severely_blurred"
        elif any(_mean_absolute_difference(luma, previous) <= 3.0 for previous in accepted_luma):
            reason = "near_duplicate"
        else:
            reason = "accepted"
        assessment = VideoFrameAssessment(
            frame=frame,
            reason=reason,
            brightness=round(brightness, 3),
            edge_energy=round(edge_energy, 3),
        )
        if reason == "accepted":
            accepted.append(assessment)
            accepted_luma.append(luma)
        else:
            rejected.append(assessment)
    return VideoFrameFilterResult(accepted=tuple(accepted), rejected=tuple(rejected))


def prepare_video_analysis_clip(
    video_path: Path,
    paths: ProjectPaths,
    *,
    start_seconds: float,
    end_seconds: float,
    temporal_need: bool,
    ffmpeg_path: str = "ffmpeg",
    runner: Runner = subprocess.run,
) -> VideoAnalysisClip | None:
    if not temporal_need:
        return None
    source = video_path.expanduser().resolve()
    _require_video_under_raw(source, paths)
    start = float(start_seconds)
    end = float(end_seconds)
    duration = end - start
    if start < 0 or duration <= 0 or duration > 12:
        raise ValueError("analysis clip range must be positive and no longer than 12 seconds")
    source_fingerprint = _sha256(source)
    clip_dir = (
        paths.generated_dir
        / "cache"
        / "video-analysis-clips"
        / source_fingerprint
    )
    output_path = (
        clip_dir
        / f"clip_{round(start * 1000):010d}_{round(end * 1000):010d}.mp4"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = (
        ffmpeg_path,
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(source),
        "-t",
        f"{duration:.3f}",
        "-map",
        "0:v:0",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "20",
        "-an",
        "-movflags",
        "+faststart",
        str(output_path),
    )
    completed = runner(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(error or f"analysis clip extraction failed with exit code {completed.returncode}")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"analysis clip extraction produced no output: {output_path}")
    register_video_cache_entry(
        paths,
        output_path,
        kind="analysis_clip",
        state="complete",
        last_used_at=datetime.now(timezone.utc).isoformat(),
    )
    return VideoAnalysisClip(
        start_seconds=start,
        end_seconds=end,
        source_fingerprint=source_fingerprint,
        clip_path=output_path,
    )


def inspect_video_candidate(
    video_path: Path,
    paths: ProjectPaths,
    *,
    product_id: str,
    source_classification: tuple[str, ...],
    ffprobe_path: str = "ffprobe",
    ffmpeg_path: str = "ffmpeg",
    runner: Runner = subprocess.run,
    frame_decoder: FrameDecoder | None = None,
) -> VideoCandidateInspection:
    source = video_path.expanduser().resolve()
    asset = register_video_asset(source, paths, product_id=product_id)
    media_facts = probe_video_media(source, paths, ffprobe_path=ffprobe_path, runner=runner)
    changes = detect_video_change_candidates(source, paths, ffmpeg_path=ffmpeg_path, runner=runner)
    analysis_plan = build_video_analysis_plan(
        media_facts,
        detected_change_seconds=changes,
        max_frames=24,
    )
    cache_dir = (
        paths.generated_dir
        / "cache"
        / "video-tracer-inspection"
        / asset.source_fingerprint
    )
    frame_dir = cache_dir / "analysis-frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[ExtractedVideoFrame] = []
    for index, sample in enumerate(analysis_plan.samples):
        milliseconds = round(sample.timestamp_seconds * 1000)
        output_path = frame_dir / f"frame_{index:03d}_{milliseconds:010d}.png"
        command = (
            ffmpeg_path,
            "-y",
            "-ss",
            f"{sample.timestamp_seconds:.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            str(output_path),
        )
        completed = runner(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            error = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(error or f"frame extraction failed at {sample.timestamp_seconds:.3f}s")
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise RuntimeError(
                f"frame extraction produced no image at {sample.timestamp_seconds:.3f}s: {output_path}"
            )
        register_video_cache_entry(
            paths,
            output_path,
            kind="analysis_frame",
            state="complete",
            last_used_at=datetime.now(timezone.utc).isoformat(),
        )
        extracted.append(
            ExtractedVideoFrame(
                timestamp_seconds=sample.timestamp_seconds,
                frame_path=output_path,
            )
        )

    decoder = frame_decoder or (lambda path: _decode_frame_luma(path, ffmpeg_path=ffmpeg_path))
    filtered = filter_video_frame_candidates(tuple(extracted), decoder=decoder)
    representatives = _spread_representatives(filtered.accepted, maximum=6)
    status = "awaiting_codex_review" if len(representatives) >= 3 else "review_required"
    report_path = cache_dir / "inspection.json"
    result = VideoCandidateInspection(
        status=status,
        asset=asset,
        media_facts=media_facts,
        source_classification=source_classification,
        analysis_plan=analysis_plan,
        accepted_frames=filtered.accepted,
        rejected_frames=filtered.rejected,
        representative_candidates=representatives,
        report_path=report_path,
    )
    _write_inspection_report(result)
    register_video_cache_entry(
        paths,
        report_path,
        kind="inspection_report",
        state=(
            "review_required"
            if status in {"awaiting_codex_review", "review_required"}
            else "complete"
        ),
        last_used_at=datetime.now(timezone.utc).isoformat(),
    )
    return result


def inspect_video_candidate_batch(
    product_video_dir: Path,
    paths: ProjectPaths,
    *,
    product_id: str,
    expected_count: int,
    ffprobe_path: str = "ffprobe",
    ffmpeg_path: str = "ffmpeg",
    runner: Runner = subprocess.run,
    frame_decoder: FrameDecoder | None = None,
) -> VideoCandidateBatchInspection:
    folder = product_video_dir.expanduser().resolve()
    try:
        source_classification = tuple(folder.relative_to(paths.raw_dir).parts)
    except ValueError as exc:
        raise ValueError(f"product video folder must be under raw_dir: {folder}") from exc
    if not folder.is_dir():
        raise FileNotFoundError(folder)
    videos = tuple(
        path
        for path in sorted(folder.rglob("*"))
        if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
    )
    inspections = tuple(
        inspect_video_candidate(
            video,
            paths,
            product_id=product_id,
            source_classification=source_classification,
            ffprobe_path=ffprobe_path,
            ffmpeg_path=ffmpeg_path,
            runner=runner,
            frame_decoder=frame_decoder,
        )
        for video in videos
    )
    if len(videos) != expected_count:
        status = "blocked_source_count_mismatch"
    elif any(item.status != "awaiting_codex_review" for item in inspections):
        status = "review_required"
    else:
        status = "awaiting_codex_review"
    product_slug = product_id.split("/", 1)[-1]
    report_path = (
        paths.generated_dir
        / "cache"
        / "video-tracer-inspection"
        / "batches"
        / product_slug
        / "candidate-batch.json"
    )
    result = VideoCandidateBatchInspection(
        status=status,
        product_id=product_id,
        source_classification=source_classification,
        expected_count=expected_count,
        discovered_count=len(videos),
        recommendation_allowed=False,
        inspections=inspections,
        report_path=report_path,
    )
    _write_batch_inspection_report(result)
    return result


def finalize_video_candidate_batch_recommendation(
    batch_report_path: Path,
    paths: ProjectPaths,
    *,
    recommended_asset_id: str,
    reason: str,
) -> VideoTracerRecommendation:
    report_path = batch_report_path.expanduser().resolve()
    batches_root = (
        paths.generated_dir / "cache" / "video-tracer-inspection" / "batches"
    ).resolve()
    try:
        report_path.relative_to(batches_root)
    except ValueError as exc:
        raise ValueError(f"candidate batch report must be under tracer batch cache: {report_path}") from exc
    if not report_path.is_file():
        raise FileNotFoundError(report_path)
    data = json.loads(report_path.read_text(encoding="utf-8"))
    if data.get("status") == "blocked_source_count_mismatch":
        raise ValueError("tracer recommendation requires the complete expected source batch")
    if data.get("discovered_count") != data.get("expected_count"):
        raise ValueError("tracer recommendation requires the complete expected source batch")
    candidates = data.get("candidates", [])
    if not candidates or any(
        candidate.get("status") != "codex_review_completed"
        for candidate in candidates
    ):
        raise ValueError("tracer recommendation requires all candidates to complete Codex review")
    recommended = next(
        (
            candidate
            for candidate in candidates
            if candidate.get("asset_id") == recommended_asset_id
        ),
        None,
    )
    if recommended is None:
        raise ValueError("recommended tracer Asset ID is not in the candidate batch")
    suitability = recommended.get("codex_review", {}).get("tracer_suitability")
    if suitability == "not_recommended":
        raise ValueError("a candidate marked not_recommended cannot become the tracer recommendation")
    recommendation_reason = reason.strip()
    if not recommendation_reason:
        raise ValueError("tracer recommendation requires a human-readable reason")
    data["status"] = "awaiting_tracer_confirmation"
    data["recommendation_allowed"] = True
    data["tracer_recommendation"] = {
        "recommended_asset_id": recommended_asset_id,
        "reason": recommendation_reason,
        "recommended_at": datetime.now(timezone.utc).isoformat(),
        "recommended_by": "codex",
    }
    temporary = report_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(report_path)
    return VideoTracerRecommendation(
        status="awaiting_tracer_confirmation",
        recommended_asset_id=recommended_asset_id,
        reason=recommendation_reason,
        report_path=report_path,
    )


def record_codex_candidate_review(
    inspection_report_path: Path,
    paths: ProjectPaths,
    review: CodexVideoCandidateReview,
) -> CodexVideoCandidateReviewResult:
    report_path = inspection_report_path.expanduser().resolve()
    inspection_root = (
        paths.generated_dir / "cache" / "video-tracer-inspection"
    ).resolve()
    try:
        report_path.relative_to(inspection_root)
    except ValueError as exc:
        raise ValueError(f"inspection report must be under tracer cache: {report_path}") from exc
    if not report_path.is_file():
        raise FileNotFoundError(report_path)
    data = json.loads(report_path.read_text(encoding="utf-8"))
    if data.get("formal_profile_published"):
        raise ValueError("candidate inspection report cannot be updated after formal publication")
    reviewed_at = datetime.now(timezone.utc).isoformat()
    data["status"] = "codex_review_completed"
    data["codex_review"] = {
        **_jsonable(asdict(review)),
        "reviewed_at": reviewed_at,
        "reviewer": "codex",
    }
    temporary = report_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(report_path)
    _sync_candidate_review_to_batch_reports(paths, report_path, data["codex_review"])
    return CodexVideoCandidateReviewResult(
        status="codex_review_completed",
        report_path=report_path,
        reviewed_at=reviewed_at,
    )


def confirm_video_tracer_candidate(
    inspection_report_path: Path,
    paths: ProjectPaths,
    *,
    confirmed_asset_id: str,
) -> VideoTracerConfirmation:
    report_path = inspection_report_path.expanduser().resolve()
    inspection_root = (
        paths.generated_dir / "cache" / "video-tracer-inspection"
    ).resolve()
    try:
        report_path.relative_to(inspection_root)
    except ValueError as exc:
        raise ValueError(f"inspection report must be under tracer cache: {report_path}") from exc
    if not report_path.is_file():
        raise FileNotFoundError(report_path)
    data = json.loads(report_path.read_text(encoding="utf-8"))
    if data.get("status") != "codex_review_completed":
        raise ValueError("tracer confirmation requires a completed Codex review")
    if data.get("formal_profile_published"):
        raise ValueError("published candidate inspection cannot be confirmed as a new tracer")
    asset_id = str(data.get("asset", {}).get("asset_id", ""))
    if confirmed_asset_id != asset_id:
        raise ValueError("confirmed tracer Asset ID does not match the inspected video")
    confirmed_at = datetime.now(timezone.utc).isoformat()
    data["status"] = "tracer_confirmed"
    data["tracer_confirmation"] = {
        "confirmed_asset_id": asset_id,
        "confirmed_at": confirmed_at,
        "confirmation_scope": "source_video_for_s01_tracer",
    }
    temporary = report_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(report_path)
    _sync_candidate_confirmation_to_batch_reports(paths, report_path, data["tracer_confirmation"])
    return VideoTracerConfirmation(
        status="tracer_confirmed",
        asset_id=asset_id,
        report_path=report_path,
        confirmed_at=confirmed_at,
    )


def stage_video_profile_draft(
    inspection_report_path: Path,
    paths: ProjectPaths,
    *,
    batch_id: str,
    proposal: dict,
) -> StagedVideoProfileDraft:
    report_path = inspection_report_path.expanduser().resolve()
    inspection_root = (
        paths.generated_dir / "cache" / "video-tracer-inspection"
    ).resolve()
    try:
        report_path.relative_to(inspection_root)
    except ValueError as exc:
        raise ValueError(f"inspection report must be under tracer cache: {report_path}") from exc
    if not report_path.is_file():
        raise FileNotFoundError(report_path)
    inspection = json.loads(report_path.read_text(encoding="utf-8"))
    if (
        inspection.get("status") != "tracer_confirmed"
        or not inspection.get("tracer_confirmation")
    ):
        raise ValueError("video profile draft requires explicit tracer confirmation")
    if inspection.get("formal_profile_published"):
        raise ValueError("published candidate inspection cannot be restaged as a draft")
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", batch_id):
        raise ValueError("batch_id may contain only letters, numbers, underscore, and hyphen")
    asset = inspection.get("asset", {})
    source_relative_path = str(asset.get("source_relative_path", ""))
    source_revision = str(asset.get("source_fingerprint", ""))
    source_path = (paths.raw_dir / source_relative_path).resolve()
    try:
        source_path.relative_to(paths.raw_dir.resolve())
    except ValueError as exc:
        raise ValueError("inspection report contains an invalid raw source reference") from exc
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if _sha256(source_path) != source_revision:
        raise ValueError("source revision no longer matches the inspected video")
    duration = float(inspection.get("media_facts", {}).get("duration_seconds", 0))
    if duration <= 0:
        raise ValueError("video profile requires a positive media duration")
    required_fields = {
        "title",
        "summary",
        "observed_classifications",
        "product_visibility",
        "key_segments",
        "anchor_moments",
        "representative_frames",
        "use_capabilities",
        "audio_observations",
        "transcript_detail",
        "source_audio_use_policy",
        "observation_confidence",
        "risk_summary",
        "evidence_links",
        "analysis_completeness",
        "analysis_provenance",
        "exclusions",
    }
    missing = sorted(required_fields - set(proposal))
    if missing:
        raise ValueError(f"video profile proposal missing required fields: {', '.join(missing)}")

    segments = proposal["key_segments"]
    if not isinstance(segments, list) or not segments:
        raise ValueError("video profile requires at least one key segment")
    segments_by_id: dict[str, dict] = {}
    for segment in segments:
        segment_id = str(segment.get("segment_id", ""))
        if not segment_id or segment_id in segments_by_id:
            raise ValueError("key segment IDs must be present and unique")
        start = float(segment.get("start_seconds", -1))
        end = float(segment.get("end_seconds", -1))
        if start < 0 or end <= start or end > duration:
            raise ValueError(
                f"key segment {segment_id or '<unknown>'} is outside video duration"
            )
        for field in (
            "description",
            "action",
            "product_visibility",
            "reuse_mode",
            "editing_suitability",
        ):
            if not str(segment.get(field, "")).strip():
                raise ValueError(f"key segment {segment_id} missing required field: {field}")
        segments_by_id[segment_id] = segment

    anchors = proposal["anchor_moments"]
    if not isinstance(anchors, list) or not anchors:
        raise ValueError("video profile requires at least one anchor moment")
    anchors_by_id: dict[str, dict] = {}
    for anchor in anchors:
        anchor_id = str(anchor.get("anchor_id", ""))
        segment_id = str(anchor.get("segment_id", ""))
        if not anchor_id or anchor_id in anchors_by_id:
            raise ValueError("anchor IDs must be present and unique")
        segment = segments_by_id.get(segment_id)
        if segment is None:
            raise ValueError(f"anchor {anchor_id} references unknown segment: {segment_id}")
        timestamp = float(anchor.get("timestamp_seconds", -1))
        if not (
            float(segment["start_seconds"])
            <= timestamp
            <= float(segment["end_seconds"])
        ):
            raise ValueError(f"anchor {anchor_id} is outside its key segment")
        anchors_by_id[anchor_id] = anchor

    representative_frames = proposal["representative_frames"]
    if not isinstance(representative_frames, list) or not 3 <= len(representative_frames) <= 6:
        raise ValueError("video profile requires three to six representative frames")
    inspected_representatives = tuple(
        (
            Path(str(item.get("frame", {}).get("frame_path", ""))).expanduser().resolve(),
            float(item.get("frame", {}).get("timestamp_seconds", -1)),
        )
        for item in inspection.get("representative_candidates", [])
    )
    normalized_frames: list[dict] = []
    for frame in representative_frames:
        anchor_id = str(frame.get("anchor_id", ""))
        anchor = anchors_by_id.get(anchor_id)
        if anchor is None:
            raise ValueError(f"representative frame references unknown anchor: {anchor_id}")
        timestamp = float(frame.get("timestamp_seconds", -1))
        if abs(timestamp - float(anchor["timestamp_seconds"])) > 0.05:
            raise ValueError(f"representative frame timestamp does not match anchor: {anchor_id}")
        frame_path = Path(str(frame.get("frame_path", ""))).expanduser().resolve()
        try:
            generated_relative_path = frame_path.relative_to(paths.generated_dir.resolve())
        except ValueError as exc:
            raise ValueError("representative frames must be stored under generated_dir") from exc
        if not frame_path.is_file():
            raise FileNotFoundError(frame_path)
        if not any(
            candidate_path == frame_path
            and abs(candidate_timestamp - timestamp) <= 0.05
            for candidate_path, candidate_timestamp in inspected_representatives
        ):
            raise ValueError(
                "representative frames must come from this video's inspected representative candidates"
            )
        normalized = dict(frame)
        normalized.pop("frame_path", None)
        normalized["generated_ref"] = generated_relative_path.as_posix()
        normalized_frames.append(normalized)

    asset_id = str(asset.get("asset_id", ""))
    product_id = str(asset.get("product_id", ""))
    if not re.fullmatch(r"video_asset_[0-9a-f]{32}", asset_id):
        raise ValueError("inspection report contains an invalid video asset ID")
    if "/" not in product_id:
        raise ValueError("inspection report contains an invalid product ID")
    if not re.fullmatch(r"[0-9a-f]{64}", source_revision):
        raise ValueError("inspection report contains an invalid source revision")
    product_slug = product_id.split("/", 1)[1]
    profile_id = f"video_profile/{product_slug}/{asset_id}"
    provenance = dict(proposal["analysis_provenance"])
    provenance["inspection_report_ref"] = report_path.relative_to(paths.generated_dir).as_posix()
    test_metadata = validate_test_video_profile_metadata(
        {
            **proposal,
            "source_classification": list(
                inspection.get("source_classification", [])
            ),
        },
        require_human_review=False,
    )
    domain_object = {
        "schema_version": "1.0",
        "profile_id": profile_id,
        "video_asset_id": asset_id,
        "product_id": product_id,
        "source_revision": source_revision,
        "source_classification": list(inspection.get("source_classification", [])),
        "observed_classifications": list(proposal["observed_classifications"]),
        "title": str(proposal["title"]).strip(),
        "summary": str(proposal["summary"]).strip(),
        "duration": duration,
        "media_facts": inspection["media_facts"],
        "product_visibility": proposal["product_visibility"],
        "key_segments": segments,
        "anchor_moments": anchors,
        "representative_frames": normalized_frames,
        "use_capabilities": list(proposal["use_capabilities"]),
        "audio_observations": list(proposal["audio_observations"]),
        "transcript_detail": proposal["transcript_detail"],
        "source_audio_use_policy": proposal["source_audio_use_policy"],
        "observation_confidence": proposal["observation_confidence"],
        "risk_summary": list(proposal["risk_summary"]),
        "evidence_links": list(proposal["evidence_links"]),
        "processing_state": "review_required",
        "analysis_completeness": proposal["analysis_completeness"],
        "analysis_provenance": provenance,
        "exclusions": list(proposal["exclusions"]),
        **test_metadata,
    }
    canonical = json.dumps(
        domain_object,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest_hex = hashlib.sha256(canonical).hexdigest()
    content_digest = f"sha256:{digest_hex}"
    profile_revision = f"video_profile_rev_{digest_hex[:16]}"
    structured = {
        **domain_object,
        "profile_revision": profile_revision,
        "content_digest": content_digest,
    }
    staging_dir = (
        paths.generated_dir
        / "staging"
        / "video-profiles"
        / batch_id
        / product_slug
    )
    markdown_path = staging_dir / f"{asset_id}.md"
    structured_path = staging_dir / f"{asset_id}.json"
    staging_dir.mkdir(parents=True, exist_ok=True)
    markdown_temporary = Path(f"{markdown_path}.tmp")
    structured_temporary = Path(f"{structured_path}.tmp")
    markdown_temporary.write_text(
        _render_staged_video_profile_markdown(structured),
        encoding="utf-8",
    )
    structured_temporary.write_text(
        json.dumps(structured, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    structured_temporary.replace(structured_path)
    markdown_temporary.replace(markdown_path)
    return StagedVideoProfileDraft(
        status="staged_valid",
        profile_id=profile_id,
        profile_revision=profile_revision,
        content_digest=content_digest,
        markdown_path=markdown_path,
        structured_path=structured_path,
    )


def _require_video_under_raw(path: Path, paths: ProjectPaths) -> None:
    try:
        path.relative_to(paths.raw_dir)
    except ValueError as exc:
        raise ValueError(f"video must be under raw_dir: {path}") from exc
    if path.suffix.lower() not in VIDEO_SUFFIXES:
        raise ValueError(f"unsupported video type: {path.suffix}")
    if not path.is_file():
        raise FileNotFoundError(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _float_value(value: object, *, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid ffprobe {field}: {value!r}") from exc


def _frame_rate(value: object) -> float:
    text = str(value or "0")
    if "/" not in text:
        return _float_value(text, field="frame rate")
    numerator, denominator = text.split("/", 1)
    denominator_value = _float_value(denominator, field="frame rate denominator")
    if denominator_value == 0:
        return 0.0
    return _float_value(numerator, field="frame rate numerator") / denominator_value


def _rotation(video_stream: dict) -> int:
    tags = video_stream.get("tags") or {}
    if "rotate" in tags:
        return int(round(_float_value(tags["rotate"], field="rotation"))) % 360
    for item in video_stream.get("side_data_list") or []:
        if "rotation" in item:
            return int(round(_float_value(item["rotation"], field="rotation"))) % 360
    return 0


def _broad_sample_count(duration_seconds: float) -> int:
    if duration_seconds <= 15:
        return 6
    if duration_seconds <= 60:
        return 9
    if duration_seconds <= 180:
        return 12
    return 16


def _add_sample(
    samples: list[VideoAnalysisSample],
    timestamp: float,
    reason: str,
    *,
    max_frames: int,
) -> None:
    rounded = round(timestamp, 3)
    for index, existing in enumerate(samples):
        if abs(existing.timestamp_seconds - rounded) <= 0.05:
            if reason == "detected_change" and existing.reason != "detected_change":
                samples[index] = VideoAnalysisSample(timestamp_seconds=existing.timestamp_seconds, reason=reason)
            return
    if len(samples) < max_frames:
        samples.append(VideoAnalysisSample(timestamp_seconds=rounded, reason=reason))


def _decode_frame_luma(frame_path: Path, *, ffmpeg_path: str = "ffmpeg") -> bytes:
    command = (
        ffmpeg_path,
        "-v",
        "error",
        "-i",
        str(frame_path),
        "-vf",
        "scale=16:16:flags=area,format=gray",
        "-frames:v",
        "1",
        "-f",
        "rawvideo",
        "-",
    )
    completed = subprocess.run(command, capture_output=True, check=False)
    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(error or f"failed to decode frame: {frame_path}")
    return completed.stdout


def _edge_energy(luma: bytes) -> float:
    values = list(luma)
    differences: list[int] = []
    for row in range(16):
        for column in range(16):
            index = row * 16 + column
            if column < 15:
                differences.append(abs(values[index] - values[index + 1]))
            if row < 15:
                differences.append(abs(values[index] - values[index + 16]))
    return sum(differences) / len(differences)


def _mean_absolute_difference(left: bytes, right: bytes) -> float:
    return sum(abs(a - b) for a, b in zip(left, right)) / len(left)


def _spread_representatives(
    accepted: tuple[VideoFrameAssessment, ...],
    *,
    maximum: int,
) -> tuple[VideoFrameAssessment, ...]:
    if len(accepted) <= maximum:
        return accepted
    indexes = {
        round(position * (len(accepted) - 1) / (maximum - 1))
        for position in range(maximum)
    }
    return tuple(accepted[index] for index in sorted(indexes))


def _write_inspection_report(result: VideoCandidateInspection) -> None:
    data = {
        "schema_version": "1.0",
        "status": result.status,
        "asset": _jsonable(asdict(result.asset)),
        "media_facts": _jsonable(asdict(result.media_facts)),
        "source_classification": list(result.source_classification),
        "analysis_plan": _jsonable(asdict(result.analysis_plan)),
        "accepted_frames": _jsonable(asdict(result)["accepted_frames"]),
        "rejected_frames": _jsonable(asdict(result)["rejected_frames"]),
        "representative_candidates": _jsonable(asdict(result)["representative_candidates"]),
        "formal_profile_published": False,
    }
    result.report_path.parent.mkdir(parents=True, exist_ok=True)
    result.report_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_batch_inspection_report(result: VideoCandidateBatchInspection) -> None:
    data = {
        "schema_version": "1.0",
        "status": result.status,
        "product_id": result.product_id,
        "source_classification": list(result.source_classification),
        "expected_count": result.expected_count,
        "discovered_count": result.discovered_count,
        "recommendation_allowed": result.recommendation_allowed,
        "candidates": [
            {
                "asset_id": item.asset.asset_id,
                "source_relative_path": item.asset.source_relative_path,
                "status": item.status,
                "duration_seconds": item.media_facts.duration_seconds,
                "resolution": [item.media_facts.width, item.media_facts.height],
                "has_audio": item.media_facts.has_audio,
                "representative_candidates": [
                    {
                        "timestamp_seconds": frame.frame.timestamp_seconds,
                        "frame_path": str(frame.frame.frame_path),
                    }
                    for frame in item.representative_candidates
                ],
                "inspection_report": str(item.report_path),
            }
            for item in result.inspections
        ],
        "formal_profile_published": False,
    }
    result.report_path.parent.mkdir(parents=True, exist_ok=True)
    result.report_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _sync_candidate_review_to_batch_reports(
    paths: ProjectPaths,
    inspection_report_path: Path,
    codex_review: dict,
) -> None:
    batches_root = (
        paths.generated_dir / "cache" / "video-tracer-inspection" / "batches"
    )
    if not batches_root.is_dir():
        return
    target = inspection_report_path.resolve()
    for batch_report in batches_root.rglob("candidate-batch.json"):
        data = json.loads(batch_report.read_text(encoding="utf-8"))
        changed = False
        for candidate in data.get("candidates", []):
            candidate_report = candidate.get("inspection_report")
            if not candidate_report:
                continue
            if Path(candidate_report).expanduser().resolve() != target:
                continue
            candidate["status"] = "codex_review_completed"
            candidate["codex_review"] = codex_review
            changed = True
        if not changed:
            continue
        temporary = batch_report.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(batch_report)


def _sync_candidate_confirmation_to_batch_reports(
    paths: ProjectPaths,
    inspection_report_path: Path,
    tracer_confirmation: dict,
) -> None:
    batches_root = (
        paths.generated_dir / "cache" / "video-tracer-inspection" / "batches"
    )
    if not batches_root.is_dir():
        return
    target = inspection_report_path.resolve()
    for batch_report in batches_root.rglob("candidate-batch.json"):
        data = json.loads(batch_report.read_text(encoding="utf-8"))
        changed = False
        confirmed_asset_id = str(tracer_confirmation.get("confirmed_asset_id") or "")
        for candidate in data.get("candidates", []):
            candidate_report = candidate.get("inspection_report")
            if not candidate_report:
                continue
            if Path(candidate_report).expanduser().resolve() != target:
                continue
            candidate["status"] = "tracer_confirmed"
            candidate["tracer_confirmation"] = tracer_confirmation
            changed = True
        if not changed:
            continue
        recommendation = data.get("tracer_recommendation", {})
        if recommendation.get("recommended_asset_id") == confirmed_asset_id:
            data["status"] = "tracer_confirmed"
            data["recommendation_allowed"] = False
            data["tracer_confirmation"] = tracer_confirmation
        temporary = batch_report.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(batch_report)


def _render_staged_video_profile_markdown(profile: dict) -> str:
    segment_lines = []
    for segment in profile["key_segments"]:
        segment_lines.extend(
            [
                f"### {segment['segment_id']}",
                "",
                f"- 时间：{float(segment['start_seconds']):.3f}s–{float(segment['end_seconds']):.3f}s",
                f"- 画面描述：{segment['description']}",
                f"- 动作：{segment['action']}",
                f"- 产品可见度：{segment['product_visibility']}",
                f"- 复用模式：{segment['reuse_mode']}",
                f"- 编辑适用性：{segment['editing_suitability']}",
                "",
            ]
        )
    representative_lines = [
        (
            f"- {item['timestamp_seconds']:.3f}s：{item.get('description', '')} "
            f"（{item['generated_ref']}）"
        )
        for item in profile["representative_frames"]
    ]
    return "\n".join(
        [
            "---",
            'type: "video_profile_draft"',
            f'id: "{profile["profile_id"]}"',
            f'title: "{profile["title"]}"',
            f'profile_revision: "{profile["profile_revision"]}"',
            f'content_digest: "{profile["content_digest"]}"',
            f'video_asset_id: "{profile["video_asset_id"]}"',
            f'product_id: "{profile["product_id"]}"',
            f'source_revision: "{profile["source_revision"]}"',
            'processing_state: "review_required"',
            "---",
            "",
            "# 视频讲了什么",
            "",
            profile["summary"],
            "",
            "## 关键片段",
            "",
            *segment_lines,
            "## 代表帧",
            "",
            *representative_lines,
            "",
            "## 可用于",
            "",
            *[f"- {item}" for item in profile["use_capabilities"]],
            "",
            "## 风险与使用边界",
            "",
            *[f"- {item}" for item in profile["risk_summary"]],
            "",
            f"- 原音频策略：{profile['source_audio_use_policy']}",
            f"- 分析完整度：{profile['analysis_completeness']}",
            "",
        ]
    )


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value

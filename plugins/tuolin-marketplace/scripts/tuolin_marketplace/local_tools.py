from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .project_layout import ProjectPaths

Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class PdfTextResult:
    source_pdf: Path
    status: str
    markdown_path: Path | None
    cache_dir: Path | None
    command: tuple[str, ...] | None
    error: str | None = None


@dataclass(frozen=True)
class VideoFrame:
    timestamp: str
    frame_path: Path
    status: str
    command: tuple[str, ...]
    error: str | None = None


@dataclass(frozen=True)
class VideoFrameResult:
    source_video: Path
    frames: tuple[VideoFrame, ...]


def prepare_pdf_text(
    pdf_path: Path,
    paths: ProjectPaths,
    mineru_command: str = "mineru",
    runner: Runner = subprocess.run,
) -> PdfTextResult:
    pdf_path = pdf_path.expanduser().resolve()
    _require_under_raw(pdf_path, paths)
    _require_suffix(pdf_path, {".pdf"})

    same_name_markdown = pdf_path.with_suffix(".md")
    if same_name_markdown.exists():
        _require_under_raw(same_name_markdown.resolve(), paths)
        return PdfTextResult(
            source_pdf=pdf_path,
            status="raw_markdown_available",
            markdown_path=same_name_markdown,
            cache_dir=None,
            command=None,
        )

    cache_dir = pdf_markdown_cache_dir(pdf_path, paths)
    cache_dir.mkdir(parents=True, exist_ok=True)
    command = (
        mineru_command,
        "-p",
        str(pdf_path),
        "-o",
        str(cache_dir),
        "-b",
        "pipeline",
        "-l",
        "ch",
    )
    completed = runner(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return PdfTextResult(
            source_pdf=pdf_path,
            status="conversion_failed",
            markdown_path=None,
            cache_dir=cache_dir,
            command=command,
            error=_tool_error(completed),
        )

    return PdfTextResult(
        source_pdf=pdf_path,
        status="converted_to_cache",
        markdown_path=_find_first_markdown(cache_dir),
        cache_dir=cache_dir,
        command=command,
    )


def extract_video_keyframes(
    video_path: Path,
    paths: ProjectPaths,
    ffmpeg_path: str = "ffmpeg",
    timestamps: Sequence[str] = ("00:00:00",),
    runner: Runner = subprocess.run,
) -> VideoFrameResult:
    video_path = video_path.expanduser().resolve()
    _require_under_raw(video_path, paths)
    _require_suffix(video_path, {".mp4", ".mov", ".m4v", ".avi", ".mkv"})

    output_dir = video_frame_cache_dir(video_path, paths)
    output_dir.mkdir(parents=True, exist_ok=True)

    frames: list[VideoFrame] = []
    for index, timestamp in enumerate(timestamps):
        output_path = output_dir / f"frame_{index:03d}_{_safe_timestamp(timestamp)}.jpg"
        command = (
            ffmpeg_path,
            "-y",
            "-ss",
            timestamp,
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            str(output_path),
        )
        completed = runner(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            status = "extracted_to_cache"
            error = None
        else:
            status = "extraction_failed"
            error = _tool_error(completed)
        frames.append(
            VideoFrame(
                timestamp=timestamp,
                frame_path=output_path,
                status=status,
                command=command,
                error=error,
            )
        )
    return VideoFrameResult(source_video=video_path, frames=tuple(frames))


def write_tool_report(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def pdf_markdown_cache_dir(pdf_path: Path, paths: ProjectPaths) -> Path:
    relative = pdf_path.resolve().relative_to(paths.raw_dir)
    return paths.generated_dir / "cache" / "pdf-markdown" / relative.with_suffix("")


def video_frame_cache_dir(video_path: Path, paths: ProjectPaths) -> Path:
    relative = video_path.resolve().relative_to(paths.raw_dir)
    return paths.generated_dir / "cache" / "video-frames" / relative.with_suffix("")


def _require_under_raw(path: Path, paths: ProjectPaths) -> None:
    try:
        path.relative_to(paths.raw_dir)
    except ValueError as exc:
        raise ValueError(f"input must be under raw_dir: {path}") from exc


def _require_suffix(path: Path, allowed_suffixes: set[str]) -> None:
    if path.suffix.lower() not in allowed_suffixes:
        allowed = ", ".join(sorted(allowed_suffixes))
        raise ValueError(f"unsupported file type {path.suffix!r}; expected one of: {allowed}")


def _find_first_markdown(cache_dir: Path) -> Path | None:
    markdown_files = sorted(cache_dir.rglob("*.md"))
    return markdown_files[0] if markdown_files else None


def _safe_timestamp(timestamp: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in timestamp).strip("_") or "t"


def _tool_error(completed: subprocess.CompletedProcess[str]) -> str:
    stderr = (completed.stderr or "").strip()
    stdout = (completed.stdout or "").strip()
    if stderr:
        return stderr
    if stdout:
        return stdout
    return f"command failed with exit code {completed.returncode}"


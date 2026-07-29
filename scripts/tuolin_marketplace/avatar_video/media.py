from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any


def run_ffmpeg(command: list[str]) -> None:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError(f"找不到媒体命令：{command[0]}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()[-2000:]
        raise RuntimeError(f"媒体命令执行失败：{detail}")


def probe_media(path: Path, *, ffprobe_command: str = "ffprobe") -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= 0:
        raise ValueError(f"媒体文件不存在或为空：{path}")
    try:
        completed = subprocess.run(
            [
                ffprobe_command,
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"找不到 ffprobe 命令：{ffprobe_command}") from exc
    if completed.returncode != 0:
        raise ValueError(f"媒体不可读：{(completed.stderr or '').strip()}")
    payload = json.loads(completed.stdout or "{}")
    streams = list(payload.get("streams") or [])
    duration = float((payload.get("format") or {}).get("duration") or 0)
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    frame_rate = 0.0
    if video:
        raw_rate = str(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1")
        try:
            frame_rate = float(Fraction(raw_rate))
        except (ValueError, ZeroDivisionError):
            frame_rate = 0.0
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "duration_seconds": duration,
        "has_video": video is not None,
        "has_audio": audio is not None,
        "width": int((video or {}).get("width") or 0),
        "height": int((video or {}).get("height") or 0),
        "video_codec": (video or {}).get("codec_name"),
        "pixel_format": (video or {}).get("pix_fmt"),
        "frame_rate": frame_rate,
        "audio_codec": (audio or {}).get("codec_name"),
    }

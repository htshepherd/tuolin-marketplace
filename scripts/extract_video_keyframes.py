from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from tuolin_marketplace.local_tools import extract_video_keyframes
from tuolin_marketplace.project_layout import load_config, resolve_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract video keyframes into generated cache.")
    parser.add_argument("video_path", help="Video path under raw_dir.")
    parser.add_argument("--project-dir", default=".", help="Knowledge project directory.")
    parser.add_argument("--config", help="Optional config JSON path.")
    parser.add_argument("--ffmpeg-path", default=None, help="ffmpeg path override.")
    parser.add_argument("--timestamp", action="append", default=[], help="Timestamp to extract.")
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None
    config = load_config(config_path)
    paths = resolve_paths(Path(args.project_dir), config)
    ffmpeg_path = args.ffmpeg_path or config.get("ffmpeg_path", "ffmpeg")
    timestamps = tuple(args.timestamp) if args.timestamp else ("00:00:00",)
    result = extract_video_keyframes(Path(args.video_path), paths, ffmpeg_path=ffmpeg_path, timestamps=timestamps)
    print(json.dumps(_jsonable(asdict(result)), ensure_ascii=False, indent=2))
    return 0 if all(frame.status != "extraction_failed" for frame in result.frames) else 1


def _jsonable(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.project_layout import load_config, resolve_paths
from tuolin_marketplace.video_creation_agent import create_video_creation_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Tuolin quartz-fiber-tape video creation run.")
    parser.add_argument("text", help="Chinese natural-language video creation request.")
    parser.add_argument("--language", required=True, help="Video language version: zh/en, 中文版/英文版.")
    parser.add_argument(
        "--platform",
        action="append",
        required=True,
        help="Target platform. Repeat for both platforms. Supported: youtube_shorts, tiktok.",
    )
    parser.add_argument("--duration", type=int, default=60, help="Video duration: 15, 20, 30, 45, 60, 90, or 120 seconds.")
    parser.add_argument("--audience", default="", help="Target audience.")
    parser.add_argument("--objective", default="", help="Core objective.")
    parser.add_argument("--project-dir", default=".", help="Knowledge project directory.")
    parser.add_argument("--config", help="Optional config JSON path.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None
    paths = resolve_paths(Path(args.project_dir), load_config(config_path))
    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = create_video_creation_run(
        paths,
        args.text,
        language_version=args.language,
        platforms=args.platform,
        duration_seconds=args.duration,
        target_audience=args.audience,
        core_objective=args.objective,
        now=now,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

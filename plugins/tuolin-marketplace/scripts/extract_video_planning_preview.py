from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.project_layout import load_config, resolve_paths
from tuolin_marketplace.video_planning_agent import extract_video_planning_preview


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract one muted, bounded video candidate preview.")
    parser.add_argument("run_id")
    parser.add_argument("profile_id")
    parser.add_argument("segment_id")
    parser.add_argument("planned_use_id")
    parser.add_argument("start_seconds", type=float)
    parser.add_argument("end_seconds", type=float)
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--config")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    paths = resolve_paths(Path(args.project_dir), load_config(Path(args.config) if args.config else None))
    result = extract_video_planning_preview(
        paths,
        run_id=args.run_id,
        profile_id=args.profile_id,
        segment_id=args.segment_id,
        planned_use_id=args.planned_use_id,
        start_seconds=args.start_seconds,
        end_seconds=args.end_seconds,
        ffmpeg_path=args.ffmpeg,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

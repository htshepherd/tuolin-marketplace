from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.project_layout import load_project_config, resolve_paths
from tuolin_marketplace.video_planning_agent import create_video_planning_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an independent Tuolin video-planning run.")
    parser.add_argument("text")
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--platform", action="append", required=True, choices=("youtube_shorts", "tiktok"))
    parser.add_argument("--language", required=True, choices=("zh", "en"))
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--initial-decisions", help="Path to a JSON object of already-known interview decisions.")
    parser.add_argument("--initial-decision-evidence", help="Path to formal-card evidence JSON keyed by decision name.")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--config")
    args = parser.parse_args()
    decisions = json.loads(Path(args.initial_decisions).read_text(encoding="utf-8")) if args.initial_decisions else None
    evidence = json.loads(Path(args.initial_decision_evidence).read_text(encoding="utf-8")) if args.initial_decision_evidence else None
    paths = resolve_paths(Path(args.project_dir), load_project_config(Path(args.project_dir), Path(args.config) if args.config else None))
    result = create_video_planning_run(
        paths,
        args.text,
        product_id=args.product_id,
        platforms=args.platform,
        language_version=args.language,
        duration_seconds=args.duration,
        initial_decisions=decisions,
        initial_decision_evidence=evidence,
        invoked_skill="$tuolin-video-planner",
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

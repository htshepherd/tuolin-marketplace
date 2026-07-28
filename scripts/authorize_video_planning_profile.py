from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.project_layout import load_project_config, resolve_paths
from tuolin_marketplace.video_planning_agent import authorize_video_profile_for_planning_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Authorize a shortlisted processed video profile for one planning run.")
    parser.add_argument("run_id")
    parser.add_argument("profile_id")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--config")
    args = parser.parse_args()
    paths = resolve_paths(Path(args.project_dir), load_project_config(Path(args.project_dir), Path(args.config) if args.config else None))
    print(json.dumps(authorize_video_profile_for_planning_run(paths, args.run_id, args.profile_id), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

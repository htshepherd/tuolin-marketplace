from __future__ import annotations

import argparse
import json

from tuolin_marketplace.video_planning_agent import resume_video_planning_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect and resume an independent video-planning run.")
    parser.add_argument("run_dir")
    args = parser.parse_args()
    print(json.dumps(resume_video_planning_run(args.run_dir).to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

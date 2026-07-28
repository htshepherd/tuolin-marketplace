from __future__ import annotations

import argparse
import json

from tuolin_marketplace.video_planning_agent import confirm_video_shot_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Confirm shot plan and narration, then automatically generate SRT.")
    parser.add_argument("run_dir")
    args = parser.parse_args()
    print(json.dumps(confirm_video_shot_plan(args.run_dir).to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

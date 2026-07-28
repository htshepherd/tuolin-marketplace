from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.video_planning_agent import write_video_shot_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Write and validate a production-ready video shot plan.")
    parser.add_argument("run_dir")
    parser.add_argument("plan_json")
    args = parser.parse_args()
    plan = json.loads(Path(args.plan_json).read_text(encoding="utf-8"))
    print(json.dumps(write_video_shot_plan(args.run_dir, plan).to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

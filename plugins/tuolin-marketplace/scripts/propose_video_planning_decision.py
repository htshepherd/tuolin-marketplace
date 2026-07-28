from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.video_planning_agent import propose_video_planning_decision


def main() -> int:
    parser = argparse.ArgumentParser(description="Propose one contextual video-planning decision.")
    parser.add_argument("run_dir")
    parser.add_argument("proposal_json")
    args = parser.parse_args()
    proposal = json.loads(Path(args.proposal_json).read_text(encoding="utf-8"))
    print(json.dumps(propose_video_planning_decision(args.run_dir, proposal).to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

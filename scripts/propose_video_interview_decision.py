from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.video_creation_agent import propose_video_interview_decision


def main() -> int:
    parser = argparse.ArgumentParser(description="Record one Codex-reasoned video interview proposal.")
    parser.add_argument("run_dir", help="Video creation run directory.")
    parser.add_argument("proposal_file", help="UTF-8 JSON proposal file.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()
    proposal = json.loads(Path(args.proposal_file).read_text(encoding="utf-8"))
    if not isinstance(proposal, dict):
        raise ValueError("proposal_file 必须包含一个 JSON 对象。")
    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = propose_video_interview_decision(Path(args.run_dir), proposal, now=now)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

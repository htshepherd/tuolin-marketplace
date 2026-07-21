from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.linkedin_search_agent import continue_linkedin_search_interview


def main() -> int:
    parser = argparse.ArgumentParser(description="Answer the current Tuolin LinkedIn search interview question.")
    parser.add_argument("reply", help="Confirmation or replacement answer for the current question only.")
    parser.add_argument("--run-dir", required=True, help="Existing LinkedIn search run directory.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()
    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = continue_linkedin_search_interview(Path(args.run_dir), args.reply, now=now)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

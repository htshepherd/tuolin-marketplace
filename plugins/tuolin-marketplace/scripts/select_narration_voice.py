from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.video_creation_agent import select_voice


def main() -> int:
    parser = argparse.ArgumentParser(description="Select one narration voice sample for a Tuolin video creation run.")
    parser.add_argument("run_dir", help="Video creation run directory.")
    parser.add_argument("sample_id", type=int, help="Voice sample id: 1, 2, or 3.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()
    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = select_voice(Path(args.run_dir), args.sample_id, now=now)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.video_creation_agent import resume_video_creation_run


def main() -> int:
    parser = argparse.ArgumentParser(description="Resume a Tuolin video creation run and print the current pending step.")
    parser.add_argument("run_dir", help="Video creation run directory.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()

    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = resume_video_creation_run(Path(args.run_dir), now=now)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


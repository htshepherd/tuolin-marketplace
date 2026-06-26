from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.video_creation_agent import generate_dreamina_jobs


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Dreamina job plan for a Tuolin video creation run.")
    parser.add_argument("run_dir", help="Video creation run directory.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing Dreamina job plan.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()
    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = generate_dreamina_jobs(Path(args.run_dir), overwrite=args.overwrite, now=now)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

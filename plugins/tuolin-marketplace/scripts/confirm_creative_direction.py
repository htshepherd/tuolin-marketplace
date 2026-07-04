from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.video_creation_agent import confirm_creative_direction


def main() -> int:
    parser = argparse.ArgumentParser(description="Confirm Tuolin video creative directions before video planning.")
    parser.add_argument("run_dir", help="Video creation run directory.")
    parser.add_argument("--primary-direction", required=True, help="Primary video creative direction id, name, or number.")
    parser.add_argument("--supporting-direction", help="Optional supporting video creative direction id, name, or number.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()

    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = confirm_creative_direction(
        Path(args.run_dir),
        primary_direction=args.primary_direction,
        supporting_direction=args.supporting_direction,
        now=now,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

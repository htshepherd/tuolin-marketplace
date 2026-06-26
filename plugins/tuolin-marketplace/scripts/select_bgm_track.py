from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.video_creation_agent import select_bgm_track


def main() -> int:
    parser = argparse.ArgumentParser(description="Record commercially usable BGM selection for a Tuolin video creation run.")
    parser.add_argument("run_dir", help="Video creation run directory.")
    parser.add_argument("--title", required=True, help="BGM track title.")
    parser.add_argument("--source", required=True, help="BGM source or provider.")
    parser.add_argument("--license", required=True, dest="license_name", help="BGM license name.")
    parser.add_argument("--local-path", required=True, help="Local audio file path.")
    parser.add_argument("--license-url", default="", help="License URL if available.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()
    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = select_bgm_track(
        Path(args.run_dir),
        title=args.title,
        source=args.source,
        license_name=args.license_name,
        local_path=Path(args.local_path),
        license_url=args.license_url,
        now=now,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

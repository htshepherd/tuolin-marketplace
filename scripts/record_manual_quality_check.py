from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.video_creation_agent import record_manual_quality_check


def main() -> int:
    parser = argparse.ArgumentParser(description="Record manual audio/visual quality check for a Tuolin video creation run.")
    parser.add_argument("run_dir", help="Video creation run directory.")
    parser.add_argument("--audio-ok", action="store_true", help="Confirm audio passed manual check.")
    parser.add_argument("--visual-ok", action="store_true", help="Confirm visual/subtitle passed manual check.")
    parser.add_argument("--notes", default="", help="Manual check notes.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()
    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = record_manual_quality_check(Path(args.run_dir), audio_ok=args.audio_ok, visual_ok=args.visual_ok, notes=args.notes, now=now)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

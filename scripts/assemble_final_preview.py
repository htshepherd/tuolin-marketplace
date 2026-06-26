from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.video_creation_agent import assemble_final_preview


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble final preview manifest, subtitles, and BGM metadata for a Tuolin video creation run.")
    parser.add_argument("run_dir", help="Video creation run directory.")
    parser.add_argument("--execute", action="store_true", help="Actually call ffmpeg. Default is dry-run manifest generation.")
    parser.add_argument("--ffmpeg-command", default=None, help="ffmpeg command name or path. Defaults to run config.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()
    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = assemble_final_preview(Path(args.run_dir), execute=args.execute, ffmpeg_command=args.ffmpeg_command, now=now)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.video_creation_agent import apply_video_plan_semantic_revision


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a Codex-authored semantic revision to allowed video-plan fields.")
    parser.add_argument("run_dir", help="Video creation run directory.")
    parser.add_argument("change_file", help="UTF-8 JSON file with change_request and changes.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()
    payload = json.loads(Path(args.change_file).read_text(encoding="utf-8"))
    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = apply_video_plan_semantic_revision(
        Path(args.run_dir),
        dict(payload.get("changes") or {}),
        str(payload.get("change_request") or "").strip(),
        now=now,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

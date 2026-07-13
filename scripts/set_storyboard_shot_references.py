from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.video_creation_agent import set_storyboard_shot_reference_images


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set one storyboard shot's inspected ordered image references and continuity checks."
    )
    parser.add_argument("run_dir", help="Video creation run directory.")
    parser.add_argument("reference_file", help="UTF-8 JSON object with shot_id, references, and continuity_checks.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()
    payload = json.loads(Path(args.reference_file).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("reference_file 必须包含一个 JSON 对象。")
    references = payload.get("references") or []
    continuity_checks = payload.get("continuity_checks") or {}
    if not isinstance(references, list):
        raise ValueError("references 必须是数组。")
    if not isinstance(continuity_checks, dict):
        raise ValueError("continuity_checks 必须是对象。")
    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = set_storyboard_shot_reference_images(
        Path(args.run_dir),
        str(payload.get("shot_id") or ""),
        references,
        continuity_checks,
        now=now,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

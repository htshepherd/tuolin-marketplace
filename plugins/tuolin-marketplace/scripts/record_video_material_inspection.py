from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.video_creation_agent import record_material_visual_inspection


def main() -> int:
    parser = argparse.ArgumentParser(description="Record Codex visual inspection results for video-plan candidate images.")
    parser.add_argument("run_dir", help="Video creation run directory.")
    parser.add_argument("assessment_file", help="UTF-8 JSON file containing an assessments array or a raw array.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()
    payload = json.loads(Path(args.assessment_file).read_text(encoding="utf-8"))
    assessments = payload.get("assessments", []) if isinstance(payload, dict) else payload
    if not isinstance(assessments, list):
        raise ValueError("assessment_file 必须是数组，或包含 assessments 数组。")
    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = record_material_visual_inspection(Path(args.run_dir), assessments, now=now)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

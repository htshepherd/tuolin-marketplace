from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.video_creation_agent import record_video_interview_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Record audited trend or image evidence for video creative discovery.")
    parser.add_argument("run_dir", help="Video creation run directory.")
    parser.add_argument("evidence_file", help="UTF-8 JSON object with decision_key, value, evidence, and evidence_source.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()
    payload = json.loads(Path(args.evidence_file).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("evidence_file 必须包含一个 JSON 对象。")
    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = record_video_interview_evidence(
        Path(args.run_dir),
        decision_key=str(payload.get("decision_key") or ""),
        value=str(payload.get("value") or ""),
        evidence=list(payload.get("evidence") or []),
        evidence_source=str(payload.get("evidence_source") or "codex_evidence"),
        now=now,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

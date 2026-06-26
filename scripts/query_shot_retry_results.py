from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.video_creation_agent import query_shot_retry_results


def main() -> int:
    parser = argparse.ArgumentParser(description="Query one Dreamina shot retry result and merge it back into Tuolin video results.")
    parser.add_argument("run_dir", help="Video creation run directory.")
    parser.add_argument("--shot-id", default=None, help="Optional expected shot id, such as 03. Used as a safety check.")
    parser.add_argument("--execute", action="store_true", help="Actually call Dreamina CLI. Default is dry-run.")
    parser.add_argument("--dreamina-command", default=None, help="Dreamina CLI command name or path. Defaults to run config.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()
    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = query_shot_retry_results(
        Path(args.run_dir),
        execute=args.execute,
        dreamina_command=args.dreamina_command,
        now=now,
        expected_shot_id=args.shot_id,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

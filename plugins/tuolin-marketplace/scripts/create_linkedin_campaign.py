from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.linkedin_agent import create_linkedin_campaign_plan
from tuolin_marketplace.project_layout import load_config, resolve_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Tuolin LinkedIn campaign planning package.")
    parser.add_argument("text", help="Chinese LinkedIn campaign request.")
    parser.add_argument("--project-dir", default=".", help="Knowledge project directory.")
    parser.add_argument("--config", help="Optional config JSON path.")
    parser.add_argument("--output-root", help="Optional output root. Defaults to the user's Desktop.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMM timestamp for deterministic tests.")
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None
    paths = resolve_paths(Path(args.project_dir), load_config(config_path))
    output_root = Path(args.output_root) if args.output_root else None
    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M") if args.timestamp else None
    result = create_linkedin_campaign_plan(paths, args.text, output_root=output_root, now=now)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

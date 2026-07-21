from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.linkedin_search_agent import create_linkedin_search_run
from tuolin_marketplace.project_layout import load_config, resolve_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Tuolin product-grounded LinkedIn search run.")
    parser.add_argument("text", help="Natural-language LinkedIn prospect-search request.")
    parser.add_argument("--product-id", help="Optional canonical product ID.")
    parser.add_argument("--project-dir", default=".", help="Knowledge project directory.")
    parser.add_argument("--config", help="Optional config JSON path.")
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()

    paths = resolve_paths(Path(args.project_dir), load_config(Path(args.config) if args.config else None))
    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = create_linkedin_search_run(paths, args.text, product_id=args.product_id, now=now)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.status != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())

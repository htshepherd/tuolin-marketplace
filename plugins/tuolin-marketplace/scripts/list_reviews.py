from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from tuolin_marketplace.project_layout import load_config, resolve_paths
from tuolin_marketplace.review_workflow import list_review_items


def main() -> int:
    parser = argparse.ArgumentParser(description="List open Tuolin OKF review items.")
    parser.add_argument("--project-dir", default=".", help="Knowledge project directory.")
    parser.add_argument("--config", help="Optional config JSON path.")
    parser.add_argument("--partition", help="Optional product or partition name/slug filter.")
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None
    paths = resolve_paths(Path(args.project_dir), load_config(config_path))
    reviews = list_review_items(paths, args.partition)
    print(json.dumps([asdict(item) for item in reviews], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

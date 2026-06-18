from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.project_layout import inspect_project, load_config, resolve_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Tuolin project path boundaries.")
    parser.add_argument("--project-dir", default=".", help="Knowledge project directory.")
    parser.add_argument("--config", help="Optional config JSON path.")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    config_path = Path(args.config) if args.config else None
    paths = resolve_paths(project_dir, load_config(config_path))
    report = inspect_project(paths)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


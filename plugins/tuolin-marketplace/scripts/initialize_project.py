from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.project_layout import initialize_project, load_config, resolve_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a Tuolin local knowledge project.")
    parser.add_argument("--project-dir", default=".", help="Knowledge project directory.")
    parser.add_argument("--config", help="Optional config JSON path.")
    parser.add_argument(
        "--skip-raw-template",
        action="store_true",
        help="Do not create the raw template directories.",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    config_path = Path(args.config) if args.config else None
    paths = resolve_paths(project_dir, load_config(config_path))
    created = initialize_project(paths, include_raw_template=not args.skip_raw_template)
    print(json.dumps({"created_count": len(created), "created": [str(path) for path in created]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


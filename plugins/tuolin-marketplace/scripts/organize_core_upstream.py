from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from tuolin_marketplace.core_upstream import organize_core_upstream, preview_core_upstream
from tuolin_marketplace.project_layout import load_config, resolve_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Organize Tuolin core upstream materials into OKF candidates.")
    parser.add_argument("--project-dir", default=".", help="Knowledge project directory.")
    parser.add_argument("--config", help="Optional config JSON path.")
    parser.add_argument("--preview-only", action="store_true", help="Only generate a preview under generated/cache.")
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None
    paths = resolve_paths(Path(args.project_dir), load_config(config_path))
    result = preview_core_upstream(paths) if args.preview_only else organize_core_upstream(paths)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

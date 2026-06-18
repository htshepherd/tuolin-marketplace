from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.agent_interface import rebuild_agent_interface
from tuolin_marketplace.project_layout import load_config, resolve_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild Tuolin generated agent-interface from knowledge/okf.")
    parser.add_argument("--project-dir", default=".", help="Knowledge project directory.")
    parser.add_argument("--config", help="Optional config JSON path.")
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None
    paths = resolve_paths(Path(args.project_dir), load_config(config_path))
    summary = rebuild_agent_interface(paths)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

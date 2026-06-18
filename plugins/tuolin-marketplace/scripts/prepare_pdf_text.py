from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from tuolin_marketplace.local_tools import prepare_pdf_text
from tuolin_marketplace.project_layout import load_config, resolve_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare PDF text for Tuolin knowledge processing.")
    parser.add_argument("pdf_path", help="PDF path under raw_dir.")
    parser.add_argument("--project-dir", default=".", help="Knowledge project directory.")
    parser.add_argument("--config", help="Optional config JSON path.")
    parser.add_argument("--mineru-command", default=None, help="MinerU command override.")
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None
    config = load_config(config_path)
    paths = resolve_paths(Path(args.project_dir), config)
    mineru_command = args.mineru_command or config.get("mineru_command", "mineru")
    result = prepare_pdf_text(Path(args.pdf_path), paths, mineru_command=mineru_command)
    print(json.dumps(_jsonable(asdict(result)), ensure_ascii=False, indent=2))
    return 0 if result.status != "conversion_failed" else 1


def _jsonable(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


if __name__ == "__main__":
    raise SystemExit(main())


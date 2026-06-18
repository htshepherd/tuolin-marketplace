from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.card_validator import validate_card_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Tuolin OKF knowledge cards.")
    parser.add_argument("paths", nargs="+", help="Markdown files or directories to validate.")
    args = parser.parse_args()

    files: list[Path] = []
    for raw_path in args.paths:
        path = Path(raw_path)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
        else:
            files.append(path)

    results = [validate_card_file(path) for path in files]
    report = [
        {
            "path": str(result.path),
            "skipped": result.skipped,
            "valid": result.valid,
            "errors": list(result.errors),
        }
        for result in results
    ]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(result.valid for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

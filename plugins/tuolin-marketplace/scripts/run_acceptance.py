from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.acceptance_runner import run_acceptance


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Tuolin Marketplace end-to-end acceptance checks.")
    parser.add_argument("--project-dir", help="Optional local project directory. Defaults to a temp acceptance project.")
    parser.add_argument("--no-report", action="store_true", help="Do not write generated/reports/ACCEPTANCE_REPORT.md.")
    args = parser.parse_args()

    report = run_acceptance(
        project_dir=Path(args.project_dir) if args.project_dir else None,
        write_report=not args.no_report,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

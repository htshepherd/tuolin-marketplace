from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from tuolin_marketplace.project_layout import load_config, resolve_paths
from tuolin_marketplace.review_workflow import apply_review_decision


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a confirmed Tuolin OKF review decision.")
    parser.add_argument("review_id", help="Review item card id.")
    parser.add_argument(
        "--decision",
        required=True,
        choices=["approve_external", "approve_internal", "reject", "defer"],
        help="Decision to apply.",
    )
    parser.add_argument("--confirmation-token", required=True, help="Token from preview_review.py output.")
    parser.add_argument("--reviewer", default="human", help="Human reviewer name or label.")
    parser.add_argument("--project-dir", default=".", help="Knowledge project directory.")
    parser.add_argument("--config", help="Optional config JSON path.")
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None
    paths = resolve_paths(Path(args.project_dir), load_config(config_path))
    result = apply_review_decision(
        paths=paths,
        review_id=args.review_id,
        decision=args.decision,
        confirmation_token=args.confirmation_token,
        reviewer=args.reviewer,
    )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

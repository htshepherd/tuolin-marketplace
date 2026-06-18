from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.downstream_context import build_downstream_context
from tuolin_marketplace.project_layout import load_config, resolve_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Tuolin downstream-agent task context.")
    parser.add_argument(
        "task_type",
        choices=["youtube_video", "linkedin_post", "outreach_email", "follow_up_email", "video_script", "customer_support"],
    )
    parser.add_argument("--product-id", help="Optional product card id, e.g. product/quartz_fiber_tape.")
    parser.add_argument("--query", help="Optional scenario, customer question, or task keyword.")
    parser.add_argument("--include-review-items", action="store_true", help="Include review items as risk markers.")
    parser.add_argument("--project-dir", default=".", help="Knowledge project directory.")
    parser.add_argument("--config", help="Optional config JSON path.")
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None
    paths = resolve_paths(Path(args.project_dir), load_config(config_path))
    context = build_downstream_context(
        paths,
        task_type=args.task_type,
        product_id=args.product_id,
        query=args.query,
        include_review_items=args.include_review_items,
    )
    print(json.dumps(context, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

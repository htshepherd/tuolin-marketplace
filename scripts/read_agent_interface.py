from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.agent_interface import (
    evidence_for_card,
    generate_task_context,
    knowledge_status,
    open_reviews,
    read_cards_by_type,
    search_cards,
)
from tuolin_marketplace.project_layout import load_config, resolve_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Read Tuolin generated agent-interface.")
    parser.add_argument("--project-dir", default=".", help="Knowledge project directory.")
    parser.add_argument("--config", help="Optional config JSON path.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status")

    cards_parser = subparsers.add_parser("cards")
    cards_parser.add_argument("card_type")
    cards_parser.add_argument("--include-non-official", action="store_true")

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--include-non-official", action="store_true")
    search_parser.add_argument("--limit", type=int, default=10)

    evidence_parser = subparsers.add_parser("evidence")
    evidence_parser.add_argument("card_id")

    subparsers.add_parser("reviews")

    context_parser = subparsers.add_parser("context")
    context_parser.add_argument("context_id")
    context_parser.add_argument("card_ids", nargs="+")
    context_parser.add_argument("--task-type", default="generic")

    args = parser.parse_args()
    config_path = Path(args.config) if args.config else None
    paths = resolve_paths(Path(args.project_dir), load_config(config_path))

    if args.command == "status":
        payload = knowledge_status(paths)
    elif args.command == "cards":
        payload = read_cards_by_type(paths, args.card_type, args.include_non_official)
    elif args.command == "search":
        payload = search_cards(paths, args.query, args.include_non_official, args.limit)
    elif args.command == "evidence":
        payload = evidence_for_card(paths, args.card_id)
    elif args.command == "reviews":
        payload = open_reviews(paths)
    elif args.command == "context":
        payload = generate_task_context(paths, args.context_id, args.card_ids, args.task_type)
    else:
        raise SystemExit(f"Unsupported command: {args.command}")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

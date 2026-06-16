from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.project_layout import load_config, resolve_paths
from tuolin_marketplace.question_answering import answer_question


def main() -> int:
    parser = argparse.ArgumentParser(description="Answer a Tuolin business question from generated official cards.")
    parser.add_argument("question", help="Chinese business question.")
    parser.add_argument("--audience", choices=["internal", "external"], default="internal")
    parser.add_argument("--project-dir", default=".", help="Knowledge project directory.")
    parser.add_argument("--config", help="Optional config JSON path.")
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None
    paths = resolve_paths(Path(args.project_dir), load_config(config_path))
    result = answer_question(paths, args.question, args.audience)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

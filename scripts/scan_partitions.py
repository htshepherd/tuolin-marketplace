from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.partitions import (
    PARTITIONS,
    find_partition,
    mark_partition_organized,
    scan_all_partitions,
    scan_partition,
    summaries_to_json,
)
from tuolin_marketplace.project_layout import load_config, resolve_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan Tuolin raw business partitions.")
    parser.add_argument("--project-dir", default=".", help="Knowledge project directory.")
    parser.add_argument("--config", help="Optional config JSON path.")
    parser.add_argument("--partition", help="Partition name or slug.")
    parser.add_argument(
        "--mark-organized",
        action="store_true",
        help="Store the current raw fingerprint for the selected partition or all partitions.",
    )
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None
    paths = resolve_paths(Path(args.project_dir), load_config(config_path))

    if args.partition:
        definition = find_partition(args.partition)
        if definition is None:
            raise SystemExit(f"Unknown or ambiguous partition: {args.partition}")
        definitions = [definition]
    else:
        definitions = list(PARTITIONS)

    if args.mark_organized:
        snapshots = [str(mark_partition_organized(paths, definition)) for definition in definitions]
        print(json.dumps({"marked_organized": snapshots}, ensure_ascii=False, indent=2))
        return 0

    if args.partition:
        summaries = [scan_partition(paths, definitions[0])]
    else:
        summaries = scan_all_partitions(paths)
    print(json.dumps(summaries_to_json(summaries), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

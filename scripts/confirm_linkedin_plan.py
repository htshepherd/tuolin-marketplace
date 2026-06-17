from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.linkedin_agent import confirm_linkedin_campaign_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Confirm a Tuolin LinkedIn campaign plan and create the Chinese 30-day draft.")
    parser.add_argument("--campaign-dir", required=True, help="LinkedIn campaign directory.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing Chinese 30-day draft.")
    args = parser.parse_args()

    result = confirm_linkedin_campaign_plan(Path(args.campaign_dir), overwrite=args.overwrite)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

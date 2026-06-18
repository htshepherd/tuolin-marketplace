from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.linkedin_agent import confirm_linkedin_chinese_draft


def main() -> int:
    parser = argparse.ArgumentParser(description="Confirm a Tuolin LinkedIn Chinese draft and create the English publishing package.")
    parser.add_argument("--campaign-dir", required=True, help="LinkedIn campaign directory.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing English publishing package files.")
    args = parser.parse_args()

    result = confirm_linkedin_chinese_draft(Path(args.campaign_dir), overwrite=args.overwrite)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.linkedin_agent import generate_linkedin_publishing_images


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate watermarked Tuolin LinkedIn publishing images.")
    parser.add_argument("--campaign-dir", required=True, help="LinkedIn campaign directory.")
    parser.add_argument("--logo", required=True, help="Transparent logo image path.")
    parser.add_argument("--source-image", required=True, help="Source product/application image path.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing publishing images.")
    args = parser.parse_args()

    result = generate_linkedin_publishing_images(
        Path(args.campaign_dir),
        logo_path=Path(args.logo),
        source_image_path=Path(args.source_image),
        overwrite=args.overwrite,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

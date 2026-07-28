from __future__ import annotations

import argparse
import json
from pathlib import Path

from tuolin_marketplace.video_planning_agent import handle_video_planning_reply


def main() -> int:
    parser = argparse.ArgumentParser(description="Record the reply to the current video-planning decision.")
    parser.add_argument("run_dir")
    parser.add_argument("reply")
    parser.add_argument("--remaining-recommendations", help="JSON file used only after explicit all-remaining authorization.")
    args = parser.parse_args()
    recommendations = (
        json.loads(Path(args.remaining_recommendations).read_text(encoding="utf-8"))
        if args.remaining_recommendations
        else None
    )
    print(
        json.dumps(
            handle_video_planning_reply(
                args.run_dir,
                args.reply,
                remaining_recommendations=recommendations,
            ).to_dict(),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

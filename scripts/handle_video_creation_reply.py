from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tuolin_marketplace.video_creation_agent import handle_video_creation_reply


def main() -> int:
    parser = argparse.ArgumentParser(description="Handle a natural-language confirmation reply for a Tuolin video creation run.")
    parser.add_argument("run_dir", help="Video creation run directory.")
    parser.add_argument(
        "reply",
        help=(
            "Natural-language reply, such as 生成分镜, 确认策划, 声音选 2, "
            "确认即梦生成, 重做镜头 03, 提交重做镜头 03, 查询重做镜头 03, "
            "修改策划, 修改分镜, 修改镜头03, 人工音视频检查通过, or 更换背景音乐."
        ),
    )
    parser.add_argument("--timestamp", help="Optional YYYYMMDD_HHMMSS timestamp for deterministic tests.")
    args = parser.parse_args()

    now = datetime.strptime(args.timestamp, "%Y%m%d_%H%M%S") if args.timestamp else None
    result = handle_video_creation_reply(Path(args.run_dir), args.reply, now=now)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

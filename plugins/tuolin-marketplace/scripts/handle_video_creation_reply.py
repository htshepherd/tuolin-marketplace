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
            "Natural-language reply, such as 按推荐, 剩下都按推荐, 确认策划, "
            "修改策划, 确认分镜, 删除镜头 03, 镜头 04 图片换成 E:/path/image.jpg, "
            "确认即梦生成, 提交即梦任务, 查询即梦结果, 确认镜头, or 合并视频."
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

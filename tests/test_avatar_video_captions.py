from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.avatar_video.captions import write_srt


class AvatarVideoCaptionTests(unittest.TestCase):
    def test_english_srt_uses_only_the_confirmed_english_narration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            narration = "Meet the product. Review the evidence before selecting it."
            path = write_srt(narration, "en", 30, Path(tmp) / "captions.srt")
            text = path.read_text(encoding="utf-8")
            spoken = _spoken_text(text)
            self.assertEqual(spoken, narration)
            self.assertNotRegex(text, r"[\u4e00-\u9fff]")
            self.assertIn("00:00:30,000", text)

    def test_chinese_srt_uses_only_the_confirmed_chinese_narration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            narration = "这是产品介绍。请查看正式参数并联系我们。"
            path = write_srt(narration, "zh", 45, Path(tmp) / "captions.srt")
            text = path.read_text(encoding="utf-8")
            self.assertEqual(_spoken_text(text), narration)
            self.assertIn("00:00:45,000", text)


def _spoken_text(srt: str) -> str:
    lines = []
    for line in srt.splitlines():
        stripped = line.strip()
        if not stripped or stripped.isdigit() or " --> " in stripped:
            continue
        lines.append(stripped)
    joined = " ".join(lines)
    return re.sub(r"\s+([.!?])", r"\1", joined).replace(" ", "") if re.search(r"[\u4e00-\u9fff]", joined) else joined


if __name__ == "__main__":
    unittest.main()

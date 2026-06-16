from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.card_validator import validate_card_file
from scripts.tuolin_marketplace.core_upstream import organize_core_upstream, preview_core_upstream
from scripts.tuolin_marketplace.partitions import PARTITIONS, mark_partition_organized, scan_partition
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths


class CoreUpstreamTests(unittest.TestCase):
    def test_preview_only_writes_preview_without_knowledge_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            source = paths.raw_dir / "00_知识库核心资料" / "01_产品核心资料" / "石英纤维资料.md"
            source.write_text("石英纤维隔热带核心资料", encoding="utf-8")

            result = preview_core_upstream(paths)

            self.assertEqual(result.candidate_count, 1)
            self.assertTrue(Path(result.preview_path).exists())
            self.assertEqual(list((paths.knowledge_dir / "证据").rglob("*.md")), [])
            self.assertIsNone(result.generated_summary)

            preview = json.loads(Path(result.preview_path).read_text(encoding="utf-8"))
            self.assertEqual(preview["candidates"][0]["related_product_slugs"], ["quartz_fiber_tape"])
            self.assertIn("不会移动", preview["note"])

    def test_core_upstream_generates_candidate_cards_and_review_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            (paths.raw_dir / "00_知识库核心资料" / "01_产品核心资料" / "石英纤维资料.md").write_text(
                "石英纤维隔热带核心资料",
                encoding="utf-8",
            )
            (paths.raw_dir / "00_知识库核心资料" / "02_产品对比资料" / "石英陶瓷对比.md").write_text(
                "石英纤维和陶瓷纤维对比",
                encoding="utf-8",
            )
            (paths.raw_dir / "00_知识库核心资料" / "03_客服常用回答" / "冒烟异味.md").write_text(
                "石英纤维隔热带冒烟异味回答",
                encoding="utf-8",
            )
            (paths.raw_dir / "00_知识库核心资料" / "04_公共内容素材" / "安装视频.mp4").write_text(
                "fake video",
                encoding="utf-8",
            )

            result = organize_core_upstream(paths)

            self.assertEqual(result.candidate_count, 4)
            self.assertEqual(len(result.evidence_cards), 4)
            self.assertEqual(len(result.candidate_cards), 3)
            self.assertEqual(len(result.review_item_cards), 4)
            self.assertEqual(result.generated_summary["validation_error_count"], 0)

            self.assertTrue((paths.knowledge_dir / "客户问题" / "core_upstream").is_dir())
            self.assertTrue((paths.knowledge_dir / "内容素材" / "core_upstream").is_dir())
            self.assertTrue((paths.knowledge_dir / "应用场景" / "core_upstream").is_dir())
            self.assertTrue((paths.knowledge_dir / "复核项" / "quartz_fiber_tape").is_dir())

            invalid = [path for path in paths.knowledge_dir.rglob("*.md") if not validate_card_file(path).valid]
            self.assertEqual(invalid, [])

            cards = json.loads((paths.generated_dir / "indexes" / "cards.json").read_text(encoding="utf-8"))
            non_evidence_official = [
                card for card in cards if card["type"] != "evidence" and card["status"] == "official"
            ]
            self.assertEqual(non_evidence_official, [])

    def test_product_related_core_candidates_count_in_product_partition_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            quartz = next(partition for partition in PARTITIONS if partition.slug == "quartz_fiber_tape")
            product_source = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
            product_source.write_text("report", encoding="utf-8")
            core_source = paths.raw_dir / "00_知识库核心资料" / "01_产品核心资料" / "石英纤维资料.md"
            core_source.write_text("石英纤维隔热带核心资料", encoding="utf-8")
            mark_partition_organized(paths, quartz)

            organize_core_upstream(paths)
            summary = scan_partition(paths, quartz)

            self.assertGreaterEqual(summary.recognized_unapplied_count, 1)
            self.assertEqual(summary.recommended_next_action, "organize_usable")

    def test_core_upstream_does_not_add_a_long_term_business_partition(self) -> None:
        self.assertNotIn("知识库核心资料", [partition.name for partition in PARTITIONS])
        self.assertEqual(len(PARTITIONS), 11)

    def test_core_upstream_does_not_modify_raw_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            source = paths.raw_dir / "00_知识库核心资料" / "03_客服常用回答" / "石英问题.md"
            source.write_text("石英纤维隔热带客服回答", encoding="utf-8")
            raw_before = sorted(path.relative_to(paths.raw_dir).as_posix() for path in paths.raw_dir.rglob("*") if path.is_file())

            organize_core_upstream(paths)

            raw_after = sorted(path.relative_to(paths.raw_dir).as_posix() for path in paths.raw_dir.rglob("*") if path.is_file())
            self.assertEqual(raw_before, raw_after)


if __name__ == "__main__":
    unittest.main()

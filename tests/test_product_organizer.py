from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.card_validator import validate_card_file
from scripts.tuolin_marketplace.partitions import PARTITIONS, scan_partition
from scripts.tuolin_marketplace.product_organizer import organize_product_partition
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths


class ProductOrganizerTests(unittest.TestCase):
    def test_quartz_tracer_generates_cards_and_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            quartz_raw = paths.raw_dir / "01_产品" / "02_石英纤维隔热带"
            (quartz_raw / "01_检测报告与认证" / "report.pdf").write_text("fake pdf", encoding="utf-8")
            (quartz_raw / "02_产品图片" / "product.jpg").write_text("fake image", encoding="utf-8")
            (quartz_raw / "03_产品视频" / "demo.mp4").write_text("fake video", encoding="utf-8")
            (quartz_raw / "04_应用场景素材" / "scene.png").write_text("fake scene", encoding="utf-8")
            (paths.raw_dir / "00_知识库核心资料" / "01_产品核心资料" / "core.md").write_text("core", encoding="utf-8")

            result = organize_product_partition(paths, "石英纤维隔热带")

            self.assertEqual(result.product_card, "product/quartz_fiber_tape")
            self.assertEqual(len(result.evidence_cards), 4)
            self.assertEqual(len(result.content_asset_cards), 3)
            self.assertEqual(len(result.application_scenario_cards), 1)
            self.assertEqual(result.review_item_cards, ("review_item/quartz_fiber_tape/product_facts_pending",))
            self.assertEqual(len(result.card_inventory["content_asset"]), 3)
            self.assertIn("视频创作可用素材卡 3 张", "\n".join(result.completion_receipt["user_receipt"]))
            self.assertTrue(Path(result.report_path).exists())

            product_card = paths.knowledge_dir / "产品" / "石英纤维隔热带.md"
            self.assertTrue(product_card.exists())
            self.assertTrue(validate_card_file(product_card).valid)
            self.assertIn("status: draft", product_card.read_text(encoding="utf-8"))
            receipt = Path(result.report_path).read_text(encoding="utf-8")
            self.assertIn("## 生成或更新的知识卡", receipt)
            self.assertIn("content_asset/quartz_fiber_tape/product_", receipt)

            content_asset = next((paths.knowledge_dir / "内容素材" / "quartz_fiber_tape").glob("product_*.md"))
            content_text = content_asset.read_text(encoding="utf-8")
            self.assertIn("status: official", content_text)
            self.assertIn("usage_scope: review_before_external", content_text)
            self.assertIn("usable_for:", content_text)
            self.assertIn("- video_creation", content_text)
            self.assertIn("source_paths:", content_text)
            self.assertIn("files:", content_text)

            card_paths = list(paths.knowledge_dir.rglob("*.md"))
            invalid = [path for path in card_paths if not validate_card_file(path).valid]
            self.assertEqual(invalid, [])

            cards_index = json.loads((paths.generated_dir / "indexes" / "cards.json").read_text(encoding="utf-8"))
            ids = {card["id"] for card in cards_index}
            self.assertIn("product/quartz_fiber_tape", ids)
            self.assertIn("review_item/quartz_fiber_tape/product_facts_pending", ids)
            self.assertEqual(result.generated_summary["validation_error_count"], 0)

            product_json = json.loads(
                (paths.generated_dir / "agent-interface" / "cards" / "product.json").read_text(encoding="utf-8")
            )
            self.assertEqual([item["id"] for item in product_json], ["product/quartz_fiber_tape"])
            self.assertTrue((paths.generated_dir / "reports" / "BUILD_REPORT.md").exists())

    def test_product_organizer_does_not_generate_other_product_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            quartz_raw = paths.raw_dir / "01_产品" / "02_石英纤维隔热带"
            ceramic_raw = paths.raw_dir / "01_产品" / "01_陶瓷纤维隔热带"
            (quartz_raw / "01_检测报告与认证" / "report.pdf").write_text("fake pdf", encoding="utf-8")
            (ceramic_raw / "01_检测报告与认证" / "ceramic.pdf").write_text("fake pdf", encoding="utf-8")

            organize_product_partition(paths, "石英纤维隔热带")

            self.assertTrue((paths.knowledge_dir / "产品" / "石英纤维隔热带.md").exists())
            self.assertFalse((paths.knowledge_dir / "产品" / "陶瓷纤维隔热带.md").exists())

    def test_product_organizer_only_uses_the_requested_product_raw_partition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            quartz_raw = paths.raw_dir / "01_产品" / "02_石英纤维隔热带"
            (quartz_raw / "01_检测报告与认证" / "report.pdf").write_text("fake pdf", encoding="utf-8")
            (paths.raw_dir / "00_知识库核心资料" / "01_产品核心资料" / "石英核心.md").write_text(
                "石英核心资料",
                encoding="utf-8",
            )
            (paths.raw_dir / "04_市场情报" / "01_市场现状与平台调研" / "石英市场.md").write_text(
                "石英市场资料",
                encoding="utf-8",
            )
            (paths.raw_dir / "05_销售物料" / "01_Datasheet" / "石英datasheet.md").write_text(
                "Special Glass Fiber Tape",
                encoding="utf-8",
            )

            organize_product_partition(paths, "石英纤维隔热带")

            cards = json.loads((paths.generated_dir / "indexes" / "cards.json").read_text(encoding="utf-8"))
            for card in cards:
                self.assertEqual(card["raw_partitions"], ["raw/01_产品/02_石英纤维隔热带/"])
                for source_path in card.get("source_paths", []):
                    self.assertTrue(source_path.startswith("raw/01_产品/02_石英纤维隔热带/"))

    def test_product_organizer_marks_partition_pending_review_after_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            quartz = next(partition for partition in PARTITIONS if partition.slug == "quartz_fiber_tape")
            (paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf").write_text(
                "fake pdf",
                encoding="utf-8",
            )

            organize_product_partition(paths, "quartz_fiber_tape")
            summary = scan_partition(paths, quartz)

            self.assertEqual(summary.status, "pending_review")
            self.assertEqual(summary.review_item_count, 1)
            self.assertEqual(summary.recommended_next_action, "review_required")

    def test_product_organizer_recovers_corrupt_homepage_without_blocking_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            (paths.knowledge_dir / "首页.md").write_bytes(b"\xff\xfeold navigation")
            report = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
            report.write_text("fake pdf", encoding="utf-8")

            organize_product_partition(paths, "石英纤维隔热带")

            self.assertTrue((paths.knowledge_dir / "产品" / "石英纤维隔热带.md").exists())
            homepage = (paths.knowledge_dir / "首页.md").read_text(encoding="utf-8")
            self.assertIn("# 拓霖知识库", homepage)
            self.assertIn("产品", homepage)
            self.assertTrue((paths.generated_dir / "reports" / "NAVIGATION_RECOVERY_REPORT.md").exists())
            backups = list((paths.generated_dir / "cache" / "navigation-backups").rglob("首页-*.md"))
            self.assertTrue(backups)

    def test_product_organizer_rejects_ambiguous_high_silica(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)

            with self.assertRaises(ValueError):
                organize_product_partition(paths, "高硅氧纤维隔热带")

    def test_product_organizer_rejects_non_product_partition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)

            with self.assertRaises(ValueError):
                organize_product_partition(paths, "标准法规")

    def test_product_organizer_does_not_write_generated_files_into_raw(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            quartz_raw = paths.raw_dir / "01_产品" / "02_石英纤维隔热带"
            report = quartz_raw / "01_检测报告与认证" / "report.pdf"
            report.write_text("fake pdf", encoding="utf-8")
            raw_before = sorted(path.relative_to(paths.raw_dir).as_posix() for path in paths.raw_dir.rglob("*") if path.is_file())

            organize_product_partition(paths, "石英纤维隔热带")

            raw_after = sorted(path.relative_to(paths.raw_dir).as_posix() for path in paths.raw_dir.rglob("*") if path.is_file())
            self.assertEqual(raw_before, raw_after)


if __name__ == "__main__":
    unittest.main()

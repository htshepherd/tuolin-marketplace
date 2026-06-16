from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.natural_language import route_natural_language
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths


class NaturalLanguageRoutingTests(unittest.TestCase):
    def test_organize_knowledge_recommends_one_next_step_without_executing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            report = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
            report.write_text("fake report", encoding="utf-8")

            response = route_natural_language(paths, "整理一下拓霖知识库。")

            self.assertEqual(response.intent, "recommend_next")
            self.assertFalse(response.executed)
            self.assertTrue(response.needs_confirmation)
            self.assertEqual(response.recommended_partition, "石英纤维隔热带")
            self.assertEqual(response.recommended_action, "continue_reading")
            self.assertIn("确认，继续看石英纤维隔热带资料。", response.copyable_reply)
            self.assertFalse((paths.knowledge_dir / "产品" / "石英纤维隔热带.md").exists())

    def test_organize_knowledge_prioritizes_quartz_over_other_actionable_partitions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            quartz_report = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
            quartz_report.write_text("fake report", encoding="utf-8")
            market_report = paths.raw_dir / "04_市场情报" / "01_市场现状与平台调研" / "market.md"
            market_report.write_text("market material", encoding="utf-8")

            response = route_natural_language(paths, "整理一下拓霖知识库。")

            self.assertEqual(response.intent, "recommend_next")
            self.assertEqual(response.recommended_partition, "石英纤维隔热带")
            self.assertEqual(response.copyable_reply, "确认，继续看石英纤维隔热带资料。")

    def test_confirm_recommended_executes_current_product_next_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            report = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
            report.write_text("fake report", encoding="utf-8")

            response = route_natural_language(paths, "确认，按推荐的下一步执行。")

            self.assertTrue(response.executed)
            self.assertEqual(response.intent, "partition_execute")
            self.assertTrue((paths.knowledge_dir / "产品" / "石英纤维隔热带.md").exists())
            self.assertIn("不会对外发布内容", response.message)

    def test_pending_partitions_returns_actionable_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            route_natural_language(paths, "确认，开始整理石英纤维隔热带资料。")

            response = route_natural_language(paths, "查看当前还有哪些资料需要继续整理。")

            self.assertEqual(response.intent, "pending_partitions")
            self.assertTrue(response.needs_confirmation)
            self.assertTrue(all(item["next_step"] != "直接使用现有资料" for item in response.details))

    def test_manual_judgment_material_wording_routes_to_buffer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            source = paths.raw_dir / "90_待迁移素材暂存区" / "90_待人工判定" / "素材.mp4"
            source.write_text("video", encoding="utf-8")

            response = route_natural_language(paths, "整理不好判断归属的素材。")

            self.assertEqual(response.intent, "partition_plan")
            self.assertEqual(response.recommended_partition, "待迁移素材暂存区")

    def test_status_returns_full_partition_status_and_card_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)

            response = route_natural_language(paths, "查看知识库状态。")

            self.assertEqual(response.intent, "knowledge_status")
            self.assertFalse(response.needs_confirmation)
            self.assertEqual(len(response.details["partitions"]), 11)
            self.assertIn("知识卡片数量", response.message)

    def test_full_rebuild_request_returns_partition_queue_and_waits_for_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)

            response = route_natural_language(paths, "全量整理拓霖知识库。")

            self.assertEqual(response.intent, "full_rebuild_plan")
            self.assertFalse(response.executed)
            self.assertTrue(response.needs_confirmation)
            self.assertEqual(len(response.details), 10)
            self.assertIn("按业务分区逐个执行", response.message)

    def test_high_silica_without_variant_is_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)

            response = route_natural_language(paths, "整理高硅氧纤维隔热带资料。")

            self.assertEqual(response.intent, "ambiguous_partition")
            self.assertTrue(response.needs_confirmation)
            self.assertEqual(len(response.details), 2)
            self.assertIn("有背胶和无背胶两个产品", response.message)

    def test_core_material_request_generates_preview_before_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            source = paths.raw_dir / "00_知识库核心资料" / "03_客服常用回答" / "石英问题.md"
            source.write_text("石英纤维隔热带客服回答", encoding="utf-8")

            response = route_natural_language(paths, "阅读一下知识库核心资料，整理进知识库。")

            self.assertEqual(response.intent, "core_upstream_preview")
            self.assertFalse(response.executed)
            self.assertTrue(response.needs_confirmation)
            self.assertEqual(response.details["candidate_count"], 1)
            self.assertFalse((paths.knowledge_dir / "客户问题" / "core_upstream").exists())

    def test_confirm_core_material_request_writes_candidate_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            source = paths.raw_dir / "00_知识库核心资料" / "03_客服常用回答" / "石英问题.md"
            source.write_text("石英纤维隔热带客服回答", encoding="utf-8")

            response = route_natural_language(paths, "确认，继续看核心资料里的图片、报告和视频。")

            self.assertEqual(response.intent, "core_upstream_execute")
            self.assertTrue(response.executed)
            self.assertTrue((paths.knowledge_dir / "客户问题" / "core_upstream").exists())
            self.assertIn("原始资料没有被移动", response.message)

    def test_review_request_lists_open_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            report = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
            report.write_text("fake report", encoding="utf-8")
            route_natural_language(paths, "确认，开始整理石英纤维隔热带资料。")

            response = route_natural_language(paths, "有哪些内容需要我复核？")

            self.assertEqual(response.intent, "review_list")
            self.assertTrue(response.needs_confirmation)
            self.assertEqual(len(response.details), 1)
            self.assertEqual(response.copyable_reply, "请先生成知识卡片修改预览，不要直接写入。")


if __name__ == "__main__":
    unittest.main()

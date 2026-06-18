from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.tuolin_marketplace.agent_interface import rebuild_agent_interface
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

    def test_product_completion_check_is_read_only_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            report = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
            report.write_text("fake report", encoding="utf-8")

            response = route_natural_language(paths, "石英纤维隔热带资料整理完了吗？")

            self.assertEqual(response.intent, "partition_completion_check")
            self.assertFalse(response.executed)
            self.assertEqual(response.recommended_partition, "石英纤维隔热带")
            self.assertIn("当前状态", response.message)
            self.assertFalse((paths.knowledge_dir / "产品" / "石英纤维隔热带.md").exists())

    def test_common_quartz_typo_routes_to_quartz_partition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)

            response = route_natural_language(paths, "整理世英纤维隔热带资料。")

            self.assertEqual(response.intent, "partition_plan")
            self.assertEqual(response.recommended_partition, "石英纤维隔热带")

    def test_core_material_completion_check_does_not_start_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)

            response = route_natural_language(paths, "知识库核心资料整理完了吗？")

            self.assertEqual(response.intent, "core_upstream_completion_check")
            self.assertFalse(response.executed)
            self.assertTrue(response.needs_confirmation)
            self.assertFalse((paths.generated_dir / "cache" / "core-upstream-preview" / "preview.json").exists())

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
            self.assertIn("PDF/视频素材需要继续处理", response.message)

    def test_status_details_include_pdf_and_video_processing_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            pdf = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
            video = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "03_产品视频" / "demo.mp4"
            pdf.write_text("fake pdf", encoding="utf-8")
            video.write_text("fake video", encoding="utf-8")

            response = route_natural_language(paths, "查看知识库状态。")

            quartz = next(item for item in response.details["partitions"] if item["name"] == "石英纤维隔热带")
            self.assertEqual(quartz["pdf_progress"], "0/1")
            self.assertEqual(quartz["video_progress"], "0/1")
            self.assertEqual(quartz["pending_processing_count"], 2)
            self.assertEqual(quartz["product_material_status"], "整理中")
            self.assertEqual(len(quartz["product_material_progress"]), 5)
            self.assertEqual(quartz["product_material_progress"][0]["name"], "01_检测报告与认证")
            self.assertEqual(quartz["product_material_progress"][2]["name"], "03_产品视频")
            self.assertEqual(quartz["product_pending_subfolder_count"], 5)

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

    def test_linkedin_campaign_routes_through_manual_confirmation_steps(self) -> None:
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("Pillow is not available")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(root / "knowledge-project", {})
            initialize_project(paths)
            _write_linkedin_official_cards(paths)
            rebuild_agent_interface(paths)
            logo_path, source_path = _write_linkedin_test_images(root)
            default_logo = paths.project_dir / "assets" / "logo" / "tuolin-logo-transparent.png"
            default_logo.write_bytes(logo_path.read_bytes())
            request = (
                "请做一个30天在Linkedin上发贴宣传的计划。"
                "要求：产品面向欧美市场；产品名称不叫石英纤维，改成特种玻璃纤维带；"
                "重点突出带子的耐高温1000度、不刺痒、不冒烟的特性。"
            )

            with patch.dict(os.environ, {"TUOLIN_LINKEDIN_OUTPUT_ROOT": str(root / "Desktop")}):
                plan_response = route_natural_language(paths, request)

            self.assertEqual(plan_response.intent, "linkedin_campaign_plan")
            self.assertTrue(plan_response.executed)
            self.assertTrue(plan_response.needs_confirmation)
            campaign_dir = Path(plan_response.details["campaign_dir"])
            self.assertEqual(campaign_dir.parent.resolve(), (root / "Desktop").resolve())
            self.assertTrue((campaign_dir / "01_中文策划.md").exists())
            self.assertIn("确认策划，活动文件夹：", plan_response.copyable_reply)

            chinese_response = route_natural_language(paths, plan_response.copyable_reply)

            self.assertEqual(chinese_response.intent, "linkedin_chinese_draft")
            self.assertTrue(chinese_response.executed)
            self.assertTrue((campaign_dir / "02_中文30天贴文总稿.md").exists())
            self.assertEqual(chinese_response.copyable_reply, f"确认中文总稿，活动文件夹：{campaign_dir}")

            english_response = route_natural_language(paths, chinese_response.copyable_reply)

            self.assertEqual(english_response.intent, "linkedin_english_package")
            self.assertTrue(english_response.executed)
            self.assertTrue((campaign_dir / "04_英文发布日历.csv").exists())
            self.assertEqual(len(list((campaign_dir / "daily").glob("day-*.md"))), 30)
            self.assertTrue((campaign_dir / "Manual-Posting-Package" / "Campaign Overview.md").exists())
            self.assertTrue((campaign_dir / "Manual-Posting-Package" / "Publishing Calendar.csv").exists())
            self.assertTrue((campaign_dir / "Manual-Posting-Package" / "Day 01" / "LinkedIn Post Content.md").exists())
            self.assertNotIn("logo：", english_response.copyable_reply)
            self.assertIn(str(default_logo), english_response.message)
            self.assertIn("人工发布包", english_response.message)

            image_response = route_natural_language(
                paths,
                f"生成 LinkedIn 配图，活动文件夹：{campaign_dir}，源图：{source_path}",
            )

            self.assertEqual(image_response.intent, "linkedin_image_assets")
            self.assertTrue(image_response.executed)
            self.assertFalse(image_response.needs_confirmation)
            self.assertEqual(len(list((campaign_dir / "assets" / "publishing-images").glob("day-*.png"))), 30)
            self.assertTrue(
                (campaign_dir / "Manual-Posting-Package" / "Day 01" / "assets" / "linkedin-publishing-image.png").exists()
            )
            self.assertIn("重新生成 LinkedIn Day 01 发布图", image_response.copyable_reply)
            manifest = json.loads((campaign_dir / "campaign-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "image_assets_ready")
            self.assertEqual(manifest["files"]["transparent_logo"], str(default_logo.resolve()))

            single_day_response = route_natural_language(
                paths,
                (
                    f"重新生成 LinkedIn Day 03 发布图，活动文件夹：{campaign_dir}，"
                    "tags：Custom Heat, No Itch, Clean Install"
                ),
            )

            self.assertEqual(single_day_response.intent, "linkedin_single_day_image")
            self.assertTrue(single_day_response.executed)
            self.assertIn("Day 03", single_day_response.message)
            day_3_notes = (campaign_dir / "Manual-Posting-Package" / "Day 03" / "Asset Notes.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Custom Heat, No Itch, Clean Install", day_3_notes)

    def test_linkedin_confirmation_without_campaign_dir_asks_for_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)

            response = route_natural_language(paths, "确认策划，继续生成 LinkedIn 中文总稿。")

            self.assertEqual(response.intent, "linkedin_campaign_dir_required")
            self.assertFalse(response.executed)
            self.assertTrue(response.needs_confirmation)
            self.assertIn("活动文件夹", response.message)

    def test_linkedin_campaign_request_in_invalid_project_returns_business_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)

            response = route_natural_language(paths, "请做一个30天在Linkedin上发贴宣传的计划。")

            self.assertEqual(response.intent, "linkedin_operation_blocked")
            self.assertFalse(response.executed)
            self.assertTrue(response.needs_confirmation)
            self.assertIn("Agent读取接口", response.message)
            self.assertIn("有效知识库项目目录", response.copyable_reply)

    def test_linkedin_image_request_accepts_windows_style_labeled_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)

            response = route_natural_language(
                paths,
                (
                    "生成 LinkedIn 配图，"
                    "活动文件夹：C:\\Users\\worker\\Desktop\\campaign，"
                    "logo：C:\\Users\\worker\\logo.png，"
                    "源图：C:\\Users\\worker\\source.png"
                ),
            )

            self.assertEqual(response.intent, "linkedin_operation_blocked")
            self.assertFalse(response.executed)
            self.assertIn("manifest", response.message)

def _write_linkedin_official_cards(paths) -> None:
    _write_linkedin_card(
        paths.knowledge_dir / "产品" / "石英纤维隔热带.md",
        [
            "card_template_version: product-card-v1",
            "type: product",
            "id: product/quartz_fiber_tape",
            "title: 石英纤维隔热带",
            "aliases:",
            "  - 特种玻璃纤维带",
            "status: official",
            "usage_scope: external_allowed",
            "raw_partitions:",
            "  - raw/01_产品/02_石英纤维隔热带/",
            "tags:",
            "  - 产品",
            "updated_at: 2026-06-17T00:00:00+08:00",
            "last_reviewed_at: 2026-06-17T00:00:00+08:00",
            "evidence_refs: []",
            "review_refs: []",
            "product_line: 隔热带",
            "related_refs: []",
        ],
        "正式产品卡摘要。",
    )
    _write_linkedin_card(
        paths.knowledge_dir / "内容素材" / "quartz_product_photo.md",
        [
            "card_template_version: content-asset-card-v1",
            "type: content_asset",
            "id: content_asset/quartz_product_photo",
            "title: 石英纤维隔热带产品图片",
            "aliases: []",
            "status: official",
            "usage_scope: external_allowed",
            "raw_partitions:",
            "  - raw/01_产品/02_石英纤维隔热带/02_产品图片/",
            "tags:",
            "  - 产品图片",
            "updated_at: 2026-06-17T00:00:00+08:00",
            "last_reviewed_at: 2026-06-17T00:00:00+08:00",
            "evidence_refs: []",
            "review_refs: []",
            "asset_category: 产品图片",
            "media_types:",
            "  - image",
            "related_products:",
            "  - product/quartz_fiber_tape",
            "usable_for:",
            "  - LinkedIn配图",
        ],
        "可用于 LinkedIn 配图的产品素材；不能单独证明产品性能事实。",
    )


def _write_linkedin_card(path: Path, frontmatter_lines: list[str], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + "\n".join(frontmatter_lines) + "\n---\n\n" + body + "\n", encoding="utf-8")


def _write_linkedin_test_images(root: Path) -> tuple[Path, Path]:
    from PIL import Image, ImageDraw

    logo_path = root / "transparent-logo.png"
    source_path = root / "source-product.png"
    logo = Image.new("RGBA", (220, 72), (0, 0, 0, 0))
    draw = ImageDraw.Draw(logo)
    draw.text((12, 16), "TuoLin", fill=(245, 158, 11, 255))
    logo.save(logo_path)

    source = Image.new("RGB", (900, 520), (240, 240, 236))
    draw = ImageDraw.Draw(source)
    draw.rectangle((140, 180, 760, 320), fill=(250, 250, 250), outline=(160, 160, 160), width=4)
    draw.text((300, 235), "Product Tape", fill=(80, 80, 80))
    source.save(source_path)
    return logo_path, source_path


if __name__ == "__main__":
    unittest.main()

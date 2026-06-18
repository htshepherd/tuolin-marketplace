from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scripts.tuolin_marketplace.agent_interface import rebuild_agent_interface
from scripts.tuolin_marketplace.linkedin_agent import (
    EXTERNAL_PRODUCT_NAME_EN,
    EXTERNAL_PRODUCT_NAME_ZH,
    confirm_linkedin_chinese_draft,
    confirm_linkedin_campaign_plan,
    copy_linkedin_campaign_to_desktop,
    create_linkedin_campaign_plan,
    create_linkedin_image_selection_sheet,
    create_linkedin_marketing_review,
    decide_linkedin_marketing_review,
    is_linkedin_campaign_request,
    prepare_linkedin_image_generation,
    validate_linkedin_project,
)
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths


class LinkedInAgentTests(unittest.TestCase):
    def test_identifies_linkedin_campaign_requests(self) -> None:
        self.assertTrue(is_linkedin_campaign_request("请做一个30天在Linkedin上发贴宣传的计划。"))
        self.assertTrue(is_linkedin_campaign_request("帮我做领英30天发帖计划"))
        self.assertFalse(is_linkedin_campaign_request("整理一下拓霖知识库。"))

    def test_validates_current_directory_has_agent_interface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)

            validation = validate_linkedin_project(paths)

            self.assertFalse(validation.valid)
            self.assertTrue(any("Agent读取接口" in error for error in validation.errors))

    def test_creates_chinese_plan_package_from_agent_interface_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(root / "knowledge-project", {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            output_root = root / "Desktop"
            request = (
                "请做一个30天在Linkedin上发贴宣传的计划。"
                "要求：产品面向欧美市场；产品名称不叫石英纤维，改成特种玻璃纤维带；"
                "重点突出带子的耐高温1000度、不刺痒、不冒烟的特性。"
            )

            result = create_linkedin_campaign_plan(
                paths,
                request,
                output_root=output_root,
                now=datetime(2026, 6, 17, 15, 30),
            )

            campaign_dir = Path(result.campaign_dir)
            self.assertEqual(campaign_dir.name, "拓霖领英30天_特种玻璃纤维带_20260617_1530")
            self.assertTrue((campaign_dir / "daily").is_dir())
            self.assertTrue((campaign_dir / "assets" / "logo").is_dir())
            self.assertTrue((campaign_dir / "assets" / "source-images").is_dir())
            self.assertFalse((campaign_dir / "assets" / "publishing-images").exists())
            plan_text = (campaign_dir / "01_中文策划.md").read_text(encoding="utf-8")
            self.assertIn(EXTERNAL_PRODUCT_NAME_ZH, plan_text)
            self.assertIn(EXTERNAL_PRODUCT_NAME_EN, plan_text)
            self.assertIn("内容素材卡：1 张（只用于配图，不证明产品事实）", plan_text)
            self.assertIn("确认本策划后", plan_text)
            self.assertFalse((campaign_dir / "02_中文30天贴文总稿.md").exists())

            manifest = json.loads((campaign_dir / "campaign-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "planning_ready")
            self.assertEqual([item["status"] for item in manifest["status_history"]], ["planning_ready"])
            self.assertEqual(manifest["product"]["external_name_zh"], EXTERNAL_PRODUCT_NAME_ZH)
            self.assertFalse(manifest["context"]["raw_access"])
            self.assertFalse(manifest["context"]["policy"]["content_assets_prove_product_facts"])
            self.assertEqual(manifest["content_assets"][0]["id"], "content_asset/quartz_product_photo")
            self.assertFalse(manifest["image_policy"]["content_assets_prove_product_facts"])
            self.assertEqual(
                [item["source"] for item in manifest["claim_sources"]],
                ["campaign_user_confirmed", "campaign_user_confirmed", "campaign_user_confirmed"],
            )

    def test_confirm_plan_creates_chinese_30_day_draft_and_updates_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(root / "knowledge-project", {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            request = (
                "请做一个30天在Linkedin上发贴宣传的计划。"
                "要求：产品面向欧美市场；产品名称不叫石英纤维，改成特种玻璃纤维带；"
                "重点突出带子的耐高温1000度、不刺痒、不冒烟的特性。"
            )
            created = create_linkedin_campaign_plan(
                paths,
                request,
                output_root=root / "Desktop",
                now=datetime(2026, 6, 17, 15, 30),
            )

            result = confirm_linkedin_campaign_plan(Path(created.campaign_dir))

            campaign_dir = Path(created.campaign_dir)
            draft_path = campaign_dir / "02_中文30天贴文总稿.md"
            self.assertEqual(result.status, "chinese_draft_ready")
            self.assertTrue(draft_path.exists())
            draft_text = draft_path.read_text(encoding="utf-8")
            self.assertEqual(draft_text.count("### Day "), 30)
            self.assertIn("### Day 1: 对外名称发布", draft_text)
            self.assertIn("### Day 30: 询盘收口", draft_text)
            self.assertIn(EXTERNAL_PRODUCT_NAME_ZH, draft_text)
            self.assertIn(EXTERNAL_PRODUCT_NAME_EN, draft_text)
            self.assertIn("优先使用已批准内容素材", draft_text)
            self.assertIn("content_asset/quartz_product_photo", draft_text)
            self.assertNotIn("Quartz Fiber Tape", draft_text)
            self.assertIn("tuolin@tuolintech.com", draft_text)
            self.assertIn("确认中文30天贴文总稿后", draft_text)

            manifest = json.loads((campaign_dir / "campaign-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "chinese_draft_ready")
            self.assertEqual(
                [item["status"] for item in manifest["status_history"]],
                ["planning_ready", "marketing_review_skipped", "chinese_draft_ready"],
            )
            self.assertEqual(manifest["marketing_review"]["status"], "skipped")
            self.assertEqual(manifest["files"]["chinese_draft"], str(draft_path))

    def test_marketing_review_can_be_accepted_before_chinese_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(root / "knowledge-project", {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            created = create_linkedin_campaign_plan(
                paths,
                "请做一个30天在Linkedin上发贴宣传的计划。重点突出耐高温1000度、不刺痒、不冒烟。",
                output_root=root / "Desktop",
                now=datetime(2026, 6, 17, 15, 30),
            )

            review = create_linkedin_marketing_review(Path(created.campaign_dir))

            campaign_dir = Path(created.campaign_dir)
            review_path = campaign_dir / "01_中文策划_营销审阅.md"
            self.assertEqual(review.status, "marketing_review_ready")
            self.assertTrue(review_path.exists())
            review_text = review_path.read_text(encoding="utf-8")
            self.assertIn("## 审阅结论", review_text)
            self.assertIn("是否建议进入中文 30 天贴文总稿", review_text)
            manifest = json.loads((campaign_dir / "campaign-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["marketing_review"]["status"], "ready")

            result = decide_linkedin_marketing_review(campaign_dir, "accepted")

            draft_path = campaign_dir / "02_中文30天贴文总稿.md"
            draft_text = draft_path.read_text(encoding="utf-8")
            self.assertEqual(result.status, "chinese_draft_ready")
            self.assertIn("营销策划审阅：已采纳", draft_text)
            manifest = json.loads((campaign_dir / "campaign-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["marketing_review"]["status"], "accepted")
            self.assertTrue(manifest["marketing_review"]["applied_to_chinese_draft"])

    def test_confirm_plan_does_not_silently_overwrite_existing_chinese_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(root / "knowledge-project", {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            created = create_linkedin_campaign_plan(
                paths,
                "请做一个30天在Linkedin上发贴宣传的计划。重点突出耐高温1000度、不刺痒、不冒烟。",
                output_root=root / "Desktop",
                now=datetime(2026, 6, 17, 15, 30),
            )
            confirm_linkedin_campaign_plan(Path(created.campaign_dir))
            manifest_path = Path(created.campaign_dir) / "campaign-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["status"] = "planning_ready"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            with self.assertRaises(FileExistsError):
                confirm_linkedin_campaign_plan(Path(created.campaign_dir))

    def test_confirm_chinese_draft_creates_english_publishing_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(root / "knowledge-project", {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            created = create_linkedin_campaign_plan(
                paths,
                "请做一个30天在Linkedin上发贴宣传的计划。重点突出耐高温1000度、不刺痒、不冒烟。",
                output_root=root / "Desktop",
                now=datetime(2026, 6, 17, 15, 30),
            )
            confirm_linkedin_campaign_plan(Path(created.campaign_dir))

            result = confirm_linkedin_chinese_draft(Path(created.campaign_dir))

            campaign_dir = Path(created.campaign_dir)
            overview_path = campaign_dir / "03_英文发布总览.md"
            calendar_path = campaign_dir / "04_英文发布日历.csv"
            daily_dir = campaign_dir / "daily"
            daily_files = sorted(daily_dir.glob("day-*.md"))
            self.assertEqual(result.status, "english_package_ready")
            self.assertTrue(overview_path.exists())
            self.assertTrue(calendar_path.exists())
            self.assertEqual(len(daily_files), 30)
            self.assertEqual(daily_files[0].name, "day-01.md")
            self.assertEqual(daily_files[-1].name, "day-30.md")
            manual_dir = campaign_dir / "Manual-Posting-Package"
            self.assertTrue((manual_dir / "Campaign Overview.md").exists())
            self.assertTrue((manual_dir / "Publishing Calendar.csv").exists())
            self.assertTrue((manual_dir / "Day 01" / "LinkedIn Post Content.md").exists())
            self.assertTrue((manual_dir / "Day 01" / "Asset Notes.md").exists())
            self.assertTrue((manual_dir / "Day 01" / "assets").is_dir())

            overview_text = overview_path.read_text(encoding="utf-8")
            self.assertIn(EXTERNAL_PRODUCT_NAME_EN, overview_text)
            self.assertIn("manual review and manual LinkedIn posting only", overview_text)
            self.assertNotIn("Quartz Fiber Tape", overview_text.replace("`Quartz Fiber Tape`", ""))

            day_1 = (daily_dir / "day-01.md").read_text(encoding="utf-8")
            self.assertIn("# Day 1:", day_1)
            self.assertIn("## LinkedIn Post", day_1)
            self.assertIn(EXTERNAL_PRODUCT_NAME_EN, day_1)
            self.assertIn("#ThermalInsulation", day_1)
            self.assertIn("#Tuolin", day_1)
            self.assertIn("## Approved Asset Reference", day_1)
            self.assertIn("content_asset/quartz_product_photo", day_1)
            self.assertIn("Manual LinkedIn posting only", day_1)
            self.assertNotIn("Quartz Fiber Tape", day_1)

            calendar_text = calendar_path.read_text(encoding="utf-8")
            self.assertEqual(len(calendar_text.strip().splitlines()), 31)
            self.assertIn("Day 30", calendar_text)
            self.assertIn("asset_reference", calendar_text.splitlines()[0])

            manifest = json.loads((campaign_dir / "campaign-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "english_package_ready")
            self.assertEqual(
                [item["status"] for item in manifest["status_history"]],
                [
                    "planning_ready",
                    "marketing_review_skipped",
                    "chinese_draft_ready",
                    "chinese_draft_confirmed",
                    "english_package_ready",
                ],
            )
            self.assertEqual(manifest["files"]["english_overview"], str(overview_path))
            self.assertEqual(manifest["files"]["english_calendar"], str(calendar_path))
            self.assertEqual(len(manifest["files"]["daily_files"]), 30)
            self.assertEqual(manifest["files"]["manual_package_dir"], str(manual_dir))
            self.assertEqual(len(manifest["files"]["manual_day_dirs"]), 30)

    def test_confirm_chinese_draft_does_not_silently_overwrite_english_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(root / "knowledge-project", {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            created = create_linkedin_campaign_plan(
                paths,
                "请做一个30天在Linkedin上发贴宣传的计划。重点突出耐高温1000度、不刺痒、不冒烟。",
                output_root=root / "Desktop",
                now=datetime(2026, 6, 17, 15, 30),
            )
            confirm_linkedin_campaign_plan(Path(created.campaign_dir))
            confirm_linkedin_chinese_draft(Path(created.campaign_dir))
            manifest_path = Path(created.campaign_dir) / "campaign-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["status"] = "chinese_draft_ready"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            with self.assertRaises(FileExistsError):
                confirm_linkedin_chinese_draft(Path(created.campaign_dir))

    def test_campaign_without_content_assets_generates_image_briefs_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(root / "knowledge-project", {})
            initialize_project(paths)
            _write_official_product_card(paths)
            rebuild_agent_interface(paths)
            created = create_linkedin_campaign_plan(
                paths,
                "请做一个30天在Linkedin上发贴宣传的计划。重点突出耐高温1000度、不刺痒、不冒烟。",
                output_root=root / "Desktop",
                now=datetime(2026, 6, 17, 15, 30),
            )
            confirm_linkedin_campaign_plan(Path(created.campaign_dir))
            confirm_linkedin_chinese_draft(Path(created.campaign_dir))

            campaign_dir = Path(created.campaign_dir)
            manifest = json.loads((campaign_dir / "campaign-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["content_assets"], [])

            draft_text = (campaign_dir / "02_中文30天贴文总稿.md").read_text(encoding="utf-8")
            self.assertIn("当前没有可用真实内容素材", draft_text)
            self.assertIn("不伪装成产品实拍", draft_text)

            day_1 = (campaign_dir / "daily" / "day-01.md").read_text(encoding="utf-8")
            self.assertIn("No approved real content asset is available", day_1)
            self.assertIn("Use image brief only", day_1)
            self.assertNotIn("content_asset/quartz_product_photo", day_1)

    def test_image_selection_sheet_reads_day_assets_and_recommends_categories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(root / "knowledge-project", {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            created = create_linkedin_campaign_plan(
                paths,
                "请做一个30天在Linkedin上发贴宣传的计划。重点突出耐高温1000度、不刺痒、不冒烟。",
                output_root=root / "Desktop",
                now=datetime(2026, 6, 17, 15, 30),
            )
            confirm_linkedin_campaign_plan(Path(created.campaign_dir))
            confirm_linkedin_chinese_draft(Path(created.campaign_dir))
            campaign_dir = Path(created.campaign_dir)
            source_path = campaign_dir / "Manual-Posting-Package" / "Day 01" / "assets" / "main_product.jpg"
            source_path.write_bytes(b"image")

            result = create_linkedin_image_selection_sheet(campaign_dir, 1)

            selection_path = campaign_dir / "Manual-Posting-Package" / "Day 01" / "Publishing Image Selection.md"
            selection_text = selection_path.read_text(encoding="utf-8")
            self.assertEqual(result.status, "image_selection_ready")
            self.assertEqual(Path(result.selection_path), selection_path)
            self.assertIn("## Source Images", selection_text)
            self.assertIn("main_product.jpg", selection_text)
            self.assertIn("## Recommended Categories", selection_text)
            self.assertIn("原图轻量增强型", selection_text)
            self.assertIn("20. 问答科普型", selection_text)
            manifest = json.loads((campaign_dir / "campaign-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "image_selection_ready")
            self.assertEqual(manifest["single_day_images"]["day-01"]["selection_sheet_status"], "shown")
            self.assertFalse((campaign_dir / "assets" / "publishing-images").exists())

    def test_prepare_image_generation_creates_category_dirs_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(root / "knowledge-project", {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            created = create_linkedin_campaign_plan(
                paths,
                "请做一个30天在Linkedin上发贴宣传的计划。重点突出耐高温1000度、不刺痒、不冒烟。",
                output_root=root / "Desktop",
                now=datetime(2026, 6, 17, 15, 30),
            )
            confirm_linkedin_campaign_plan(Path(created.campaign_dir))
            confirm_linkedin_chinese_draft(Path(created.campaign_dir))
            campaign_dir = Path(created.campaign_dir)
            source_path = campaign_dir / "Manual-Posting-Package" / "Day 01" / "assets" / "main_product.jpg"
            source_path.write_bytes(b"image")
            create_linkedin_image_selection_sheet(campaign_dir, 1)

            result = prepare_linkedin_image_generation(
                campaign_dir,
                1,
                1,
                ["原图轻量增强型", "minimal-premium"],
            )

            self.assertEqual(result.status, "image_generation_ready")
            self.assertEqual(result.source_image, str(source_path))
            self.assertEqual([category["slug"] for category in result.categories], ["original-light-enhancement", "minimal-premium"])
            self.assertTrue((campaign_dir / "Manual-Posting-Package" / "Day 01" / "Publish-Images" / "original-light-enhancement").is_dir())
            self.assertTrue((campaign_dir / "Manual-Posting-Package" / "Day 01" / "Publish-Images" / "minimal-premium").is_dir())
            manifest = json.loads((campaign_dir / "campaign-manifest.json").read_text(encoding="utf-8"))
            day_selection = manifest["single_day_images"]["day-01"]
            self.assertEqual(manifest["status"], "image_generation_ready")
            self.assertEqual(day_selection["selected_source_image"]["path"], str(source_path))
            self.assertEqual([category["slug"] for category in day_selection["selected_categories"]], ["original-light-enhancement", "minimal-premium"])
            self.assertEqual(len(day_selection["output_dirs"]), 2)

    def test_prepare_image_generation_copies_output_dirs_to_desktop_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(root / "knowledge-project", {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            created = create_linkedin_campaign_plan(
                paths,
                "请做一个30天在Linkedin上发贴宣传的计划。重点突出耐高温1000度、不刺痒、不冒烟。",
                output_root=root / "Desktop",
                now=datetime(2026, 6, 17, 15, 30),
            )
            confirm_linkedin_campaign_plan(Path(created.campaign_dir))
            confirm_linkedin_chinese_draft(Path(created.campaign_dir))
            campaign_dir = Path(created.campaign_dir)
            desktop_result = copy_linkedin_campaign_to_desktop(
                campaign_dir,
                desktop_dir=root / "DesktopReview",
                now=datetime(2026, 6, 18, 10, 30, 0),
            )
            source_path = campaign_dir / "Manual-Posting-Package" / "Day 01" / "assets" / "main_product.jpg"
            source_path.write_bytes(b"image")
            create_linkedin_image_selection_sheet(campaign_dir, 1)

            result = prepare_linkedin_image_generation(campaign_dir, 1, 1, ["原图轻量增强型"])

            desktop_dir = Path(desktop_result.plan_path)
            self.assertTrue(desktop_dir.exists())
            self.assertTrue((desktop_dir / "02_中文30天贴文总稿.md").exists())
            self.assertEqual(len(result.desktop_output_dirs), 1)
            self.assertTrue(Path(result.desktop_output_dirs[0]).is_dir())
            self.assertEqual(
                Path(result.desktop_output_dirs[0]),
                desktop_dir / "Manual-Posting-Package" / "Day 01" / "Publish-Images" / "original-light-enhancement",
            )
            manifest = json.loads((campaign_dir / "campaign-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["desktop_delivery"]["path"], str(desktop_dir))

    def test_copy_to_desktop_requires_chinese_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(root / "knowledge-project", {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            created = create_linkedin_campaign_plan(
                paths,
                "请做一个30天在Linkedin上发贴宣传的计划。重点突出耐高温1000度、不刺痒、不冒烟。",
                output_root=root / "Desktop",
                now=datetime(2026, 6, 17, 15, 30),
            )

            with self.assertRaises(ValueError):
                copy_linkedin_campaign_to_desktop(Path(created.campaign_dir), desktop_dir=root / "DesktopReview")

    def test_configured_default_logo_path_is_recorded_for_image_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(
                root / "knowledge-project",
                {"linkedin": {"transparent_logo_path": "brand/tuolin-logo.png"}},
            )
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            created = create_linkedin_campaign_plan(
                paths,
                "请做一个30天在Linkedin上发贴宣传的计划。重点突出耐高温1000度、不刺痒、不冒烟。",
                output_root=root / "Desktop",
                now=datetime(2026, 6, 17, 15, 30),
            )

            manifest = json.loads((Path(created.campaign_dir) / "campaign-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["files"]["default_transparent_logo"],
                str((paths.project_dir / "brand" / "tuolin-logo.png").resolve()),
            )

    def test_official_evidence_marks_claims_as_supported_by_external_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(root / "knowledge-project", {})
            initialize_project(paths)
            _write_official_cards_with_performance_evidence(paths)
            rebuild_agent_interface(paths)

            created = create_linkedin_campaign_plan(
                paths,
                "请做一个30天在Linkedin上发贴宣传的计划。重点突出耐高温1000度、不刺痒、不冒烟。",
                output_root=root / "Desktop",
                now=datetime(2026, 6, 17, 15, 30),
            )

            manifest = json.loads((Path(created.campaign_dir) / "campaign-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [item["source"] for item in manifest["claim_sources"]],
                ["official_external_knowledge", "official_external_knowledge", "official_external_knowledge"],
            )
            self.assertFalse(any(item["requires_publish_review"] for item in manifest["claim_sources"]))


def _write_official_cards(paths) -> None:
    _write_official_product_card(paths)
    _write_card(
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


def _write_official_product_card(paths) -> None:
    _write_card(
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


def _write_official_cards_with_performance_evidence(paths) -> None:
    _write_card(
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
            "evidence_refs:",
            "  - evidence/quartz_fiber_tape/performance_claims",
            "review_refs: []",
            "product_line: 隔热带",
            "related_refs: []",
        ],
        "正式产品卡摘要。",
    )
    _write_card(
        paths.knowledge_dir / "证据" / "quartz_fiber_tape" / "performance_claims.md",
        [
            "card_template_version: evidence-card-v1",
            "type: evidence",
            "id: evidence/quartz_fiber_tape/performance_claims",
            "title: 石英纤维隔热带性能证据",
            "aliases: []",
            "status: official",
            "usage_scope: evidence_only",
            "raw_partitions:",
            "  - raw/01_产品/02_石英纤维隔热带/01_检测报告与认证/",
            "tags:",
            "  - 1000度",
            "  - 不刺痒",
            "  - 不冒烟",
            "updated_at: 2026-06-17T00:00:00+08:00",
            "last_reviewed_at: 2026-06-17T00:00:00+08:00",
            "evidence_refs: []",
            "review_refs: []",
            "evidence_type: 检测与人工确认",
            "source_paths:",
            "  - raw/01_产品/02_石英纤维隔热带/01_检测报告与认证/performance.pdf",
            "proves:",
            "  - 耐高温1000度",
            "  - 不刺痒",
            "  - 不冒烟",
            "confidence: high",
        ],
        "正式证据摘要：该产品耐高温1000度，接触不刺痒，使用不冒烟。",
    )


def _write_card(path: Path, frontmatter_lines: list[str], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + "\n".join(frontmatter_lines) + "\n---\n\n" + body + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()

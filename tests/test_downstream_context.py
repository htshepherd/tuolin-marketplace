from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.agent_interface import rebuild_agent_interface
from scripts.tuolin_marketplace.downstream_context import build_downstream_context
from scripts.tuolin_marketplace.product_organizer import organize_product_partition
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths
from scripts.tuolin_marketplace.review_workflow import apply_review_decision, create_review_preview


class DownstreamContextTests(unittest.TestCase):
    def test_external_context_uses_only_official_external_cards_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)

            context = build_downstream_context(
                paths,
                "linkedin_post",
                product_id="product/quartz_fiber_tape",
                query="排气管",
            )

            self.assertEqual(context["audience"], "external")
            self.assertFalse(context["raw_access"])
            self.assertIn("product", context["cards_by_type"])
            self.assertIn("application_scenario", context["cards_by_type"])
            self.assertIn("sales_material", context["cards_by_type"])
            self.assertIn("content_asset", context["cards_by_type"])
            self.assertNotIn("customer_question", context["cards_by_type"])
            self.assertTrue(context["evidence"])
            self.assertEqual(context["risk_items"], [])
            self.assertEqual(context["policy"]["source_boundary"], "generated/agent-interface only")
            self.assertFalse(context["policy"]["content_assets_prove_product_facts"])
            self.assertTrue((paths.generated_dir / "agent-interface" / "contexts" / f"{context['context_id']}.json").exists())

    def test_customer_support_context_can_use_internal_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)

            context = build_downstream_context(
                paths,
                "customer_support",
                product_id="product/quartz_fiber_tape",
                query="冒烟",
            )

            self.assertEqual(context["audience"], "internal")
            self.assertIn("customer_question", context["cards_by_type"])
            question = context["cards_by_type"]["customer_question"][0]
            self.assertEqual(question["usage_scope"], "internal_only")

    def test_review_items_are_risks_not_facts_when_explicitly_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths, leave_open_review=True)

            context = build_downstream_context(
                paths,
                "youtube_video",
                product_id="product/quartz_fiber_tape",
                include_review_items=True,
            )

            self.assertIn("product", context["cards_by_type"])
            self.assertEqual(len(context["risk_items"]), 1)
            self.assertEqual(context["risk_items"][0]["id"], "review_item/quartz_fiber_tape/product_facts_pending")
            self.assertFalse(context["policy"]["review_items_are_facts"])

    def test_context_invalidates_when_related_cards_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            context = build_downstream_context(paths, "video_creation", product_id="product/quartz_fiber_tape")
            context_path = paths.generated_dir / "agent-interface" / "contexts" / f"{context['context_id']}.json"

            product_path = paths.knowledge_dir / "产品" / "石英纤维隔热带.md"
            product_text = product_path.read_text(encoding="utf-8")
            product_path.write_text(product_text.replace("tags:\n  - 产品", "tags:\n  - 已更新\n  - 产品"), encoding="utf-8")
            rebuild_agent_interface(paths)

            invalidated = json.loads(context_path.read_text(encoding="utf-8"))
            self.assertFalse(invalidated["valid"])
            self.assertEqual(invalidated["invalidated_reason"], "agent interface revision changed")

    def test_video_creation_context_reads_only_quartz_product_and_related_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            _write_other_product(paths)
            _write_unrelated_content_asset(paths)
            rebuild_agent_interface(paths)

            context = build_downstream_context(
                paths,
                "video_creation",
                product_id="product/quartz_fiber_tape",
                query="排气管 玄武岩 车间",
            )

            self.assertEqual(context["task_type"], "video_creation")
            self.assertEqual(context["product_id"], "product/quartz_fiber_tape")
            self.assertFalse(context["raw_access"])
            self.assertTrue(context["policy"]["no_keyword_expansion"])
            self.assertEqual(context["policy"]["fixed_product_scope"], "product/quartz_fiber_tape")
            self.assertEqual({card["id"] for card in context["cards_by_type"]["product"]}, {"product/quartz_fiber_tape"})
            self.assertEqual(
                {card["id"] for card in context["cards_by_type"]["content_asset"]},
                {"content_asset/quartz_product_photo"},
            )
            self.assertNotIn("application_scenario", context["cards_by_type"])
            self.assertNotIn("sales_material", context["cards_by_type"])
            self.assertNotIn("customer_question", context["cards_by_type"])
            self.assertFalse(context["policy"]["content_assets_prove_product_facts"])

    def test_video_creation_rejects_other_product_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)

            with self.assertRaisesRegex(ValueError, "video_creation only supports product/quartz_fiber_tape"):
                build_downstream_context(paths, "video_creation", product_id="product/basalt_fiber_tape")

    def test_video_script_is_not_primary_video_creation_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)

            with self.assertRaisesRegex(ValueError, "Unsupported downstream task type: video_script"):
                build_downstream_context(paths, "video_script", product_id="product/quartz_fiber_tape")

    def test_linkedin_search_context_is_product_grounded_without_campaign_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)

            context = build_downstream_context(
                paths,
                "linkedin_search",
                product_id="product/quartz_fiber_tape",
                query="exhaust wrap",
            )

            self.assertEqual(context["task_type"], "linkedin_search")
            self.assertEqual(context["product_id"], "product/quartz_fiber_tape")
            self.assertFalse(context["raw_access"])
            self.assertTrue(context["policy"]["market_terms_search_only"])
            self.assertTrue(context["policy"]["no_keyword_expansion"])
            self.assertEqual(
                {card["id"] for card in context["cards_by_type"]["product"]},
                {"product/quartz_fiber_tape"},
            )
            self.assertIn("sales_material", context["cards_by_type"])
            self.assertNotIn("content_asset", context["cards_by_type"])


def _create_fixture(paths, leave_open_review: bool = False) -> None:
    initialize_project(paths)
    report = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
    report.write_text("fake report", encoding="utf-8")
    organize_product_partition(paths, "石英纤维隔热带")
    if not leave_open_review:
        preview = create_review_preview(paths, "review_item/quartz_fiber_tape/product_facts_pending", "approve_external")
        apply_review_decision(
            paths,
            "review_item/quartz_fiber_tape/product_facts_pending",
            "approve_external",
            preview.confirmation_token,
            reviewer="kkid",
        )
    else:
        product_path = paths.knowledge_dir / "产品" / "石英纤维隔热带.md"
        product_path.write_text(product_path.read_text(encoding="utf-8").replace("status: draft", "status: official").replace("usage_scope: review_before_external", "usage_scope: external_allowed"), encoding="utf-8")
    _write_application_scenario(paths)
    _write_sales_material(paths)
    _write_customer_question(paths)
    _write_content_asset(paths)
    rebuild_agent_interface(paths)


def _write_application_scenario(paths) -> None:
    _write_card(
        paths.knowledge_dir / "应用场景" / "quartz_fiber_tape" / "indoor_exhaust_pipe.md",
        [
            "card_template_version: application-scenario-card-v1",
            "type: application_scenario",
            "id: application_scenario/quartz_fiber_tape/indoor_exhaust_pipe",
            "title: 室内排气管隔热",
            "aliases: []",
            "status: official",
            "usage_scope: external_allowed",
            "raw_partitions:",
            "  - raw/01_产品/02_石英纤维隔热带/",
            "tags:",
            "  - 排气管",
            "updated_at: 2026-06-15T00:00:00+08:00",
            "last_reviewed_at: 2026-06-15T00:00:00+08:00",
            "evidence_refs: []",
            "review_refs: []",
            "scenario_category: 排气管隔热",
            "related_products:",
            "  - product/quartz_fiber_tape",
            "usable_channels:",
            "  - LinkedIn",
        ],
        "室内排气管隔热是已确认应用场景。",
    )


def _write_sales_material(paths) -> None:
    _write_card(
        paths.knowledge_dir / "销售物料" / "quartz_tape_datasheet.md",
        [
            "card_template_version: sales-material-card-v1",
            "type: sales_material",
            "id: sales_material/quartz_tape_datasheet",
            "title: 石英纤维隔热带 Datasheet",
            "aliases: []",
            "status: official",
            "usage_scope: external_allowed",
            "raw_partitions:",
            "  - raw/05_销售物料/01_Datasheet/",
            "tags:",
            "  - Datasheet",
            "updated_at: 2026-06-15T00:00:00+08:00",
            "last_reviewed_at: 2026-06-15T00:00:00+08:00",
            "evidence_refs: []",
            "review_refs: []",
            "material_type: Datasheet",
            "language: 中文",
            "related_products:",
            "  - product/quartz_fiber_tape",
        ],
        "可用于对外内容的 Datasheet 摘要。",
    )


def _write_customer_question(paths) -> None:
    _write_card(
        paths.knowledge_dir / "客户问题" / "quartz_smoke.md",
        [
            "card_template_version: customer-question-card-v1",
            "type: customer_question",
            "id: customer_question/quartz_smoke",
            "title: 石英纤维隔热带冒烟问题",
            "aliases:",
            "  - 冒烟",
            "status: official",
            "usage_scope: internal_only",
            "raw_partitions:",
            "  - raw/06_客户问题与客服反馈/",
            "tags:",
            "  - 冒烟",
            "updated_at: 2026-06-15T00:00:00+08:00",
            "last_reviewed_at: 2026-06-15T00:00:00+08:00",
            "evidence_refs: []",
            "review_refs: []",
            "question_category: 冒烟异味",
            "customer_channel: 客服记录",
            "related_products:",
            "  - product/quartz_fiber_tape",
            "response_status: 已确认内部参考",
        ],
        "客户问题只能作为内部客服参考。",
    )


def _write_content_asset(paths) -> None:
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
            "updated_at: 2026-06-15T00:00:00+08:00",
            "last_reviewed_at: 2026-06-15T00:00:00+08:00",
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


def _write_other_product(paths) -> None:
    _write_card(
        paths.knowledge_dir / "产品" / "玄武岩纤维隔热带.md",
        [
            "card_template_version: product-card-v1",
            "type: product",
            "id: product/basalt_fiber_tape",
            "title: 玄武岩纤维隔热带",
            "aliases: []",
            "status: official",
            "usage_scope: external_allowed",
            "raw_partitions:",
            "  - raw/01_产品/03_玄武岩纤维隔热带/",
            "tags:",
            "  - 产品",
            "updated_at: 2026-06-15T00:00:00+08:00",
            "last_reviewed_at: 2026-06-15T00:00:00+08:00",
            "evidence_refs: []",
            "review_refs: []",
            "product_line: 耐高温隔热带",
            "related_refs: []",
        ],
        "玄武岩纤维隔热带不应进入首期视频创作上下文。",
    )


def _write_unrelated_content_asset(paths) -> None:
    _write_card(
        paths.knowledge_dir / "内容素材" / "basalt_product_photo.md",
        [
            "card_template_version: content-asset-card-v1",
            "type: content_asset",
            "id: content_asset/basalt_product_photo",
            "title: 玄武岩纤维隔热带产品图片",
            "aliases: []",
            "status: official",
            "usage_scope: external_allowed",
            "raw_partitions:",
            "  - raw/01_产品/03_玄武岩纤维隔热带/02_产品图片/",
            "tags:",
            "  - 产品图片",
            "updated_at: 2026-06-15T00:00:00+08:00",
            "last_reviewed_at: 2026-06-15T00:00:00+08:00",
            "evidence_refs: []",
            "review_refs: []",
            "asset_category: 产品图片",
            "media_types:",
            "  - image",
            "related_products:",
            "  - product/basalt_fiber_tape",
            "usable_for:",
            "  - video_creation",
        ],
        "不应进入石英纤维隔热带视频创作上下文的素材。",
    )


def _write_card(path: Path, frontmatter_lines: list[str], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + "\n".join(frontmatter_lines) + "\n---\n\n" + body + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()

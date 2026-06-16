from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.card_validator import parse_frontmatter, validate_card_file
from scripts.tuolin_marketplace.partitions import PARTITIONS, scan_partition
from scripts.tuolin_marketplace.product_organizer import organize_product_partition
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths
from scripts.tuolin_marketplace.review_workflow import (
    apply_review_decision,
    create_review_preview,
    list_review_items,
)


class ReviewWorkflowTests(unittest.TestCase):
    def test_list_review_items_can_filter_by_product_partition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_quartz_review_fixture(paths)

            all_reviews = list_review_items(paths)
            quartz_reviews = list_review_items(paths, "石英纤维隔热带")
            ceramic_reviews = list_review_items(paths, "陶瓷纤维隔热带")

            self.assertEqual(len(all_reviews), 1)
            self.assertEqual(len(quartz_reviews), 1)
            self.assertEqual(ceramic_reviews, [])
            self.assertEqual(quartz_reviews[0].review_id, "review_item/quartz_fiber_tape/product_facts_pending")
            self.assertIn("product/quartz_fiber_tape", quartz_reviews[0].affected_cards)

    def test_preview_review_does_not_modify_knowledge_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_quartz_review_fixture(paths)
            product_path = paths.knowledge_dir / "产品" / "石英纤维隔热带.md"
            before = product_path.read_text(encoding="utf-8")

            preview = create_review_preview(
                paths,
                "review_item/quartz_fiber_tape/product_facts_pending",
                "approve_external",
            )

            self.assertTrue(Path(preview.preview_path).exists())
            self.assertTrue(preview.confirmation_token.startswith("confirm-"))
            self.assertEqual(preview.affected_cards, ("product/quartz_fiber_tape",))
            self.assertEqual(product_path.read_text(encoding="utf-8"), before)

            payload = json.loads(Path(preview.preview_path).read_text(encoding="utf-8"))
            self.assertIn("未提供确认令牌前不会写入", payload["note"])

    def test_apply_review_requires_confirmation_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_quartz_review_fixture(paths)

            with self.assertRaises(ValueError):
                apply_review_decision(
                    paths,
                    "review_item/quartz_fiber_tape/product_facts_pending",
                    "approve_external",
                    "wrong-token",
                    reviewer="kkid",
                )

            product_frontmatter = _frontmatter(paths.knowledge_dir / "产品" / "石英纤维隔热带.md")
            self.assertEqual(product_frontmatter["status"], "draft")

    def test_apply_review_promotes_draft_card_and_archives_review_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            quartz = next(partition for partition in PARTITIONS if partition.slug == "quartz_fiber_tape")
            _create_quartz_review_fixture(paths, initialized=True)
            before_summary = scan_partition(paths, quartz)
            self.assertEqual(before_summary.status, "pending_review")

            preview = create_review_preview(
                paths,
                "review_item/quartz_fiber_tape/product_facts_pending",
                "approve_external",
            )
            result = apply_review_decision(
                paths,
                "review_item/quartz_fiber_tape/product_facts_pending",
                "approve_external",
                preview.confirmation_token,
                reviewer="kkid",
            )

            self.assertEqual(result.updated_cards, ("product/quartz_fiber_tape",))
            product_path = paths.knowledge_dir / "产品" / "石英纤维隔热带.md"
            product_frontmatter = _frontmatter(product_path)
            self.assertEqual(product_frontmatter["status"], "official")
            self.assertEqual(product_frontmatter["usage_scope"], "external_allowed")
            self.assertEqual(product_frontmatter["review_refs"], [])
            self.assertIn("# 复核记录", product_path.read_text(encoding="utf-8"))
            self.assertTrue(validate_card_file(product_path).valid)

            review_path = paths.knowledge_dir / "复核项" / "quartz_fiber_tape" / "product_facts_pending.md"
            review_frontmatter = _frontmatter(review_path)
            self.assertEqual(review_frontmatter["status"], "archived")
            self.assertIn("# 复核记录", review_path.read_text(encoding="utf-8"))
            self.assertTrue(validate_card_file(review_path).valid)

            self.assertEqual(list_review_items(paths), [])
            after_summary = scan_partition(paths, quartz)
            self.assertEqual(after_summary.status, "ready")
            self.assertEqual(after_summary.review_item_count, 0)

            product_json = json.loads(
                (paths.generated_dir / "agent-interface" / "cards" / "product.json").read_text(encoding="utf-8")
            )
            self.assertEqual(product_json[0]["status"], "official")
            self.assertTrue((paths.generated_dir / "reports" / "REVIEW_REPORT.md").exists())
            self.assertIn("复核处理", (paths.knowledge_dir / "变更记录.md").read_text(encoding="utf-8"))

    def test_reject_archives_review_without_updating_affected_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_quartz_review_fixture(paths)

            preview = create_review_preview(paths, "review_item/quartz_fiber_tape/product_facts_pending", "reject")
            apply_review_decision(
                paths,
                "review_item/quartz_fiber_tape/product_facts_pending",
                "reject",
                preview.confirmation_token,
                reviewer="kkid",
            )

            product_frontmatter = _frontmatter(paths.knowledge_dir / "产品" / "石英纤维隔热带.md")
            review_frontmatter = _frontmatter(
                paths.knowledge_dir / "复核项" / "quartz_fiber_tape" / "product_facts_pending.md"
            )
            self.assertEqual(product_frontmatter["status"], "draft")
            self.assertEqual(review_frontmatter["status"], "archived")
            self.assertEqual(list_review_items(paths), [])


def _create_quartz_review_fixture(paths, initialized: bool = False) -> None:
    if not initialized:
        initialize_project(paths)
    raw = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
    raw.write_text("fake report", encoding="utf-8")
    organize_product_partition(paths, "石英纤维隔热带")


def _frontmatter(path: Path) -> dict:
    return parse_frontmatter(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.agent_interface import (
    evidence_for_card,
    generate_task_context,
    knowledge_status,
    open_reviews,
    read_cards_by_type,
    rebuild_agent_interface,
    refresh_agent_interface_after_write,
    search_cards,
)
from scripts.tuolin_marketplace.card_validator import PROFILE
from scripts.tuolin_marketplace.product_organizer import organize_product_partition
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths
from scripts.tuolin_marketplace.review_workflow import apply_review_decision, create_review_preview


class AgentInterfaceTests(unittest.TestCase):
    def test_rebuild_generated_exports_manifest_partitions_and_ten_card_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_official_quartz_fixture(paths)
            shutil.rmtree(paths.generated_dir)

            summary = rebuild_agent_interface(paths)

            self.assertTrue((paths.generated_dir / "indexes" / "cards.json").exists())
            self.assertTrue((paths.generated_dir / "indexes" / "links.json").exists())
            self.assertTrue((paths.generated_dir / "indexes" / "search_index.json").exists())
            self.assertTrue((paths.generated_dir / "agent-interface" / "manifest.json").exists())
            self.assertTrue((paths.generated_dir / "agent-interface" / "manifest_summary.json").exists())
            self.assertTrue((paths.generated_dir / "reports" / "BUILD_REPORT.md").exists())
            self.assertTrue((paths.generated_dir / "reports" / "REVIEW_REPORT.md").exists())

            for card_type in PROFILE["card_types"]:
                self.assertTrue((paths.generated_dir / "agent-interface" / "cards" / f"{card_type}.json").exists())

            manifest = json.loads((paths.generated_dir / "agent-interface" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], "2.0")
            self.assertEqual(len(manifest["partitions"]), 11)
            self.assertIn("knowledge_status", manifest["capabilities"])
            self.assertIn("task_context", manifest["capabilities"])
            self.assertEqual(set(summary["counts_by_type"]), PROFILE["card_types"])
            self.assertIn("partition_totals", summary)

    def test_default_agent_reads_only_official_allowed_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_official_quartz_fixture(paths)

            products = read_cards_by_type(paths, "product")
            reviews = read_cards_by_type(paths, "review_item")
            all_reviews = read_cards_by_type(paths, "review_item", include_non_official=True)
            search_results = search_cards(paths, "石英纤维隔热带")

            self.assertEqual([item["id"] for item in products], ["product/quartz_fiber_tape"])
            self.assertEqual(reviews, [])
            self.assertEqual([item["id"] for item in all_reviews], ["review_item/quartz_fiber_tape/product_facts_pending"])
            result_ids = [item["id"] for item in search_results]
            self.assertIn("product/quartz_fiber_tape", result_ids)
            self.assertTrue(any(item_id.startswith("evidence/quartz_fiber_tape/report_") for item_id in result_ids))

    def test_evidence_lookup_and_review_queue_use_generated_interface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_official_quartz_fixture(paths)

            evidence = evidence_for_card(paths, "product/quartz_fiber_tape")
            reviews = open_reviews(paths)
            status = knowledge_status(paths)

            self.assertEqual(len(evidence), 1)
            self.assertEqual(evidence[0]["type"], "evidence")
            self.assertEqual(reviews, [])
            self.assertEqual(status["manifest_summary"]["open_review_count"], 0)
            self.assertEqual(status["manifest"]["partition_totals"]["review_item_count"], 0)

    def test_task_context_is_temporary_and_invalidates_on_interface_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_official_quartz_fixture(paths)

            context = generate_task_context(
                paths,
                "quartz-product-question",
                ["product/quartz_fiber_tape"],
                task_type="product_qa",
            )
            context_path = paths.generated_dir / "agent-interface" / "contexts" / "quartz-product-question.json"
            self.assertTrue(context["valid"])
            self.assertEqual(context["cards"][0]["id"], "product/quartz_fiber_tape")
            self.assertIn("不得反向写入", context["note"])

            product_path = paths.knowledge_dir / "产品" / "石英纤维隔热带.md"
            product_text = product_path.read_text(encoding="utf-8")
            product_path.write_text(product_text.replace("tags:\n  - 产品", "tags:\n  - 已更新\n  - 产品"), encoding="utf-8")
            rebuild_agent_interface(paths)

            invalidated = json.loads(context_path.read_text(encoding="utf-8"))
            self.assertFalse(invalidated["valid"])
            self.assertEqual(invalidated["invalidated_reason"], "agent interface revision changed")

    def test_product_organization_forces_and_verifies_agent_interface_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            report = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
            report.write_text("fake report", encoding="utf-8")

            result = organize_product_partition(paths, "石英纤维隔热带")

            refresh = result.generated_summary["agent_interface_refresh"]
            self.assertTrue(refresh["verified"])
            self.assertEqual(refresh["action"], "organize_product")
            self.assertIn("product/quartz_fiber_tape", refresh["verified_card_ids"])
            self.assertEqual(
                refresh["interface_revision"],
                knowledge_status(paths)["manifest"]["interface_revision"],
            )

    def test_refresh_fails_loudly_when_written_card_is_missing_from_interface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)

            with self.assertRaisesRegex(RuntimeError, "missing expected cards"):
                refresh_agent_interface_after_write(
                    paths,
                    action="test_missing_card",
                    expected_card_ids=["product/not_written"],
                )


def _create_official_quartz_fixture(paths) -> None:
    initialize_project(paths)
    report = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
    report.write_text("fake report", encoding="utf-8")
    organize_product_partition(paths, "石英纤维隔热带")
    preview = create_review_preview(paths, "review_item/quartz_fiber_tape/product_facts_pending", "approve_external")
    apply_review_decision(
        paths,
        "review_item/quartz_fiber_tape/product_facts_pending",
        "approve_external",
        preview.confirmation_token,
        reviewer="kkid",
    )


if __name__ == "__main__":
    unittest.main()

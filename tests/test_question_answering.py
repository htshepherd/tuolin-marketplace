from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.agent_interface import rebuild_agent_interface
from scripts.tuolin_marketplace.product_organizer import organize_product_partition
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths
from scripts.tuolin_marketplace.question_answering import answer_question
from scripts.tuolin_marketplace.review_workflow import apply_review_decision, create_review_preview


class QuestionAnsweringTests(unittest.TestCase):
    def test_answers_product_scenarios_from_official_application_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_official_quartz_fixture(paths)
            _write_application_scenario(paths, status="official", usage_scope="external_allowed")
            rebuild_agent_interface(paths)

            answer = answer_question(paths, "石英纤维隔热带适合哪些客户场景？")

            self.assertTrue(answer.answerable)
            self.assertIn("室内排气管隔热", answer.answer)
            self.assertIn("application_scenario/quartz_fiber_tape/indoor_exhaust_pipe", answer.used_cards)
            self.assertTrue(answer.citations)

    def test_does_not_use_draft_or_review_required_cards_as_facts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_official_quartz_fixture(paths)
            _write_application_scenario(paths, status="draft", usage_scope="review_before_external")
            rebuild_agent_interface(paths)

            answer = answer_question(paths, "石英纤维隔热带适合哪些客户场景？")

            self.assertFalse(answer.answerable)
            self.assertEqual(answer.answer, "无法给出已确认答案。")
            self.assertIn("没有已确认的应用场景卡", answer.reason)

    def test_does_not_use_evidence_only_as_product_fact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            raw = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
            raw.write_text("fake report", encoding="utf-8")
            organize_product_partition(paths, "石英纤维隔热带")

            answer = answer_question(paths, "根据现有资料，帮我写一段石英纤维隔热带产品介绍。")

            self.assertFalse(answer.answerable)
            self.assertIn("没有已确认", answer.reason)

    def test_stale_partition_blocks_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            report = _create_official_quartz_fixture(paths)
            report.write_text("changed report", encoding="utf-8")
            rebuild_agent_interface(paths)

            answer = answer_question(paths, "根据现有资料，帮我写一段石英纤维隔热带产品介绍。")

            self.assertFalse(answer.answerable)
            self.assertIn("资料已经变化", answer.reason)
            self.assertIn("确认，先更新石英纤维隔热带资料", answer.next_step)

    def test_product_intro_uses_official_external_product_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_official_quartz_fixture(paths)

            answer = answer_question(paths, "根据现有资料，帮我写一段石英纤维隔热带产品介绍。", audience="external")

            self.assertTrue(answer.answerable)
            self.assertIn("石英纤维隔热带", answer.answer)
            self.assertIn("product/quartz_fiber_tape", answer.used_cards)
            self.assertTrue(any(citation["card_id"].startswith("evidence/quartz_fiber_tape/") for citation in answer.citations))

    def test_products_for_scenario_uses_official_scenario_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_official_quartz_fixture(paths)
            _write_application_scenario(paths, status="official", usage_scope="external_allowed")
            rebuild_agent_interface(paths)

            answer = answer_question(paths, "哪些产品适合排气管隔热？")

            self.assertTrue(answer.answerable)
            self.assertIn("石英纤维隔热带", answer.answer)
            self.assertIn("product/quartz_fiber_tape", answer.used_cards)


def _create_official_quartz_fixture(paths):
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
    return report


def _write_application_scenario(paths, status: str, usage_scope: str) -> None:
    path = paths.knowledge_dir / "应用场景" / "quartz_fiber_tape" / "indoor_exhaust_pipe.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                "card_template_version: application-scenario-card-v1",
                "type: application_scenario",
                "id: application_scenario/quartz_fiber_tape/indoor_exhaust_pipe",
                "title: 室内排气管隔热",
                "aliases:",
                "  - 排气管隔热",
                f"status: {status}",
                f"usage_scope: {usage_scope}",
                "raw_partitions:",
                "  - raw/01_产品/02_石英纤维隔热带/",
                "tags:",
                "  - 应用场景",
                "  - 排气管",
                "updated_at: 2026-06-15T00:00:00+08:00",
                "last_reviewed_at: 2026-06-15T00:00:00+08:00",
                "evidence_refs: []",
                "review_refs: []",
                "scenario_category: 排气管隔热",
                "related_products:",
                "  - product/quartz_fiber_tape",
                "usable_channels:",
                "  - 内部问答",
                "---",
                "",
                "# 场景说明",
                "",
                "室内排气管隔热是已确认应用场景。",
                "",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()

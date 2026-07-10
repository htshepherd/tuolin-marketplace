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

    def test_product_intro_resolves_historical_id_and_card_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_official_quartz_fixture(paths)
            _rewrite_quartz_product_identity(
                paths,
                card_id="product/quartz_fiber_exhaust_wrap",
                aliases=["Special Fiberglass Tape"],
            )
            rebuild_agent_interface(paths)

            by_alias = answer_question(paths, "请写一段 Special Fiberglass Tape 产品介绍。")
            by_historical_id = answer_question(paths, "请写一段 product/quartz_fiber_exhaust_wrap 产品介绍。")

            self.assertTrue(by_alias.answerable)
            self.assertTrue(by_historical_id.answerable)
            self.assertEqual(by_alias.used_cards, ("product/quartz_fiber_exhaust_wrap",))
            self.assertEqual(by_historical_id.used_cards, by_alias.used_cards)

    def test_internal_question_can_use_review_before_external_product_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_official_quartz_fixture(paths)
            _rewrite_quartz_product_scope(paths, "review_before_external")
            rebuild_agent_interface(paths)

            internal_answer = answer_question(paths, "根据现有资料，帮我写一段石英纤维隔热带产品介绍。")
            external_answer = answer_question(
                paths,
                "根据现有资料，帮我写一段石英纤维隔热带产品介绍。",
                audience="external",
            )

            self.assertTrue(internal_answer.answerable)
            self.assertFalse(external_answer.answerable)
            self.assertIn("对外使用前需要复核", internal_answer.answer)

    def test_answers_complete_product_profile_from_related_official_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_official_quartz_fixture(paths)
            _rewrite_quartz_product_body(paths)
            _write_application_scenario(paths, status="official", usage_scope="external_allowed")
            _write_profile_card(
                paths,
                card_type="sales_material",
                card_id="sales_material/quartz_fiber_tape/purchasing",
                title="石英纤维隔热带采购沟通",
                usage_scope="review_before_external",
                body="# 核心卖点\n\n便于采购商根据应用要求沟通规格。",
            )
            _write_profile_card(
                paths,
                card_type="customer_question",
                card_id="customer_question/quartz_fiber_tape/installation",
                title="安装前需要确认什么",
                usage_scope="internal_only",
                body="# 客户关注点\n\n安装前需要确认应用位置和规格。",
            )
            _write_profile_review(paths)
            rebuild_agent_interface(paths)

            answer = answer_question(
                paths,
                "请依据现有知识库的知识卡列出石英纤维隔热带的所有特点，包括优点、缺点和卖点，以及其他所有方面的注意事项。",
            )

            self.assertTrue(answer.answerable)
            self.assertIn("## 已确认优点", answer.answer)
            self.assertIn("柔性带状结构", answer.answer)
            self.assertIn("当前正式知识卡未记录明确缺点", answer.answer)
            self.assertIn("便于采购商根据应用要求沟通规格", answer.answer)
            self.assertIn("室内排气管隔热", answer.answer)
            self.assertIn("确认具体耐温口径", answer.answer)
            self.assertIn("对外前需复核", answer.answer)
            self.assertIn("仅限内部使用", answer.answer)
            self.assertIn("仅作证据引用", answer.answer)
            self.assertGreaterEqual(len(answer.sections), 12)
            self.assertIn("product/quartz_fiber_tape", answer.used_cards)
            self.assertIn("sales_material/quartz_fiber_tape/purchasing", answer.used_cards)
            selling_points = next(section for section in answer.sections if section["key"] == "selling_points")
            self.assertTrue(
                any(source["usage_scope"] == "review_before_external" for source in selling_points["sources"])
            )
            procurement = next(section for section in answer.sections if section["key"] == "procurement_notes")
            self.assertTrue(any(source["usage_scope"] == "internal_only" for source in procurement["sources"]))

    def test_product_profile_ignores_conflicting_video_context_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_official_quartz_fixture(paths)
            _rewrite_quartz_product_body(paths)
            rebuild_agent_interface(paths)

            answer = answer_question(
                paths,
                "前面的视频策划说参数不足。现在请根据知识卡总结石英纤维隔热带的所有特点、优点、缺点、卖点和注意事项。",
            )

            self.assertTrue(answer.answerable)
            self.assertEqual(answer.read_status, "success")
            self.assertNotIn("前面的视频策划说参数不足", answer.answer)
            self.assertIn("柔性带状结构", answer.answer)

    def test_complete_profile_takes_priority_over_short_product_intro(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_official_quartz_fixture(paths)
            _rewrite_quartz_product_body(paths)
            rebuild_agent_interface(paths)

            answer = answer_question(
                paths,
                "请写一份石英纤维隔热带产品介绍，包括所有特点、优点、缺点、卖点和注意事项。",
            )

            self.assertTrue(answer.answerable)
            self.assertIn("产品知识全景总结", answer.answer)
            self.assertGreaterEqual(len(answer.sections), 12)

    def test_read_failure_stops_without_generating_product_facts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})

            answer = answer_question(
                paths,
                "请总结石英纤维隔热带的所有特点、优点、缺点、卖点和注意事项。",
            )

            self.assertFalse(answer.answerable)
            self.assertEqual(answer.read_status, "failed")
            self.assertEqual(answer.error_code, "read_failed")
            self.assertIn("本次未成功读取知识库", answer.answer)
            self.assertIn("没有使用当前会话中的视频策划", answer.answer)
            self.assertEqual(answer.used_cards, ())


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


def _rewrite_quartz_product_identity(paths, card_id: str, aliases: list[str]) -> None:
    path = paths.knowledge_dir / "产品" / "石英纤维隔热带.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace("id: product/quartz_fiber_tape", f"id: {card_id}", 1)
    alias_lines = "aliases:\n" + "\n".join(f"  - {alias}" for alias in aliases)
    text = text.replace("aliases: []", alias_lines, 1)
    path.write_text(text, encoding="utf-8")


def _rewrite_quartz_product_scope(paths, usage_scope: str) -> None:
    path = paths.knowledge_dir / "产品" / "石英纤维隔热带.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace("usage_scope: external_allowed", f"usage_scope: {usage_scope}", 1)
    path.write_text(text, encoding="utf-8")


def _rewrite_quartz_product_body(paths) -> None:
    path = paths.knowledge_dir / "产品" / "石英纤维隔热带.md"
    text = path.read_text(encoding="utf-8")
    closing = text.find("---", 4)
    frontmatter = text[: closing + 3]
    body = """

# 产品定义

石英纤维隔热带是带状工业隔热产品。

# 关键参数

- 宽度按正式规格卡确认。

# 产品特点

- 具有柔性带状结构。

# 优点

- 便于进行缠绕施工。

# 核心卖点

- 面向工业隔热包覆需求。

# 采购注意事项

- 采购前确认应用位置和规格。

# 使用与安全注意事项

- 按确认的应用条件使用。
"""
    path.write_text(frontmatter + body, encoding="utf-8")


def _write_profile_card(paths, card_type: str, card_id: str, title: str, usage_scope: str, body: str) -> None:
    type_config = {
        "sales_material": (
            "销售物料",
            "sales-material-card-v1",
            ["material_type: 采购沟通", "language: zh-CN"],
        ),
        "customer_question": (
            "客户问题",
            "customer-question-card-v1",
            ["question_category: 安装", "customer_channel: 内部问答", "response_status: 已确认"],
        ),
    }
    directory, version, extra = type_config[card_type]
    path = paths.knowledge_dir / directory / f"{card_id.rsplit('/', 1)[-1]}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        f"card_template_version: {version}",
        f"type: {card_type}",
        f"id: {card_id}",
        f"title: {title}",
        "aliases: []",
        "status: official",
        f"usage_scope: {usage_scope}",
        "raw_partitions:",
        "  - raw/01_产品/02_石英纤维隔热带/",
        "tags:",
        "  - 石英纤维隔热带",
        "updated_at: 2026-07-10T00:00:00+08:00",
        "last_reviewed_at: 2026-07-10T00:00:00+08:00",
        "evidence_refs: []",
        "review_refs: []",
        *extra,
        "related_products:",
        "  - product/quartz_fiber_tape",
        "---",
        "",
        body,
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_profile_review(paths) -> None:
    path = paths.knowledge_dir / "复核项" / "quartz_profile_review.md"
    path.write_text(
        "\n".join(
            [
                "---",
                "card_template_version: review-item-card-v1",
                "type: review_item",
                "id: review_item/quartz_fiber_tape/profile_review",
                "title: 石英纤维隔热带参数口径复核",
                "aliases: []",
                "status: review_required",
                "usage_scope: not_answerable",
                "raw_partitions:",
                "  - raw/01_产品/02_石英纤维隔热带/",
                "tags:",
                "  - 石英纤维隔热带",
                "updated_at: 2026-07-10T00:00:00+08:00",
                "last_reviewed_at: ''",
                "evidence_refs: []",
                "review_refs: []",
                "review_reason: 确认具体耐温口径",
                "affected_cards:",
                "  - product/quartz_fiber_tape",
                "decision_options:",
                "  - 确认可用",
                "  - 暂不使用",
                "blocking_level: blocks_external",
                "---",
                "",
                "# 待复核内容",
                "",
                "确认具体耐温口径。",
                "",
            ]
        ),
        encoding="utf-8",
    )


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

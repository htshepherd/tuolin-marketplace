from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scripts.tuolin_marketplace.linkedin_search_agent import (
    continue_linkedin_search_interview,
    create_linkedin_search_run,
    is_linkedin_search_request,
)
from scripts.tuolin_marketplace.linkedin_search.browser_contract import (
    LinkedInAccountObservation,
    LinkedInPostSearchObservation,
    bind_linkedin_account,
    confirm_effective_limit,
    finish_current_keyword,
    record_first_posts_search,
    record_next_posts_search,
)
from scripts.tuolin_marketplace.linkedin_search.discovery import (
    CompanyContactObservation,
    IndividualCandidateObservation,
    LinkedInPostObservation,
    record_company_post_evaluation,
    record_individual_post_evaluation,
)
from scripts.tuolin_marketplace.linkedin_search.ledger import ledger_path, reserve_candidate
from scripts.tuolin_marketplace.linkedin_search.review import (
    authorize_dispatch_batch,
    confirm_candidate_batch,
    prepare_candidate_batch_review,
    prepare_dispatch_authorization,
    remove_candidates_from_batch,
)
from scripts.tuolin_marketplace.linkedin_search.dispatch import (
    InvitationDispatchObservation,
    authorize_interruption_recovery,
    dispatch_next_candidate,
    prepare_interruption_recovery,
    prepare_platform_restart_handoff,
    resolve_note_unavailable,
)
from scripts.tuolin_marketplace.natural_language import route_natural_language
from scripts.tuolin_marketplace.project_layout import resolve_paths
from tests.test_downstream_context import _create_fixture


class LinkedInSearchAgentTests(unittest.TestCase):
    def test_linkedin_search_skill_and_runtime_are_packaged_in_plugin_mirror(self) -> None:
        root = Path(__file__).resolve().parents[1]
        pairs = [
            (
                root / "skills" / "tuolin-linkedin-search" / "SKILL.md",
                root / "plugins" / "tuolin-marketplace" / "skills" / "tuolin-linkedin-search" / "SKILL.md",
            ),
            (
                root / "scripts" / "tuolin_marketplace" / "linkedin_search" / "agent.py",
                root / "plugins" / "tuolin-marketplace" / "scripts" / "tuolin_marketplace" / "linkedin_search" / "agent.py",
            ),
            (
                root / "scripts" / "tuolin_marketplace" / "linkedin_search" / "dispatch.py",
                root / "plugins" / "tuolin-marketplace" / "scripts" / "tuolin_marketplace" / "linkedin_search" / "dispatch.py",
            ),
            (
                root / "scripts" / "update_linkedin_search_run.py",
                root / "plugins" / "tuolin-marketplace" / "scripts" / "update_linkedin_search_run.py",
            ),
        ]
        for source, plugin in pairs:
            self.assertTrue(source.exists(), source)
            self.assertTrue(plugin.exists(), plugin)
            self.assertEqual(source.read_bytes(), plugin.read_bytes(), source)
        root_manifest = json.loads((root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        plugin_manifest = json.loads(
            (root / "plugins" / "tuolin-marketplace" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(root_manifest, plugin_manifest)
        self.assertEqual(root_manifest["version"], "1.52.0")

    def test_request_detection_is_separate_from_linkedin_content_planning(self) -> None:
        self.assertTrue(is_linkedin_search_request("在领英通过贴文搜索石英纤维隔热带潜在客户"))
        self.assertTrue(is_linkedin_search_request("Use LinkedIn to find prospects for quartz fiber tape"))
        self.assertFalse(is_linkedin_search_request("生成下周 LinkedIn 发帖计划"))
        self.assertFalse(is_linkedin_search_request("生成 LinkedIn Day 01 发布图"))

    def test_create_run_binds_one_official_product_and_verified_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)

            result = create_linkedin_search_run(
                paths,
                "在领英通过贴文搜索石英纤维隔热带潜在客户",
                now=datetime(2026, 7, 21, 9, 30, 0),
            )

            self.assertEqual(result.status, "search_interview_required")
            self.assertEqual(result.phase, "awaiting_search_interview")
            self.assertEqual(result.product_id, "product/quartz_fiber_tape")
            run_dir = Path(result.run_dir)
            self.assertEqual(run_dir.name, "20260721_093000_quartz_fiber_tape")
            state = json.loads(Path(result.workflow_state_path).read_text(encoding="utf-8"))
            self.assertEqual(state["workflow"], "tuolin-linkedin-search")
            self.assertEqual(state["product"]["id"], "product/quartz_fiber_tape")
            self.assertFalse(state["knowledge_context"]["raw_access"])
            self.assertTrue(state["knowledge_context"]["policy"]["market_terms_search_only"])
            self.assertIsNone(state["account_binding"])
            self.assertFalse(state["interview"]["completed"])
            self.assertTrue(Path(state["files"]["knowledge_context"]).exists())
            self.assertTrue((run_dir / "requirements.md").exists())
            self.assertTrue((run_dir / "change_log.md").exists())

    def test_missing_agent_interface_creates_a_blocked_auditable_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})

            result = create_linkedin_search_run(
                paths,
                "在领英搜索石英纤维隔热带潜在客户",
                product_id="product/quartz_fiber_tape",
                now=datetime(2026, 7, 21, 9, 31, 0),
            )

            self.assertEqual(result.status, "blocked")
            self.assertEqual(result.phase, "blocked_before_interview")
            state = json.loads(Path(result.workflow_state_path).read_text(encoding="utf-8"))
            self.assertEqual(state["blockers"][0]["code"], "agent_interface_unavailable")
            self.assertIsNone(state["interview"])

    def test_unresolved_product_blocks_without_guessing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)

            result = create_linkedin_search_run(
                paths,
                "在领英搜索潜在客户",
                now=datetime(2026, 7, 21, 9, 32, 0),
            )

            self.assertEqual(result.status, "blocked")
            state = json.loads(Path(result.workflow_state_path).read_text(encoding="utf-8"))
            self.assertEqual(state["blockers"][0]["code"], "product_resolution_failed")
            self.assertIn("没有可唯一解析", result.message)

    def test_natural_language_routes_search_before_linkedin_campaign(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)

            response = route_natural_language(paths, "在领英通过贴文搜索石英纤维隔热带潜在客户")

            self.assertEqual(response.intent, "linkedin_search_interview")
            self.assertTrue(response.executed)
            self.assertTrue(response.needs_confirmation)
            self.assertEqual(response.details["product_id"], "product/quartz_fiber_tape")
            self.assertIn("尚未操作浏览器", response.message)

    def test_interview_asks_one_recommended_question_and_confirms_only_current_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result = create_linkedin_search_run(
                paths,
                "在领英通过贴文搜索石英纤维隔热带潜在客户",
                now=datetime(2026, 7, 21, 10, 0, 0),
            )

            state = json.loads(Path(result.workflow_state_path).read_text(encoding="utf-8"))
            pending = state["interview"]["pending_question"]
            self.assertEqual(pending["field"], "keywords")
            self.assertIn("第一问", result.message)
            self.assertIn("我的推荐答案：", result.message)
            self.assertIn("推荐理由：", result.message)
            self.assertTrue(result.message.rstrip().endswith("是否确认？"))

            step = continue_linkedin_search_interview(
                Path(result.run_dir),
                "确认",
                now=datetime(2026, 7, 21, 10, 1, 0),
            )

            updated = json.loads(Path(step.workflow_state_path).read_text(encoding="utf-8"))
            self.assertIn("keywords", updated["interview"]["answers"])
            self.assertNotIn("sort_order", updated["interview"]["answers"])
            self.assertEqual(updated["interview"]["pending_question"]["field"], "sort_order")
            self.assertIn("第二问", step.message)

    def test_interview_does_not_repeat_explicit_supported_answers_or_ask_geography(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result = create_linkedin_search_run(
                paths,
                (
                    "在领英通过贴文搜索石英纤维隔热带潜在客户，"
                    "关键词：exhaust wrap，heat wrap；排序：最新；日期：近一个月；"
                    "不使用留言；间隔 5 分钟；最多 10 人；地区：美国"
                ),
                now=datetime(2026, 7, 21, 10, 2, 0),
            )

            state = json.loads(Path(result.workflow_state_path).read_text(encoding="utf-8"))
            self.assertTrue(state["interview"]["completed"])
            self.assertEqual(state["phase"], "awaiting_browser_account_binding")
            self.assertEqual(state["confirmed_search_brief"]["keywords"], ["exhaust wrap", "heat wrap"])
            self.assertNotIn("geography", state["confirmed_search_brief"])
            self.assertEqual(state["confirmed_search_brief"]["interval_seconds"], 300)
            self.assertEqual(state["confirmed_search_brief"]["requested_limit"], 10)

    def test_interview_rejects_bulk_remaining_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result = create_linkedin_search_run(
                paths,
                "在领英通过贴文搜索石英纤维隔热带潜在客户",
                now=datetime(2026, 7, 21, 10, 3, 0),
            )

            with self.assertRaisesRegex(ValueError, "不支持一次确认所有剩余问题"):
                continue_linkedin_search_interview(Path(result.run_dir), "剩下都按推荐")

    def test_confirmed_brief_marks_keywords_as_non_formal_search_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result = create_linkedin_search_run(
                paths,
                (
                    "在领英搜索石英纤维隔热带潜在客户，关键词：exhaust wrap；"
                    "排序最新；近一个月；不留言；间隔 5 分钟；最多 10 人"
                ),
                now=datetime(2026, 7, 21, 10, 4, 0),
            )

            state = json.loads(Path(result.workflow_state_path).read_text(encoding="utf-8"))
            self.assertEqual(
                state["confirmed_search_brief"]["search_terms"],
                [{"term": "exhaust wrap", "source": "user_supplied", "formal_knowledge": False}],
            )
            self.assertEqual(state["confirmed_search_brief"]["search_surface"], "linkedin_posts")
            self.assertEqual(state["confirmed_search_brief"]["opened_post_limit_per_keyword"], 50)

    def test_readonly_browser_contract_binds_account_and_records_posts_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result = _create_complete_search_run(paths)

            bound = bind_linkedin_account(
                Path(result.run_dir),
                LinkedInAccountObservation(
                    signed_in=True,
                    member_name="Tuolin Sales",
                    profile_url="https://www.linkedin.com/in/tuolin-sales/?trk=test",
                    dedicated_tab_group=True,
                ),
                browser_authorized=True,
                now=datetime(2026, 7, 21, 11, 0, 0),
            )
            self.assertEqual(bound.phase, "awaiting_first_posts_search")

            searched = record_first_posts_search(
                Path(result.run_dir),
                LinkedInPostSearchObservation(
                    keyword="exhaust wrap",
                    search_surface="posts",
                    sort_order="latest",
                    publication_range="past_month",
                    visible_result_count=25,
                    dedicated_tab_group=True,
                    applied_filters={"content_type": "posts"},
                ),
                now=datetime(2026, 7, 21, 11, 1, 0),
            )

            self.assertEqual(searched.phase, "discovering_posts")
            state = json.loads(Path(searched.workflow_state_path).read_text(encoding="utf-8"))
            self.assertEqual(state["account_binding"]["member_name"], "Tuolin Sales")
            self.assertEqual(state["account_binding"]["profile_url"], "https://www.linkedin.com/in/tuolin-sales")
            self.assertEqual(state["browser_authorization"]["scope"], "readonly_linkedin_post_discovery")
            self.assertEqual(state["search_progress"]["current_keyword"], "exhaust wrap")
            serialized = Path(searched.workflow_state_path).read_text(encoding="utf-8")
            self.assertNotIn("cookie", serialized.casefold())
            self.assertNotIn("otp", serialized.casefold())

    def test_browser_binding_requires_authorization_login_identity_and_tab_group(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result = _create_complete_search_run(paths)
            observation = LinkedInAccountObservation(
                signed_in=True,
                member_name="Tuolin Sales",
                profile_url="https://www.linkedin.com/in/tuolin-sales",
                dedicated_tab_group=True,
            )
            with self.assertRaisesRegex(ValueError, "明确授权"):
                bind_linkedin_account(Path(result.run_dir), observation, browser_authorized=False)

    def test_reduced_rolling_capacity_requires_confirmation_before_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result = _create_complete_search_run(paths)
            current = datetime(2026, 7, 21, 11, 30, 0).astimezone()
            shared_ledger = ledger_path(Path(result.run_dir))
            shared_ledger.parent.mkdir(parents=True, exist_ok=True)
            shared_ledger.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "accounts": {
                            "https://www.linkedin.com/in/tuolin-sales": {
                                "contacts": {},
                                "companies": {},
                                "dispatch_successes": [
                                    {"candidate_id": f"old-{index}", "occurred_at": current.isoformat()}
                                    for index in range(95)
                                ],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            bound = bind_linkedin_account(
                Path(result.run_dir),
                LinkedInAccountObservation(True, "Tuolin Sales", "https://linkedin.com/in/tuolin-sales", True),
                browser_authorized=True,
                now=current,
            )
            self.assertEqual(bound.phase, "awaiting_effective_limit_confirmation")
            self.assertIn("有效上限 5", bound.message)
            confirmed = confirm_effective_limit(Path(result.run_dir), confirmed=True, now=current)
            self.assertEqual(confirmed.phase, "awaiting_first_posts_search")

    def test_posts_search_rejects_people_surface_and_geography_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result = _create_complete_search_run(paths)
            bind_linkedin_account(
                Path(result.run_dir),
                LinkedInAccountObservation(True, "Tuolin Sales", "https://linkedin.com/in/tuolin-sales", True),
                browser_authorized=True,
            )
            with self.assertRaisesRegex(ValueError, "只支持 LinkedIn Posts"):
                record_first_posts_search(
                    Path(result.run_dir),
                    LinkedInPostSearchObservation(
                        "exhaust wrap", "people", "latest", "past_month", 10, True, {}
                    ),
                )

    def test_relevant_individual_post_writes_matching_candidate_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result = _create_discovering_run(paths)
            post = LinkedInPostObservation(
                keyword="exhaust wrap",
                post_url="https://www.linkedin.com/posts/motopack_exhaust-wrap-123?utm_source=test",
                post_text="Wrap it. Protect it. Motopack Silencer Wrap for motorcycle exhausts.",
                author_name="Motopack",
                author_type="individual",
                author_profile_url="https://www.linkedin.com/in/motopack-owner/",
                company_name="Motopack",
                company_url="https://www.linkedin.com/company/motopack/",
            )
            step = record_individual_post_evaluation(
                Path(result.run_dir),
                post,
                decision="Continue",
                reason="贴文正在推广目标品类的排气管隔热带。",
                candidate=IndividualCandidateObservation(
                    member_name="Motopack Owner",
                    title="Founder",
                    company_name="Motopack",
                    profile_url="https://linkedin.com/in/motopack-owner",
                    standard_connect_available=True,
                ),
                now=datetime(2026, 7, 21, 11, 5, 0),
            )

            card_paths = [Path(item) for item in step.output_paths if "candidate_" in Path(item).name]
            self.assertEqual(len(card_paths), 2)
            json_path = next(path for path in card_paths if path.suffix == ".json")
            markdown_path = next(path for path in card_paths if path.suffix == ".md")
            card = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(card["source_keyword"], "exhaust wrap")
            self.assertEqual(card["selected_member"]["profile_url"], "https://www.linkedin.com/in/motopack-owner")
            self.assertIn(card["post_text"], markdown_path.read_text(encoding="utf-8"))
            self.assertIn("候选卡：Motopack Owner", step.message)
            self.assertFalse((Path(result.run_dir) / "screenshots").exists())

    def test_individual_post_never_replaces_author_or_uses_email_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result = _create_discovering_run(paths)
            post = LinkedInPostObservation(
                "exhaust wrap",
                "https://linkedin.com/posts/demo-1",
                "Distributor promotes exhaust wrap.",
                "Original Author",
                "individual",
                "https://linkedin.com/in/original-author",
                "Demo Co",
                "https://linkedin.com/company/demo-co",
            )
            with self.assertRaisesRegex(ValueError, "不能自动替换"):
                record_individual_post_evaluation(
                    Path(result.run_dir),
                    post,
                    decision="Continue",
                    reason="贴文正在推广目标品类。",
                    candidate=IndividualCandidateObservation(
                        "Senior Employee", "CEO", "Demo Co", "https://linkedin.com/in/senior", True
                    ),
                )

    def test_ordered_keywords_advance_once_and_finish_without_expansion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result = _create_discovering_run(paths, keywords="exhaust wrap，heat wrap")

            first = finish_current_keyword(Path(result.run_dir), exhausted=True)
            self.assertEqual(first.phase, "awaiting_next_keyword_search")
            self.assertIn("heat wrap", first.message)
            second = record_next_posts_search(
                Path(result.run_dir),
                LinkedInPostSearchObservation("heat wrap", "posts", "latest", "past_month", 3, True, {}),
            )
            self.assertEqual(second.phase, "discovering_posts")
            completed = finish_current_keyword(Path(result.run_dir), exhausted=True)
            self.assertEqual(completed.phase, "completed")
            state = json.loads(Path(completed.workflow_state_path).read_text(encoding="utf-8"))
            self.assertEqual([item["keyword"] for item in state["completed_keywords"]], ["exhaust wrap", "heat wrap"])
            self.assertEqual(state["discovery_stop_reason"], "all_keywords_exhausted")
            self.assertEqual(state["status"], "completed_no_candidates")

    def test_company_post_selects_one_contact_by_confirmed_role_priority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result = _create_discovering_run(paths)
            post = LinkedInPostObservation(
                "exhaust wrap",
                "https://linkedin.com/posts/company-demo",
                "Our exhaust wrap range is available for distributors.",
                "Demo Wrap Co",
                "company",
                "https://linkedin.com/company/demo-wrap",
                "Demo Wrap Co",
                "https://linkedin.com/company/demo-wrap",
            )
            step = record_company_post_evaluation(
                Path(result.run_dir),
                post,
                decision="Continue",
                reason="公司正在推广目标品类并可能成为渠道采购方。",
                contacts=[
                    CompanyContactObservation("Pat Buyer", "Procurement Manager", "Demo Wrap Co", "https://linkedin.com/in/pat-buyer", True),
                    CompanyContactObservation("Alex Founder", "Founder", "Demo Wrap Co", "https://linkedin.com/in/alex-founder", True),
                    CompanyContactObservation("Chris Product", "Product Manager", "Demo Wrap Co", "https://linkedin.com/in/chris-product", True),
                ],
            )
            json_path = next(Path(item) for item in step.output_paths if Path(item).name.startswith("candidate_") and Path(item).suffix == ".json")
            card = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(card["selected_member"]["name"], "Alex Founder")
            self.assertEqual(card["author"]["type"], "company")

    def test_ledger_suppresses_duplicate_candidate_in_same_or_other_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result = _create_discovering_run(paths)
            first = reserve_candidate(
                Path(result.run_dir),
                account_profile_url="https://linkedin.com/in/tuolin-sales",
                member_profile_url="https://linkedin.com/in/duplicate",
                company_url="https://linkedin.com/company/duplicate-co",
                candidate_id="candidate_duplicate",
            )
            second = reserve_candidate(
                Path(result.run_dir),
                account_profile_url="https://www.linkedin.com/in/tuolin-sales?trk=x",
                member_profile_url="https://www.linkedin.com/in/duplicate/",
                company_url="https://www.linkedin.com/company/duplicate-co/",
                candidate_id="candidate_duplicate_2",
            )
            self.assertTrue(first["eligible"])
            self.assertFalse(second["eligible"])
            self.assertEqual(second["reason"], "ledger_reserved")
            self.assertTrue(ledger_path(Path(result.run_dir)).exists())

    def test_candidate_batch_can_remove_without_backfill_then_close(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result = _create_discovering_run(paths)
            _record_demo_candidate(Path(result.run_dir), suffix="one")
            _record_demo_candidate(Path(result.run_dir), suffix="two")
            finish_current_keyword(Path(result.run_dir), exhausted=True)
            prepared = prepare_candidate_batch_review(Path(result.run_dir))
            self.assertIn("候选人数：2", prepared.message)
            state = json.loads(Path(prepared.workflow_state_path).read_text(encoding="utf-8"))
            remove_id = state["candidate_ids"][0]
            removed = remove_candidates_from_batch(Path(result.run_dir), [remove_id])
            self.assertIn("不会自动找补", removed.message)
            prepare_candidate_batch_review(Path(result.run_dir))
            closed = confirm_candidate_batch(Path(result.run_dir))
            closed_state = json.loads(Path(closed.workflow_state_path).read_text(encoding="utf-8"))
            self.assertEqual(closed_state["closed_candidate_batch"]["candidate_count"], 1)
            self.assertEqual(closed_state["phase"], "awaiting_dispatch_brief")

    def test_final_authorization_binds_exact_account_batch_note_and_interval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result = _create_discovering_run(paths)
            _record_demo_candidate(Path(result.run_dir), suffix="auth")
            finish_current_keyword(Path(result.run_dir), exhausted=True)
            prepare_candidate_batch_review(Path(result.run_dir))
            confirm_candidate_batch(Path(result.run_dir))
            brief = prepare_dispatch_authorization(Path(result.run_dir))
            self.assertIn("精确候选人数：1", brief.message)
            self.assertIn("固定间隔：300 秒", brief.message)
            self.assertIn("手工 LinkedIn 操作：不计入本地统计", brief.message)
            authorized = authorize_dispatch_batch(
                Path(result.run_dir),
                confirmed=True,
                observed_member_name="Tuolin Sales",
                observed_profile_url="https://linkedin.com/in/tuolin-sales",
            )
            self.assertEqual(authorized.phase, "ready_to_dispatch")
            state = json.loads(Path(authorized.workflow_state_path).read_text(encoding="utf-8"))
            self.assertEqual(len(state["authorized_dispatch_batch"]["dispatch_candidate_ids"]), 1)

    def test_enabled_note_must_be_user_reviewed_and_remains_exact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result = _create_discovering_run(paths, note="使用留言")
            _record_demo_candidate(Path(result.run_dir), suffix="note")
            finish_current_keyword(Path(result.run_dir), exhausted=True)
            prepare_candidate_batch_review(Path(result.run_dir))
            confirm_candidate_batch(Path(result.run_dir))
            with self.assertRaisesRegex(ValueError, "必须先由用户确认"):
                prepare_dispatch_authorization(Path(result.run_dir), note_text="Hi, I would like to connect.")
            exact = "Hi, I noticed your exhaust wrap products and would be glad to connect."
            prepared = prepare_dispatch_authorization(
                Path(result.run_dir), note_text=exact, note_review_confirmed=True
            )
            payload_path = next(Path(item) for item in prepared.output_paths if Path(item).suffix == ".json")
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["note_text"], exact)

    def test_successful_dispatch_records_ledger_and_enforces_fixed_interval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result, candidate_ids = _create_authorized_run(paths, candidate_count=2)
            first_time = datetime(2026, 7, 21, 12, 0, 0).astimezone()
            first = dispatch_next_candidate(
                Path(result.run_dir),
                _success_observation(candidate_ids[0], suffix="dispatch-1"),
                now=first_time,
            )
            self.assertEqual(first.phase, "awaiting_dispatch_interval")
            with self.assertRaisesRegex(ValueError, "固定发送间隔尚未结束"):
                dispatch_next_candidate(
                    Path(result.run_dir),
                    _success_observation(candidate_ids[1], suffix="dispatch-2"),
                    now=first_time,
                )
            second = dispatch_next_candidate(
                Path(result.run_dir),
                _success_observation(candidate_ids[1], suffix="dispatch-2"),
                now=first_time.replace(minute=5),
            )
            self.assertEqual(second.phase, "completed")
            ledger = json.loads(ledger_path(Path(result.run_dir)).read_text(encoding="utf-8"))
            account = ledger["accounts"]["https://www.linkedin.com/in/tuolin-sales"]
            self.assertEqual(len(account["dispatch_successes"]), 2)
            self.assertEqual(account["contacts"]["https://www.linkedin.com/in/demo-dispatch-1"]["state"], "sent")

    def test_dispatch_requires_visible_success_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result, candidate_ids = _create_authorized_run(paths, candidate_count=1)
            observation = _success_observation(candidate_ids[0], suffix="dispatch-1")
            observation = InvitationDispatchObservation(**{**observation.__dict__, "visible_confirmation": ""})
            stopped = dispatch_next_candidate(Path(result.run_dir), observation)
            self.assertEqual(stopped.phase, "reconciliation_required")
            self.assertIn("不会自动恢复", stopped.message)

    def test_candidate_local_failure_continues_but_platform_failure_stops_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result, candidate_ids = _create_authorized_run(paths, candidate_count=2)
            local = dispatch_next_candidate(
                Path(result.run_dir),
                InvitationDispatchObservation(
                    "Tuolin Sales",
                    "https://linkedin.com/in/tuolin-sales",
                    candidate_ids[0],
                    "https://linkedin.com/in/demo-dispatch-1",
                    "none",
                    False,
                    True,
                    "no_connect_button",
                ),
            )
            self.assertEqual(local.phase, "ready_to_dispatch")
            stopped = dispatch_next_candidate(
                Path(result.run_dir),
                InvitationDispatchObservation(
                    "Tuolin Sales",
                    "https://linkedin.com/in/tuolin-sales",
                    candidate_ids[1],
                    "https://linkedin.com/in/demo-dispatch-2",
                    "none",
                    True,
                    True,
                    "captcha",
                ),
            )
            self.assertEqual(stopped.phase, "platform_stopped")
            report_path = Path(result.run_dir) / "batch" / "dispatch-report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(len(report["categories"]["failed"]), 1)
            self.assertFalse(report["stop"]["auto_resume"])
            handoff = prepare_platform_restart_handoff(Path(result.run_dir))
            self.assertIn("必须新建任务", handoff.message)
            handoff_path = Path(result.run_dir) / "batch" / "authorized-dispatch-restart-handoff.json"
            payload = json.loads(handoff_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["requires_fresh_batch_authorization"])
            self.assertFalse(payload["automatic_resume_allowed"])

    def test_unavailable_note_requires_new_no_note_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result, candidate_ids = _create_authorized_run(paths, candidate_count=1, note=True)
            paused = dispatch_next_candidate(
                Path(result.run_dir),
                InvitationDispatchObservation(
                    "Tuolin Sales",
                    "https://linkedin.com/in/tuolin-sales",
                    candidate_ids[0],
                    "https://linkedin.com/in/demo-dispatch-1",
                    "none",
                    True,
                    False,
                    "no_dispatch_failure",
                ),
            )
            self.assertEqual(paused.phase, "awaiting_note_unavailable_decision")
            changed = resolve_note_unavailable(Path(result.run_dir), send_without_note=True)
            self.assertEqual(changed.phase, "awaiting_dispatch_brief")
            state = json.loads(Path(changed.workflow_state_path).read_text(encoding="utf-8"))
            self.assertIsNone(state["authorized_dispatch_batch"])
            self.assertFalse(state["confirmed_search_brief"]["invitation_note"])

    def test_ordinary_interruption_requires_account_reconciliation_and_fresh_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result, _ = _create_authorized_run(paths, candidate_count=1)
            prepared = prepare_interruption_recovery(
                Path(result.run_dir),
                observed_member_name="Tuolin Sales",
                observed_profile_url="https://linkedin.com/in/tuolin-sales",
                last_candidate_live_state="none",
            )
            self.assertEqual(prepared.phase, "awaiting_dispatch_reauthorization")
            self.assertIn("不会重新搜索或找补", prepared.message)
            resumed = authorize_interruption_recovery(Path(result.run_dir), confirmed=True)
            self.assertEqual(resumed.phase, "ready_to_dispatch")

    def test_ambiguous_recovery_and_platform_stop_cannot_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            _create_fixture(paths)
            result, candidate_ids = _create_authorized_run(paths, candidate_count=1)
            ambiguous = prepare_interruption_recovery(
                Path(result.run_dir),
                observed_member_name="Tuolin Sales",
                observed_profile_url="https://linkedin.com/in/tuolin-sales",
                last_candidate_live_state="ambiguous",
            )
            self.assertEqual(ambiguous.phase, "reconciliation_required")
            with self.assertRaisesRegex(ValueError, "不能原地恢复"):
                prepare_interruption_recovery(
                    Path(result.run_dir),
                    observed_member_name="Tuolin Sales",
                    observed_profile_url="https://linkedin.com/in/tuolin-sales",
                    last_candidate_live_state="none",
                )


def _create_complete_search_run(paths, *, keywords="exhaust wrap", note="不使用留言"):
    return create_linkedin_search_run(
        paths,
        (
            f"在领英搜索石英纤维隔热带潜在客户，关键词：{keywords}；"
            f"排序：最新；日期：近一个月；{note}；间隔 5 分钟；最多 10 人"
        ),
        now=datetime(2026, 7, 21, 10, 30, 0),
    )


def _create_discovering_run(paths, *, keywords="exhaust wrap", note="不使用留言"):
    result = _create_complete_search_run(paths, keywords=keywords, note=note)
    bind_linkedin_account(
        Path(result.run_dir),
        LinkedInAccountObservation(True, "Tuolin Sales", "https://linkedin.com/in/tuolin-sales", True),
        browser_authorized=True,
        now=datetime(2026, 7, 21, 10, 31, 0),
    )
    record_first_posts_search(
        Path(result.run_dir),
        LinkedInPostSearchObservation("exhaust wrap", "posts", "latest", "past_month", 20, True, {}),
        now=datetime(2026, 7, 21, 10, 32, 0),
    )
    return result


def _record_demo_candidate(run_dir: Path, *, suffix: str) -> None:
    profile = f"https://linkedin.com/in/demo-{suffix}"
    record_individual_post_evaluation(
        run_dir,
        LinkedInPostObservation(
            "exhaust wrap",
            f"https://linkedin.com/posts/demo-{suffix}",
            f"Demo {suffix} promotes exhaust wrap.",
            f"Demo {suffix}",
            "individual",
            profile,
            f"Demo {suffix} Co",
            f"https://linkedin.com/company/demo-{suffix}",
        ),
        decision="Continue",
        reason="贴文正在推广目标品类。",
        candidate=IndividualCandidateObservation(
            f"Demo {suffix}", "Founder", f"Demo {suffix} Co", profile, True
        ),
    )


def _create_authorized_run(paths, *, candidate_count: int, note: bool = False):
    result = _create_discovering_run(paths, note="使用留言" if note else "不使用留言")
    candidate_ids = []
    for index in range(1, candidate_count + 1):
        suffix = f"dispatch-{index}"
        _record_demo_candidate(Path(result.run_dir), suffix=suffix)
    finish_current_keyword(Path(result.run_dir), exhausted=True)
    prepare_candidate_batch_review(Path(result.run_dir))
    confirm_candidate_batch(Path(result.run_dir))
    prepare_dispatch_authorization(
        Path(result.run_dir),
        note_text="Hi, I noticed your exhaust wrap products and would be glad to connect." if note else None,
        note_review_confirmed=note,
    )
    authorize_dispatch_batch(
        Path(result.run_dir),
        confirmed=True,
        observed_member_name="Tuolin Sales",
        observed_profile_url="https://linkedin.com/in/tuolin-sales",
    )
    state = json.loads(Path(result.workflow_state_path).read_text(encoding="utf-8"))
    candidate_ids = list(state["authorized_dispatch_batch"]["dispatch_candidate_ids"])
    return result, candidate_ids


def _success_observation(candidate_id: str, *, suffix: str) -> InvitationDispatchObservation:
    return InvitationDispatchObservation(
        "Tuolin Sales",
        "https://linkedin.com/in/tuolin-sales",
        candidate_id,
        f"https://linkedin.com/in/demo-{suffix}",
        "none",
        True,
        True,
        "success",
        "Invitation sent",
    )


if __name__ == "__main__":
    unittest.main()

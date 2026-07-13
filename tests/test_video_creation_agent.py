from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import re
import wave
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from scripts.tuolin_marketplace.agent_interface import rebuild_agent_interface
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths
from scripts.tuolin_marketplace.video_creation_agent import (
    assemble_final_preview,
    apply_storyboard_semantic_revision,
    apply_video_plan_semantic_revision,
    approve_plan_material_repetition,
    confirm_narration,
    confirm_dreamina_generation,
    confirm_final_video,
    confirm_narration_script,
    confirm_shot_retry,
    confirm_shots,
    assemble_confirmed_video,
    confirm_storyboard,
    confirm_video_plan,
    create_video_creation_run,
    continue_video_creation_interview,
    download_dreamina_results_once,
    generate_full_narration,
    generate_dreamina_jobs,
    generate_narration_script,
    generate_storyboard,
    generate_video_plan as _generate_video_plan,
    generate_voice_samples,
    handle_video_creation_reply,
    inspect_video_creation_adapters,
    is_video_creation_request,
    plan_shot_retry,
    propose_video_interview_decision,
    query_dreamina_results,
    query_shot_retry_results,
    record_material_visual_inspection,
    record_video_interview_evidence,
    record_video_results_not_accepted,
    record_manual_quality_check,
    resume_video_creation_run,
    revise_storyboard,
    revise_storyboard_shot,
    revise_video_plan,
    run_quality_gate,
    select_bgm_track,
    select_voice,
    set_storyboard_shot_reference_images,
    submit_dreamina_jobs,
    submit_shot_retry,
    shorten_video_plan_duration,
    validate_video_creation_project,
)


def _material_assessments(run_dir: Path, *, usable_limit: int | None = None) -> list[dict[str, object]]:
    inspection = json.loads((run_dir / "material_visual_inspection.json").read_text(encoding="utf-8"))
    assessments = []
    for index, candidate in enumerate(inspection.get("candidates", []), start=1):
        assessments.append(
            {
                "material_id": candidate["material_id"],
                "subject": "产品或应用主体清晰",
                "clarity": "清晰可用",
                "composition": "主体构图可用于镜头",
                "vertical_crop": "可安全裁切为 9:16",
                "near_duplicate_of": "",
                "usable": usable_limit is None or index <= usable_limit,
                "notes": "测试视觉检查记录",
                "rank": index,
            }
        )
    return assessments


def _complete_material_visual_inspection(
    run_dir: Path,
    *,
    usable_limit: int | None = None,
    approve_shortage: bool = True,
):
    result = record_material_visual_inspection(
        run_dir,
        _material_assessments(run_dir, usable_limit=usable_limit),
        now=datetime(2026, 6, 25, 15, 1, 0),
    )
    plan = json.loads((run_dir / "video_plan.json").read_text(encoding="utf-8"))
    if approve_shortage and plan.get("material_supported_duration", {}).get("status") != "supported":
        approve_plan_material_repetition(run_dir, "测试夹具明确批准素材重复")
    return result


def generate_video_plan(run_dir: Path, *args, **kwargs):
    return _generate_video_plan(run_dir, *args, **kwargs)


class VideoCreationAgentTests(unittest.TestCase):
    def test_identifies_quartz_fiber_tape_video_requests(self) -> None:
        self.assertTrue(is_video_creation_request("做一个60秒石英纤维隔热带产品介绍视频"))
        self.assertTrue(is_video_creation_request("make a TikTok video for quartz fiberglass tape"))
        self.assertFalse(is_video_creation_request("整理一下拓霖知识库"))
        self.assertFalse(is_video_creation_request("做一个车间介绍视频"))
        self.assertFalse(is_video_creation_request("做一个玄武岩纤维带产品视频"))

    def test_validates_current_directory_has_agent_interface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)

            validation = validate_video_creation_project(paths)

            self.assertFalse(validation.valid)
            self.assertTrue(any("Agent读取接口" in error for error in validation.errors))

    def test_blocks_mismatched_or_unverified_agent_interface_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            summary_path = paths.generated_dir / "agent-interface" / "manifest_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["interface_revision"] = "stale-revision"
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

            validation = validate_video_creation_project(paths)

            self.assertFalse(validation.valid)
            self.assertTrue(any("版本不一致" in error for error in validation.errors))

    def test_creates_video_creation_run_from_agent_interface_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)

            result = create_video_creation_run(
                paths,
                "做一个60秒石英纤维隔热带产品介绍视频，面向欧美工业采购商，用在 YouTube Shorts。",
                language_version="en",
                platforms=["youtube_shorts"],
                duration_seconds=60,
                target_audience="欧美工业采购商",
                core_objective="突出耐高温、隔热、不刺痒和不冒烟",
                now=datetime(2026, 6, 25, 14, 30, 5),
            )

            run_dir = Path(result.run_dir)
            self.assertEqual(run_dir.name, "20260625_143005_quartz_fiber_tape_en")
            self.assertTrue((run_dir / "requirements.md").exists())
            self.assertTrue((run_dir / "workflow_state.json").exists())
            self.assertTrue((run_dir / "change_log.md").exists())
            self.assertTrue((run_dir / "dreamina_generation" / "generated_shots").is_dir())
            self.assertFalse((run_dir / "narration").exists())
            self.assertFalse((run_dir / "audio").exists())
            self.assertFalse((run_dir / "subtitles").exists())

            requirements = (run_dir / "requirements.md").read_text(encoding="utf-8")
            self.assertIn("## 视频创作访谈", requirements)
            self.assertNotIn("固定视频创意方向", requirements)
            self.assertNotIn("主创意方向", requirements)
            self.assertIn("不得包含 `master`", requirements)

            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(result.status, "video_interview_in_progress")
            self.assertEqual(state["phase"], "awaiting_video_creation_interview")
            self.assertEqual(state["language_version"], "en")
            self.assertEqual(state["platforms"], ["youtube_shorts"])
            self.assertEqual(state["duration_seconds"], 60)
            self.assertEqual(state["workflow_mode"], "video_only")
            self.assertNotIn("narration_script", state["confirmations"])
            self.assertNotIn("voice", state["confirmations"])
            self.assertNotIn("narration", state["confirmations"])
            self.assertNotIn("final_video", state["confirmations"])
            self.assertNotIn("audience", state["video_brief"])
            self.assertEqual(state["requirements_payload"]["target_audience"], "欧美工业采购商")
            self.assertNotIn("intended_takeaway", state["video_brief"])
            self.assertEqual(
                state["requirements_payload"]["core_objective"],
                "突出耐高温、隔热、不刺痒和不冒烟",
            )
            self.assertFalse(state["confirmations"]["video_brief"])
            self.assertEqual(state["context"]["task_type"], "video_creation")
            self.assertFalse(state["context"]["raw_access"])
            self.assertTrue(state["context"]["policy"]["no_keyword_expansion"])
            self.assertEqual(state["outputs"]["final_filename"], "quartz_fiber_tape_en_9x16.mp4")
            self.assertEqual(state["outputs"]["dreamina_model"], "seedance2.0_vip")
            self.assertEqual(state["adapters"]["dreamina_command"], "dreamina")
            self.assertEqual(state["adapters"]["ffmpeg_command"], "ffmpeg")
            self.assertNotIn("tts_provider", state["adapters"])
            self.assertNotIn("bgm_provider", state["adapters"])
            self.assertTrue(Path(state["files"]["context"]).exists())

    def test_short_video_durations_create_matching_storyboard_shot_counts(self) -> None:
        cases = {
            15: 3,
            20: 3,
            30: 4,
            45: 6,
        }
        for duration, expected_shots in cases.items():
            with self.subTest(duration=duration):
                with tempfile.TemporaryDirectory() as tmp:
                    paths = resolve_paths(Path(tmp), {})
                    initialize_project(paths)
                    _write_official_cards(paths)
                    rebuild_agent_interface(paths)

                    result = create_video_creation_run(
                        paths,
                        f"做一个{duration}秒英文版石英纤维隔热带产品视频，面向欧美工业采购商，用于 YouTube Shorts。",
                        language_version="en",
                        platforms=["youtube_shorts"],
                        duration_seconds=duration,
                        target_audience="欧美工业采购商",
                        core_objective="短视频快速展示产品价值",
                        now=datetime(2026, 6, 25, 14, 30, 5),
                    )
                    run_dir = Path(result.run_dir)
                    _complete_video_interview(run_dir)
                    state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
                    self.assertEqual(state["duration_seconds"], duration)

                    generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))
                    plan = json.loads((run_dir / "video_plan.json").read_text(encoding="utf-8"))
                    self.assertEqual(plan["format"]["duration_seconds"], duration)
                    self.assertEqual(plan["format"]["duration_tolerance_seconds"], {"min": duration, "max": duration})

                    confirm_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 5, 0))
                    generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))
                    storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
                    self.assertEqual(len(storyboard["shots"]), expected_shots)
                    self.assertEqual(storyboard["actual_duration_seconds"], duration)
                    self.assertTrue(all(4 <= shot["duration_seconds"] <= 15 for shot in storyboard["shots"]))

    def test_video_creation_resolves_legacy_quartz_product_id_and_draft_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_legacy_quartz_video_cards(paths)
            rebuild_agent_interface(paths)

            result = create_video_creation_run(
                paths,
                "做一个60秒石英纤维隔热带产品介绍视频，面向欧美工业采购商，用在 YouTube Shorts。",
                language_version="en",
                platforms=["youtube_shorts"],
                duration_seconds=60,
                target_audience="欧美工业采购商",
                core_objective="突出隔热、易施工和采购判断",
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            _complete_video_interview(run_dir)
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["context"]["product_id"], "product/quartz_fiber_exhaust_wrap")
            self.assertEqual(state["context"]["canonical_product_id"], "product/quartz_fiber_tape")
            self.assertIn("product/quartz_fiber_exhaust_wrap", state["context"]["product_alias_ids"])

            generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))

            plan = json.loads((run_dir / "video_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["product"]["internal_id"], "product/quartz_fiber_exhaust_wrap")
            self.assertEqual(plan["product"]["canonical_id"], "product/quartz_fiber_tape")
            self.assertEqual(plan["product"]["usage_scope"], "review_before_external")
            self.assertTrue(plan["knowledge_boundary"]["draft_only_until_external_review"])
            self.assertFalse(plan["knowledge_boundary"]["external_publication_ready"])
            self.assertEqual(plan["content_assets"][0]["id"], "content_asset/quartz_legacy_product_photo")

    def test_video_creation_does_not_use_product_matrix_as_primary_product_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_product_matrix_card(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)

            result = create_video_creation_run(
                paths,
                "做一个15秒英文版石英纤维隔热带产品视频，面向欧美工业采购商，用于 YouTube Shorts。",
                language_version="en",
                platforms=["youtube_shorts"],
                duration_seconds=15,
                target_audience="欧美工业采购商",
                core_objective="突出隔热防护价值并引导询盘",
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            _complete_video_interview(run_dir)
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["context"]["product_id"], "product/quartz_fiber_tape")

            generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))

            plan = json.loads((run_dir / "video_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["product"]["internal_id"], "product/quartz_fiber_tape")
            self.assertEqual(plan["product"]["external_name_en"], "Specialty Glass Fiber Tape")
            plan_text = (run_dir / "video_plan.md").read_text(encoding="utf-8")
            self.assertNotIn("product/exhaust_wrap_matrix", plan_text)
            self.assertNotIn("玄武岩", plan_text)
            self.assertNotIn("陶瓷纤维", plan_text)

    def test_video_plan_uses_agent_interface_evidence_knowledge_for_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)

            result = create_video_creation_run(
                paths,
                "做一个15秒英文版石英纤维隔热带产品视频，面向欧美工业采购商，用于 YouTube Shorts。",
                language_version="en",
                platforms=["youtube_shorts"],
                duration_seconds=15,
                target_audience="欧美工业采购商",
                core_objective="快速展示隔热、易施工和采购判断",
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            _complete_video_interview(run_dir)

            generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))

            plan = json.loads((run_dir / "video_plan.json").read_text(encoding="utf-8"))
            usable_knowledge = "\n".join(plan["usable_product_knowledge"])
            self.assertIn("证据知识卡：石英纤维隔热带关键参数", usable_knowledge)
            self.assertIn("耐高温1000度", usable_knowledge)
            self.assertIn("不刺痒", usable_knowledge)
            self.assertIn("不冒烟", usable_knowledge)
            plan_text = (run_dir / "video_plan.md").read_text(encoding="utf-8")
            self.assertIn("证据知识卡：石英纤维隔热带关键参数", plan_text)
            self.assertNotIn("关键参数需要从检测报告", plan_text)

    def test_video_creation_run_requires_core_interview_before_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)

            result = create_video_creation_run(
                paths,
                "做一个60秒石英纤维隔热带产品介绍视频，面向欧美工业采购商，用在 YouTube Shorts。",
                language_version="en",
                platforms=["youtube_shorts"],
                duration_seconds=60,
                target_audience="欧美工业采购商",
                core_objective="突出隔热、易施工和采购判断",
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            self.assertEqual(result.status, "video_interview_in_progress")
            requirements = (run_dir / "requirements.md").read_text(encoding="utf-8")
            self.assertIn("## 视频创作访谈", requirements)
            self.assertNotIn("固定视频创意方向", requirements)
            with self.assertRaisesRegex(ValueError, "核心信息尚未完整|当前阶段"):
                generate_video_plan(run_dir)

            with self.assertRaisesRegex(ValueError, "不使用.*按推荐"):
                continue_video_creation_interview(run_dir, "剩下都按推荐", now=datetime(2026, 6, 25, 14, 35, 0))
            _complete_video_interview(run_dir)
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["video_brief"])
            self.assertEqual(state["video_brief"]["audience"], "负责高温设备隔热材料选型的欧美工程与采购人员。")
            self.assertIn("官方图片", state["video_brief"]["material_visual_direction"])

            plan_result = generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))
            self.assertEqual(plan_result.status, "video_plan_ready")

    def test_video_creation_reply_rejects_bulk_delegation_and_requires_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)

            result = create_video_creation_run(
                paths,
                "做一个60秒石英纤维隔热带产品介绍视频",
                language_version="en",
                platforms=["youtube_shorts"],
                duration_seconds=60,
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            with self.assertRaisesRegex(ValueError, "不使用.*批量"):
                handle_video_creation_reply(
                    run_dir,
                    "你来决定并直接出策划",
                    now=datetime(2026, 6, 25, 14, 35, 0),
                )
            _complete_video_interview(run_dir)
            reply_result = handle_video_creation_reply(run_dir, "生成策划", now=datetime(2026, 6, 25, 14, 36, 0))
            self.assertEqual(reply_result.phase, "awaiting_video_plan_confirmation")
            self.assertEqual(reply_result.status, "video_plan_ready")
            self.assertTrue((run_dir / "video_plan.md").exists())
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["video_brief"])
            self.assertEqual(state["current_pending_confirmation"], "确认策划")

    def test_video_interview_accepts_plain_confirmation_only_for_current_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            result = create_video_creation_run(
                paths,
                "做一个15秒英文版石英纤维隔热带视频，用于 YouTube Shorts。",
                language_version="en",
                platforms=["youtube_shorts"],
                duration_seconds=15,
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)

            with self.assertRaisesRegex(ValueError, "不使用.*按推荐"):
                handle_video_creation_reply(run_dir, "按推荐", now=datetime(2026, 6, 25, 14, 31, 0))
            proposed = propose_video_interview_decision(
                run_dir,
                {
                    "decision_key": "audience",
                    "question": "这条视频首先要影响哪类具体决策者？",
                    "recommendation": "负责高温设备隔热材料选型的欧美工程与采购人员。",
                    "reason": "他们的选型职责会直接决定开场问题、证据顺序和 CTA。",
                    "evidence": [{"source": "formal_product_context", "summary": "产品用于工业选型沟通"}],
                },
                now=datetime(2026, 6, 25, 14, 31, 10),
            )
            self.assertIn("是否确认", proposed.message)
            first = handle_video_creation_reply(run_dir, "确认", now=datetime(2026, 6, 25, 14, 31, 30))
            self.assertEqual(first.phase, "awaiting_video_creation_interview")
            self.assertIn("Codex 内部动作", first.message)
            self.assertFalse((run_dir / "video_plan.json").exists())
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(len(state["interview"]["answers"]), 1)
            self.assertIsNone(state["interview"]["pending_decision"])
            self.assertFalse(state["confirmations"]["video_brief"])
            _complete_video_interview(run_dir)
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["phase"], "ready_for_video_plan")
            self.assertIn("viewer_interest_direction", state["video_brief"])
            self.assertIn("trend_evidence", state["video_brief"])

    def test_video_interview_never_injects_a_fixed_fallback_question(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            result = create_video_creation_run(
                paths,
                "做一个英文石英纤维隔热带 YouTube Shorts，面向欧美工业采购商。",
                language_version="en",
                platforms=["youtube_shorts"],
                duration_seconds=15,
                target_audience="欧美工业采购商",
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))

            self.assertIsNone(state["interview"]["pending_decision"])
            self.assertNotIn("audience", state["interview"]["decisions"])
            self.assertIn("基于当前知识、证据和已确认决策", result.message)
            with self.assertRaisesRegex(ValueError, "当前没有可由用户确认"):
                continue_video_creation_interview(run_dir, "确认")

    def test_internal_trend_and_material_evidence_wait_for_audience_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            result = create_video_creation_run(
                paths,
                "做一个英文石英纤维隔热带 YouTube Shorts。",
                language_version="en",
                platforms=["youtube_shorts"],
                duration_seconds=15,
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)

            with self.assertRaisesRegex(ValueError, "证据依赖尚未解决.*受众"):
                record_video_interview_evidence(
                    run_dir,
                    "trend_evidence",
                    "当前工业短视频信号。",
                    [{
                        "source_url": "https://www.youtube.com/shorts/test-evidence",
                        "scanned_at": "2026-06-25",
                        "observed_signal": "真实问题开场后用产品细节推进",
                        "why_it_worked": "目标受众能快速识别自己的选型问题并获得连续证据",
                        "mechanism": "problem-proof-decision",
                        "transfer_to_product": "把高温包覆判断转译为纹理和应用细节的连续展示",
                        "relevance_level": "comparable_industrial",
                        "target_language": "en",
                        "target_region": "North America and Europe",
                        "excluded_methods": ["无关娱乐梗", "夸张破坏性测试"],
                    }],
                    "public_youtube_scan",
                )

    def test_fact_bearing_interview_decisions_require_current_formal_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            result = create_video_creation_run(
                paths,
                "做一个英文石英纤维隔热带 YouTube Shorts。",
                language_version="en",
                platforms=["youtube_shorts"],
                duration_seconds=15,
                core_objective="宣称一个知识卡里没有的认证",
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertNotIn("intended_takeaway", state["interview"]["decisions"])

            with self.assertRaisesRegex(ValueError, "正式上下文之外"):
                propose_video_interview_decision(
                    run_dir,
                    {
                        "decision_key": "intended_takeaway",
                        "question": "观众应该记住什么？",
                        "recommendation": "记住产品适合进一步核对工况与规格。",
                        "reason": "保持一个可验证的核心认知。",
                        "evidence": [{"card_id": "evidence/not-in-context"}],
                    },
                )

            context = json.loads(Path(state["files"]["context"]).read_text(encoding="utf-8"))
            product_id = context["cards_by_type"]["product"][0]["id"]
            propose_video_interview_decision(
                run_dir,
                {
                    "decision_key": "intended_takeaway",
                    "question": "观众应该记住什么？",
                    "recommendation": "记住产品适合结合具体工况进一步核对规格。",
                    "reason": "保持一个正式知识可支持的核心认知。",
                    "evidence": [{"card_id": product_id, "source": "formal_product_card"}],
                },
            )
            corrected = continue_video_creation_interview(run_dir, "改成宣传一个新的认证")
            self.assertIn("正式知识卡核验", corrected.message)
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertNotIn("intended_takeaway", state["interview"]["decisions"])
            self.assertEqual(
                state["interview"]["unvalidated_corrections"]["intended_takeaway"],
                "改成宣传一个新的认证",
            )

    def test_each_new_video_task_gets_an_isolated_run_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)
            kwargs = {
                "request_text": "做一个15秒英文版石英纤维隔热带视频，用于 YouTube Shorts。",
                "language_version": "en",
                "platforms": ["youtube_shorts"],
                "duration_seconds": 15,
                "now": datetime(2026, 6, 25, 14, 30, 5),
            }

            first = create_video_creation_run(paths, **kwargs)
            second = create_video_creation_run(paths, **kwargs)

            self.assertNotEqual(first.run_dir, second.run_dir)
            self.assertTrue(Path(first.run_dir).exists())
            self.assertTrue(Path(second.run_dir).exists())
            self.assertTrue(Path(second.run_dir).name.endswith("_02"))

    def test_detailed_initial_request_still_requires_evidence_backed_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(root, {})
            initialize_project(paths)
            _write_official_cards(paths)
            _write_raw_image_files(root)
            rebuild_agent_interface(paths)

            result = create_video_creation_run(
                paths,
                "做一个15秒英文视频，应用场景和产品细节均衡，引导询盘，不要未经确认的认证。",
                language_version="en",
                platforms=["youtube_shorts"],
                duration_seconds=15,
                target_audience="欧美工业采购商",
                core_objective="让采购商记住产品用途、真实外观和包覆方式",
                now=datetime(2026, 6, 25, 14, 30, 5),
            )

            self.assertEqual(result.status, "video_interview_in_progress")
            self.assertFalse((Path(result.run_dir) / "video_plan.json").exists())
            _complete_video_interview(Path(result.run_dir))
            reviewed = _generate_video_plan(Path(result.run_dir))
            self.assertEqual(reviewed.status, "video_plan_ready")
            self.assertIn("## 视频策划摘要", reviewed.message)

    def test_video_creation_run_captures_adapter_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(
                Path(tmp),
                {
                    "video_creation": {
                        "dreamina_command": "/opt/dreamina",
                    }
                },
            )
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)

            result = create_video_creation_run(
                paths,
                "做一个60秒石英纤维隔热带产品介绍视频",
                language_version="en",
                platforms=["youtube_shorts"],
                duration_seconds=60,
                now=datetime(2026, 6, 25, 14, 30, 5),
            )

            state = json.loads((Path(result.run_dir) / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["adapters"]["dreamina_command"], "/opt/dreamina")
            self.assertEqual(state["adapters"]["ffmpeg_command"], "ffmpeg")
            self.assertEqual(set(state["adapters"]), {"dreamina_command", "dreamina_execute_default", "ffmpeg_command"})

    def test_video_creation_run_records_default_dreamina_capability_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))

            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            profile = state["dreamina_capability_profile"]
            self.assertEqual(profile["model"], "seedance2.0_vip")
            self.assertEqual(profile["resolution"], "1080P")
            self.assertEqual(profile["aspect_ratio"], "9:16")
            self.assertEqual(profile["min_duration_seconds"], 4)
            self.assertEqual(profile["max_duration_seconds"], 15)
            self.assertEqual(profile["max_images"], 9)
            self.assertEqual(profile["max_total_files"], 12)

    def test_custom_dreamina_capability_profile_drives_jobs_and_adapter_inspection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(
                root,
                {
                    "video_creation": {
                        "dreamina_capability_profile": {
                            "model": "seedance-custom",
                            "resolution": "720P",
                            "aspect_ratio": "9:16",
                            "min_duration_seconds": 4,
                            "max_duration_seconds": 6,
                            "max_images": 4,
                            "max_videos": 1,
                            "max_audios": 1,
                            "max_total_files": 6,
                        }
                    }
                },
            )
            initialize_project(paths)
            _write_official_cards(paths)
            _write_raw_image_files(root)
            rebuild_agent_interface(paths)
            result = create_video_creation_run(
                paths,
                "做一个60秒石英纤维隔热带产品介绍视频",
                language_version="en",
                platforms=["youtube_shorts"],
                duration_seconds=60,
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            _complete_video_interview(run_dir)
            generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))
            confirm_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 5, 0))
            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))
            confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))
            generate_dreamina_jobs(run_dir, now=datetime(2026, 6, 25, 15, 30, 0))
            inspect_video_creation_adapters(run_dir, now=datetime(2026, 6, 25, 16, 20, 0))

            jobs = json.loads((run_dir / "dreamina_generation" / "dreamina_jobs.json").read_text(encoding="utf-8"))
            self.assertEqual(jobs["format"]["model"], "seedance-custom")
            self.assertEqual(jobs["format"]["dreamina_resolution"], "720P")
            self.assertEqual(jobs["format"]["capability_profile"]["max_images"], 4)
            self.assertTrue(all(job["model"] == "seedance-custom" for job in jobs["jobs"]))
            report = json.loads((run_dir / "adapter_inspection.json").read_text(encoding="utf-8"))
            self.assertEqual(report["dreamina_capability_profile"]["model"], "seedance-custom")
            self.assertTrue(any(item["name"] == "dreamina_capability_profile" for item in report["checks"]))

    def test_capability_profile_duration_limit_blocks_dreamina_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(
                root,
                {
                    "video_creation": {
                        "dreamina_capability_profile": {
                            "max_duration_seconds": 4,
                        }
                    }
                },
            )
            initialize_project(paths)
            _write_official_cards(paths)
            _write_raw_image_files(root)
            rebuild_agent_interface(paths)
            result = create_video_creation_run(
                paths,
                "做一个60秒石英纤维隔热带产品介绍视频",
                language_version="en",
                platforms=["youtube_shorts"],
                duration_seconds=60,
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            _complete_video_interview(run_dir)
            generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))
            confirm_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 5, 0))
            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))
            confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))
            generate_dreamina_jobs(run_dir, now=datetime(2026, 6, 25, 15, 30, 0))

            jobs = json.loads((run_dir / "dreamina_generation" / "dreamina_jobs.json").read_text(encoding="utf-8"))
            self.assertTrue(any(job["validation"]["status"] == "blocked" for job in jobs["jobs"]))
            with self.assertRaisesRegex(ValueError, "存在 blocked 即梦任务"):
                confirm_dreamina_generation(run_dir, now=datetime(2026, 6, 25, 15, 35, 0))

    def test_multishot_reference_count_does_not_apply_seedance_per_task_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(
                root,
                {
                    "video_creation": {
                        "dreamina_capability_profile": {
                            "max_images": 1,
                        }
                    }
                },
            )
            initialize_project(paths)
            _write_official_cards(paths)
            _write_raw_image_files(root)
            rebuild_agent_interface(paths)
            result = create_video_creation_run(
                paths,
                "做一个60秒石英纤维隔热带产品介绍视频",
                language_version="en",
                platforms=["youtube_shorts"],
                duration_seconds=60,
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            _complete_video_interview(run_dir)
            generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))
            confirm_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 5, 0))
            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))
            confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))
            generate_dreamina_jobs(run_dir, now=datetime(2026, 6, 25, 15, 30, 0))

            jobs = json.loads((run_dir / "dreamina_generation" / "dreamina_jobs.json").read_text(encoding="utf-8"))
            self.assertEqual(
                jobs["material_reference_map"]["counts"]["images"],
                len(jobs["jobs"]),
            )
            self.assertFalse(any("Seedance 多模态输入超限" in "; ".join(job["validation"]["messages"]) for job in jobs["jobs"]))
            self.assertTrue(all(job["validation"]["status"] == "ok" for job in jobs["jobs"]))
            result = confirm_dreamina_generation(run_dir, now=datetime(2026, 6, 25, 15, 35, 0))
            self.assertEqual(result.status, "dreamina_generation_confirmed")

    def test_multi_image_shot_blocks_when_provider_contract_is_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_plan_confirmed_run(Path(tmp))
            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))
            storyboard_path = run_dir / "storyboard.json"
            storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
            source_paths = [run_dir / "multi-reference-a.jpg", run_dir / "multi-reference-b.jpg"]
            for index, source_path in enumerate(source_paths, start=1):
                source_path.write_bytes(f"inspected reference {index}".encode("utf-8"))
            assessment = {
                "subject": "产品或应用主体清楚",
                "clarity": "清晰可用",
                "composition": "主体构图支持镜头推进",
                "vertical_crop": "可安全裁切为 9:16",
                "near_duplicate_of": "",
                "usable": True,
            }
            revised = set_storyboard_shot_reference_images(
                run_dir,
                "02",
                [
                    {"image_path": str(source_paths[0]), "reference_role": "opening_product_reference", "assessment": assessment},
                    {"image_path": str(source_paths[1]), "reference_role": "ending_detail_reference", "assessment": assessment},
                ],
                {
                    "product_identity": "两张图展示同一产品身份",
                    "scale": "卷装与细节尺度变化可解释",
                    "environment": "背景变化不构成客户现场暗示",
                    "lighting": "亮度与色温保持连贯",
                    "action": "从产品全貌推进到织纹细节",
                    "transition": "以同一织纹方向完成连续过渡",
                },
                now=datetime(2026, 6, 25, 15, 12, 0),
            )
            self.assertEqual(revised.status, "storyboard_revised")
            storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
            shot = next(item for item in storyboard["shots"] if item["shot_id"] == "02")
            self.assertEqual(len(shot["selected_materials"]), 2)
            self.assertEqual([item["reference_order"] for item in shot["selected_materials"]], [1, 2])
            self.assertIn("参考图 2", revised.message)

            confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))
            generate_dreamina_jobs(run_dir, now=datetime(2026, 6, 25, 15, 30, 0))

            jobs = json.loads((run_dir / "dreamina_generation" / "dreamina_jobs.json").read_text(encoding="utf-8"))
            multi = next(job for job in jobs["jobs"] if len(job["reference_material_ids"]) == 2)
            self.assertEqual(multi["validation"]["status"], "blocked")
            self.assertIn("重新确认分镜与 SRT", "；".join(multi["validation"]["messages"]))
            self.assertEqual(len(multi["reference_material_ids"]), 2)

    def test_clear_human_face_material_blocks_dreamina_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(root, {})
            initialize_project(paths)
            _write_official_cards(paths, human_face_risk="clear_face")
            _write_raw_image_files(root)
            rebuild_agent_interface(paths)
            result = create_video_creation_run(
                paths,
                "做一个60秒石英纤维隔热带产品介绍视频",
                language_version="en",
                platforms=["youtube_shorts"],
                duration_seconds=60,
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            _complete_video_interview(run_dir)
            generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))
            confirm_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 5, 0))
            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))
            storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
            self.assertTrue(any(shot["human_face_risk"] == "clear_face" for shot in storyboard["shots"]))
            self.assertTrue(any(shot["shot_design_validation"]["status"] == "blocked" for shot in storyboard["shots"]))
            confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))
            generate_dreamina_jobs(run_dir, now=datetime(2026, 6, 25, 15, 30, 0))

            jobs = json.loads((run_dir / "dreamina_generation" / "dreamina_jobs.json").read_text(encoding="utf-8"))
            self.assertTrue(any(job["human_face_risk"] == "clear_face" for job in jobs["jobs"]))
            self.assertTrue(any("清晰可辨识真人脸部" in "; ".join(job["validation"]["messages"]) for job in jobs["jobs"]))
            with self.assertRaisesRegex(ValueError, "存在 blocked 即梦任务"):
                confirm_dreamina_generation(run_dir, now=datetime(2026, 6, 25, 15, 35, 0))

    def test_generates_video_plan_and_waits_for_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))

            result = _generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))

            self.assertEqual(result.status, "video_plan_ready")
            self.assertEqual(result.phase, "awaiting_video_plan_confirmation")
            plan_md = run_dir / "video_plan.md"
            plan_json = run_dir / "video_plan.json"
            inspection_json = run_dir / "material_visual_inspection.json"
            self.assertTrue(plan_md.exists())
            self.assertTrue(plan_json.exists())
            self.assertTrue(inspection_json.exists())
            plan_text = plan_md.read_text(encoding="utf-8")
            self.assertIn("# 视频策划", plan_text)
            self.assertIn("对外中文名：特种玻璃纤维带", plan_text)
            self.assertIn("对外英文名：Specialty Glass Fiber Tape", plan_text)
            self.assertIn("允许 55-65 秒", plan_text)
            self.assertIn("content_asset/quartz_product_photo", plan_text)
            self.assertNotIn("content_asset/quartz_product_video", plan_text)
            self.assertIn("## 视频创作素材准备度", plan_text)
            self.assertIn("产品图片素材：4", plan_text)
            self.assertIn("可用于 image2video 的图片参考素材：12", plan_text)
            self.assertIn("## 生成范围", plan_text)
            self.assertIn("生成并锁定标准 storyboard.srt", plan_text)
            self.assertIn("不生成配音、不烧录字幕、不生成背景音乐", plan_text)
            self.assertNotIn("音乐 brief", plan_text)
            self.assertIn("不得使用 video_script", plan_text)
            self.assertIn("不得使用母版/master", plan_text)
            self.assertIn("请确认策划后继续生成分镜", plan_text)
            self.assertIn("## 策划代表图片", plan_text)
            self.assertIn("已由 Codex 实际打开并完成主体", plan_text)
            self.assertIn("## 视频策划摘要", result.message)
            inspection = json.loads(inspection_json.read_text(encoding="utf-8"))
            self.assertEqual(inspection["status"], "completed")
            self.assertGreaterEqual(len(inspection["candidates"]), 6)
            self.assertIn("![代表图 01]", result.message)

            plan = json.loads(plan_json.read_text(encoding="utf-8"))
            self.assertEqual(plan["status"], "draft_pending_confirmation")
            self.assertEqual(plan["product"]["external_name_zh"], "特种玻璃纤维带")
            self.assertEqual(plan["product"]["external_name_en"], "Specialty Glass Fiber Tape")
            self.assertEqual(plan["knowledge_boundary"]["task_type"], "video_creation")
            self.assertFalse(plan["knowledge_boundary"]["raw_access"])
            self.assertTrue(plan["knowledge_boundary"]["no_keyword_expansion"])
            self.assertEqual(plan["format"]["duration_tolerance_seconds"], {"min": 55, "max": 65})
            self.assertEqual(plan["generation_policy"]["dreamina_model"], "seedance2.0_vip")
            self.assertEqual(plan["production_style"]["id"], "industrial_professional")
            self.assertIn("hook", plan["creative_quality"])
            self.assertIn("dexhunter/seedance2-skill", {item["source"] for item in plan["external_skill_absorption"]})
            self.assertTrue(plan["prompt_policy"]["visible_product_requires_real_reference"])
            self.assertEqual(plan["material_availability"]["counts"]["product_image_assets"], 4)
            self.assertEqual(plan["material_availability"]["counts"]["usable_visual_reference_assets"], 12)
            self.assertNotIn("product_video_assets", plan["material_availability"]["counts"])
            self.assertEqual(len(plan["content_assets"]), 12)
            content_asset_ids = {asset["id"] for asset in plan["content_assets"]}
            self.assertIn("content_asset/quartz_product_photo", content_asset_ids)
            self.assertIn("content_asset/quartz_application_pipe_01", content_asset_ids)
            self.assertNotIn("music_brief", plan)
            self.assertNotIn("subtitle_policy", plan)
            self.assertNotIn("audio_policy", plan)

            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertFalse(state["confirmations"]["video_plan"])
            self.assertEqual(state["current_pending_confirmation"], "确认策划")
            self.assertEqual(state["files"]["video_plan_md"], str(plan_md))
            self.assertEqual(
                [item["status"] for item in state["status_history"]],
                [
                    "video_interview_in_progress",
                    "video_brief_confirmed",
                    "material_visual_inspection_required",
                    "material_visual_inspection_completed",
                    "video_plan_ready",
                ],
            )

    def test_video_plan_does_not_silently_overwrite_existing_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))
            generate_video_plan(run_dir)

            with self.assertRaises(FileExistsError):
                _generate_video_plan(run_dir)

    def test_confirms_video_plan_and_moves_to_storyboard_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))
            generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))

            result = confirm_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 5, 0))

            self.assertEqual(result.status, "video_plan_confirmed")
            self.assertEqual(result.phase, "ready_for_storyboard")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["video_plan"])
            self.assertFalse(state["confirmations"]["storyboard"])
            self.assertEqual(state["current_pending_confirmation"], "生成分镜")
            self.assertEqual(
                [item["status"] for item in state["status_history"]],
                [
                    "video_interview_in_progress",
                    "video_brief_confirmed",
                    "material_visual_inspection_required",
                    "material_visual_inspection_completed",
                    "video_plan_ready",
                    "video_plan_confirmed",
                ],
            )
            change_log = (run_dir / "change_log.md").read_text(encoding="utf-8")
            self.assertIn("确认视频策划，进入分镜生成阶段。", change_log)

    def test_video_plan_rejects_incomplete_pre_direction_material_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))
            state_path = run_dir / "workflow_state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["interview"]["decision_evidence"]["material_visual_direction"].pop()
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "证据与策划候选图片集合不一致"):
                _generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))

    def test_material_shortage_blocks_plan_until_duration_is_shortened(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))
            _mark_interview_materials_usable(run_dir, 3)
            _generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))

            with self.assertRaisesRegex(ValueError, "只支持约 15 秒"):
                confirm_video_plan(run_dir)
            shortened = shorten_video_plan_duration(run_dir, 15)
            self.assertEqual(shortened.status, "video_plan_ready")
            confirmed = confirm_video_plan(run_dir)
            self.assertEqual(confirmed.phase, "ready_for_storyboard")

    def test_explicit_repetition_approval_allows_longer_storyboard_from_inspected_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))
            _mark_interview_materials_usable(run_dir, 3)
            _generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))

            approve_plan_material_repetition(run_dir, "我确认有意重复这三张图片")
            confirm_video_plan(run_dir)
            generate_storyboard(run_dir)

            storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
            selected_ids = {
                shot["selected_material"]["id"]
                for shot in storyboard["shots"]
                if shot.get("selected_material")
            }
            self.assertLessEqual(len(selected_ids), 3)
            self.assertTrue(storyboard["deliberate_repetition_approved"])

    def test_resumes_current_video_creation_phase_without_restarting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))
            generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))

            result = resume_video_creation_run(run_dir, now=datetime(2026, 6, 25, 15, 1, 0))

            self.assertEqual(result.status, "video_plan_ready")
            self.assertEqual(result.phase, "awaiting_video_plan_confirmation")
            status_json = run_dir / "workflow_status.json"
            status_md = run_dir / "workflow_status.md"
            self.assertTrue(status_json.exists())
            self.assertTrue(status_md.exists())
            status = json.loads(status_json.read_text(encoding="utf-8"))
            self.assertEqual(status["current_pending_confirmation"], "确认策划")
            self.assertIn("确认", status["suggested_replies"])
            self.assertTrue(status["policy"]["resume_from_current_phase_only"])
            self.assertIn("不重复已确认步骤", status_md.read_text(encoding="utf-8"))

    def test_resume_blocks_legacy_tiktok_or_fixed_interview_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))
            state_path = run_dir / "workflow_state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["platforms"] = ["youtube_shorts", "tiktok"]
            state["interview"]["schema_version"] = "video-creation-interview-v1"
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

            result = resume_video_creation_run(run_dir)

            self.assertEqual(result.status, "legacy_video_run_migration_blocked")
            self.assertEqual(result.phase, "blocked")
            self.assertIn("YouTube Shorts 单平台", result.message)
            self.assertIn("证据驱动决策账本", result.message)

    def test_handles_natural_language_confirmation_reply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))
            generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))

            result = handle_video_creation_reply(run_dir, "确认策划", now=datetime(2026, 6, 25, 15, 5, 0))

            self.assertEqual(result.status, "storyboard_ready")
            self.assertEqual(result.phase, "awaiting_storyboard_confirmation")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["video_plan"])
            self.assertEqual(state["current_pending_confirmation"], "确认当前分镜与 SRT")
            self.assertTrue((run_dir / "storyboard.md").exists())
            self.assertTrue((run_dir / "storyboard.srt").exists())

    def test_handles_generation_reply_for_current_pending_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_plan_confirmed_run(Path(tmp))

            result = handle_video_creation_reply(run_dir, "生成分镜", now=datetime(2026, 6, 25, 15, 10, 0))

            self.assertEqual(result.status, "storyboard_ready")
            self.assertEqual(result.phase, "awaiting_storyboard_confirmation")
            self.assertTrue((run_dir / "storyboard.md").exists())
            self.assertTrue((run_dir / "storyboard.srt").exists())
            self.assertFalse((run_dir / "prompts.json").exists())

    def test_cannot_confirm_video_plan_before_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))

            with self.assertRaisesRegex(ValueError, "找不到可确认的视频策划"):
                confirm_video_plan(run_dir)

    def test_generates_storyboard_and_srt_then_prompts_after_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_plan_confirmed_run(Path(tmp))

            result = generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))

            self.assertEqual(result.status, "storyboard_ready")
            self.assertEqual(result.phase, "awaiting_storyboard_confirmation")
            storyboard_md = run_dir / "storyboard.md"
            storyboard_json = run_dir / "storyboard.json"
            storyboard_srt = run_dir / "storyboard.srt"
            prompts_md = run_dir / "prompts.md"
            prompts_json = run_dir / "prompts.json"
            self.assertTrue(storyboard_md.exists())
            self.assertTrue(storyboard_json.exists())
            self.assertTrue(storyboard_srt.exists())
            self.assertFalse(prompts_md.exists())
            self.assertFalse(prompts_json.exists())

            storyboard_text = storyboard_md.read_text(encoding="utf-8")
            self.assertIn("# 视频分镜", storyboard_text)
            self.assertIn("Prompt 只在共同确认后生成", storyboard_text)
            self.assertIn("content_asset/quartz_product_photo", storyboard_text)
            self.assertIn("需要真实产品参考：是", storyboard_text)
            self.assertIn("## 分镜与 SRT 共同确认", result.message)
            self.assertIn("![镜头 01 参考图 1]", result.message)

            storyboard = json.loads(storyboard_json.read_text(encoding="utf-8"))
            self.assertEqual(storyboard["status"], "draft_pending_confirmation")
            self.assertEqual(len(storyboard["shots"]), 8)
            self.assertTrue(storyboard["policy"]["srt_is_sole_future_narration_transcript"])
            self.assertTrue(storyboard["policy"]["prompts_created_only_after_confirmation"])
            self.assertEqual(storyboard["production_style"]["id"], "industrial_professional")
            self.assertTrue(all(shot["creative_quality_checks"] for shot in storyboard["shots"]))
            self.assertTrue(all(shot["shot_design_validation"]["status"] == "ok" for shot in storyboard["shots"]))
            self.assertTrue(any(shot["material_mode"] == "image2video" for shot in storyboard["shots"]))
            self.assertFalse(any(shot["material_mode"] == "text2video" and shot["product_visible"] for shot in storyboard["shots"]))
            selected_ids = [shot["selected_material"]["id"] for shot in storyboard["shots"] if shot.get("selected_material")]
            self.assertEqual(len(selected_ids), len(set(selected_ids)))
            product_hero = next(shot for shot in storyboard["shots"] if shot["role"] == "product_hero")
            product_detail = next(shot for shot in storyboard["shots"] if shot["role"] == "product_detail")
            closing_cta = next(shot for shot in storyboard["shots"] if shot["role"] == "closing_cta")
            self.assertEqual(product_hero["first_frame_reference_id"], "content_asset/quartz_product_photo")
            self.assertEqual(product_detail["first_frame_reference_id"], "content_asset/quartz_texture_detail_01")
            self.assertEqual(closing_cta["last_frame_reference_id"], "content_asset/quartz_closing_product_01")
            self.assertEqual(product_hero["human_face_risk"], "none")

            srt_text = storyboard_srt.read_text(encoding="utf-8")
            self.assertIn("00:00:00,000 -->", srt_text)
            self.assertIsNone(re.search(r"[\u3400-\u9fff]", srt_text))
            self.assertTrue(all(shot.get("subtitle_text") or shot.get("intentional_silence") for shot in storyboard["shots"]))

            confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))
            self.assertTrue(prompts_md.exists())
            self.assertTrue(prompts_json.exists())
            prompts_text = prompts_md.read_text(encoding="utf-8")
            self.assertIn("# 即梦 Prompts", prompts_text)
            self.assertIn("以下英文 Prompt 是给即梦使用，不是视频字幕", prompts_text)
            self.assertIn("@图片1", prompts_text)
            self.assertIn("用途：", prompts_text)
            prompts = json.loads(prompts_json.read_text(encoding="utf-8"))
            self.assertFalse(prompts["prompts_are_subtitles"])
            self.assertEqual(len(prompts["prompts"]), len(storyboard["shots"]))
            self.assertEqual(prompts["model"], "seedance2.0_vip")
            self.assertEqual(prompts["prompt_policy"]["structure"][0], "timebox")
            self.assertTrue(prompts["prompt_policy"]["conflict_rules"])
            self.assertTrue(prompts["prompt_policy"]["duration_complexity_policy"])
            self.assertEqual(prompts["material_reference_map"]["counts"]["images"], len(storyboard["shots"]))
            self.assertEqual(prompts["material_reference_map"]["references"][0]["label"], "@图片1")
            reference_material_ids = [item["material_id"] for item in prompts["material_reference_map"]["references"]]
            self.assertEqual(len(reference_material_ids), len(set(reference_material_ids)))
            self.assertTrue(any(item["usages"] for item in prompts["material_reference_map"]["references"]))
            self.assertTrue(any(item["reference_required"] for item in prompts["prompts"]))
            self.assertTrue(all(item["prompt_standard"] == "tuolin-industrial-seedance-v2" for item in prompts["prompts"]))
            self.assertTrue(all(item["prompt_quality_checks"]["status"] == "ok" for item in prompts["prompts"]))
            self.assertTrue(all(item["prompt_components"]["reference_material"] for item in prompts["prompts"]))
            self.assertTrue(all(item["prompt_components"]["time_segments"] for item in prompts["prompts"]))
            self.assertTrue(all(item["prompt_components"]["product_display_template"] for item in prompts["prompts"]))
            self.assertTrue(any("0-2s" in item["prompt_components"]["time_segments"] for item in prompts["prompts"]))
            self.assertTrue(any("织纹微距" in item["prompt_components"]["motion_and_camera"] or "woven texture" in item["prompt_components"]["product_display_template"] for item in prompts["prompts"]))
            self.assertTrue(any("first-frame reference" in item["prompt"] for item in prompts["prompts"]))
            self.assertTrue(any("last-frame reference" in item["prompt"] for item in prompts["prompts"]))
            for item in prompts["prompts"]:
                prompt_without_reference_labels = re.sub(r"@图片\d+", "", item["prompt"])
                self.assertIsNone(re.search(r"[\u3400-\u9fff]", prompt_without_reference_labels))
            self.assertFalse(any("short drama" in item["prompt"].lower() or "dance" in item["prompt"].lower() or "xianxia" in item["prompt"].lower() for item in prompts["prompts"]))
            referenced = [item for item in prompts["prompts"] if item["reference_required"]]
            self.assertEqual(
                [item["numbered_reference_label"] for item in referenced],
                [f"@图片{index}" for index in range(1, len(referenced) + 1)],
            )
            self.assertTrue(all(item["reference_usage"] for item in referenced))

            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["storyboard"])
            self.assertEqual(state["current_pending_confirmation"], "规划即梦任务")
            self.assertEqual(state["files"]["storyboard_json"], str(storyboard_json))
            self.assertEqual(state["files"]["prompts_json"], str(prompts_json))

    def test_storyboard_markdown_embeds_reference_image_previews(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_plan_confirmed_run(root)
            _write_raw_image_files(root)

            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))

            storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
            storyboard_md = (run_dir / "storyboard.md").read_text(encoding="utf-8")
            self.assertEqual(storyboard["image_reference_summary"]["status"], "ok")
            self.assertEqual(storyboard["image_reference_summary"]["copied_preview_count"], len(storyboard["shots"]))
            self.assertTrue((run_dir / "storyboard_assets" / "shot_02_reference_01.jpg").exists())
            self.assertIn("![镜头 02 参考图 1](storyboard_assets/shot_02_reference_01.jpg)", storyboard_md)
            self.assertIn("primary_product_or_action_reference", storyboard_md)
            self.assertIn("图片引用检查", storyboard_md)

    def test_natural_language_can_delete_storyboard_shot_and_recalculate_duration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_plan_confirmed_run(Path(tmp))
            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))

            result = handle_video_creation_reply(run_dir, "删除镜头 03", now=datetime(2026, 6, 25, 15, 12, 0))

            self.assertEqual(result.status, "storyboard_revised")
            self.assertEqual(result.phase, "awaiting_storyboard_confirmation")
            storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
            self.assertNotIn("03", [shot["shot_id"] for shot in storyboard["shots"]])
            self.assertFalse((run_dir / "prompts.json").exists())
            self.assertEqual(storyboard["actual_duration_seconds"], 52)
            self.assertIn("减少约 8 秒", (run_dir / "storyboard.md").read_text(encoding="utf-8"))
            self.assertTrue((run_dir / "storyboard.srt").exists())
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertFalse(state["confirmations"]["storyboard"])
            self.assertNotIn("dreamina_jobs_json", state["files"])

    def test_natural_language_can_replace_storyboard_shot_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_plan_confirmed_run(root)
            _write_raw_image_files(root)
            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))
            override_path = root / "manual-shot-03.jpg"
            override_path.write_bytes(b"manual image")

            result = handle_video_creation_reply(
                run_dir,
                f"镜头 03 图片换成 {override_path}",
                now=datetime(2026, 6, 25, 15, 13, 0),
            )

            self.assertEqual(result.status, "storyboard_revised")
            storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
            shot_03 = next(shot for shot in storyboard["shots"] if shot["shot_id"] == "03")
            self.assertEqual(shot_03["selected_material"]["id"], "user_image_override/shot_03")
            self.assertEqual(shot_03["selected_materials"][0]["id"], "user_image_override/shot_03")
            self.assertEqual(shot_03["image_preview"]["status"], "copied")
            self.assertFalse((run_dir / "prompts.json").exists())
            self.assertIn("manual-shot-03.jpg", (run_dir / "storyboard.md").read_text(encoding="utf-8"))

    def test_storyboard_reorder_updates_order_and_prompts_before_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_plan_confirmed_run(Path(tmp))
            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))

            result = handle_video_creation_reply(run_dir, "把镜头 04 移到镜头 02 前面", now=datetime(2026, 6, 25, 15, 12, 0))

            self.assertEqual(result.status, "storyboard_revised")
            storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
            self.assertEqual([shot["shot_id"] for shot in storyboard["shots"][:3]], ["01", "04", "02"])
            self.assertFalse((run_dir / "prompts.json").exists())
            self.assertTrue((run_dir / "storyboard.srt").exists())
            self.assertIn("镜头 04", result.message)

    def test_duplicate_storyboard_image_requires_explicit_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_plan_confirmed_run(Path(tmp))
            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))
            storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
            first_source = storyboard["shots"][0]["image_preview"]["source_path"]
            handle_video_creation_reply(
                run_dir,
                f"镜头 02 图片换成 {first_source}",
                now=datetime(2026, 6, 25, 15, 11, 0),
            )

            with self.assertRaisesRegex(ValueError, "重复图片参考"):
                confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 12, 0))

            approved = handle_video_creation_reply(
                run_dir,
                "允许有意重复图片",
                now=datetime(2026, 6, 25, 15, 13, 0),
            )
            self.assertIn("重复图片警告", approved.message)
            confirmed = confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 14, 0))
            self.assertEqual(confirmed.status, "storyboard_confirmed")

    def test_storyboard_does_not_silently_overwrite_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_plan_confirmed_run(Path(tmp))
            generate_storyboard(run_dir)

            with self.assertRaises(FileExistsError):
                generate_storyboard(run_dir)

    def test_confirms_storyboard_and_moves_to_dreamina_planning_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_plan_confirmed_run(Path(tmp))
            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))

            result = confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))

            self.assertEqual(result.status, "storyboard_confirmed")
            self.assertEqual(result.phase, "ready_for_dreamina_jobs")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["storyboard"])
            self.assertNotIn("narration_script", state["confirmations"])
            self.assertNotIn("voice", state["confirmations"])
            self.assertNotIn("narration", state["confirmations"])
            self.assertEqual(state["current_pending_confirmation"], "规划即梦任务")
            self.assertEqual(
                [item["status"] for item in state["status_history"]],
                [
                    "video_interview_in_progress",
                    "video_brief_confirmed",
                    "material_visual_inspection_required",
                    "material_visual_inspection_completed",
                    "video_plan_ready",
                    "video_plan_confirmed",
                    "storyboard_ready",
                    "storyboard_confirmed",
                ],
            )

    def test_video_only_run_skips_narration_and_goes_straight_to_dreamina_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_video_only_ready_run(Path(tmp))
            generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))
            confirm_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 5, 0))
            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))

            confirmed = confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))
            self.assertEqual(confirmed.phase, "ready_for_dreamina_jobs")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["workflow_mode"], "video_only")
            self.assertEqual(state["current_pending_confirmation"], "规划即梦任务")
            self.assertNotEqual(state["phase"], "ready_for_narration_script")

            result = generate_dreamina_jobs(run_dir, now=datetime(2026, 6, 25, 15, 20, 0))
            self.assertEqual(result.phase, "awaiting_dreamina_generation_confirmation")
            jobs = json.loads((run_dir / "dreamina_generation" / "dreamina_jobs.json").read_text(encoding="utf-8"))
            self.assertTrue(jobs["policy"]["video_only_mode"])
            self.assertNotIn("narration_timing", jobs["source_files"])

            confirm_dreamina_generation(run_dir, now=datetime(2026, 6, 25, 15, 25, 0))
            submit_dreamina_jobs(run_dir, now=datetime(2026, 6, 25, 15, 30, 0))
            query_dreamina_results(run_dir, now=datetime(2026, 6, 25, 15, 35, 0))
            shots = confirm_shots(run_dir, now=datetime(2026, 6, 25, 15, 40, 0))
            self.assertEqual(shots.phase, "ready_for_video_assembly")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["current_pending_confirmation"], "合并视频")
            self.assertNotIn("narration_script", state["confirmations"])
            self.assertNotIn("voice", state["confirmations"])
            self.assertNotIn("narration", state["confirmations"])
            self.assertNotIn("final_video", state["confirmations"])

    def test_cannot_generate_storyboard_before_plan_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))
            generate_video_plan(run_dir)

            with self.assertRaisesRegex(ValueError, "当前阶段是 'awaiting_video_plan_confirmation'"):
                generate_storyboard(run_dir)

    def test_removed_audio_subtitle_and_final_edit_helpers_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_storyboard_confirmed_run(Path(tmp))

            removed_message = "已收敛为只负责即梦视频生成"
            removed_calls = [
                lambda: generate_narration_script(run_dir),
                lambda: confirm_narration_script(run_dir),
                lambda: generate_voice_samples(run_dir),
                lambda: select_voice(run_dir, 1),
                lambda: generate_full_narration(run_dir),
                lambda: confirm_narration(run_dir),
                lambda: assemble_final_preview(run_dir),
                lambda: select_bgm_track(run_dir, title="x", source="x", license_name="x", local_path=run_dir / "x.mp3"),
                lambda: run_quality_gate(run_dir),
                lambda: record_manual_quality_check(run_dir, audio_ok=True, visual_ok=True),
                lambda: confirm_final_video(run_dir),
            ]
            for call in removed_calls:
                with self.assertRaisesRegex(ValueError, removed_message):
                    call()

    def test_rejects_removed_voice_selection_reply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_storyboard_confirmed_run(Path(tmp))

            with self.assertRaisesRegex(ValueError, "未支持的视频创作回复"):
                handle_video_creation_reply(run_dir, "声音选 2", now=datetime(2026, 6, 25, 15, 23, 0))

    def test_generates_dreamina_jobs_after_storyboard_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_storyboard_confirmed_run(Path(tmp))

            result = generate_dreamina_jobs(run_dir, now=datetime(2026, 6, 25, 15, 30, 0))

            self.assertEqual(result.status, "dreamina_jobs_ready")
            self.assertEqual(result.phase, "awaiting_dreamina_generation_confirmation")
            jobs_md = run_dir / "dreamina_generation" / "dreamina_jobs.md"
            jobs_json = run_dir / "dreamina_generation" / "dreamina_jobs.json"
            self.assertTrue(jobs_md.exists())
            self.assertTrue(jobs_json.exists())
            jobs_text = jobs_md.read_text(encoding="utf-8")
            self.assertIn("# 即梦任务计划", jobs_text)
            self.assertIn("确认即梦生成", jobs_text)
            self.assertIn("预计总额度", jobs_text)
            self.assertIn("本文件只是任务计划，不会提交即梦任务", jobs_text)
            self.assertIn("编号引用：@图片1", jobs_text)
            jobs = json.loads(jobs_json.read_text(encoding="utf-8"))
            self.assertEqual(jobs["status"], "planned_pending_user_confirmation")
            self.assertEqual(jobs["format"]["model"], "seedance2.0_vip")
            self.assertEqual(jobs["format"]["dreamina_resolution"], "1080P")
            self.assertEqual(jobs["material_reference_map"]["counts"]["images"], len(jobs["jobs"]))
            self.assertTrue(jobs["policy"]["do_not_submit_before_confirmation"])
            self.assertTrue(jobs["policy"]["job_validation_required"])
            self.assertEqual(len(jobs["jobs"]), 8)
            self.assertGreater(jobs["estimated_total_credits"], 0)
            self.assertTrue(all(job["job_type"] == "image2video" for job in jobs["jobs"]))
            self.assertTrue(all(job["estimated_credits"] > 0 for job in jobs["jobs"]))
            self.assertTrue(all("narration_timing" not in job for job in jobs["jobs"]))
            material_ids = [job["reference_material_id"] for job in jobs["jobs"]]
            reference_labels = [job["numbered_reference_label"] for job in jobs["jobs"]]
            self.assertEqual(len(material_ids), len(set(material_ids)))
            self.assertEqual(reference_labels, [f"@图片{index}" for index in range(1, len(jobs["jobs"]) + 1)])
            self.assertTrue(all(job["reference_usage"] for job in jobs["jobs"]))
            self.assertTrue(any(job["first_frame_reference_id"] == "content_asset/quartz_product_photo" for job in jobs["jobs"]))
            self.assertTrue(any(job["last_frame_reference_id"] == "content_asset/quartz_closing_product_01" for job in jobs["jobs"]))
            self.assertTrue(all(job["human_face_risk"] == "none" for job in jobs["jobs"]))
            self.assertTrue(all(job["validation"]["status"] == "ok" for job in jobs["jobs"]))

            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertFalse(state["confirmations"]["dreamina_generation"])
            self.assertEqual(state["current_pending_confirmation"], "确认即梦生成")
            self.assertEqual(state["files"]["dreamina_jobs_json"], str(jobs_json))

    def test_confirms_dreamina_generation_authorization_without_submitting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_jobs_ready_run(Path(tmp))

            result = confirm_dreamina_generation(run_dir, now=datetime(2026, 6, 25, 15, 35, 0))

            self.assertEqual(result.status, "dreamina_generation_confirmed")
            self.assertEqual(result.phase, "ready_for_dreamina_submission")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["dreamina_generation"])
            self.assertEqual(state["current_pending_confirmation"], "提交即梦任务")
            self.assertEqual(
                state["dreamina_authorization"]["estimated_total_credits"],
                sum(job["estimated_credits"] for job in json.loads(
                    (run_dir / "dreamina_generation" / "dreamina_jobs.json").read_text(encoding="utf-8")
                )["jobs"]),
            )
            self.assertIn("本步骤不实际提交任务", state["dreamina_authorization"]["note"])
            self.assertFalse((run_dir / "dreamina_generation" / "dreamina_results.json").exists())

    def test_dreamina_jobs_do_not_silently_overwrite_existing_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_storyboard_confirmed_run(Path(tmp))
            generate_dreamina_jobs(run_dir)

            with self.assertRaises(FileExistsError):
                generate_dreamina_jobs(run_dir)

    def test_cannot_generate_dreamina_jobs_before_storyboard_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_plan_confirmed_run(Path(tmp))

            with self.assertRaisesRegex(ValueError, "当前阶段是 'ready_for_storyboard'"):
                generate_dreamina_jobs(run_dir)

    def test_missing_official_images_block_video_task_at_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_product_card_only(paths)
            rebuild_agent_interface(paths)

            with self.assertRaisesRegex(ValueError, "没有关联的官方图片素材"):
                create_video_creation_run(
                    paths,
                    "做一个60秒石英纤维隔热带 YouTube Shorts。",
                    language_version="en",
                    platforms=["youtube_shorts"],
                    duration_seconds=60,
                )

    def test_duplicate_dreamina_image_references_are_blocked_before_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_storyboard_confirmed_run(Path(tmp))
            prompts_path = run_dir / "prompts.json"
            prompts = json.loads(prompts_path.read_text(encoding="utf-8"))
            first_reference = prompts["prompts"][0]
            for item in prompts["prompts"][1:]:
                item["reference_material_id"] = first_reference["reference_material_id"]
                item["numbered_reference_label"] = first_reference["numbered_reference_label"]
                item["reference_usage"] = first_reference["reference_usage"]
                item["first_frame_reference_id"] = first_reference["first_frame_reference_id"]
                item["last_frame_reference_id"] = first_reference["last_frame_reference_id"]
            prompts_path.write_text(json.dumps(prompts, ensure_ascii=False, indent=2), encoding="utf-8")

            generate_dreamina_jobs(run_dir)

            jobs = json.loads((run_dir / "dreamina_generation" / "dreamina_jobs.json").read_text(encoding="utf-8"))
            duplicate_jobs = [job for job in jobs["jobs"] if job["shot_id"] != "01"]
            self.assertTrue(any(job["validation"]["status"] == "blocked" for job in duplicate_jobs))
            self.assertTrue(any("重复使用同一张图片参考素材" in " ".join(job["validation"]["messages"]) for job in duplicate_jobs))
            with self.assertRaisesRegex(ValueError, "存在 blocked 即梦任务"):
                confirm_dreamina_generation(run_dir)

    def test_prompt_conflicts_and_duration_complexity_block_dreamina_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_storyboard_confirmed_run(Path(tmp))
            prompts_path = run_dir / "prompts.json"
            prompts = json.loads(prompts_path.read_text(encoding="utf-8"))
            prompts["prompts"][0]["prompt_components"]["motion_and_camera"] = "Fixed camera, static camera, fast pan, orbit, tracking shot."
            prompts["prompts"][0]["prompt_components"]["time_segments"] = (
                "0-1s: product. 1-2s: cut to pipe. 2-3s: new scene. "
                "3-4s: montage. 4-5s: split screen."
            )
            prompts["prompts"][0]["prompt"] = (
                prompts["prompts"][0]["prompt"]
                + " Fixed camera, static camera, fast pan, orbit, tracking shot. "
                + "Cut to a new scene, montage, split screen, rapid transition."
            )
            prompts["prompts"][0].pop("prompt_quality_checks", None)
            prompts_path.write_text(json.dumps(prompts, ensure_ascii=False, indent=2), encoding="utf-8")

            generate_dreamina_jobs(run_dir)

            jobs = json.loads((run_dir / "dreamina_generation" / "dreamina_jobs.json").read_text(encoding="utf-8"))
            first_job = jobs["jobs"][0]
            self.assertEqual(first_job["validation"]["status"], "blocked")
            self.assertEqual(first_job["prompt_quality_checks"]["status"], "blocked")
            validation_text = "\n".join(first_job["validation"]["messages"])
            self.assertIn("固定镜头", validation_text)
            self.assertIn("场景/转场复杂度", validation_text)
            with self.assertRaisesRegex(ValueError, "存在 blocked 即梦任务"):
                confirm_dreamina_generation(run_dir)

    def test_submits_dreamina_jobs_as_dry_run_after_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_generation_confirmed_run(Path(tmp))

            result = submit_dreamina_jobs(run_dir, now=datetime(2026, 6, 25, 15, 40, 0))

            self.assertEqual(result.status, "dreamina_manual_submission_handoff_ready")
            self.assertEqual(result.phase, "awaiting_dreamina_results")
            submission_json = run_dir / "dreamina_generation" / "dreamina_submission.json"
            submission_md = run_dir / "dreamina_generation" / "dreamina_submission.md"
            manual_ps1 = run_dir / "dreamina_generation" / "submit_real_dreamina_jobs.ps1"
            manual_template = run_dir / "dreamina_generation" / "manual_submission_template.json"
            self.assertIn("请打开 Windows PowerShell", result.message)
            self.assertIn("powershell.exe -ExecutionPolicy Bypass -File", result.message)
            self.assertIn(str(manual_ps1), result.message)
            self.assertIn("即梦已全部生成", result.message)
            self.assertTrue(submission_json.exists())
            self.assertTrue(submission_md.exists())
            self.assertTrue(manual_ps1.exists())
            self.assertTrue(manual_template.exists())
            submission = json.loads(submission_json.read_text(encoding="utf-8"))
            self.assertEqual(submission["mode"], "dry_run")
            self.assertTrue(submission["policy"]["dry_run_does_not_consume_credits"])
            self.assertEqual(len(submission["submissions"]), 8)
            self.assertTrue(all(item["status"] == "dry_run_submitted" for item in submission["submissions"]))
            self.assertTrue(all(item["provider_task_id"].startswith("dryrun_shot_") for item in submission["submissions"]))
            submission_text = submission_md.read_text(encoding="utf-8")
            self.assertIn("人工真实提交脚本", submission_text)
            self.assertIn("请打开 Windows PowerShell，复制并运行下面这条命令", submission_text)
            self.assertIn("powershell.exe -ExecutionPolicy Bypass -File", submission_text)
            self.assertIn("submit_real_dreamina_jobs.ps1", submission_text)
            self.assertIn("回到 Codex 回复：`即梦已全部生成`", submission_text)
            self.assertIn("dreamina image2video", submission_text)
            ps1_text = manual_ps1.read_text(encoding="utf-8")
            self.assertIn("manual_submission.json", ps1_text)
            self.assertIn("--model_version", ps1_text)
            self.assertTrue(manual_ps1.read_bytes().startswith(b"\xef\xbb\xbf"))
            self.assertNotIn("'--image' '--prompt'", ps1_text)
            self.assertIn("product.jpg", ps1_text)
            self.assertIn("Convert-DreaminaOutputJson", ps1_text)
            self.assertIn("Save-ManualSubmission", ps1_text)
            self.assertIn("Loaded existing manual submission progress", ps1_text)
            self.assertIn("already submitted", ps1_text)
            self.assertIn("resumable_manual_submission", ps1_text)
            template = json.loads(manual_template.read_text(encoding="utf-8"))
            self.assertEqual(template["mode"], "manual_execute")
            self.assertTrue(all(item["status"] == "pending_manual_execution" for item in template["submissions"]))

            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(
                state["current_pending_confirmation"],
                "先执行 PowerShell 真实提交，再在即梦网页端确认全部任务完成",
            )
            self.assertEqual(state["files"]["dreamina_submission_json"], str(submission_json))
            self.assertEqual(state["files"]["dreamina_manual_submit_ps1"], str(manual_ps1))

    def test_dreamina_submission_uses_content_asset_local_path_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_jobs_ready_run(Path(tmp))
            jobs_path = run_dir / "dreamina_generation" / "dreamina_jobs.json"
            jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
            for job in jobs["jobs"]:
                selected = job["selected_material"]
                selected.pop("files", None)
                selected["local_path"] = "raw/01_产品/02_石英纤维隔热带/02_产品图片/local-product.png"
                job["validation"] = {"status": "ok", "messages": ["ok"]}
            jobs_path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")

            confirm_dreamina_generation(run_dir, now=datetime(2026, 6, 25, 15, 35, 0))
            submit_dreamina_jobs(run_dir, now=datetime(2026, 6, 25, 15, 40, 0))

            manual_ps1 = run_dir / "dreamina_generation" / "submit_real_dreamina_jobs.ps1"
            ps1_text = manual_ps1.read_text(encoding="utf-8-sig")
            self.assertIn("local-product.png", ps1_text)
            self.assertNotIn("'--image' '--prompt'", ps1_text)

    def test_task_plan_change_invalidates_paid_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_generation_confirmed_run(Path(tmp))
            jobs_path = run_dir / "dreamina_generation" / "dreamina_jobs.json"
            jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
            jobs["estimated_total_credits"] += 1
            jobs_path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "原额度授权已撤销"):
                submit_dreamina_jobs(run_dir)

            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "dreamina_authorization_invalidated")
            self.assertEqual(state["phase"], "awaiting_dreamina_generation_confirmation")
            self.assertFalse(state["confirmations"]["dreamina_generation"])

    def test_cannot_submit_dreamina_jobs_without_generation_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_jobs_ready_run(Path(tmp))

            with self.assertRaisesRegex(ValueError, "当前阶段是 'awaiting_dreamina_generation_confirmation'"):
                submit_dreamina_jobs(run_dir)

    def test_queries_dreamina_results_and_confirms_shots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_submitted_run(Path(tmp))

            result = query_dreamina_results(run_dir, now=datetime(2026, 6, 25, 15, 45, 0))

            self.assertEqual(result.status, "dreamina_results_ready")
            self.assertEqual(result.phase, "awaiting_shot_confirmation")
            results_json = run_dir / "dreamina_generation" / "dreamina_results.json"
            results_md = run_dir / "dreamina_generation" / "dreamina_results.md"
            self.assertTrue(results_json.exists())
            self.assertTrue(results_md.exists())
            results = json.loads(results_json.read_text(encoding="utf-8"))
            self.assertEqual(results["mode"], "dry_run")
            self.assertTrue(all(item["status"] == "succeeded" for item in results["results"]))
            self.assertTrue(all(item["output_path"].endswith(".mp4") for item in results["results"]))
            self.assertIn("内部一次性下载记录", results_md.read_text(encoding="utf-8"))

            confirmed = confirm_shots(run_dir, now=datetime(2026, 6, 25, 15, 50, 0))
            self.assertEqual(confirmed.status, "shots_confirmed")
            self.assertEqual(confirmed.phase, "ready_for_video_assembly")
            shot_preview_manifest = run_dir / "dreamina_generation" / "shot_preview_manifest.json"
            self.assertTrue(shot_preview_manifest.exists())
            shot_preview = json.loads(shot_preview_manifest.read_text(encoding="utf-8"))
            self.assertTrue(shot_preview["policy"]["video_only"])
            self.assertNotIn("contains_confirmed_narration", shot_preview)
            self.assertNotIn("contains_temporary_subtitles", shot_preview)
            self.assertNotIn("contains_final_bgm", shot_preview)
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["shots"])
            self.assertFalse(state["confirmations"]["video_assembly"])
            self.assertEqual(state["current_pending_confirmation"], "合并视频")

    def test_assembling_confirmed_shots_blocks_when_videos_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_results_ready_run(Path(tmp))
            confirm_shots(run_dir, now=datetime(2026, 6, 25, 15, 50, 0))

            result = assemble_confirmed_video(run_dir, runner=_ffmpeg_completed, now=datetime(2026, 6, 25, 15, 55, 0))

            self.assertEqual(result.status, "video_assembly_blocked")
            self.assertEqual(result.phase, "awaiting_video_assembly")
            manifest = json.loads((run_dir / "dreamina_generation" / "assembly_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "blocked")
            self.assertTrue(any("视频文件不存在" in blocker for blocker in manifest["blockers"]))
            self.assertTrue((run_dir / "storyboard.srt").exists())
            self.assertFalse((run_dir / "dreamina_generation" / "editing_subtitles.md").exists())
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertFalse(state["confirmations"]["video_assembly"])
            self.assertEqual(state["current_pending_confirmation"], "合并视频")

    def test_assembles_confirmed_shots_and_preserves_confirmed_srt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_results_ready_run(Path(tmp))
            _write_dreamina_result_videos(run_dir)
            confirm_shots(run_dir, now=datetime(2026, 6, 25, 15, 50, 0))

            result = assemble_confirmed_video(run_dir, runner=_ffmpeg_completed, now=datetime(2026, 6, 25, 15, 55, 0))

            self.assertEqual(result.status, "video_assembled")
            self.assertEqual(result.phase, "completed")
            stitched = run_dir / "dreamina_generation" / "stitched_video.mp4"
            subtitles = run_dir / "storyboard.srt"
            self.assertTrue(stitched.exists())
            self.assertTrue(subtitles.exists())
            subtitle_text = subtitles.read_text(encoding="utf-8")
            self.assertIn("00:00:00,000 -->", subtitle_text)
            self.assertIn(str(subtitles), result.message)
            self.assertFalse((run_dir / "dreamina_generation" / "voiceover_script.md").exists())
            self.assertFalse((run_dir / "dreamina_generation" / "editing_notes.md").exists())
            manifest = json.loads((run_dir / "dreamina_generation" / "assembly_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "succeeded")
            self.assertTrue(manifest["policy"]["no_subtitles_burned"])
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["video_assembly"])
            self.assertEqual(state["files"]["assembled_video_mp4"], str(stitched))
            self.assertEqual(state["files"]["storyboard_srt"], str(subtitles))
            self.assertNotIn("voiceover_script_md", state["files"])
            self.assertNotIn("editing_notes_md", state["files"])

    def test_queries_manual_dreamina_submission_file_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_submitted_run(Path(tmp))
            submission = json.loads((run_dir / "dreamina_generation" / "dreamina_submission.json").read_text(encoding="utf-8"))
            manual = deepcopy(submission)
            manual["mode"] = "manual_execute"
            for item in manual["submissions"]:
                item["status"] = "submitted"
                item["provider_task_id"] = f"real_submit_{item['shot_id']}"
            (run_dir / "dreamina_generation" / "manual_submission.json").write_text(
                json.dumps(manual, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            calls = []

            def fake_query_runner(command, capture_output, text, check):
                calls.append(command)
                submit_id = next(part.split("=", 1)[1] for part in command if part.startswith("--submit_id="))
                payload = {
                    "submit_id": submit_id,
                    "gen_status": "success",
                    "result_json": {
                        "videos": [
                            {
                                "path": str(run_dir / "dreamina_generation" / "generated_shots" / f"{submit_id}.mp4")
                            }
                        ]
                    },
                }
                return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

            result = query_dreamina_results(run_dir, now=datetime(2026, 6, 25, 15, 45, 0), runner=fake_query_runner)

            self.assertEqual(result.status, "dreamina_results_ready")
            self.assertTrue(all("query_result" in call for call in calls))
            self.assertTrue(all(any(part.startswith("--download_dir=") for part in call) for call in calls))
            results = json.loads((run_dir / "dreamina_generation" / "dreamina_results.json").read_text(encoding="utf-8"))
            self.assertEqual(results["mode"], "execute")
            self.assertTrue(all(item["provider_task_id"].startswith("real_submit_") for item in results["results"]))

    def test_operator_completion_triggers_one_shot_download_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_submitted_run(Path(tmp))
            submission = json.loads((run_dir / "dreamina_generation" / "dreamina_submission.json").read_text(encoding="utf-8"))
            manual = deepcopy(submission)
            manual["mode"] = "manual_execute"
            for item in manual["submissions"]:
                item["status"] = "submitted"
                item["provider_task_id"] = f"real_submit_{item['shot_id']}"
            (run_dir / "dreamina_generation" / "manual_submission.json").write_text(
                json.dumps(manual, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            def fake_query_runner(command, capture_output, text, check):
                submit_id = next(part.split("=", 1)[1] for part in command if part.startswith("--submit_id="))
                output = run_dir / "dreamina_generation" / "generated_shots" / f"{submit_id}.mp4"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"generated-video")
                payload = {
                    "submit_id": submit_id,
                    "gen_status": "success",
                    "result_json": {"videos": [{"path": str(output)}]},
                }
                return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

            result = download_dreamina_results_once(
                run_dir,
                "即梦已全部生成",
                runner=fake_query_runner,
                media_probe=lambda path: (True, ""),
                now=datetime(2026, 6, 25, 15, 45, 0),
            )

            self.assertEqual(result.status, "dreamina_results_downloaded_and_validated")
            self.assertEqual(result.phase, "ready_for_video_assembly")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["one_shot_download"]["attempted"])
            self.assertEqual(state["one_shot_download"]["blockers"], [])
            self.assertTrue(state["confirmations"]["shots"])
            with self.assertRaisesRegex(ValueError, "不能执行一次性下载|已经执行过一次性下载"):
                download_dreamina_results_once(run_dir, "即梦已全部生成", runner=fake_query_runner)

    def test_one_shot_download_rejects_dry_run_submission_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_submitted_run(Path(tmp))

            with self.assertRaisesRegex(ValueError, "dry-run 即梦提交记录"):
                download_dreamina_results_once(run_dir, "即梦已全部生成")

    def test_direct_single_shot_retry_is_out_of_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_results_ready_run(Path(tmp))

            with self.assertRaisesRegex(ValueError, "单镜头重做本期暂未实现"):
                plan_shot_retry(run_dir, "3", reason="产品边缘不够清楚")

    def test_natural_language_shot_improvement_is_out_of_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_results_ready_run(Path(tmp))

            result = handle_video_creation_reply(
                run_dir,
                "重做镜头 03，产品边缘不够清楚",
                now=datetime(2026, 6, 25, 15, 55, 0),
            )

            self.assertEqual(result.status, "video_results_not_accepted")
            self.assertEqual(result.phase, "stopped")
            self.assertTrue((run_dir / "dreamina_generation" / "result_acceptance.json").exists())
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["current_pending_confirmation"], "新建视频任务")

    def test_retry_submission_and_query_entrypoints_are_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_results_ready_run(Path(tmp))
            for call in (
                lambda: confirm_shot_retry(run_dir, "03"),
                lambda: submit_shot_retry(run_dir, expected_shot_id="03"),
                lambda: query_shot_retry_results(run_dir, expected_shot_id="03"),
            ):
                with self.assertRaisesRegex(ValueError, "单镜头重做本期暂未实现"):
                    call()

    def test_natural_language_shot_retry_submission_is_not_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_results_ready_run(Path(tmp))
            result = handle_video_creation_reply(run_dir, "提交重做镜头 03", now=datetime(2026, 6, 25, 15, 57, 0))
            self.assertEqual(result.status, "video_results_not_accepted")
            self.assertEqual(result.phase, "stopped")

    def test_rejects_mismatched_shot_retry_submission_reply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_results_ready_run(Path(tmp))
            result = handle_video_creation_reply(run_dir, "提交重做镜头 04", now=datetime(2026, 6, 25, 15, 57, 0))
            self.assertEqual(result.status, "video_results_not_accepted")
            self.assertEqual(result.phase, "stopped")

    def test_revising_video_plan_clears_downstream_confirmations_and_file_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_results_ready_run(Path(tmp))

            requested = revise_video_plan(
                run_dir,
                "修改策划，开场更突出高温设备密封痛点。",
                now=datetime(2026, 6, 25, 16, 20, 0),
            )
            self.assertEqual(requested.status, "semantic_plan_revision_required")
            result = apply_video_plan_semantic_revision(
                run_dir,
                {"story_outline": {"opening": "开场先呈现高温设备密封痛点，再引出产品。"}},
                "修改策划，开场更突出高温设备密封痛点。",
                now=datetime(2026, 6, 25, 16, 20, 30),
            )

            self.assertEqual(result.status, "video_plan_revised")
            self.assertEqual(result.phase, "awaiting_video_plan_confirmation")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertFalse(state["confirmations"]["video_plan"])
            self.assertFalse(state["confirmations"]["storyboard"])
            self.assertNotIn("narration_script", state["confirmations"])
            self.assertNotIn("voice", state["confirmations"])
            self.assertNotIn("narration", state["confirmations"])
            self.assertNotIn("final_video", state["confirmations"])
            self.assertFalse(state["confirmations"]["dreamina_generation"])
            self.assertFalse(state["confirmations"]["shots"])
            self.assertEqual(state["current_pending_confirmation"], "确认策划")
            self.assertNotIn("storyboard_json", state["files"])
            self.assertNotIn("dreamina_results_json", state["files"])
            self.assertNotIn("shot_preview_mp4", state["files"])
            plan = json.loads((run_dir / "video_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["change_requests"][0]["scope"], "video_plan")
            self.assertIn("高温设备密封痛点", (run_dir / "video_plan.md").read_text(encoding="utf-8"))
            self.assertIn("Codex 已应用策划语义修改", (run_dir / "change_log.md").read_text(encoding="utf-8"))

    def test_revising_storyboard_clears_generation_confirmations_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_results_ready_run(Path(tmp))

            requested = revise_storyboard(
                run_dir,
                "修改分镜，减少泛泛介绍，增加采购判断信息。",
                now=datetime(2026, 6, 25, 16, 21, 0),
            )
            self.assertEqual(requested.status, "semantic_storyboard_revision_required")
            result = apply_storyboard_semantic_revision(
                run_dir,
                [{"shot_id": "01", "changes": {"message": "增加采购判断信息，减少泛泛介绍。"}}],
                "修改分镜，减少泛泛介绍，增加采购判断信息。",
                now=datetime(2026, 6, 25, 16, 21, 30),
            )

            self.assertEqual(result.status, "storyboard_revised")
            self.assertEqual(result.phase, "awaiting_storyboard_confirmation")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["video_plan"])
            self.assertFalse(state["confirmations"]["storyboard"])
            self.assertFalse(state["confirmations"]["dreamina_generation"])
            self.assertFalse(state["confirmations"]["shots"])
            self.assertEqual(state["current_pending_confirmation"], "确认当前分镜与 SRT")
            self.assertIn("storyboard_json", state["files"])
            self.assertNotIn("dreamina_jobs_json", state["files"])
            storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
            shot_01 = next(item for item in storyboard["shots"] if item["shot_id"] == "01")
            self.assertEqual(shot_01["change_requests"][0]["scope"], "shot_01")
            self.assertIn("采购判断信息", (run_dir / "storyboard.md").read_text(encoding="utf-8"))

    def test_revising_single_shot_marks_only_that_shot_and_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_results_ready_run(Path(tmp))

            requested = revise_storyboard_shot(
                run_dir,
                "03",
                "修改镜头03，突出编织纹理和边缘厚度。",
                now=datetime(2026, 6, 25, 16, 22, 0),
            )
            self.assertEqual(requested.status, "semantic_storyboard_revision_required")
            result = apply_storyboard_semantic_revision(
                run_dir,
                [{"shot_id": "03", "changes": {"visual_description": "Macro view emphasizing woven texture and edge thickness."}}],
                "修改镜头03，突出编织纹理和边缘厚度。",
                now=datetime(2026, 6, 25, 16, 22, 30),
            )

            self.assertEqual(result.status, "storyboard_revised")
            storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
            shot_03 = next(item for item in storyboard["shots"] if item["shot_id"] == "03")
            shot_04 = next(item for item in storyboard["shots"] if item["shot_id"] == "04")
            self.assertEqual(shot_03["change_requests"][0]["scope"], "shot_03")
            self.assertIn("woven texture", shot_03["visual_description"])
            self.assertNotIn("change_requests", shot_04)
            self.assertFalse((run_dir / "prompts.json").exists())
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertFalse(state["confirmations"]["storyboard"])
            self.assertEqual(state["current_pending_confirmation"], "确认当前分镜与 SRT")

    def test_handles_revision_replies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_results_ready_run(Path(tmp))

            requested = handle_video_creation_reply(run_dir, "修改镜头03，突出编织纹理", now=datetime(2026, 6, 25, 16, 23, 0))
            self.assertEqual(requested.status, "semantic_storyboard_revision_required")
            result = apply_storyboard_semantic_revision(
                run_dir,
                [{"shot_id": "03", "changes": {"visual_description": "Macro view of the woven texture."}}],
                "修改镜头03，突出编织纹理",
                now=datetime(2026, 6, 25, 16, 23, 30),
            )

            self.assertEqual(result.status, "storyboard_revised")
            self.assertEqual(result.phase, "awaiting_storyboard_confirmation")
            storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
            shot_03 = next(item for item in storyboard["shots"] if item["shot_id"] == "03")
            self.assertIn("编织纹理", shot_03["change_requests"][0]["request"])

    def test_mock_full_chain_from_natural_language_replies_to_confirmed_dreamina_shots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))

            handle_video_creation_reply(run_dir, "生成策划", now=datetime(2026, 6, 25, 15, 0, 0))
            handle_video_creation_reply(run_dir, "确认", now=datetime(2026, 6, 25, 15, 1, 0))
            handle_video_creation_reply(run_dir, "确认", now=datetime(2026, 6, 25, 15, 3, 0))
            handle_video_creation_reply(run_dir, "确认即梦生成", now=datetime(2026, 6, 25, 15, 11, 0))
            submitted = handle_video_creation_reply(run_dir, "提交即梦任务", now=datetime(2026, 6, 25, 15, 12, 0))
            self.assertIn("powershell.exe -ExecutionPolicy Bypass -File", submitted.message)
            with self.assertRaisesRegex(ValueError, "不暴露即梦状态查询"):
                handle_video_creation_reply(run_dir, "查询即梦结果", now=datetime(2026, 6, 25, 15, 13, 0))

            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["workflow_mode"], "video_only")
            self.assertFalse(state["confirmations"]["shots"])
            self.assertEqual(state["phase"], "awaiting_dreamina_results")
            self.assertFalse((run_dir / "subtitles").exists())
            self.assertFalse((run_dir / "audio").exists())

    def test_inspects_video_creation_adapters_without_paid_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))

            result = inspect_video_creation_adapters(run_dir, now=datetime(2026, 6, 25, 16, 20, 0))

            self.assertEqual(result.status, "video_brief_confirmed")
            report_json = run_dir / "adapter_inspection.json"
            report_md = run_dir / "adapter_inspection.md"
            self.assertTrue(report_json.exists())
            self.assertTrue(report_md.exists())
            report = json.loads(report_json.read_text(encoding="utf-8"))
            self.assertEqual(report["schema_version"], "video-adapter-inspection-v1")
            self.assertIn(report["status"], {"passed", "passed_with_warnings", "failed"})
            self.assertTrue(any(item["name"] == "dreamina_command" for item in report["checks"]))
            self.assertIn("不提交即梦任务", report_md.read_text(encoding="utf-8"))

    def test_rejects_unsupported_language_platform_duration_and_direction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)

            base = {
                "paths": paths,
                "request_text": "做一个60秒石英纤维隔热带产品介绍视频",
                "language_version": "en",
                "platforms": ["youtube_shorts"],
                "duration_seconds": 60,
            }
            with self.assertRaisesRegex(ValueError, "视频语言版本只支持"):
                create_video_creation_run(**{**base, "language_version": "fr"})
            with self.assertRaisesRegex(ValueError, "视频平台只支持"):
                create_video_creation_run(**{**base, "platforms": ["linkedin"]})
            with self.assertRaisesRegex(ValueError, "请求中包含 TikTok"):
                create_video_creation_run(**{**base, "request_text": "做一个用于 YouTube Shorts 和 TikTok 的产品视频"})
            with self.assertRaisesRegex(ValueError, "包含其他产品"):
                create_video_creation_run(**{**base, "request_text": "做一个玄武岩纤维隔热带 YouTube Shorts"})
            with self.assertRaisesRegex(ValueError, "视频时长只支持"):
                create_video_creation_run(**{**base, "duration_seconds": 10})
            result = create_video_creation_run(**base)
            requirements = Path(result.requirements_path).read_text(encoding="utf-8")
            self.assertNotIn("固定视频创意方向", requirements)
            self.assertNotIn("主创意方向", requirements)


def _write_official_cards(paths, human_face_risk: str = "none") -> None:
    _write_card(
        paths.knowledge_dir / "产品" / "石英纤维隔热带.md",
        [
            "card_template_version: product-card-v1",
            "type: product",
            "id: product/quartz_fiber_tape",
            "title: 石英纤维隔热带",
            "aliases:",
            "  - 特种玻璃纤维带",
            "  - Specialty Glass Fiber Tape",
            "status: official",
            "usage_scope: external_allowed",
            "raw_partitions:",
            "  - raw/01_产品/02_石英纤维隔热带/",
            "tags:",
            "  - 产品",
            "updated_at: 2026-06-25T00:00:00+08:00",
            "last_reviewed_at: 2026-06-25T00:00:00+08:00",
            "evidence_refs:",
            "  - evidence/quartz_fiber_tape/key_parameters",
            "review_refs: []",
            "product_line: 耐高温隔热带",
            "related_refs: []",
        ],
        "石英纤维隔热带是首期视频创作产品。",
    )
    _write_card(
        paths.knowledge_dir / "证据" / "quartz_fiber_tape" / "key_parameters.md",
        [
            "card_template_version: evidence-card-v1",
            "type: evidence",
            "id: evidence/quartz_fiber_tape/key_parameters",
            "title: 石英纤维隔热带关键参数",
            "aliases: []",
            "status: official",
            "usage_scope: evidence_only",
            "raw_partitions: []",
            "tags:",
            "  - 关键参数",
            "  - 石英纤维隔热带",
            "updated_at: 2026-06-25T00:00:00+08:00",
            "last_reviewed_at: 2026-06-25T00:00:00+08:00",
            "evidence_refs: []",
            "review_refs: []",
            "evidence_type: 知识卡整理",
            "source_paths:",
            "  - knowledge/okf/证据/quartz_fiber_tape/key_parameters.md",
            "proves:",
            "  - 耐高温1000度",
            "  - 不刺痒",
            "  - 不冒烟",
            "confidence: high",
            "related_products:",
            "  - product/quartz_fiber_tape",
        ],
        "正式知识摘要：该产品可围绕耐高温1000度、不刺痒、不冒烟进行谨慎表达。",
    )
    image_assets = [
        ("quartz_product_photo", "石英纤维隔热带产品图片", "产品图片", "产品图片", "product.jpg"),
        ("quartz_product_roll_02", "石英纤维隔热带卷装图片 02", "产品图片", "产品图片", "product-02.jpg"),
        ("quartz_product_roll_03", "石英纤维隔热带卷装图片 03", "产品图片", "产品图片", "product-03.jpg"),
        ("quartz_texture_detail_01", "石英纤维隔热带织纹细节图片 01", "产品细节图片", "产品细节", "texture-01.jpg"),
        ("quartz_texture_detail_02", "石英纤维隔热带边缘厚度细节图片 02", "产品细节图片", "产品细节", "texture-02.jpg"),
        ("quartz_texture_detail_03", "石英纤维隔热带柔性细节图片 03", "产品细节图片", "产品细节", "texture-03.jpg"),
        ("quartz_application_pipe_01", "石英纤维隔热带排气管包覆图片 01", "应用场景图片", "应用场景", "application-01.jpg"),
        ("quartz_application_pipe_02", "石英纤维隔热带排烟管包覆图片 02", "应用场景图片", "应用场景", "application-02.jpg"),
        ("quartz_application_pipe_03", "石英纤维隔热带安装应用图片 03", "应用场景图片", "应用场景", "application-03.jpg"),
        ("quartz_test_context_01", "石英纤维隔热带测试辅助图片 01", "测试验证图片", "测试验证", "test-01.jpg"),
        ("quartz_test_context_02", "石英纤维隔热带高温场景辅助图片 02", "测试验证图片", "测试验证", "test-02.jpg"),
        ("quartz_closing_product_01", "石英纤维隔热带收尾产品图片 01", "产品图片", "产品图片", "closing-01.jpg"),
    ]
    for asset_id, title, asset_category, tag, file_name in image_assets:
        _write_card(
            paths.knowledge_dir / "内容素材" / f"{asset_id}.md",
            [
                "card_template_version: content-asset-card-v1",
                "type: content_asset",
                f"id: content_asset/{asset_id}",
                f"title: {title}",
                "aliases: []",
                "status: official",
                "usage_scope: external_allowed",
                "raw_partitions:",
                "  - raw/01_产品/02_石英纤维隔热带/02_产品图片/",
                "tags:",
                f"  - {tag}",
                "updated_at: 2026-06-25T00:00:00+08:00",
                "last_reviewed_at: 2026-06-25T00:00:00+08:00",
                "evidence_refs: []",
                "review_refs: []",
                f"asset_category: {asset_category}",
                "media_types:",
                "  - image",
                f"human_face_risk: {human_face_risk}",
                "related_products:",
                "  - product/quartz_fiber_tape",
                "files:",
                f"  - raw/01_产品/02_石英纤维隔热带/02_产品图片/{file_name}",
                "usable_for:",
                "  - video_creation",
            ],
            "可用于视频创作的图片素材；不能单独证明产品性能事实。",
        )
    _write_card(
        paths.knowledge_dir / "内容素材" / "quartz_product_video.md",
        [
            "card_template_version: content-asset-card-v1",
            "type: content_asset",
            "id: content_asset/quartz_product_video",
            "title: 石英纤维隔热带产品视频",
            "aliases: []",
            "status: official",
            "usage_scope: external_allowed",
            "raw_partitions:",
            "  - raw/01_产品/02_石英纤维隔热带/03_产品视频/",
            "tags:",
            "  - 产品视频",
            "updated_at: 2026-06-25T00:00:00+08:00",
            "last_reviewed_at: 2026-06-25T00:00:00+08:00",
            "evidence_refs: []",
            "review_refs: []",
            "asset_category: 产品视频",
            "media_types:",
            "  - video",
            f"human_face_risk: {human_face_risk}",
            "related_products:",
            "  - product/quartz_fiber_tape",
            "files:",
            "  - raw/01_产品/02_石英纤维隔热带/03_产品视频/product.mp4",
            "usable_for:",
            "  - video_creation",
        ],
        "这是产品实拍视频素材；视频创作 Agent 不应把视频文件用于策划素材或即梦任务。",
    )


def _write_product_matrix_card(paths) -> None:
    _write_card(
        paths.knowledge_dir / "产品" / "00排气管隔热带产品矩阵.md",
        [
            "card_template_version: product-card-v1",
            "type: product",
            "id: product/exhaust_wrap_matrix",
            "title: 排气管隔热带产品矩阵",
            "aliases:",
            "  - Exhaust Wrap",
            "status: official",
            "usage_scope: external_allowed",
            "raw_partitions: []",
            "tags:",
            "  - 石英纤维隔热带",
            "  - 产品矩阵",
            "updated_at: 2026-06-25T00:00:00+08:00",
            "last_reviewed_at: 2026-06-25T00:00:00+08:00",
            "evidence_refs: []",
            "review_refs: []",
            "product_line: 耐高温隔热带",
            "related_refs:",
            "  - product/quartz_fiber_tape",
            "related_products:",
            "  - product/quartz_fiber_tape",
        ],
        "## 产品矩阵\n\n| 产品 | 市场名称 |\n| --- | --- |\n| 玄武岩纤维隔热带 | 玄武岩隔热带 |\n| 陶瓷纤维隔热带 | 陶瓷隔热带 |\n| 石英纤维隔热带 | Exhaust Wrap |\n",
    )


def _write_legacy_quartz_video_cards(paths) -> None:
    _write_card(
        paths.knowledge_dir / "产品" / "石英纤维隔热带.md",
        [
            "card_template_version: product-card-v1",
            "type: product",
            "id: product/quartz_fiber_exhaust_wrap",
            "title: 石英纤维隔热带",
            "aliases:",
            "  - product/quartz_fiber_tape",
            "  - 特种玻璃纤维带",
            "  - Quartz Fiber Exhaust Wrap",
            "status: official",
            "usage_scope: review_before_external",
            "raw_partitions:",
            "  - raw/04_产品/01_石英纤维隔热带/",
            "tags:",
            "  - 产品",
            "updated_at: 2026-06-25T00:00:00+08:00",
            "last_reviewed_at: 2026-06-25T00:00:00+08:00",
            "evidence_refs: []",
            "review_refs: []",
            "product_line: 耐高温隔热带",
            "related_refs: []",
        ],
        "石英纤维隔热带是首期视频创作产品；外发前需要复核高风险 claim。",
    )
    _write_card(
        paths.knowledge_dir / "内容素材" / "quartz_legacy_product_photo.md",
        [
            "card_template_version: content-asset-card-v1",
            "type: content_asset",
            "id: content_asset/quartz_legacy_product_photo",
            "title: 石英纤维隔热带精选图片",
            "aliases: []",
            "status: official",
            "usage_scope: external_allowed",
            "raw_partitions:",
            "  - raw/04_产品/01_石英纤维隔热带/精选图片/",
            "tags:",
            "  - 产品图片",
            "updated_at: 2026-06-25T00:00:00+08:00",
            "last_reviewed_at: 2026-06-25T00:00:00+08:00",
            "evidence_refs: []",
            "review_refs: []",
            "asset_category: 产品图片",
            "media_types:",
            "  - image",
            "human_face_risk: none",
            "related_products:",
            "  - product/quartz_fiber_exhaust_wrap",
            "usable_for:",
            "  - video_creation",
        ],
        "可用于视频创作的石英纤维隔热带产品素材。",
    )


def _write_card(path: Path, frontmatter_lines: list[str], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + "\n".join(frontmatter_lines) + "\n---\n\n" + body + "\n", encoding="utf-8")


def _write_raw_image_files(root: Path) -> None:
    image_dir = root / "raw" / "01_产品" / "02_石英纤维隔热带" / "02_产品图片"
    image_dir.mkdir(parents=True, exist_ok=True)
    for file_name in [
        "product.jpg",
        "product-02.jpg",
        "product-03.jpg",
        "texture-01.jpg",
        "texture-02.jpg",
        "texture-03.jpg",
        "application-01.jpg",
        "application-02.jpg",
        "application-03.jpg",
        "test-01.jpg",
        "test-02.jpg",
        "closing-01.jpg",
    ]:
        (image_dir / file_name).write_bytes(f"fake image {file_name}".encode("utf-8"))


def _mark_interview_materials_usable(run_dir: Path, usable_limit: int) -> None:
    state_path = run_dir / "workflow_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    evidence = state["interview"]["decision_evidence"]["material_visual_direction"]
    for index, item in enumerate(evidence, start=1):
        item["usable"] = index <= usable_limit
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _create_ready_run(
    root: Path,
    request_text: str = "做一个60秒石英纤维隔热带产品介绍视频，面向欧美工业采购商，用在 YouTube Shorts。",
) -> Path:
    paths = resolve_paths(root, {})
    initialize_project(paths)
    _write_official_cards(paths)
    _write_raw_image_files(root)
    rebuild_agent_interface(paths)
    result = create_video_creation_run(
        paths,
        request_text,
        language_version="en",
        platforms=["youtube_shorts"],
        duration_seconds=60,
        target_audience="欧美工业采购商",
        core_objective="突出耐高温、隔热、不刺痒和不冒烟",
        now=datetime(2026, 6, 25, 14, 30, 5),
    )
    run_dir = Path(result.run_dir)
    _complete_video_interview(run_dir)
    return run_dir


def _complete_video_interview(run_dir: Path) -> None:
    fixture_proposals = {
        "audience": (
            "这条视频首先需要影响哪类具体决策者？",
            "负责高温设备隔热材料选型的欧美工程与采购人员。",
            "具体选型职责会决定问题场景、证据顺序和行动设计。",
        ),
        "audience_problem_scenario": (
            "他们会在什么具体决策场景下需要这条视频？",
            "在评估高温部位包覆材料时，先判断产品是否值得进一步核对规格和样品。",
            "真实选型判断比泛泛产品展示更能形成观看理由。",
        ),
        "viewing_motivation": (
            "观众为什么会开始并继续观看？",
            "先呈现熟悉的高温包覆难题，再用真实纹理和应用细节逐步回答。",
            "问题获得注意，连续可见证据维持可信度和停留。",
        ),
        "trend_mechanism": (
            "当前 YouTube 信号中哪个机制适合本产品？",
            "采用真实问题开场、细节证据推进、应用判断收束的机制。",
            "该机制可迁移到工业选型，同时避免照搬娱乐化形式。",
        ),
        "viewer_interest_direction": (
            "综合受众、趋势和素材，最终兴趣方向是什么？",
            "让观众从一个真实高温包覆判断出发，看懂产品纹理和应用细节为何值得继续核对。",
            "该方向同时受正式知识、公开趋势机制和现有图片支持。",
        ),
        "intended_takeaway": (
            "观众最终只需要记住什么？",
            "这是一款值得结合具体工况进一步核对规格的高温包覆材料。",
            "单一可信认知比罗列大量参数更容易留下采购记忆。",
        ),
        "desired_action": (
            "看完后希望观众采取什么行动？",
            "带着应用温度、尺寸和包覆条件联系拓霖，索取规格、样品或报价。",
            "这符合工业采购下一步，也让视频有明确业务承接。",
        ),
        "priority_messages": (
            "哪些正式信息必须优先表达？",
            "优先表达知识卡确认的耐温、隔热、施工体验与真实产品细节。",
            "这些信息与当前任务目标直接相关，并能由正式知识和素材支撑。",
        ),
        "human_relevance_angle": (
            "什么人物动作能增强真实代入？",
            "展示工程或维护人员检查部位、比较材料并准备包覆的局部动作。",
            "具体工作动作能增加人的关联，又不虚构客户身份。",
        ),
        "excluded_content": (
            "哪些内容必须排除？",
            "排除未经确认的参数、认证、绝对化承诺、竞品攻击和虚构客户现场。",
            "这些内容会造成事实越界或对外传播风险。",
        ),
        "ai_simulation_scope": (
            "允许 AI 模拟到什么边界？",
            "只模拟知识卡已确认的通用应用说明场景，产品可见画面必须绑定真实产品图。",
            "这样可补足画面，同时不把模拟包装成真实案例或测试。",
        ),
    }
    for offset in range(40):
        state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
        if state.get("phase") == "ready_for_video_plan":
            return
        interview = state.get("interview") or {}
        pending = interview.get("pending_decision") or {}
        if pending:
            continue_video_creation_interview(run_dir, "确认", now=datetime(2026, 6, 25, 14, 35, min(offset, 59)))
            continue
        required = set(interview.get("internal_evidence_required") or [])
        if "trend_evidence" in required:
            record_video_interview_evidence(
                run_dir,
                "trend_evidence",
                "工业短视频中，真实问题开场、细节证据推进和应用判断收束更适合当前受众。",
                [{
                    "source_url": "https://www.youtube.com/shorts/test-evidence",
                    "scanned_at": "2026-06-25",
                    "observed_signal": "真实问题开场后用产品细节推进",
                    "why_it_worked": "目标受众能快速识别自己的选型问题并获得连续证据",
                    "mechanism": "problem-proof-decision",
                    "transfer_to_product": "把高温包覆判断转译为纹理和应用细节的连续展示",
                    "relevance_level": "comparable_industrial",
                    "target_language": "en",
                    "target_region": "North America and Europe",
                    "excluded_methods": ["无关娱乐梗", "夸张破坏性测试"],
                }],
                "public_youtube_scan",
            )
            continue
        if "material_visual_direction" in required:
            context_path = Path(state["files"]["context"])
            context = json.loads(context_path.read_text(encoding="utf-8"))
            material_evidence = []
            for rank, card in enumerate(context.get("cards_by_type", {}).get("content_asset", []), start=1):
                frontmatter = card.get("frontmatter") or {}
                media_types = {str(item).lower() for item in frontmatter.get("media_types", [])}
                files = [str(item) for item in frontmatter.get("files", [])]
                if "image" not in media_types and not any(Path(item).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} for item in files):
                    continue
                material_evidence.append({
                    "material_id": card["id"],
                    "subject": "产品、细节或应用主体",
                    "clarity": "清晰",
                    "composition": "主体构图可用于竖屏",
                    "vertical_crop": "可裁切 9:16",
                    "near_duplicate_of": "",
                    "usable": True,
                    "notes": "测试夹具模拟 Codex 已实际打开图片",
                    "rank": rank,
                })
            record_video_interview_evidence(
                run_dir,
                "material_visual_direction",
                "官方图片支持产品卷装、织纹细节和包覆应用的竖屏叙事。",
                material_evidence,
                "codex_pixel_inspection",
            )
            continue
        remaining = list(interview.get("remaining_fields") or [])
        for decision_key in (
            "audience",
            "audience_problem_scenario",
            "viewing_motivation",
            "trend_mechanism",
            "viewer_interest_direction",
            "intended_takeaway",
            "desired_action",
            "priority_messages",
            "human_relevance_angle",
            "excluded_content",
            "ai_simulation_scope",
        ):
            if decision_key not in remaining:
                continue
            question, recommendation, reason = fixture_proposals[decision_key]
            proposal_evidence = [{"source": "test_fixture", "summary": "受控业务夹具"}]
            if decision_key in {"intended_takeaway", "priority_messages"}:
                context = json.loads(Path(state["files"]["context"]).read_text(encoding="utf-8"))
                formal_product = context["cards_by_type"]["product"][0]
                proposal_evidence = [{
                    "source": "formal_product_card",
                    "card_id": formal_product["id"],
                    "summary": "受控夹具中的正式产品知识",
                }]
            try:
                propose_video_interview_decision(
                    run_dir,
                    {
                        "decision_key": decision_key,
                        "question": question,
                        "recommendation": recommendation,
                        "reason": reason,
                        "evidence": proposal_evidence,
                        "proposal_source": "test_codex_reasoning",
                    },
                    now=datetime(2026, 6, 25, 14, 35, min(offset, 59)),
                )
            except ValueError as exc:
                if "依赖尚未解决" in str(exc):
                    continue
                raise
            break
        else:
            raise AssertionError(f"没有可提出的测试决策：{interview}")
        continue
        raise AssertionError(f"访谈无法继续：{interview}")
    raise AssertionError("视频创作访谈未在预期轮次内完成")


def _create_video_only_ready_run(root: Path) -> Path:
    return _create_ready_run(
        root,
        request_text="做一个60秒石英纤维隔热带产品介绍视频，不加配音和字幕，只用即梦cli生成视频。",
    )


def _create_plan_confirmed_run(root: Path) -> Path:
    run_dir = _create_ready_run(root)
    generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))
    confirm_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 5, 0))
    return run_dir


def _create_storyboard_confirmed_run(root: Path) -> Path:
    run_dir = _create_plan_confirmed_run(root)
    generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))
    confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))
    return run_dir


def _create_dreamina_jobs_ready_run(root: Path) -> Path:
    run_dir = _create_storyboard_confirmed_run(root)
    generate_dreamina_jobs(run_dir, now=datetime(2026, 6, 25, 15, 30, 0))
    return run_dir


def _create_dreamina_generation_confirmed_run(root: Path) -> Path:
    run_dir = _create_dreamina_jobs_ready_run(root)
    confirm_dreamina_generation(run_dir, now=datetime(2026, 6, 25, 15, 35, 0))
    return run_dir


def _create_dreamina_submitted_run(root: Path) -> Path:
    run_dir = _create_dreamina_generation_confirmed_run(root)
    submit_dreamina_jobs(run_dir, now=datetime(2026, 6, 25, 15, 40, 0))
    return run_dir


def _create_dreamina_results_ready_run(root: Path) -> Path:
    run_dir = _create_dreamina_submitted_run(root)
    query_dreamina_results(run_dir, now=datetime(2026, 6, 25, 15, 45, 0))
    return run_dir


def _create_shots_confirmed_run(root: Path) -> Path:
    run_dir = _create_dreamina_results_ready_run(root)
    confirm_shots(run_dir, now=datetime(2026, 6, 25, 15, 50, 0))
    return run_dir


def _create_storyboard_confirmed_run_without_assets(root: Path) -> Path:
    paths = resolve_paths(root, {})
    initialize_project(paths)
    _write_product_card_only(paths)
    rebuild_agent_interface(paths)
    result = create_video_creation_run(
        paths,
        "做一个60秒石英纤维隔热带产品介绍视频，面向欧美工业采购商，用在 YouTube Shorts。",
        language_version="en",
        platforms=["youtube_shorts"],
        duration_seconds=60,
        target_audience="欧美工业采购商",
        core_objective="突出耐高温、隔热、不刺痒和不冒烟",
        now=datetime(2026, 6, 25, 14, 30, 5),
    )
    run_dir = Path(result.run_dir)
    _complete_video_interview(run_dir)
    generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))
    approve_plan_material_repetition(run_dir, "测试明确批准素材不足时重复", now=datetime(2026, 6, 25, 15, 3, 0))
    confirm_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 5, 0))
    generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))
    confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))
    return run_dir


def _write_product_card_only(paths) -> None:
    _write_card(
        paths.knowledge_dir / "产品" / "石英纤维隔热带.md",
        [
            "card_template_version: product-card-v1",
            "type: product",
            "id: product/quartz_fiber_tape",
            "title: 石英纤维隔热带",
            "aliases:",
            "  - 特种玻璃纤维带",
            "  - Specialty Glass Fiber Tape",
            "status: official",
            "usage_scope: external_allowed",
            "raw_partitions:",
            "  - raw/01_产品/02_石英纤维隔热带/",
            "tags:",
            "  - 产品",
            "updated_at: 2026-06-25T00:00:00+08:00",
            "last_reviewed_at: 2026-06-25T00:00:00+08:00",
            "evidence_refs: []",
            "review_refs: []",
            "product_line: 耐高温隔热带",
            "related_refs: []",
        ],
        "石英纤维隔热带是首期视频创作产品。",
    )


def _write_test_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * 800)


def _write_dreamina_result_videos(run_dir: Path) -> None:
    results_json = run_dir / "dreamina_generation" / "dreamina_results.json"
    results = json.loads(results_json.read_text(encoding="utf-8"))
    for item in results["results"]:
        output_path = Path(item["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(f"fake video {item['shot_id']}".encode("utf-8"))


def _completed(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")


def _ffmpeg_completed(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    output_path = Path(command[-1])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"stitched video")
    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


if __name__ == "__main__":
    unittest.main()

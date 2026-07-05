from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import wave
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from scripts.tuolin_marketplace.agent_interface import rebuild_agent_interface
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths
from scripts.tuolin_marketplace.video_creation_agent import (
    VIDEO_CREATIVE_DIRECTIONS,
    assemble_final_preview,
    confirm_narration,
    confirm_dreamina_generation,
    confirm_final_video,
    confirm_creative_direction,
    confirm_narration_script,
    confirm_shot_retry,
    confirm_shots,
    confirm_storyboard,
    confirm_video_plan,
    create_video_creation_run,
    generate_full_narration,
    generate_dreamina_jobs,
    generate_narration_script,
    generate_storyboard,
    generate_video_plan,
    generate_voice_samples,
    handle_video_creation_reply,
    inspect_video_creation_adapters,
    is_video_creation_request,
    plan_shot_retry,
    query_dreamina_results,
    query_shot_retry_results,
    record_manual_quality_check,
    resume_video_creation_run,
    revise_storyboard,
    revise_storyboard_shot,
    revise_video_plan,
    run_quality_gate,
    select_bgm_track,
    select_voice,
    submit_dreamina_jobs,
    submit_shot_retry,
    validate_video_creation_project,
)


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

    def test_creates_video_creation_run_from_agent_interface_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)

            result = create_video_creation_run(
                paths,
                "做一个60秒石英纤维隔热带产品介绍视频，面向欧美工业采购商，用在 YouTube Shorts 和 TikTok。",
                language_version="en",
                platforms=["youtube_shorts", "tiktok"],
                duration_seconds=60,
                target_audience="欧美工业采购商",
                core_objective="突出耐高温、隔热、不刺痒和不冒烟",
                primary_direction="3",
                supporting_direction="产品细节型",
                now=datetime(2026, 6, 25, 14, 30, 5),
            )

            run_dir = Path(result.run_dir)
            self.assertEqual(run_dir.name, "20260625_143005_quartz_fiber_tape_en")
            self.assertTrue((run_dir / "requirements.md").exists())
            self.assertTrue((run_dir / "workflow_state.json").exists())
            self.assertTrue((run_dir / "change_log.md").exists())
            self.assertTrue((run_dir / "narration" / "voice_samples").is_dir())
            self.assertTrue((run_dir / "dreamina_generation" / "generated_shots").is_dir())
            self.assertTrue((run_dir / "audio").is_dir())
            self.assertTrue((run_dir / "subtitles").is_dir())

            requirements = (run_dir / "requirements.md").read_text(encoding="utf-8")
            self.assertIn("## 动态推荐", requirements)
            self.assertIn("## 固定视频创意方向全集", requirements)
            self.assertEqual(requirements.count("### 推荐 "), 3)
            self.assertEqual(requirements.count("**"), len(VIDEO_CREATIVE_DIRECTIONS) * 2)
            self.assertIn("多卖点概览型", requirements)
            self.assertIn("产品细节型", requirements)
            self.assertIn("不得包含 `master`", requirements)

            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(result.status, "requirements_confirmed")
            self.assertEqual(state["phase"], "ready_for_video_plan")
            self.assertEqual(state["language_version"], "en")
            self.assertEqual(state["platforms"], ["youtube_shorts", "tiktok"])
            self.assertEqual(state["duration_seconds"], 60)
            self.assertEqual(state["creative_direction"]["primary"]["id"], "multiple_benefit_overview")
            self.assertEqual(state["creative_direction"]["supporting"]["id"], "product_detail")
            self.assertEqual(state["context"]["task_type"], "video_creation")
            self.assertFalse(state["context"]["raw_access"])
            self.assertTrue(state["context"]["policy"]["no_keyword_expansion"])
            self.assertEqual(state["outputs"]["final_filename"], "quartz_fiber_tape_en_9x16.mp4")
            self.assertEqual(state["outputs"]["dreamina_model"], "seedance2.0_vip")
            self.assertEqual(state["adapters"]["dreamina_command"], "dreamina")
            self.assertEqual(state["adapters"]["ffmpeg_command"], "ffmpeg")
            self.assertEqual(state["adapters"]["bgm_provider"], "manual_licensed_file")
            self.assertTrue(Path(state["files"]["context"]).exists())

    def test_video_creation_resolves_legacy_quartz_product_id_and_draft_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_legacy_quartz_video_cards(paths)
            rebuild_agent_interface(paths)

            result = create_video_creation_run(
                paths,
                "做一个60秒石英纤维隔热带产品介绍视频，面向欧美工业采购商，用在 YouTube Shorts 和 TikTok。",
                language_version="en",
                platforms=["youtube_shorts", "tiktok"],
                duration_seconds=60,
                target_audience="欧美工业采购商",
                core_objective="突出隔热、易施工和采购判断",
                primary_direction="3",
                supporting_direction="产品细节型",
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
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

    def test_video_creation_run_requires_user_creative_direction_confirmation_before_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)

            result = create_video_creation_run(
                paths,
                "做一个60秒石英纤维隔热带产品介绍视频，面向欧美工业采购商，用在 YouTube Shorts 和 TikTok。",
                language_version="en",
                platforms=["youtube_shorts", "tiktok"],
                duration_seconds=60,
                target_audience="欧美工业采购商",
                core_objective="突出隔热、易施工和采购判断",
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            self.assertEqual(result.status, "creative_direction_selection_ready")
            requirements = (run_dir / "requirements.md").read_text(encoding="utf-8")
            self.assertIn("主创意方向：待用户确认", requirements)
            self.assertIn("## 固定视频创意方向全集", requirements)
            self.assertIn("## 动态推荐", requirements)
            with self.assertRaisesRegex(ValueError, "创意方向尚未确认|当前阶段"):
                generate_video_plan(run_dir)

            confirmed = confirm_creative_direction(
                run_dir,
                primary_direction="采购指南型",
                supporting_direction="产品细节型",
                now=datetime(2026, 6, 25, 14, 35, 0),
            )
            self.assertEqual(confirmed.status, "requirements_confirmed")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["creative_direction"])
            self.assertEqual(state["creative_direction"]["primary"]["id"], "procurement_guide")
            self.assertEqual(state["creative_direction"]["supporting"]["id"], "product_detail")

            plan_result = generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))
            self.assertEqual(plan_result.status, "video_plan_ready")

    def test_video_creation_reply_can_confirm_creative_direction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_official_cards(paths)
            rebuild_agent_interface(paths)

            result = create_video_creation_run(
                paths,
                "做一个60秒石英纤维隔热带产品介绍视频",
                language_version="en",
                platforms=["tiktok"],
                duration_seconds=60,
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            reply_result = handle_video_creation_reply(
                run_dir,
                "主方向：采购指南型，辅助方向：产品细节型",
                now=datetime(2026, 6, 25, 14, 35, 0),
            )

            self.assertEqual(reply_result.status, "requirements_confirmed")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["creative_direction"]["primary"]["id"], "procurement_guide")

    def test_video_creation_run_captures_adapter_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(
                Path(tmp),
                {
                    "video_creation": {
                        "dreamina_command": "/opt/dreamina",
                        "ffmpeg_command": "/opt/ffmpeg",
                        "tts_provider": "external_command",
                        "tts_command": "/opt/tts",
                        "bgm_provider": "manual_licensed_file",
                        "bgm_library_dir": "/music",
                        "logo_path": "assets/logo/custom.png",
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
                platforms=["tiktok"],
                duration_seconds=60,
                primary_direction="产品总览型",
                now=datetime(2026, 6, 25, 14, 30, 5),
            )

            state = json.loads((Path(result.run_dir) / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["adapters"]["dreamina_command"], "/opt/dreamina")
            self.assertEqual(state["adapters"]["ffmpeg_command"], "/opt/ffmpeg")
            self.assertEqual(state["adapters"]["tts_provider"], "external_command")
            self.assertEqual(state["adapters"]["tts_command"], "/opt/tts")
            self.assertEqual(state["adapters"]["bgm_library_dir"], "/music")
            self.assertEqual(state["adapters"]["logo_path"], "assets/logo/custom.png")

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
            rebuild_agent_interface(paths)
            result = create_video_creation_run(
                paths,
                "做一个60秒石英纤维隔热带产品介绍视频",
                language_version="en",
                platforms=["tiktok"],
                duration_seconds=60,
                primary_direction="产品总览型",
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))
            confirm_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 5, 0))
            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))
            confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))
            generate_narration_script(run_dir, now=datetime(2026, 6, 25, 15, 20, 0))
            confirm_narration_script(run_dir, now=datetime(2026, 6, 25, 15, 21, 0))
            generate_voice_samples(run_dir, now=datetime(2026, 6, 25, 15, 22, 0))
            select_voice(run_dir, 2, now=datetime(2026, 6, 25, 15, 23, 0))
            generate_full_narration(run_dir, now=datetime(2026, 6, 25, 15, 24, 0))
            confirm_narration(run_dir, now=datetime(2026, 6, 25, 15, 25, 0))
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
            rebuild_agent_interface(paths)
            result = create_video_creation_run(
                paths,
                "做一个60秒石英纤维隔热带产品介绍视频",
                language_version="en",
                platforms=["tiktok"],
                duration_seconds=60,
                primary_direction="产品总览型",
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))
            confirm_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 5, 0))
            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))
            confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))
            generate_narration_script(run_dir, now=datetime(2026, 6, 25, 15, 20, 0))
            confirm_narration_script(run_dir, now=datetime(2026, 6, 25, 15, 21, 0))
            generate_voice_samples(run_dir, now=datetime(2026, 6, 25, 15, 22, 0))
            select_voice(run_dir, 2, now=datetime(2026, 6, 25, 15, 23, 0))
            generate_full_narration(run_dir, now=datetime(2026, 6, 25, 15, 24, 0))
            confirm_narration(run_dir, now=datetime(2026, 6, 25, 15, 25, 0))
            generate_dreamina_jobs(run_dir, now=datetime(2026, 6, 25, 15, 30, 0))

            jobs = json.loads((run_dir / "dreamina_generation" / "dreamina_jobs.json").read_text(encoding="utf-8"))
            self.assertTrue(any(job["validation"]["status"] == "blocked" for job in jobs["jobs"]))
            with self.assertRaisesRegex(ValueError, "存在 blocked 即梦任务"):
                confirm_dreamina_generation(run_dir, now=datetime(2026, 6, 25, 15, 35, 0))

    def test_multimodal_material_limit_blocks_dreamina_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(
                root,
                {
                    "video_creation": {
                        "dreamina_capability_profile": {
                            "max_images": 0,
                        }
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
                platforms=["tiktok"],
                duration_seconds=60,
                primary_direction="产品总览型",
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))
            confirm_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 5, 0))
            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))
            confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))
            generate_narration_script(run_dir, now=datetime(2026, 6, 25, 15, 20, 0))
            confirm_narration_script(run_dir, now=datetime(2026, 6, 25, 15, 21, 0))
            generate_voice_samples(run_dir, now=datetime(2026, 6, 25, 15, 22, 0))
            select_voice(run_dir, 2, now=datetime(2026, 6, 25, 15, 23, 0))
            generate_full_narration(run_dir, now=datetime(2026, 6, 25, 15, 24, 0))
            confirm_narration(run_dir, now=datetime(2026, 6, 25, 15, 25, 0))
            generate_dreamina_jobs(run_dir, now=datetime(2026, 6, 25, 15, 30, 0))

            jobs = json.loads((run_dir / "dreamina_generation" / "dreamina_jobs.json").read_text(encoding="utf-8"))
            self.assertEqual(jobs["material_reference_map"]["counts"]["images"], 1)
            self.assertTrue(any("Seedance 多模态输入超限" in "; ".join(job["validation"]["messages"]) for job in jobs["jobs"]))
            with self.assertRaisesRegex(ValueError, "存在 blocked 即梦任务"):
                confirm_dreamina_generation(run_dir, now=datetime(2026, 6, 25, 15, 35, 0))

    def test_clear_human_face_material_blocks_dreamina_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = resolve_paths(root, {})
            initialize_project(paths)
            _write_official_cards(paths, human_face_risk="clear_face")
            rebuild_agent_interface(paths)
            result = create_video_creation_run(
                paths,
                "做一个60秒石英纤维隔热带产品介绍视频",
                language_version="en",
                platforms=["tiktok"],
                duration_seconds=60,
                primary_direction="产品总览型",
                now=datetime(2026, 6, 25, 14, 30, 5),
            )
            run_dir = Path(result.run_dir)
            generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))
            confirm_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 5, 0))
            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))
            storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
            self.assertTrue(any(shot["human_face_risk"] == "clear_face" for shot in storyboard["shots"]))
            self.assertTrue(any(shot["shot_design_validation"]["status"] == "blocked" for shot in storyboard["shots"]))
            confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))
            generate_narration_script(run_dir, now=datetime(2026, 6, 25, 15, 20, 0))
            confirm_narration_script(run_dir, now=datetime(2026, 6, 25, 15, 21, 0))
            generate_voice_samples(run_dir, now=datetime(2026, 6, 25, 15, 22, 0))
            select_voice(run_dir, 2, now=datetime(2026, 6, 25, 15, 23, 0))
            generate_full_narration(run_dir, now=datetime(2026, 6, 25, 15, 24, 0))
            confirm_narration(run_dir, now=datetime(2026, 6, 25, 15, 25, 0))
            generate_dreamina_jobs(run_dir, now=datetime(2026, 6, 25, 15, 30, 0))

            jobs = json.loads((run_dir / "dreamina_generation" / "dreamina_jobs.json").read_text(encoding="utf-8"))
            self.assertTrue(any(job["human_face_risk"] == "clear_face" for job in jobs["jobs"]))
            self.assertTrue(any("清晰可辨识真人脸部" in "; ".join(job["validation"]["messages"]) for job in jobs["jobs"]))
            with self.assertRaisesRegex(ValueError, "存在 blocked 即梦任务"):
                confirm_dreamina_generation(run_dir, now=datetime(2026, 6, 25, 15, 35, 0))

    def test_generates_video_plan_and_waits_for_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))

            result = generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))

            self.assertEqual(result.status, "video_plan_ready")
            self.assertEqual(result.phase, "awaiting_video_plan_confirmation")
            plan_md = run_dir / "video_plan.md"
            plan_json = run_dir / "video_plan.json"
            self.assertTrue(plan_md.exists())
            self.assertTrue(plan_json.exists())
            plan_text = plan_md.read_text(encoding="utf-8")
            self.assertIn("# 视频策划", plan_text)
            self.assertIn("对外中文名：特种玻璃纤维带", plan_text)
            self.assertIn("对外英文名：Specialty Glass Fiber Tape", plan_text)
            self.assertIn("允许 55-65 秒", plan_text)
            self.assertIn("content_asset/quartz_product_photo", plan_text)
            self.assertIn("## 视频创作素材准备度", plan_text)
            self.assertIn("产品图片素材：1", plan_text)
            self.assertIn("可用于 image2video/reuse_video 的真实参考素材：1", plan_text)
            self.assertIn("音乐 brief", plan_text)
            self.assertIn("不得使用 video_script", plan_text)
            self.assertIn("不得使用母版/master", plan_text)
            self.assertIn("请确认策划后继续生成分镜", plan_text)

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
            self.assertEqual(plan["material_availability"]["counts"]["product_image_assets"], 1)
            self.assertEqual(plan["material_availability"]["counts"]["usable_visual_reference_assets"], 1)
            self.assertEqual(plan["material_availability"]["usable_visual_references"][0]["id"], "content_asset/quartz_product_photo")

            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertFalse(state["confirmations"]["video_plan"])
            self.assertEqual(state["current_pending_confirmation"], "确认策划")
            self.assertEqual(state["files"]["video_plan_md"], str(plan_md))
            self.assertEqual([item["status"] for item in state["status_history"]], ["requirements_confirmed", "video_plan_ready"])

    def test_video_plan_does_not_silently_overwrite_existing_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))
            generate_video_plan(run_dir)

            with self.assertRaises(FileExistsError):
                generate_video_plan(run_dir)

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
                ["requirements_confirmed", "video_plan_ready", "video_plan_confirmed"],
            )
            change_log = (run_dir / "change_log.md").read_text(encoding="utf-8")
            self.assertIn("确认视频策划，进入分镜生成阶段。", change_log)

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
            self.assertIn("确认策划", status["suggested_replies"])
            self.assertTrue(status["policy"]["resume_from_current_phase_only"])
            self.assertIn("不重复已确认步骤", status_md.read_text(encoding="utf-8"))

    def test_handles_natural_language_confirmation_reply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))
            generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))

            result = handle_video_creation_reply(run_dir, "确认策划", now=datetime(2026, 6, 25, 15, 5, 0))

            self.assertEqual(result.status, "video_plan_confirmed")
            self.assertEqual(result.phase, "ready_for_storyboard")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["video_plan"])

    def test_handles_generation_reply_for_current_pending_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_plan_confirmed_run(Path(tmp))

            result = handle_video_creation_reply(run_dir, "生成分镜", now=datetime(2026, 6, 25, 15, 10, 0))

            self.assertEqual(result.status, "storyboard_ready")
            self.assertEqual(result.phase, "awaiting_storyboard_confirmation")
            self.assertTrue((run_dir / "storyboard.md").exists())
            self.assertTrue((run_dir / "prompts.json").exists())

    def test_cannot_confirm_video_plan_before_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))

            with self.assertRaisesRegex(ValueError, "找不到可确认的视频策划"):
                confirm_video_plan(run_dir)

    def test_generates_storyboard_and_prompts_after_plan_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_plan_confirmed_run(Path(tmp))

            result = generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))

            self.assertEqual(result.status, "storyboard_ready")
            self.assertEqual(result.phase, "awaiting_storyboard_confirmation")
            storyboard_md = run_dir / "storyboard.md"
            storyboard_json = run_dir / "storyboard.json"
            prompts_md = run_dir / "prompts.md"
            prompts_json = run_dir / "prompts.json"
            self.assertTrue(storyboard_md.exists())
            self.assertTrue(storyboard_json.exists())
            self.assertTrue(prompts_md.exists())
            self.assertTrue(prompts_json.exists())

            storyboard_text = storyboard_md.read_text(encoding="utf-8")
            self.assertIn("# 视频分镜", storyboard_text)
            self.assertIn("Prompt 是给即梦使用，不是字幕", storyboard_text)
            self.assertIn("content_asset/quartz_product_photo", storyboard_text)
            self.assertIn("需要真实产品参考：是", storyboard_text)

            storyboard = json.loads(storyboard_json.read_text(encoding="utf-8"))
            self.assertEqual(storyboard["status"], "draft_pending_confirmation")
            self.assertEqual(len(storyboard["shots"]), 12)
            self.assertTrue(storyboard["policy"]["text_prompts_are_not_subtitles"])
            self.assertEqual(storyboard["production_style"]["id"], "industrial_professional")
            self.assertTrue(all(shot["creative_quality_checks"] for shot in storyboard["shots"]))
            self.assertTrue(all(shot["shot_design_validation"]["status"] == "ok" for shot in storyboard["shots"]))
            self.assertTrue(any(shot["material_mode"] == "image2video" for shot in storyboard["shots"]))
            self.assertFalse(any(shot["material_mode"] == "text2video" and shot["product_visible"] for shot in storyboard["shots"]))
            product_hero = next(shot for shot in storyboard["shots"] if shot["role"] == "product_hero")
            product_detail = next(shot for shot in storyboard["shots"] if shot["role"] == "product_detail")
            closing_cta = next(shot for shot in storyboard["shots"] if shot["role"] == "closing_cta")
            self.assertEqual(product_hero["first_frame_reference_id"], "content_asset/quartz_product_photo")
            self.assertEqual(product_detail["first_frame_reference_id"], "content_asset/quartz_product_photo")
            self.assertEqual(closing_cta["last_frame_reference_id"], "content_asset/quartz_product_photo")
            self.assertEqual(product_hero["human_face_risk"], "none")

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
            self.assertEqual(prompts["material_reference_map"]["counts"]["images"], 1)
            self.assertEqual(prompts["material_reference_map"]["references"][0]["label"], "@图片1")
            self.assertIn("真实产品", prompts["material_reference_map"]["references"][0]["usages"][0])
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
            self.assertFalse(any("short drama" in item["prompt"].lower() or "dance" in item["prompt"].lower() or "xianxia" in item["prompt"].lower() for item in prompts["prompts"]))
            referenced = [item for item in prompts["prompts"] if item["reference_required"]]
            self.assertTrue(all(item["numbered_reference_label"] == "@图片1" for item in referenced))
            self.assertTrue(all(item["reference_usage"] for item in referenced))

            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertFalse(state["confirmations"]["storyboard"])
            self.assertEqual(state["current_pending_confirmation"], "确认分镜")
            self.assertEqual(state["files"]["storyboard_json"], str(storyboard_json))
            self.assertEqual(state["files"]["prompts_json"], str(prompts_json))

    def test_storyboard_does_not_silently_overwrite_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_plan_confirmed_run(Path(tmp))
            generate_storyboard(run_dir)

            with self.assertRaises(FileExistsError):
                generate_storyboard(run_dir)

    def test_confirms_storyboard_and_moves_to_narration_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_plan_confirmed_run(Path(tmp))
            generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))

            result = confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))

            self.assertEqual(result.status, "storyboard_confirmed")
            self.assertEqual(result.phase, "ready_for_narration_script")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["storyboard"])
            self.assertFalse(state["confirmations"]["narration_script"])
            self.assertEqual(state["current_pending_confirmation"], "生成旁白文案")
            self.assertEqual(
                [item["status"] for item in state["status_history"]],
                ["requirements_confirmed", "video_plan_ready", "video_plan_confirmed", "storyboard_ready", "storyboard_confirmed"],
            )

    def test_cannot_generate_storyboard_before_plan_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))
            generate_video_plan(run_dir)

            with self.assertRaisesRegex(ValueError, "当前阶段是 'awaiting_video_plan_confirmation'"):
                generate_storyboard(run_dir)

    def test_generates_and_confirms_narration_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_storyboard_confirmed_run(Path(tmp))

            result = generate_narration_script(run_dir, now=datetime(2026, 6, 25, 15, 20, 0))

            self.assertEqual(result.status, "narration_script_ready")
            self.assertEqual(result.phase, "awaiting_narration_script_confirmation")
            script_md = run_dir / "narration" / "script.md"
            script_json = run_dir / "narration" / "script.json"
            self.assertTrue(script_md.exists())
            self.assertTrue(script_json.exists())
            script_text = script_md.read_text(encoding="utf-8")
            self.assertIn("# 旁白文案", script_text)
            self.assertIn("middle-aged Western male", script_text)
            self.assertIn("Specialty Glass Fiber Tape", script_text)
            self.assertIn("确认旁白文案", script_text)
            script = json.loads(script_json.read_text(encoding="utf-8"))
            self.assertEqual(script["language_version"], "en")
            self.assertEqual(len(script["sentences"]), 12)
            self.assertTrue(script["policy"]["confirm_before_voice_samples"])
            self.assertTrue(script["policy"]["no_new_product_facts"])

            confirmed = confirm_narration_script(run_dir, now=datetime(2026, 6, 25, 15, 21, 0))
            self.assertEqual(confirmed.status, "narration_script_confirmed")
            self.assertEqual(confirmed.phase, "ready_for_voice_samples")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["narration_script"])
            self.assertEqual(state["current_pending_confirmation"], "生成声音样本")

    def test_voice_samples_use_same_excerpt_and_voice_selection_advances_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_narration_script_confirmed_run(Path(tmp))

            result = generate_voice_samples(run_dir, now=datetime(2026, 6, 25, 15, 22, 0))

            self.assertEqual(result.status, "voice_samples_ready")
            samples_json = run_dir / "narration" / "voice_samples.json"
            samples = json.loads(samples_json.read_text(encoding="utf-8"))
            self.assertEqual(len(samples["samples"]), 3)
            excerpts = {sample["excerpt"] for sample in samples["samples"]}
            self.assertEqual(len(excerpts), 1)
            self.assertIn("High-temperature insulation work", samples["excerpt"])
            for sample in samples["samples"]:
                sample_path = Path(sample["audio_path"])
                self.assertTrue(sample_path.exists())
                with wave.open(str(sample_path), "rb") as handle:
                    self.assertEqual(handle.getnchannels(), 1)
                    self.assertGreater(handle.getnframes(), 0)
                self.assertIn("middle-aged Western male", sample["voice_profile"]["description"])

            selected = select_voice(run_dir, 2, now=datetime(2026, 6, 25, 15, 23, 0))
            self.assertEqual(selected.status, "voice_selected")
            self.assertEqual(selected.phase, "ready_for_full_narration")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["voice"])
            self.assertEqual(state["selected_voice"]["sample_id"], 2)

    def test_handles_voice_selection_reply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_narration_script_confirmed_run(Path(tmp))
            generate_voice_samples(run_dir, now=datetime(2026, 6, 25, 15, 22, 0))

            result = handle_video_creation_reply(run_dir, "声音选 2", now=datetime(2026, 6, 25, 15, 23, 0))

            self.assertEqual(result.status, "voice_selected")
            self.assertEqual(result.phase, "ready_for_full_narration")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["selected_voice"]["sample_id"], 2)

    def test_generates_and_confirms_full_narration_with_sentence_timing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_voice_selected_run(Path(tmp))

            result = generate_full_narration(run_dir, now=datetime(2026, 6, 25, 15, 24, 0))

            self.assertEqual(result.status, "narration_ready")
            self.assertEqual(result.phase, "awaiting_narration_confirmation")
            narration_wav = run_dir / "narration" / "narration.wav"
            timing_json = run_dir / "narration" / "timing.json"
            preview_md = run_dir / "narration" / "narration_preview.md"
            self.assertTrue(narration_wav.exists())
            self.assertTrue(timing_json.exists())
            self.assertTrue(preview_md.exists())
            with wave.open(str(narration_wav), "rb") as handle:
                self.assertEqual(handle.getnchannels(), 1)
                self.assertEqual(handle.getframerate(), 8000)
                self.assertEqual(round(handle.getnframes() / handle.getframerate()), 60)
            timing = json.loads(timing_json.read_text(encoding="utf-8"))
            self.assertEqual(timing["total_duration_seconds"], 60)
            self.assertEqual(len(timing["sentence_timing"]), 12)
            self.assertEqual(timing["sentence_timing"][0]["start_seconds"], 0.0)
            self.assertEqual(timing["sentence_timing"][-1]["end_seconds"], 60.0)
            preview = preview_md.read_text(encoding="utf-8")
            self.assertIn("请检查旁白文案、声音、语速、发音和节奏", preview)

            confirmed = confirm_narration(run_dir, now=datetime(2026, 6, 25, 15, 25, 0))
            self.assertEqual(confirmed.status, "narration_confirmed")
            self.assertEqual(confirmed.phase, "ready_for_dreamina_jobs")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["narration"])
            self.assertEqual(state["current_pending_confirmation"], "规划即梦任务")

    def test_external_command_tts_generates_voice_samples_and_full_narration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_narration_script_confirmed_run(Path(tmp), tts_provider="external_command", tts_command="/opt/tts")
            calls = []

            def fake_tts_runner(command, capture_output, text, check):
                calls.append(command)
                output_path = Path(command[command.index("--output") + 1])
                _write_test_wav(output_path)
                return _completed(command)

            generate_voice_samples(run_dir, now=datetime(2026, 6, 25, 15, 22, 0), runner=fake_tts_runner)
            samples = json.loads((run_dir / "narration" / "voice_samples.json").read_text(encoding="utf-8"))
            self.assertEqual({sample["provider"] for sample in samples["samples"]}, {"external_command"})
            self.assertTrue(all("--voice-id" in call for call in calls))

            select_voice(run_dir, 2, now=datetime(2026, 6, 25, 15, 23, 0))
            generate_full_narration(run_dir, now=datetime(2026, 6, 25, 15, 24, 0), runner=fake_tts_runner)
            timing = json.loads((run_dir / "narration" / "timing.json").read_text(encoding="utf-8"))
            self.assertEqual(timing["tts_provider"], "external_command")
            self.assertTrue((run_dir / "narration" / "narration.wav").exists())

    def test_confirmed_narration_script_cannot_be_modified_before_tts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_narration_script_confirmed_run(Path(tmp))
            script_md = run_dir / "narration" / "script.md"
            script_md.write_text(script_md.read_text(encoding="utf-8") + "\nAI rewrite\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "旁白文案已确认后被修改"):
                generate_voice_samples(run_dir, now=datetime(2026, 6, 25, 15, 22, 0))

    def test_cannot_generate_voice_samples_before_script_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_storyboard_confirmed_run(Path(tmp))
            generate_narration_script(run_dir)

            with self.assertRaisesRegex(ValueError, "当前阶段是 'awaiting_narration_script_confirmation'"):
                generate_voice_samples(run_dir)

    def test_generates_dreamina_jobs_after_narration_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_narration_confirmed_run(Path(tmp))

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
            self.assertEqual(jobs["material_reference_map"]["counts"]["images"], 1)
            self.assertTrue(jobs["policy"]["do_not_submit_before_confirmation"])
            self.assertTrue(jobs["policy"]["job_validation_required"])
            self.assertEqual(len(jobs["jobs"]), 12)
            self.assertGreater(jobs["estimated_total_credits"], 0)
            self.assertTrue(all(job["job_type"] == "image2video" for job in jobs["jobs"]))
            self.assertTrue(all(job["estimated_credits"] == 8 for job in jobs["jobs"]))
            self.assertTrue(all(job["narration_timing"] for job in jobs["jobs"]))
            self.assertTrue(all(job["numbered_reference_label"] == "@图片1" for job in jobs["jobs"]))
            self.assertTrue(all(job["reference_usage"] for job in jobs["jobs"]))
            self.assertTrue(any(job["first_frame_reference_id"] == "content_asset/quartz_product_photo" for job in jobs["jobs"]))
            self.assertTrue(any(job["last_frame_reference_id"] == "content_asset/quartz_product_photo" for job in jobs["jobs"]))
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
            self.assertEqual(state["dreamina_authorization"]["estimated_total_credits"], 96)
            self.assertIn("本步骤不实际提交任务", state["dreamina_authorization"]["note"])
            self.assertFalse((run_dir / "dreamina_generation" / "dreamina_results.json").exists())

    def test_dreamina_jobs_do_not_silently_overwrite_existing_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_narration_confirmed_run(Path(tmp))
            generate_dreamina_jobs(run_dir)

            with self.assertRaises(FileExistsError):
                generate_dreamina_jobs(run_dir)

    def test_cannot_generate_dreamina_jobs_before_narration_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_voice_selected_run(Path(tmp))
            generate_full_narration(run_dir)

            with self.assertRaisesRegex(ValueError, "当前阶段是 'awaiting_narration_confirmation'"):
                generate_dreamina_jobs(run_dir)

    def test_blocked_dreamina_jobs_prevent_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_narration_confirmed_run_without_assets(Path(tmp))
            generate_dreamina_jobs(run_dir)

            jobs = json.loads((run_dir / "dreamina_generation" / "dreamina_jobs.json").read_text(encoding="utf-8"))
            self.assertTrue(any(job["job_type"] == "blocked" for job in jobs["jobs"]))
            with self.assertRaisesRegex(ValueError, "存在 blocked 即梦任务"):
                confirm_dreamina_generation(run_dir)

    def test_prompt_conflicts_and_duration_complexity_block_dreamina_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_narration_confirmed_run(Path(tmp))
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

            self.assertEqual(result.status, "dreamina_jobs_submitted")
            self.assertEqual(result.phase, "awaiting_dreamina_results")
            submission_json = run_dir / "dreamina_generation" / "dreamina_submission.json"
            submission_md = run_dir / "dreamina_generation" / "dreamina_submission.md"
            manual_ps1 = run_dir / "dreamina_generation" / "submit_real_dreamina_jobs.ps1"
            manual_template = run_dir / "dreamina_generation" / "manual_submission_template.json"
            self.assertTrue(submission_json.exists())
            self.assertTrue(submission_md.exists())
            self.assertTrue(manual_ps1.exists())
            self.assertTrue(manual_template.exists())
            submission = json.loads(submission_json.read_text(encoding="utf-8"))
            self.assertEqual(submission["mode"], "dry_run")
            self.assertTrue(submission["policy"]["dry_run_does_not_consume_credits"])
            self.assertEqual(len(submission["submissions"]), 12)
            self.assertTrue(all(item["status"] == "dry_run_submitted" for item in submission["submissions"]))
            self.assertTrue(all(item["provider_task_id"].startswith("dryrun_shot_") for item in submission["submissions"]))
            submission_text = submission_md.read_text(encoding="utf-8")
            self.assertIn("人工真实提交脚本", submission_text)
            self.assertIn("dreamina image2video", submission_text)
            ps1_text = manual_ps1.read_text(encoding="utf-8")
            self.assertIn("manual_submission.json", ps1_text)
            self.assertIn("--model_version", ps1_text)
            self.assertTrue(manual_ps1.read_bytes().startswith(b"\xef\xbb\xbf"))
            self.assertNotIn("'--image' '--prompt'", ps1_text)
            self.assertIn("product.jpg", ps1_text)
            template = json.loads(manual_template.read_text(encoding="utf-8"))
            self.assertEqual(template["mode"], "manual_execute")
            self.assertTrue(all(item["status"] == "pending_manual_execution" for item in template["submissions"]))

            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["current_pending_confirmation"], "查询即梦结果")
            self.assertEqual(state["files"]["dreamina_submission_json"], str(submission_json))
            self.assertEqual(state["files"]["dreamina_manual_submit_ps1"], str(manual_ps1))

    def test_dreamina_submission_uses_content_asset_local_path_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_generation_confirmed_run(Path(tmp))
            jobs_path = run_dir / "dreamina_generation" / "dreamina_jobs.json"
            jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
            for job in jobs["jobs"]:
                selected = job["selected_material"]
                selected.pop("files", None)
                selected["local_path"] = "raw/01_产品/02_石英纤维隔热带/02_产品图片/local-product.png"
                job["validation"] = {"status": "ok", "messages": ["ok"]}
            jobs_path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")

            submit_dreamina_jobs(run_dir, now=datetime(2026, 6, 25, 15, 40, 0))

            manual_ps1 = run_dir / "dreamina_generation" / "submit_real_dreamina_jobs.ps1"
            ps1_text = manual_ps1.read_text(encoding="utf-8-sig")
            self.assertIn("local-product.png", ps1_text)
            self.assertNotIn("'--image' '--prompt'", ps1_text)

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
            self.assertIn("确认镜头", results_md.read_text(encoding="utf-8"))

            confirmed = confirm_shots(run_dir, now=datetime(2026, 6, 25, 15, 50, 0))
            self.assertEqual(confirmed.status, "shots_confirmed")
            self.assertEqual(confirmed.phase, "ready_for_final_assembly")
            shot_preview_manifest = run_dir / "dreamina_generation" / "shot_preview_manifest.json"
            self.assertTrue(shot_preview_manifest.exists())
            shot_preview = json.loads(shot_preview_manifest.read_text(encoding="utf-8"))
            self.assertTrue(shot_preview["contains_confirmed_narration"])
            self.assertTrue(shot_preview["contains_temporary_subtitles"])
            self.assertFalse(shot_preview["contains_final_bgm"])
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["shots"])
            self.assertEqual(state["current_pending_confirmation"], "生成成片预览")

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

    def test_plans_and_confirms_single_shot_retry_with_credit_estimate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_results_ready_run(Path(tmp))

            result = plan_shot_retry(run_dir, "3", reason="产品边缘不够清楚", now=datetime(2026, 6, 25, 15, 55, 0))

            self.assertEqual(result.status, "shot_retry_planned")
            self.assertEqual(result.phase, "awaiting_shot_retry_confirmation")
            retry_json = run_dir / "dreamina_generation" / "retry_plans" / "retry_shot_03_20260625_155500.json"
            retry_md = run_dir / "dreamina_generation" / "retry_plans" / "retry_shot_03_20260625_155500.md"
            self.assertTrue(retry_json.exists())
            self.assertTrue(retry_md.exists())
            retry = json.loads(retry_json.read_text(encoding="utf-8"))
            self.assertEqual(retry["shot_id"], "03")
            self.assertEqual(retry["estimated_credits"], 8)
            self.assertEqual(retry["submit_requires_confirmation"], "确认重做镜头 03")
            self.assertIn("只重做当前镜头", retry_md.read_text(encoding="utf-8"))

            confirmed = confirm_shot_retry(run_dir, "03", now=datetime(2026, 6, 25, 15, 56, 0))
            self.assertEqual(confirmed.status, "shot_retry_confirmed")
            self.assertEqual(confirmed.phase, "ready_for_shot_retry_submission")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["pending_shot_retry"]["shot_id"], "03")
            self.assertEqual(state["current_pending_confirmation"], "提交重做镜头 03")

    def test_handles_shot_retry_request_reply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_results_ready_run(Path(tmp))

            result = handle_video_creation_reply(run_dir, "重做镜头 03，产品边缘不够清楚", now=datetime(2026, 6, 25, 15, 55, 0))

            self.assertEqual(result.status, "shot_retry_planned")
            self.assertEqual(result.phase, "awaiting_shot_retry_confirmation")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["pending_shot_retry"]["shot_id"], "03")
            self.assertEqual(state["current_pending_confirmation"], "确认重做镜头 03")

    def test_submits_and_queries_single_shot_retry_without_resubmitting_other_shots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_results_ready_run(Path(tmp))
            original_results = json.loads((run_dir / "dreamina_generation" / "dreamina_results.json").read_text(encoding="utf-8"))
            original_result_count = len(original_results["results"])
            plan_shot_retry(run_dir, "03", reason="产品边缘不够清楚", now=datetime(2026, 6, 25, 15, 55, 0))
            confirm_shot_retry(run_dir, "03", now=datetime(2026, 6, 25, 15, 56, 0))

            submitted = submit_shot_retry(run_dir, now=datetime(2026, 6, 25, 15, 57, 0), expected_shot_id="03")

            self.assertEqual(submitted.status, "shot_retry_submitted")
            self.assertEqual(submitted.phase, "awaiting_shot_retry_results")
            retry_submission = run_dir / "dreamina_generation" / "retry_submissions" / "retry_shot_03_20260625_155700.json"
            self.assertTrue(retry_submission.exists())
            submission_payload = json.loads(retry_submission.read_text(encoding="utf-8"))
            self.assertEqual(len(submission_payload["submissions"]), 1)
            self.assertEqual(submission_payload["submissions"][0]["shot_id"], "03")
            self.assertTrue(submission_payload["submissions"][0]["job_id"].startswith("retry_"))

            queried = query_shot_retry_results(run_dir, now=datetime(2026, 6, 25, 15, 58, 0), expected_shot_id="03")

            self.assertEqual(queried.status, "shot_retry_results_ready")
            self.assertEqual(queried.phase, "awaiting_shot_confirmation")
            full_results = json.loads((run_dir / "dreamina_generation" / "dreamina_results.json").read_text(encoding="utf-8"))
            self.assertEqual(len(full_results["results"]), original_result_count)
            shot_03 = next(item for item in full_results["results"] if item["shot_id"] == "03")
            shot_04 = next(item for item in full_results["results"] if item["shot_id"] == "04")
            self.assertTrue(shot_03["replaces_previous_result"])
            self.assertIn("previous_result", shot_03)
            self.assertNotIn("replaces_previous_result", shot_04)
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertNotIn("pending_shot_retry", state)
            self.assertEqual(state["shot_retry_history"][0]["shot_id"], "03")
            self.assertEqual(state["current_pending_confirmation"], "确认镜头或重做镜头 XX")

    def test_handles_submit_and_query_shot_retry_replies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_results_ready_run(Path(tmp))
            handle_video_creation_reply(run_dir, "重做镜头 03，产品边缘不够清楚", now=datetime(2026, 6, 25, 15, 55, 0))
            handle_video_creation_reply(run_dir, "确认重做镜头 03", now=datetime(2026, 6, 25, 15, 56, 0))

            submitted = handle_video_creation_reply(run_dir, "提交重做镜头 03", now=datetime(2026, 6, 25, 15, 57, 0))
            queried = handle_video_creation_reply(run_dir, "查询重做镜头 03", now=datetime(2026, 6, 25, 15, 58, 0))

            self.assertEqual(submitted.status, "shot_retry_submitted")
            self.assertEqual(queried.status, "shot_retry_results_ready")
            self.assertEqual(queried.phase, "awaiting_shot_confirmation")

    def test_rejects_mismatched_shot_retry_submission_reply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_dreamina_results_ready_run(Path(tmp))
            plan_shot_retry(run_dir, "03", reason="产品边缘不够清楚", now=datetime(2026, 6, 25, 15, 55, 0))
            confirm_shot_retry(run_dir, "03", now=datetime(2026, 6, 25, 15, 56, 0))

            with self.assertRaisesRegex(ValueError, "当前等待提交的是镜头 03，不是 04"):
                handle_video_creation_reply(run_dir, "提交重做镜头 04", now=datetime(2026, 6, 25, 15, 57, 0))

    def test_revising_video_plan_clears_downstream_confirmations_and_file_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_final_preview_contract_run(Path(tmp))

            result = revise_video_plan(
                run_dir,
                "修改策划，开场更突出高温设备密封痛点。",
                now=datetime(2026, 6, 25, 16, 20, 0),
            )

            self.assertEqual(result.status, "video_plan_revised")
            self.assertEqual(result.phase, "awaiting_video_plan_confirmation")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertFalse(state["confirmations"]["video_plan"])
            self.assertFalse(state["confirmations"]["storyboard"])
            self.assertFalse(state["confirmations"]["narration"])
            self.assertFalse(state["confirmations"]["dreamina_generation"])
            self.assertFalse(state["confirmations"]["shots"])
            self.assertEqual(state["current_pending_confirmation"], "确认策划")
            self.assertNotIn("storyboard_json", state["files"])
            self.assertNotIn("dreamina_results_json", state["files"])
            self.assertNotIn("final_preview_mp4", state["files"])
            plan = json.loads((run_dir / "video_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["change_requests"][0]["scope"], "video_plan")
            self.assertIn("高温设备密封痛点", (run_dir / "video_plan.md").read_text(encoding="utf-8"))
            self.assertIn("清除分镜及后续确认", (run_dir / "change_log.md").read_text(encoding="utf-8"))

    def test_revising_storyboard_clears_narration_and_generation_confirmations_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_final_preview_contract_run(Path(tmp))

            result = revise_storyboard(
                run_dir,
                "修改分镜，减少泛泛介绍，增加采购判断信息。",
                now=datetime(2026, 6, 25, 16, 21, 0),
            )

            self.assertEqual(result.status, "storyboard_revised")
            self.assertEqual(result.phase, "awaiting_storyboard_confirmation")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["video_plan"])
            self.assertFalse(state["confirmations"]["storyboard"])
            self.assertFalse(state["confirmations"]["narration_script"])
            self.assertFalse(state["confirmations"]["dreamina_generation"])
            self.assertFalse(state["confirmations"]["shots"])
            self.assertEqual(state["current_pending_confirmation"], "确认分镜")
            self.assertIn("storyboard_json", state["files"])
            self.assertNotIn("narration_script_json", state["files"])
            self.assertNotIn("dreamina_jobs_json", state["files"])
            storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
            self.assertEqual(storyboard["change_requests"][0]["scope"], "storyboard")
            self.assertIn("采购判断信息", (run_dir / "storyboard.md").read_text(encoding="utf-8"))

    def test_revising_single_shot_marks_only_that_shot_and_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_final_preview_contract_run(Path(tmp))

            result = revise_storyboard_shot(
                run_dir,
                "03",
                "修改镜头03，突出编织纹理和边缘厚度。",
                now=datetime(2026, 6, 25, 16, 22, 0),
            )

            self.assertEqual(result.status, "storyboard_revised")
            storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
            prompts = json.loads((run_dir / "prompts.json").read_text(encoding="utf-8"))
            shot_03 = next(item for item in storyboard["shots"] if item["shot_id"] == "03")
            shot_04 = next(item for item in storyboard["shots"] if item["shot_id"] == "04")
            prompt_03 = next(item for item in prompts["prompts"] if item["shot_id"] == "03")
            prompt_04 = next(item for item in prompts["prompts"] if item["shot_id"] == "04")
            self.assertEqual(shot_03["change_requests"][0]["scope"], "shot_03")
            self.assertEqual(prompt_03["change_requests"][0]["scope"], "shot_03")
            self.assertNotIn("change_requests", shot_04)
            self.assertNotIn("change_requests", prompt_04)
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertFalse(state["confirmations"]["storyboard"])
            self.assertEqual(state["current_pending_confirmation"], "确认分镜")

    def test_handles_revision_replies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_final_preview_contract_run(Path(tmp))

            result = handle_video_creation_reply(run_dir, "修改镜头03，突出编织纹理", now=datetime(2026, 6, 25, 16, 23, 0))

            self.assertEqual(result.status, "storyboard_revised")
            self.assertEqual(result.phase, "awaiting_storyboard_confirmation")
            storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
            shot_03 = next(item for item in storyboard["shots"] if item["shot_id"] == "03")
            self.assertIn("编织纹理", shot_03["change_requests"][0]["request"])

    def test_mock_full_chain_from_natural_language_replies_to_final_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))

            handle_video_creation_reply(run_dir, "生成策划", now=datetime(2026, 6, 25, 15, 0, 0))
            handle_video_creation_reply(run_dir, "确认策划", now=datetime(2026, 6, 25, 15, 1, 0))
            handle_video_creation_reply(run_dir, "生成分镜", now=datetime(2026, 6, 25, 15, 2, 0))
            handle_video_creation_reply(run_dir, "确认分镜", now=datetime(2026, 6, 25, 15, 3, 0))
            handle_video_creation_reply(run_dir, "生成旁白文案", now=datetime(2026, 6, 25, 15, 4, 0))
            handle_video_creation_reply(run_dir, "确认旁白文案", now=datetime(2026, 6, 25, 15, 5, 0))
            handle_video_creation_reply(run_dir, "生成声音样本", now=datetime(2026, 6, 25, 15, 6, 0))
            handle_video_creation_reply(run_dir, "声音选 2", now=datetime(2026, 6, 25, 15, 7, 0))
            handle_video_creation_reply(run_dir, "生成完整旁白", now=datetime(2026, 6, 25, 15, 8, 0))
            handle_video_creation_reply(run_dir, "确认旁白", now=datetime(2026, 6, 25, 15, 9, 0))
            handle_video_creation_reply(run_dir, "规划即梦任务", now=datetime(2026, 6, 25, 15, 10, 0))
            handle_video_creation_reply(run_dir, "确认即梦生成", now=datetime(2026, 6, 25, 15, 11, 0))
            handle_video_creation_reply(run_dir, "提交即梦任务", now=datetime(2026, 6, 25, 15, 12, 0))
            handle_video_creation_reply(run_dir, "查询即梦结果", now=datetime(2026, 6, 25, 15, 13, 0))
            handle_video_creation_reply(run_dir, "确认镜头", now=datetime(2026, 6, 25, 15, 14, 0))
            handle_video_creation_reply(run_dir, "生成成片预览", now=datetime(2026, 6, 25, 15, 15, 0))

            bgm_path = run_dir / "audio" / "licensed_bgm.mp3"
            bgm_path.write_bytes(b"fake bgm")
            select_bgm_track(
                run_dir,
                title="Industrial Clean Pulse",
                source="Licensed internal music provider",
                license_name="commercial-use",
                local_path=bgm_path,
                now=datetime(2026, 6, 25, 15, 16, 0),
            )
            handle_video_creation_reply(run_dir, "生成成片预览", now=datetime(2026, 6, 25, 15, 17, 0))
            preview = run_dir / "dreamina_generation" / "final_preview.mp4"
            preview.write_bytes(b"fake mp4 for workflow contract")
            handle_video_creation_reply(run_dir, "运行质量门禁", now=datetime(2026, 6, 25, 15, 18, 0))
            handle_video_creation_reply(run_dir, "人工音视频检查通过", now=datetime(2026, 6, 25, 15, 19, 0))
            final = handle_video_creation_reply(run_dir, "确认成片", now=datetime(2026, 6, 25, 15, 20, 0))

            self.assertEqual(final.status, "final_video_confirmed")
            self.assertEqual(final.phase, "completed")
            final_path = Path(final.output_paths[0])
            self.assertTrue(final_path.exists())
            self.assertNotIn("master", final_path.name.lower())
            self.assertNotIn("母版", final_path.name)
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["final_video"])
            self.assertIsNone(state["current_pending_confirmation"])

    def test_assembles_final_preview_contract_with_short_sentence_subtitles_and_bgm_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_shots_confirmed_run(Path(tmp))

            result = assemble_final_preview(run_dir, now=datetime(2026, 6, 25, 16, 0, 0))

            self.assertEqual(result.status, "final_preview_ready")
            self.assertEqual(result.phase, "ready_for_quality_gate")
            manifest_json = run_dir / "dreamina_generation" / "final_preview_manifest.json"
            subtitles_srt = run_dir / "subtitles" / "final_subtitles.srt"
            bgm_license = run_dir / "audio" / "bgm_license.json"
            self.assertTrue(manifest_json.exists())
            self.assertTrue(subtitles_srt.exists())
            self.assertTrue(bgm_license.exists())
            manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "dry_run_ready")
            self.assertEqual(manifest["preview_path"], str(run_dir / "dreamina_generation" / "final_preview.mp4"))
            self.assertTrue(manifest["subtitles_burned_in"])
            self.assertFalse(manifest["bgm_embedded"])
            self.assertEqual(manifest["logo_status"], "missing_or_not_configured")
            self.assertEqual(manifest["duration_tolerance_seconds"], {"min": 55, "max": 65})
            subtitle_blocks = [block for block in subtitles_srt.read_text(encoding="utf-8").split("\n\n") if block.strip()]
            self.assertEqual(len(subtitle_blocks), 12)
            for block in subtitle_blocks:
                self.assertLessEqual(len(block.splitlines()[2:]), 2)
            bgm = json.loads(bgm_license.read_text(encoding="utf-8"))
            self.assertTrue(bgm["music_policy"]["commercially_usable_required"])
            self.assertTrue(bgm["music_policy"]["do_not_use_tiktok_trending_song"])
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["current_pending_confirmation"], "运行质量门禁")

    def test_quality_gate_blocks_dry_run_without_real_preview_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_final_preview_contract_run(Path(tmp))

            result = run_quality_gate(run_dir, now=datetime(2026, 6, 25, 16, 5, 0))

            self.assertEqual(result.status, "quality_gate_failed")
            self.assertEqual(result.phase, "ready_for_quality_gate")
            report = json.loads((run_dir / "quality_report.json").read_text(encoding="utf-8"))
            codes = {item["code"] for item in report["blocking_defects"]}
            self.assertIn("missing_final_preview_mp4", codes)
            self.assertIn("dry_run_preview_only", codes)
            self.assertIn("bgm_track_not_selected", codes)
            self.assertIn("bgm_not_embedded", codes)
            self.assertTrue(report["checks"]["creative_quality_matrix_checked"])
            self.assertTrue(report["checks"]["prompt_standard_checked"])
            self.assertTrue(report["checks"]["dreamina_job_validation_checked"])
            with self.assertRaisesRegex(ValueError, "当前阶段是 'ready_for_quality_gate'"):
                record_manual_quality_check(run_dir, audio_ok=True, visual_ok=True)

    def test_quality_gate_reports_prompt_conflicts_and_duration_complexity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_final_preview_contract_run(Path(tmp))
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

            run_quality_gate(run_dir, now=datetime(2026, 6, 25, 16, 5, 0))

            report = json.loads((run_dir / "quality_report.json").read_text(encoding="utf-8"))
            codes = {item["code"] for item in report["blocking_defects"]}
            self.assertIn("fixed_camera_conflicts_with_dynamic_camera", codes)
            self.assertIn("scene_change_complexity_exceeds_duration", codes)

    def test_manual_quality_check_and_final_confirmation_after_preview_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_final_preview_contract_run(Path(tmp))
            preview = run_dir / "dreamina_generation" / "final_preview.mp4"
            preview.write_bytes(b"fake mp4 for workflow contract")
            bgm_path = run_dir / "audio" / "licensed_bgm.mp3"
            bgm_path.write_bytes(b"fake bgm")
            bgm = select_bgm_track(
                run_dir,
                title="Industrial Clean Pulse",
                source="Licensed internal music provider",
                license_name="commercial-use",
                local_path=bgm_path,
                license_url="https://license.example/bgm",
                now=datetime(2026, 6, 25, 16, 2, 0),
            )
            self.assertEqual(bgm.status, "final_preview_ready")
            assemble_final_preview(run_dir, now=datetime(2026, 6, 25, 16, 3, 0))

            gate = run_quality_gate(run_dir, now=datetime(2026, 6, 25, 16, 5, 0))
            self.assertEqual(gate.status, "quality_gate_passed")
            self.assertEqual(gate.phase, "awaiting_manual_quality_check")
            report = json.loads((run_dir / "quality_report.json").read_text(encoding="utf-8"))
            warning_codes = {item["code"] for item in report["warnings"]}
            self.assertIn("logo_missing_or_not_configured", warning_codes)
            self.assertTrue(report["checks"]["creative_quality_matrix_checked"])
            self.assertTrue(report["checks"]["prompt_standard_checked"])
            self.assertTrue(report["checks"]["dreamina_job_validation_checked"])

            manual = record_manual_quality_check(
                run_dir,
                audio_ok=True,
                visual_ok=True,
                notes="人工打开剪辑软件检查，音频与字幕同步。",
                now=datetime(2026, 6, 25, 16, 10, 0),
            )
            self.assertEqual(manual.status, "manual_quality_check_confirmed")
            self.assertEqual(manual.phase, "awaiting_final_video_confirmation")

            final = confirm_final_video(run_dir, now=datetime(2026, 6, 25, 16, 15, 0))
            self.assertEqual(final.status, "final_video_confirmed")
            self.assertEqual(final.phase, "completed")
            final_path = run_dir / "quartz_fiber_tape_en_9x16.mp4"
            self.assertTrue(final_path.exists())
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["confirmations"]["final_video"])
            self.assertEqual(state["files"]["final_video"], str(final_path))

    def test_bgm_replacement_reply_clears_manual_check_without_rebuilding_upstream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_final_preview_contract_run(Path(tmp))
            preview = run_dir / "dreamina_generation" / "final_preview.mp4"
            preview.write_bytes(b"fake mp4 for workflow contract")
            bgm_path = run_dir / "audio" / "licensed_bgm.mp3"
            bgm_path.write_bytes(b"fake bgm")
            select_bgm_track(
                run_dir,
                title="Industrial Clean Pulse",
                source="Licensed internal music provider",
                license_name="commercial-use",
                local_path=bgm_path,
                now=datetime(2026, 6, 25, 16, 2, 0),
            )
            assemble_final_preview(run_dir, now=datetime(2026, 6, 25, 16, 3, 0))
            run_quality_gate(run_dir, now=datetime(2026, 6, 25, 16, 5, 0))
            record_manual_quality_check(run_dir, audio_ok=True, visual_ok=True, now=datetime(2026, 6, 25, 16, 10, 0))

            result = handle_video_creation_reply(run_dir, "更换背景音乐", now=datetime(2026, 6, 25, 16, 12, 0))

            self.assertEqual(result.status, "bgm_replacement_requested")
            self.assertEqual(result.phase, "ready_for_quality_gate")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertNotIn("manual_quality_check", state)
            self.assertTrue(state["confirmations"]["storyboard"])
            self.assertTrue(state["confirmations"]["narration"])
            self.assertTrue(state["confirmations"]["shots"])
            self.assertEqual(state["current_pending_confirmation"], "选择新的可商用 BGM 并重新生成成片预览")

    def test_handles_manual_quality_pass_reply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_final_preview_contract_run(Path(tmp))
            preview = run_dir / "dreamina_generation" / "final_preview.mp4"
            preview.write_bytes(b"fake mp4 for workflow contract")
            bgm_path = run_dir / "audio" / "licensed_bgm.mp3"
            bgm_path.write_bytes(b"fake bgm")
            select_bgm_track(
                run_dir,
                title="Industrial Clean Pulse",
                source="Licensed internal music provider",
                license_name="commercial-use",
                local_path=bgm_path,
                now=datetime(2026, 6, 25, 16, 2, 0),
            )
            assemble_final_preview(run_dir, now=datetime(2026, 6, 25, 16, 3, 0))
            run_quality_gate(run_dir, now=datetime(2026, 6, 25, 16, 5, 0))

            result = handle_video_creation_reply(run_dir, "人工音视频检查通过", now=datetime(2026, 6, 25, 16, 10, 0))

            self.assertEqual(result.status, "manual_quality_check_confirmed")
            self.assertEqual(result.phase, "awaiting_final_video_confirmation")
            state = json.loads((run_dir / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["manual_quality_check"]["audio_ok"])
            self.assertTrue(state["manual_quality_check"]["visual_ok"])

    def test_select_bgm_track_requires_existing_local_commercial_track_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_final_preview_contract_run(Path(tmp))

            with self.assertRaisesRegex(ValueError, "必须填写"):
                select_bgm_track(run_dir, title="", source="Provider", license_name="commercial", local_path=run_dir / "audio" / "x.mp3")
            with self.assertRaisesRegex(ValueError, "找不到 BGM 本地文件"):
                select_bgm_track(run_dir, title="Track", source="Provider", license_name="commercial", local_path=run_dir / "audio" / "missing.mp3")

            bgm_path = run_dir / "audio" / "licensed_bgm.mp3"
            bgm_path.write_bytes(b"fake bgm")
            result = select_bgm_track(
                run_dir,
                title="Track",
                source="Provider",
                license_name="commercial-use",
                local_path=bgm_path,
                now=datetime(2026, 6, 25, 16, 2, 0),
            )
            self.assertEqual(result.phase, "ready_for_quality_gate")
            payload = json.loads((run_dir / "audio" / "bgm_license.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "selected")
            self.assertEqual(payload["selected_track"]["local_path"], str(bgm_path.resolve()))

    def test_inspects_video_creation_adapters_without_paid_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_ready_run(Path(tmp))

            result = inspect_video_creation_adapters(run_dir, now=datetime(2026, 6, 25, 16, 20, 0))

            self.assertEqual(result.status, "requirements_confirmed")
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
                "platforms": ["tiktok"],
                "duration_seconds": 60,
                "primary_direction": "产品总览型",
            }
            with self.assertRaisesRegex(ValueError, "视频语言版本只支持"):
                create_video_creation_run(**{**base, "language_version": "fr"})
            with self.assertRaisesRegex(ValueError, "视频平台只支持"):
                create_video_creation_run(**{**base, "platforms": ["linkedin"]})
            with self.assertRaisesRegex(ValueError, "视频时长只支持"):
                create_video_creation_run(**{**base, "duration_seconds": 30})
            with self.assertRaisesRegex(ValueError, "创意方向必须从固定 16 个视频创意方向中选择"):
                create_video_creation_run(**{**base, "primary_direction": "车间介绍型"})

    def test_fixed_creative_direction_taxonomy_has_sixteen_items(self) -> None:
        self.assertEqual(len(VIDEO_CREATIVE_DIRECTIONS), 16)
        self.assertEqual(VIDEO_CREATIVE_DIRECTIONS[0]["id"], "product_overview")
        self.assertEqual(VIDEO_CREATIVE_DIRECTIONS[-1]["id"], "inquiry_conversion")


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
            "evidence_refs: []",
            "review_refs: []",
            "product_line: 耐高温隔热带",
            "related_refs: []",
        ],
        "石英纤维隔热带是首期视频创作产品。",
    )
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
            "updated_at: 2026-06-25T00:00:00+08:00",
            "last_reviewed_at: 2026-06-25T00:00:00+08:00",
            "evidence_refs: []",
            "review_refs: []",
            "asset_category: 产品图片",
            "media_types:",
            "  - image",
            f"human_face_risk: {human_face_risk}",
            "related_products:",
            "  - product/quartz_fiber_tape",
            "files:",
            "  - raw/01_产品/02_石英纤维隔热带/02_产品图片/product.jpg",
            "usable_for:",
            "  - video_creation",
        ],
        "可用于视频创作的产品素材；不能单独证明产品性能事实。",
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


def _create_ready_run(root: Path, tts_provider: str = "mock", tts_command: str = "") -> Path:
    config = {}
    if tts_provider != "mock" or tts_command:
        config = {"video_creation": {"tts_provider": tts_provider, "tts_command": tts_command}}
    paths = resolve_paths(root, config)
    initialize_project(paths)
    _write_official_cards(paths)
    rebuild_agent_interface(paths)
    result = create_video_creation_run(
        paths,
        "做一个60秒石英纤维隔热带产品介绍视频，面向欧美工业采购商，用在 YouTube Shorts 和 TikTok。",
        language_version="en",
        platforms=["youtube_shorts", "tiktok"],
        duration_seconds=60,
        target_audience="欧美工业采购商",
        core_objective="突出耐高温、隔热、不刺痒和不冒烟",
        primary_direction="3",
        supporting_direction="产品细节型",
        now=datetime(2026, 6, 25, 14, 30, 5),
    )
    return Path(result.run_dir)


def _create_plan_confirmed_run(root: Path, tts_provider: str = "mock", tts_command: str = "") -> Path:
    run_dir = _create_ready_run(root, tts_provider=tts_provider, tts_command=tts_command)
    generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))
    confirm_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 5, 0))
    return run_dir


def _create_storyboard_confirmed_run(root: Path, tts_provider: str = "mock", tts_command: str = "") -> Path:
    run_dir = _create_plan_confirmed_run(root, tts_provider=tts_provider, tts_command=tts_command)
    generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))
    confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))
    return run_dir


def _create_narration_script_confirmed_run(root: Path, tts_provider: str = "mock", tts_command: str = "") -> Path:
    run_dir = _create_storyboard_confirmed_run(root, tts_provider=tts_provider, tts_command=tts_command)
    generate_narration_script(run_dir, now=datetime(2026, 6, 25, 15, 20, 0))
    confirm_narration_script(run_dir, now=datetime(2026, 6, 25, 15, 21, 0))
    return run_dir


def _create_voice_selected_run(root: Path) -> Path:
    run_dir = _create_narration_script_confirmed_run(root)
    generate_voice_samples(run_dir, now=datetime(2026, 6, 25, 15, 22, 0))
    select_voice(run_dir, 2, now=datetime(2026, 6, 25, 15, 23, 0))
    return run_dir


def _create_narration_confirmed_run(root: Path) -> Path:
    run_dir = _create_voice_selected_run(root)
    generate_full_narration(run_dir, now=datetime(2026, 6, 25, 15, 24, 0))
    confirm_narration(run_dir, now=datetime(2026, 6, 25, 15, 25, 0))
    return run_dir


def _create_dreamina_jobs_ready_run(root: Path) -> Path:
    run_dir = _create_narration_confirmed_run(root)
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


def _create_final_preview_contract_run(root: Path) -> Path:
    run_dir = _create_shots_confirmed_run(root)
    assemble_final_preview(run_dir, now=datetime(2026, 6, 25, 16, 0, 0))
    return run_dir


def _create_narration_confirmed_run_without_assets(root: Path) -> Path:
    paths = resolve_paths(root, {})
    initialize_project(paths)
    _write_product_card_only(paths)
    rebuild_agent_interface(paths)
    result = create_video_creation_run(
        paths,
        "做一个60秒石英纤维隔热带产品介绍视频，面向欧美工业采购商，用在 YouTube Shorts 和 TikTok。",
        language_version="en",
        platforms=["youtube_shorts", "tiktok"],
        duration_seconds=60,
        target_audience="欧美工业采购商",
        core_objective="突出耐高温、隔热、不刺痒和不冒烟",
        primary_direction="3",
        supporting_direction="产品细节型",
        now=datetime(2026, 6, 25, 14, 30, 5),
    )
    run_dir = Path(result.run_dir)
    generate_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 0, 0))
    confirm_video_plan(run_dir, now=datetime(2026, 6, 25, 15, 5, 0))
    generate_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 10, 0))
    confirm_storyboard(run_dir, now=datetime(2026, 6, 25, 15, 15, 0))
    generate_narration_script(run_dir, now=datetime(2026, 6, 25, 15, 20, 0))
    confirm_narration_script(run_dir, now=datetime(2026, 6, 25, 15, 21, 0))
    generate_voice_samples(run_dir, now=datetime(2026, 6, 25, 15, 22, 0))
    select_voice(run_dir, 2, now=datetime(2026, 6, 25, 15, 23, 0))
    generate_full_narration(run_dir, now=datetime(2026, 6, 25, 15, 24, 0))
    confirm_narration(run_dir, now=datetime(2026, 6, 25, 15, 25, 0))
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


def _completed(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import hashlib
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scripts.tuolin_marketplace.agent_interface import rebuild_agent_interface
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths
from scripts.tuolin_marketplace.video_planning_agent import (
    PLANNING_BRIEF_FIELDS,
    apply_video_shot_plan_revision,
    authorize_video_profile_for_planning_run,
    confirm_video_shot_plan,
    create_video_planning_run,
    extract_video_planning_preview,
    handle_video_planning_reply,
    propose_video_planning_decision,
    read_video_planning_asset_audit,
    write_video_shot_plan,
)


class VideoPlanningAgentTests(unittest.TestCase):
    def test_entrypoint_migrates_old_snapshot_and_loads_sales_expression_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _, _ = _project_with_image(Path(tmp))
            _write_card(
                paths,
                "sales_material",
                "sales_material/quartz_wording",
                "石英纤维隔热带销售话术",
                extra={
                    "material_type": "销售话术",
                    "language": "中文",
                    "related_products": ["product/quartz_fiber_tape"],
                },
            )
            rebuild_agent_interface(paths)
            for agent_id in ("tuolin-video-planner", "tuolin-avatar-video"):
                root = paths.generated_dir / "agent-interfaces" / agent_id
                manifest_path = root / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["card_types"].remove("sales_material")
                manifest["policy"].pop("sales_material_role", None)
                manifest["policy"].pop("sales_materials_prove_product_facts", None)
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
                (root / "cards" / "sales_material.json").unlink()

            run = create_video_planning_run(
                paths,
                "为采购商策划一个中文短视频",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                invoked_skill="$tuolin-video-planner",
                duration_seconds=15,
            )

            state = json.loads((Path(run.run_dir) / "workflow_state.json").read_text(encoding="utf-8"))
            references = state["sales_expression_references"]
            self.assertEqual([item["card_id"] for item in references], ["sales_material/quartz_wording"])
            self.assertEqual(references[0]["knowledge_role"], "expression_reference")
            self.assertFalse(references[0]["may_prove_product_facts"])

    def test_sales_material_is_readable_but_cannot_be_used_as_fact_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _, _ = _project_with_image(Path(tmp))
            _write_card(
                paths,
                "sales_material",
                "sales_material/quartz_wording",
                "石英纤维隔热带销售话术",
                extra={
                    "material_type": "销售话术",
                    "language": "中文",
                    "related_products": ["product/quartz_fiber_tape"],
                },
            )
            rebuild_agent_interface(paths)
            evidence = _complete_evidence()
            evidence["priority_messages"] = [{"card_id": "sales_material/quartz_wording"}]

            with self.assertRaisesRegex(ValueError, "销售话术只能作为表达参考"):
                create_video_planning_run(
                    paths,
                    "为采购商策划一个中文短视频",
                    product_id="product/quartz_fiber_tape",
                    platforms=["youtube_shorts"],
                    language_version="zh",
                    invoked_skill="$tuolin-video-planner",
                    duration_seconds=15,
                    initial_decisions=_complete_decisions(),
                    initial_decision_evidence=evidence,
                )

    def test_image_only_run_confirms_plan_and_generates_srt_without_provider_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, source, preview = _project_with_image(Path(tmp))
            result = create_video_planning_run(
                paths,
                "为采购商策划一个中文短视频",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts", "tiktok"],
                language_version="zh",
                invoked_skill="$tuolin-video-planner",
                duration_seconds=15,
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
                now=datetime(2026, 7, 28, 12, 0, 0),
            )
            run_dir = Path(result.run_dir)

            draft = write_video_shot_plan(run_dir, _image_plan(source, preview))
            self.assertEqual(draft.phase, "awaiting_shot_plan_confirmation")
            self.assertFalse((run_dir / "storyboard.srt").exists())
            self.assertIn(str(source), draft.message)
            self.assertIn(str(preview), draft.message)
            self.assertIn("风险检查", draft.message)
            self.assertIn(str(preview), draft.output_paths)

            confirmed = confirm_video_shot_plan(run_dir)
            self.assertEqual(confirmed.status, "completed")
            srt = (run_dir / "storyboard.srt").read_text(encoding="utf-8")
            self.assertIn("00:00:00,000 --> 00:00:15,000", srt)
            self.assertIn("看清隔热带如何贴合并固定在排烟管表面", srt)
            self.assertTrue((run_dir / "revisions" / "revision_0001" / "storyboard.srt").is_file())
            forbidden = {"prompts.md", "prompts.json", "dreamina_tasks.json", "assembled.mp4"}
            self.assertFalse(forbidden & {item.name for item in run_dir.iterdir()})

    def test_image_source_must_be_declared_by_the_asset_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _, preview = _project_with_image(Path(tmp))
            unrelated = paths.raw_dir / "fixtures" / "unrelated.png"
            unrelated.write_bytes(b"unrelated-image")
            run = create_video_planning_run(
                paths,
                "策划视频",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                invoked_skill="$tuolin-video-planner",
                duration_seconds=15,
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
            )

            with self.assertRaisesRegex(ValueError, "未由素材卡声明"):
                write_video_shot_plan(run.run_dir, _image_plan(unrelated, preview))

    def test_provider_fields_are_rejected_even_when_nested_inside_a_shot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, source, preview = _project_with_image(Path(tmp))
            run = create_video_planning_run(
                paths,
                "策划视频",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                duration_seconds=15,
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
                invoked_skill="$tuolin-video-planner",
            )
            plan = _image_plan(source, preview)
            plan["shots"][0]["dreamina_prompt"] = "provider prompt"

            with self.assertRaisesRegex(ValueError, "超出视频策划 Agent 边界"):
                write_video_shot_plan(run.run_dir, plan)

    def test_completed_run_revision_invalidates_srt_until_reconfirmed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, source, preview = _project_with_image(Path(tmp))
            run = create_video_planning_run(
                paths,
                "策划视频",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                invoked_skill="$tuolin-video-planner",
                duration_seconds=15,
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
                now=datetime(2026, 7, 28, 12, 1, 0),
            )
            root = Path(run.run_dir)
            write_video_shot_plan(root, _image_plan(source, preview))
            confirm_video_shot_plan(root)
            revised = _image_plan(source, preview)
            revised["shots"][0]["visual_action"] = "近景展示隔热带均匀缠绕后的表面状态"
            apply_video_shot_plan_revision(root, revised)

            self.assertFalse((root / "storyboard.srt").exists())
            state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["phase"], "awaiting_shot_plan_confirmation")
            self.assertEqual(state["current_revision"], 2)
            confirm_video_shot_plan(root)
            self.assertTrue((root / "revisions" / "revision_0002" / "storyboard.srt").is_file())

    def test_invalid_revision_preserves_current_completed_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, source, preview = _project_with_image(Path(tmp))
            run = create_video_planning_run(
                paths,
                "策划视频",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                invoked_skill="$tuolin-video-planner",
                duration_seconds=15,
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
            )
            root = Path(run.run_dir)
            write_video_shot_plan(root, _image_plan(source, preview))
            confirm_video_shot_plan(root)
            srt_before = (root / "storyboard.srt").read_bytes()
            plan_before = (root / "shot_plan.json").read_bytes()

            invalid = _image_plan(source, preview)
            invalid["shots"][0]["duration_seconds"] = 14
            with self.assertRaisesRegex(ValueError, "时间轴不连续"):
                apply_video_shot_plan_revision(root, invalid)

            self.assertEqual((root / "storyboard.srt").read_bytes(), srt_before)
            self.assertEqual((root / "shot_plan.json").read_bytes(), plan_before)
            state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["phase"], "completed")
            self.assertTrue(state["confirmations"]["shot_plan"])

    def test_confirmation_restores_protected_fields_from_run_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, source, preview = _project_with_image(Path(tmp))
            run = create_video_planning_run(
                paths,
                "策划视频",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                duration_seconds=15,
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
                invoked_skill="$tuolin-video-planner",
            )
            root = Path(run.run_dir)
            write_video_shot_plan(root, _image_plan(source, preview))
            path = root / "shot_plan.json"
            plan = json.loads(path.read_text(encoding="utf-8"))
            plan.update(
                {
                    "product_title": "被篡改产品",
                    "platforms": ["unsupported"],
                    "aspect_ratio": "16:9",
                    "interface_revision": "stale",
                }
            )
            path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

            confirm_video_shot_plan(root)
            confirmed = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(confirmed["product_title"], "石英纤维隔热带")
            self.assertEqual(confirmed["platforms"], ["youtube_shorts"])
            self.assertEqual(confirmed["aspect_ratio"], "9:16")
            self.assertNotEqual(confirmed["interface_revision"], "stale")

    def test_confirmation_conflict_does_not_partially_mark_draft_as_confirmed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, source, preview = _project_with_image(Path(tmp))
            run = create_video_planning_run(
                paths,
                "策划视频",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                duration_seconds=15,
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
                invoked_skill="$tuolin-video-planner",
            )
            root = Path(run.run_dir)
            write_video_shot_plan(root, _image_plan(source, preview))
            (root / "revisions" / "revision_0001").mkdir()

            with self.assertRaisesRegex(ValueError, "修订目录已存在"):
                confirm_video_shot_plan(root)

            plan = json.loads((root / "shot_plan.json").read_text(encoding="utf-8"))
            state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["status"], "draft_pending_confirmation")
            self.assertEqual(state["phase"], "awaiting_shot_plan_confirmation")
            self.assertFalse((root / "storyboard.srt").exists())

    def test_explicit_invocation_and_scope_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _, _ = _project_with_image(Path(tmp))
            common = dict(
                paths=paths,
                request_text="策划视频",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                invoked_skill="$tuolin-video-planner",
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
            )
            common["invoked_skill"] = "$tuolin-video-planner"
            without_invocation = {key: value for key, value in common.items() if key != "invoked_skill"}
            with self.assertRaisesRegex(ValueError, "显式调用"):
                create_video_planning_run(**without_invocation)
            with self.assertRaisesRegex(ValueError, "显式调用"):
                create_video_planning_run(**{**common, "invoked_skill": "$tuolin-video-workflow"})
            with self.assertRaisesRegex(ValueError, "15–90"):
                create_video_planning_run(**common, duration_seconds=91)
            with self.assertRaisesRegex(ValueError, "只支持"):
                create_video_planning_run(**{**common, "platforms": ["instagram_reels"]})

    def test_interview_asks_one_decision_and_never_has_trend_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _, _ = _project_with_image(Path(tmp))
            run = create_video_planning_run(
                paths,
                "先访谈",
                product_id="product/quartz_fiber_tape",
                platforms=["tiktok"],
                language_version="en",
                invoked_skill="$tuolin-video-planner",
            )
            proposal = {
                "decision_key": "audience",
                "question": "这条视频最需要说服谁？",
                "recommendation": "工业设备采购商",
                "reason": "他们直接决定是否进入询盘。",
                "inference": True,
            }
            propose_video_planning_decision(run.run_dir, proposal)
            interview = json.loads((Path(run.run_dir) / "interview.json").read_text(encoding="utf-8"))
            self.assertEqual(interview["current_field"], "audience")
            self.assertNotIn("trend", " ".join((*PLANNING_BRIEF_FIELDS, *interview)))
            with self.assertRaisesRegex(ValueError, "已有一个"):
                propose_video_planning_decision(run.run_dir, proposal)

            handle_video_planning_reply(run.run_dir, "按推荐")
            interview = json.loads((Path(run.run_dir) / "interview.json").read_text(encoding="utf-8"))
            self.assertEqual(interview["decisions"]["audience"], "工业设备采购商")
            self.assertEqual(interview["decision_sources"]["audience"], "planning_inference")

    def test_fact_evidence_must_belong_to_the_planned_product(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _, _ = _project_with_image(Path(tmp))
            _write_card(paths, "product", "product/unrelated", "无关产品")
            rebuild_agent_interface(paths)
            evidence = _complete_evidence()
            evidence["priority_messages"] = [{"card_id": "product/unrelated"}]

            with self.assertRaisesRegex(ValueError, "事实证据不属于当前产品"):
                create_video_planning_run(
                    paths,
                    "策划视频",
                    product_id="product/quartz_fiber_tape",
                    platforms=["youtube_shorts"],
                    language_version="zh",
                    invoked_skill="$tuolin-video-planner",
                    initial_decisions=_complete_decisions(),
                    initial_decision_evidence=evidence,
                )

    def test_explicit_all_remaining_authorization_accepts_a_complete_recommendation_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _, _ = _project_with_image(Path(tmp))
            run = create_video_planning_run(
                paths,
                "你来访谈",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                invoked_skill="$tuolin-video-planner",
            )
            propose_video_planning_decision(
                run.run_dir,
                {
                    "decision_key": "audience",
                    "question": "这条视频最需要说服谁？",
                    "recommendation": "工业设备采购商",
                    "reason": "他们负责选型。",
                    "inference": True,
                },
            )
            bundle = {
                key: {
                    "recommendation": value,
                    "reason": "基于当前业务目标与正式知识。",
                    "evidence": _complete_evidence().get(key, []),
                    "inference": key not in _complete_evidence(),
                }
                for key, value in _complete_decisions().items()
                if key != "audience"
            }

            result = handle_video_planning_reply(
                run.run_dir,
                "剩下都按推荐",
                remaining_recommendations=bundle,
            )

            self.assertEqual(result.phase, "ready_for_shot_plan")
            interview = json.loads((Path(run.run_dir) / "interview.json").read_text(encoding="utf-8"))
            self.assertTrue(interview["completed"])
            self.assertEqual(interview["decisions"]["audience"], "工业设备采购商")

    def test_video_preview_is_bounded_to_authorized_catalog_segment_and_always_muted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _, _ = _project_with_image(Path(tmp))
            run = create_video_planning_run(
                paths,
                "用已处理视频资产策划",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                invoked_skill="$tuolin-video-planner",
                duration_seconds=15,
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
                now=datetime(2026, 7, 28, 12, 2, 0),
            )
            profile_id = _install_video_profile_fixture(paths)
            authorize_video_profile_for_planning_run(paths, Path(run.run_dir).name, profile_id)
            calls = []

            def runner(command, **kwargs):
                calls.append(command)
                Path(command[-1]).write_bytes(b"muted-preview")
                return subprocess.CompletedProcess(command, 0, "", "")

            for _ in range(3):
                result = extract_video_planning_preview(
                    paths,
                    run_id=Path(run.run_dir).name,
                    profile_id=profile_id,
                    segment_id="segment_01",
                    planned_use_id="installation_hook",
                    start_seconds=1,
                    end_seconds=3,
                    runner=runner,
                )
                self.assertTrue(result.audio_removed)
            self.assertTrue(all("-an" in command for command in calls))
            self.assertTrue(all("scale=540:960" in command[command.index("-vf") + 1] for command in calls))
            plan = _base_single_shot_plan()
            plan["shots"][0]["material"] = {
                "mode": "real_video_segment",
                "profile_id": profile_id,
                "segment_id": "segment_01",
                "planned_use_id": "installation_hook",
                "source_start_seconds": 1,
                "source_end_seconds": 3,
                "preview_path": result.preview_path,
                "original_audio_used": False,
                "confirmable": True,
            }
            plan["shots"][0]["material"]["evidence_use"] = True
            with self.assertRaisesRegex(
                ValueError,
                "不能作为耐温、隔热、安全或认证结论的证据",
            ):
                write_video_shot_plan(run.run_dir, plan)
            plan["shots"][0]["material"]["evidence_use"] = False
            draft = write_video_shot_plan(run.run_dir, plan)
            stored = json.loads((Path(run.run_dir) / "shot_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["shots"][0]["material"]["video_asset_id"], "video_asset_fixture")
            self.assertFalse(
                stored["shots"][0]["material"]["usage_policy"][
                    "may_support_external_claims"
                ]
            )
            self.assertIn(
                "画面可以剪进 YouTube Shorts 和 TikTok 成片；必须删除原声；"
                "不能用画面证明耐温、隔热、安全或认证；最终发布前仍需人工确认。",
                draft.message,
            )
            Path(result.preview_path).write_bytes(b"tampered-preview")
            with self.assertRaisesRegex(ValueError, "预览内容指纹"):
                write_video_shot_plan(run.run_dir, plan)
            with self.assertRaisesRegex(ValueError, "最多生成三个"):
                extract_video_planning_preview(
                    paths,
                    run_id=Path(run.run_dir).name,
                    profile_id=profile_id,
                    segment_id="segment_01",
                    planned_use_id="installation_hook",
                    start_seconds=1,
                    end_seconds=3,
                    runner=runner,
                )
            with self.assertRaisesRegex(PermissionError, "授权范围"):
                extract_video_planning_preview(
                    paths,
                    run_id=Path(run.run_dir).name,
                    profile_id=profile_id,
                    segment_id="unknown",
                    planned_use_id="another_use",
                    start_seconds=1,
                    end_seconds=3,
                    runner=runner,
                )
            audit = read_video_planning_asset_audit(paths, Path(run.run_dir).name)
            rejected = [item for item in audit if item.get("status") == "rejected"]
            self.assertTrue(any("最多生成三个" in str(item.get("reason")) for item in rejected))
            self.assertTrue(any(item.get("segment_id") == "unknown" for item in rejected))

    def test_internal_only_video_cannot_be_authorized_for_external_shot_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _, _ = _project_with_image(Path(tmp))
            run = create_video_planning_run(
                paths,
                "为 YouTube Shorts 策划公开视频",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                invoked_skill="$tuolin-video-planner",
                duration_seconds=15,
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
            )
            profile_id = _install_video_profile_fixture(
                paths,
                visual_usage_scope="internal_only",
            )

            with self.assertRaisesRegex(
                PermissionError,
                "任何片段都不能剪进 YouTube、TikTok 或发送给客户的视频",
            ):
                authorize_video_profile_for_planning_run(
                    paths,
                    Path(run.run_dir).name,
                    profile_id,
                )

    def test_unrelated_interface_refresh_does_not_block_final_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, source, preview = _project_with_image(Path(tmp))
            run = create_video_planning_run(
                paths,
                "策划视频",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                invoked_skill="$tuolin-video-planner",
                duration_seconds=15,
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
            )
            write_video_shot_plan(run.run_dir, _image_plan(source, preview))
            _write_card(paths, "product", "product/unrelated", "无关产品")
            rebuild_agent_interface(paths)
            self.assertEqual(confirm_video_shot_plan(run.run_dir).status, "completed")

    def test_video_source_change_blocks_final_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _, _ = _project_with_image(Path(tmp))
            run = create_video_planning_run(
                paths,
                "使用真实视频片段",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                duration_seconds=15,
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
                invoked_skill="$tuolin-video-planner",
            )
            profile_id = _install_video_profile_fixture(paths)
            authorize_video_profile_for_planning_run(paths, Path(run.run_dir).name, profile_id)

            def runner(command, **kwargs):
                Path(command[-1]).write_bytes(b"muted-preview")
                return subprocess.CompletedProcess(command, 0, "", "")

            preview = extract_video_planning_preview(
                paths,
                run_id=Path(run.run_dir).name,
                profile_id=profile_id,
                segment_id="segment_01",
                planned_use_id="installation_hook",
                start_seconds=1,
                end_seconds=3,
                runner=runner,
            )
            plan = _base_single_shot_plan()
            plan["shots"][0]["material"] = {
                "mode": "real_video_segment",
                "profile_id": profile_id,
                "segment_id": "segment_01",
                "planned_use_id": "installation_hook",
                "source_start_seconds": 1,
                "source_end_seconds": 3,
                "preview_path": preview.preview_path,
                "original_audio_used": False,
                "confirmable": True,
            }
            write_video_shot_plan(run.run_dir, plan)
            (paths.raw_dir / "fixtures" / "installation.mp4").write_bytes(b"changed-source")

            with self.assertRaisesRegex(ValueError, "视频源"):
                confirm_video_shot_plan(run.run_dir)

    def test_material_change_blocks_final_confirmation_and_requires_new_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, source, preview = _project_with_image(Path(tmp))
            run = create_video_planning_run(
                paths,
                "策划视频",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                invoked_skill="$tuolin-video-planner",
                duration_seconds=15,
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
            )
            write_video_shot_plan(run.run_dir, _image_plan(source, preview))
            card_path = paths.knowledge_dir / "内容素材" / "quartz_installation.md"
            card_path.write_text(card_path.read_text(encoding="utf-8") + "\n实质变更。\n", encoding="utf-8")
            rebuild_agent_interface(paths)
            with self.assertRaisesRegex(ValueError, "必须新建"):
                confirm_video_shot_plan(run.run_dir)
            state = json.loads((Path(run.run_dir) / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "blocked_stale_reference")
            self.assertIn("必须新建", state["blocker"]["message"])

    def test_selected_image_bytes_change_blocks_final_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, source, preview = _project_with_image(Path(tmp))
            run = create_video_planning_run(
                paths,
                "策划视频",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                duration_seconds=15,
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
                invoked_skill="$tuolin-video-planner",
            )
            write_video_shot_plan(run.run_dir, _image_plan(source, preview))
            source.write_bytes(b"changed-image-bytes")

            with self.assertRaisesRegex(ValueError, "图片内容指纹"):
                confirm_video_shot_plan(run.run_dir)

    def test_revoked_material_blocks_confirmation_with_new_run_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, source, preview = _project_with_image(Path(tmp))
            run = create_video_planning_run(
                paths,
                "策划视频",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                duration_seconds=15,
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
                invoked_skill="$tuolin-video-planner",
            )
            write_video_shot_plan(run.run_dir, _image_plan(source, preview))
            card_path = paths.knowledge_dir / "内容素材" / "quartz_installation.md"
            text = card_path.read_text(encoding="utf-8").replace('status: "official"', 'status: "archived"')
            card_path.write_text(text, encoding="utf-8")
            rebuild_agent_interface(paths)

            with self.assertRaisesRegex(ValueError, "撤销.*必须新建"):
                confirm_video_shot_plan(run.run_dir)

    def test_decision_evidence_change_blocks_final_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, source, preview = _project_with_image(Path(tmp))
            run = create_video_planning_run(
                paths,
                "策划视频",
                product_id="product/quartz_fiber_tape",
                platforms=["youtube_shorts"],
                language_version="zh",
                invoked_skill="$tuolin-video-planner",
                duration_seconds=15,
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
            )
            write_video_shot_plan(run.run_dir, _image_plan(source, preview))
            card_path = paths.knowledge_dir / "应用场景" / "exhaust_pipe_wrap.md"
            card_path.write_text(card_path.read_text(encoding="utf-8") + "\n应用事实发生实质变化。\n", encoding="utf-8")
            rebuild_agent_interface(paths)

            with self.assertRaisesRegex(ValueError, "事实证据.*必须新建"):
                confirm_video_shot_plan(run.run_dir)

    def test_ai_simulation_requires_formal_application_and_cannot_be_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, source, preview = _project_with_image(Path(tmp))
            _write_card(paths, "product", "product/unrelated", "无关产品")
            _write_card(
                paths,
                "content_asset",
                "content_asset/unrelated_product_image",
                "无关产品图片",
                extra={
                    "asset_category": "product_photo",
                    "media_types": ["image"],
                    "related_products": ["product/unrelated"],
                    "usable_for": ["video_planning"],
                },
            )
            rebuild_agent_interface(paths)
            run = create_video_planning_run(
                paths,
                "允许模拟正式应用场景",
                product_id="product/quartz_fiber_tape",
                platforms=["tiktok"],
                language_version="zh",
                invoked_skill="$tuolin-video-planner",
                duration_seconds=15,
                initial_decisions={**_complete_decisions(), "ai_simulation_scope": "允许模拟已确认的排烟管应用场景"},
                initial_decision_evidence=_complete_evidence(),
            )
            plan = _base_single_shot_plan()
            plan["shots"][0]["material"] = {
                "mode": "ai_simulation",
                "application_card_id": "application_scenario/exhaust_pipe_wrap",
                "specific_product_visible": False,
                "evidence_use": True,
            }
            with self.assertRaisesRegex(ValueError, "不得充当证据"):
                write_video_shot_plan(run.run_dir, plan)
            plan["shots"][0]["material"]["evidence_use"] = False
            plan["shots"][0]["material"].update(
                {
                    "specific_product_visible": True,
                    "product_reference_card_id": "content_asset/unrelated_product_image",
                    "product_reference_source_path": str(source),
                    "product_reference_preview_path": str(preview),
                    "product_reference_confirmable": True,
                    "product_reference_inspection": _clear_image_inspection(),
                    "product_reference_risk_checks": _clear_image_risk_checks(),
                }
            )
            with self.assertRaisesRegex(ValueError, "产品参考.*当前产品"):
                write_video_shot_plan(run.run_dir, plan)
            plan["shots"][0]["material"]["product_reference_card_id"] = "content_asset/quartz_installation"
            result = write_video_shot_plan(run.run_dir, plan)
            stored = json.loads((Path(run.run_dir) / "shot_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(result.status, "awaiting_confirmation")
            self.assertTrue(stored["shots"][0]["material"]["simulated"])

    def test_ai_simulation_cannot_bypass_confirmed_no_ai_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _, _ = _project_with_image(Path(tmp))
            run = create_video_planning_run(
                paths,
                "本次不使用 AI 模拟",
                product_id="product/quartz_fiber_tape",
                platforms=["tiktok"],
                language_version="zh",
                invoked_skill="$tuolin-video-planner",
                duration_seconds=15,
                initial_decisions=_complete_decisions(),
                initial_decision_evidence=_complete_evidence(),
            )
            plan = _base_single_shot_plan()
            plan["shots"][0]["material"] = {
                "mode": "ai_simulation",
                "application_card_id": "application_scenario/exhaust_pipe_wrap",
                "specific_product_visible": False,
            }

            with self.assertRaisesRegex(ValueError, "AI 模拟边界"):
                write_video_shot_plan(run.run_dir, plan)


def _complete_decisions() -> dict[str, str]:
    return {
        "audience": "工业设备采购商和经销商",
        "audience_problem_scenario": "需要判断隔热带如何实际缠绕排烟管",
        "viewing_motivation": "快速看懂施工过程和完成状态",
        "viewer_interest_direction": "真实近景操作形成过程证明",
        "intended_takeaway": "该产品可用于已确认的排烟管缠绕应用",
        "desired_action": "用于内部选型讨论",
        "priority_messages": "贴合、拉紧、均匀缠绕和金属固定",
        "excluded_content": "不写未经证实的性能参数和认证",
        "ai_simulation_scope": "本次不使用 AI 模拟",
    }


def _complete_evidence() -> dict[str, list[dict[str, str]]]:
    return {
        "intended_takeaway": [{"card_id": "application_scenario/exhaust_pipe_wrap"}],
        "priority_messages": [{"card_id": "product/quartz_fiber_tape"}],
        "ai_simulation_scope": [{"card_id": "application_scenario/exhaust_pipe_wrap"}],
    }


def _image_plan(source: Path, preview: Path) -> dict:
    plan = _base_single_shot_plan()
    plan["shots"][0]["material"] = {
        "mode": "official_image",
        "card_id": "content_asset/quartz_installation",
        "source_path": str(source),
        "preview_path": str(preview),
        "confirmable": True,
        "inspection": _clear_image_inspection(),
        "risk_checks": _clear_image_risk_checks(),
    }
    return plan


def _clear_image_inspection() -> dict:
    return {
        "subject": "排烟管上的隔热带",
        "clarity": "清晰",
        "composition": "主体集中",
        "vertical_crop": "可裁为 9:16",
        "near_duplicate_of": None,
    }


def _clear_image_risk_checks() -> dict:
    return {
        "product_identity": "clear",
        "rights": "clear",
        "privacy": "clear",
        "test_meaning": "clear",
        "claim_risk": "clear",
    }


def _base_single_shot_plan() -> dict:
    return {
        "shots": [{
                "shot_id": "01",
                "start_seconds": 0,
                "duration_seconds": 15,
                "end_seconds": 15,
                "purpose": "让采购商理解完成状态",
                "visual_action": "近景展示隔热带贴合并固定在排烟管表面",
                "camera": "缓慢推进并保持产品主体居中",
                "transition": "直接切入",
                "editing_guidance": "保留动作前后状态，不叠加字幕或 CTA",
                "narration": "看清隔热带如何贴合并固定在排烟管表面",
                "intentional_silence": False,
            }]
    }


def _project_with_image(root: Path):
    paths = resolve_paths(root, {})
    initialize_project(paths)
    source = paths.raw_dir / "fixtures" / "official.png"
    preview = paths.generated_dir / "fixtures" / "preview.png"
    source.parent.mkdir(parents=True, exist_ok=True)
    preview.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"official-image")
    preview.write_bytes(b"inspected-preview")
    _write_card(paths, "product", "product/quartz_fiber_tape", "石英纤维隔热带")
    _write_card(
        paths,
        "content_asset",
        "content_asset/quartz_installation",
        "石英纤维隔热带排烟管应用图",
        extra={
            "asset_category": "application_photo",
            "media_types": ["image"],
            "related_products": ["product/quartz_fiber_tape"],
            "usable_for": ["video_planning"],
            "source_paths": [f"raw/{source.relative_to(paths.raw_dir).as_posix()}"],
        },
    )
    _write_card(
        paths,
        "application_scenario",
        "application_scenario/exhaust_pipe_wrap",
        "排烟管缠绕应用",
        extra={
            "scenario_category": "exhaust_insulation",
            "related_products": ["product/quartz_fiber_tape"],
            "usable_channels": ["video_planning"],
        },
    )
    rebuild_agent_interface(paths)
    return paths, source, preview


def _install_video_profile_fixture(
    paths,
    *,
    visual_usage_scope: str = "external_creative_allowed",
) -> str:
    source = paths.raw_dir / "fixtures" / "installation.mp4"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"authorized-video-source")
    revision = hashlib.sha256(source.read_bytes()).hexdigest()
    profile_id = "video_profile/video_asset_fixture"
    asset_id = "video_asset_fixture"
    root = paths.generated_dir / "agent-interfaces" / "tuolin-video-planner" / "video-profiles"
    (root / "details").mkdir(parents=True, exist_ok=True)
    catalog = [{
        "profile_id": profile_id,
        "video_asset_id": asset_id,
        "product_id": "product/quartz_fiber_tape",
        "profile_revision": "profile_revision_1",
        "title": "排烟管缠绕过程",
        "summary": "真实施工片段",
        "use_capabilities": ["clip"],
    }]
    (root / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    detail = {
        **catalog[0],
        "source_revision": revision,
        "visual_usage_scope": visual_usage_scope,
        "source_audio_use_policy": "mute-required",
        "claim_use_policy": "visual_observation_only",
        "publication_gate": "final_human_confirmation_required",
        "visual_usage_confirmation": (
            {
                "confirmed_by": "user",
                "confirmed_at": "2026-07-29T10:00:00+08:00",
            }
            if visual_usage_scope == "external_creative_allowed"
            else {}
        ),
        "key_segments": [{
            "segment_id": "segment_01",
            "start_seconds": 0,
            "end_seconds": 5,
            "use_exclusion": {"status": "allowed"},
        }],
    }
    (root / "details" / f"{asset_id}.json").write_text(json.dumps(detail, ensure_ascii=False), encoding="utf-8")
    registry = {
        "assets": [{
            "asset_id": asset_id,
            "product_id": "product/quartz_fiber_tape",
            "source_fingerprint": revision,
            "source_relative_path": "fixtures/installation.mp4",
        }]
    }
    registry_path = paths.generated_dir / "cache" / "video-assets" / "registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    return profile_id


def _write_card(paths, card_type: str, card_id: str, title: str, *, extra: dict | None = None) -> None:
    folder = {
        "product": "产品",
        "content_asset": "内容素材",
        "application_scenario": "应用场景",
        "sales_material": "销售物料",
    }[card_type]
    slug = card_id.split("/", 1)[1]
    frontmatter = {
        "card_template_version": f"{card_type}-card-v1",
        "type": card_type,
        "id": card_id,
        "title": title,
        "aliases": ["Quartz Fiber Tape"] if card_type == "product" else [],
        "status": "official",
        "usage_scope": "external_allowed",
        "raw_partitions": [f"raw/fixtures/{slug}/"],
        "tags": ["视频策划"],
        "updated_at": "2026-07-28T00:00:00+00:00",
        "last_reviewed_at": "2026-07-28T00:00:00+00:00",
        "evidence_refs": [],
        "related_refs": [],
        "review_refs": [],
        **(extra or {}),
    }
    if card_type == "product":
        frontmatter.update({"product_line": "耐高温隔热带", "related_refs": []})
    path = paths.knowledge_dir / folder / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", *[f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in frontmatter.items()], "---", "", title, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()

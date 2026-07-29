from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path

from scripts.tuolin_marketplace.agent_interface import rebuild_agent_interface
from scripts.tuolin_marketplace.avatar_video_agent import (
    accept_mock_avatar_delivery,
    compose_avatar_video,
    compose_mock_avatar_video,
    confirm_avatar_inputs,
    confirm_avatar_presenter,
    confirm_avatar_production_plan,
    create_avatar_video_run,
    generate_avatar_inputs,
    generate_mock_avatar_inputs,
    generate_mock_avatar_presenter,
    handle_avatar_interview_reply,
    approve_avatar_material_exception,
    authorize_avatar_provider_retry,
    propose_avatar_interview_decision,
    record_avatar_material_inspection,
    reject_avatar_provider_attempt,
    revise_avatar_video,
    resume_avatar_video_run,
    write_avatar_production_plan,
)
from scripts.tuolin_marketplace.avatar_video.media import probe_media
from scripts.tuolin_marketplace.avatar_video.composition import FFmpegComposer, HyperFramesAdapter
from scripts.tuolin_marketplace.avatar_video.provider_adapters import FishAudioAdapter, SupportVisualAdapter
from scripts.tuolin_marketplace.avatar_video.providers import read_provider_attempts, redact_secrets, redact_text
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe required")
class AvatarVideoAgentTests(unittest.TestCase):
    def test_hyperframes_and_ffmpeg_paths_share_the_same_composition_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, image_path = _project_with_product_image(Path(tmp))
            root = _ready_for_composition(paths, image_path)

            def executor(contract, output_path):
                FFmpegComposer().render(contract, output_path)
                return output_path

            rendered = compose_avatar_video(root, hyperframes=HyperFramesAdapter(executor))
            self.assertEqual(rendered.status, "mock_rendered")
            state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["composition_path"], "hyperframes")
            render_dir = (root / state["files"]["final_render"]).parent
            result = json.loads((render_dir / "composition.json").read_text(encoding="utf-8"))
            contract = json.loads((render_dir / "composition-contract.json").read_text(encoding="utf-8"))
            self.assertEqual(result["content_order"], [item["segment_id"] for item in contract["timeline"]])
            self.assertEqual([item["mode"] for item in contract["timeline"]], ["presenter", "evidence"])

    def test_hyperframes_failure_automatically_falls_back_without_new_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, image_path = _project_with_product_image(Path(tmp))
            root = _ready_for_composition(paths, image_path)

            def failed_executor(contract, output_path):
                raise RuntimeError("plugin unavailable")

            rendered = compose_avatar_video(root, hyperframes=HyperFramesAdapter(failed_executor))
            state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["composition_path"], "ffmpeg_fallback")
            result_path = (root / state["files"]["final_render"]).parent / "composition.json"
            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertIn("plugin unavailable", result["fallback_reason"])
            self.assertTrue(state["confirmations"]["plan"])
            self.assertTrue(state["confirmations"]["inputs"])
            self.assertTrue(state["confirmations"]["presenter"])
            self.assertEqual(rendered.phase, "awaiting_final_confirmation")

    def test_chinese_run_derives_kuaishou_and_douyin_without_repeating_providers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, image_path = _project_with_product_image(Path(tmp))
            root = _ready_for_composition(paths, image_path, language="zh")
            attempts_before = sorted(path.name for path in (root / "providers").glob("*.json"))
            compose_mock_avatar_video(root)
            attempts_after = sorted(path.name for path in (root / "providers").glob("*.json"))
            state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            outputs = [root / item for item in state["files"]["final_renders"]]
            self.assertEqual([path.name for path in outputs], ["kuaishou.mp4", "douyin.mp4"])
            self.assertEqual(attempts_before, attempts_after)
            for output in outputs:
                media = probe_media(output)
                self.assertEqual((media["width"], media["height"]), (1080, 1920))
                self.assertAlmostEqual(media["duration_seconds"], 30.0, delta=1.0)
            manifest = json.loads((root / state["files"]["platform_variants"]).read_text(encoding="utf-8"))
            self.assertTrue(manifest["provider_calls_reused"])
            self.assertEqual([item["platform"] for item in manifest["variants"]], ["kuaishou", "douyin"])

    def test_packaging_revision_rerenders_only_packaging_and_protected_changes_invalidate_exact_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths, image_path = _project_with_product_image(workspace)
            root = _ready_for_composition(paths, image_path)
            compose_mock_avatar_video(root)
            before_state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            old_render = root / before_state["files"]["final_render"]
            attempts_before = sorted(path.read_bytes() for path in (root / "providers").glob("*.json"))

            revise_avatar_video(
                root,
                "字幕去掉，只重新包装。",
                category="packaging",
                changes={"captions": {"burned": False}, "transitions": "simple_cut"},
            )
            revised_state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(revised_state["phase"], "ready_for_composition")
            self.assertTrue(old_render.is_file())
            self.assertFalse(revised_state["confirmations"]["final"])
            self.assertEqual(attempts_before, sorted(path.read_bytes() for path in (root / "providers").glob("*.json")))
            compose_mock_avatar_video(root)
            rerendered_state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            new_contract = json.loads((root / rerendered_state["files"]["composition_contract"]).read_text(encoding="utf-8"))
            self.assertFalse(new_contract["captions"]["burned"])
            self.assertEqual(new_contract["transitions"], "simple_cut")
            self.assertTrue((root / "renders" / "revision_0001").is_dir())
            self.assertTrue((root / "renders" / "revision_0002").is_dir())

            categories = {
                "narration": {"narration": "A completely revised approved narration."},
                "audio": {"speed": 0.95},
                "presenter": {"avatar_style": "normal"},
                "evidence": {"timeline": _plan(image_path)["timeline"]},
            }
            for category, changes in categories.items():
                clone = workspace / f"clone-{category}"
                shutil.copytree(root, clone)
                revise_avatar_video(clone, f"revise {category}", category=category, changes=changes)
                state = json.loads((clone / "workflow_state.json").read_text(encoding="utf-8"))
                self.assertTrue((clone / "renders" / "revision_0001").is_dir())
                if category == "narration":
                    self.assertEqual(state["phase"], "awaiting_plan_confirmation")
                    self.assertNotIn("narration_audio", state["files"])
                    self.assertNotIn("presenter_footage", state["files"])
                elif category == "audio":
                    self.assertEqual(state["retry_request"]["provider"], "fish_audio")
                    self.assertNotIn("narration_audio", state["files"])
                elif category == "presenter":
                    self.assertEqual(state["retry_request"]["provider"], "heygen")
                    self.assertIn("narration_audio", state["files"])
                    self.assertNotIn("presenter_footage", state["files"])
                else:
                    self.assertEqual(state["phase"], "awaiting_plan_confirmation")
                    self.assertIn("narration_audio", state["files"])
                    self.assertIn("presenter_footage", state["files"])

    def test_resume_detects_corrupt_active_media_and_composition_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths, image_path = _project_with_product_image(workspace)
            root = _ready_for_composition(paths, image_path)
            attempts_before = sorted(path.read_bytes() for path in (root / "providers").glob("*.json"))
            resumed = resume_avatar_video_run(root)
            self.assertEqual(resumed.phase, "ready_for_composition")
            first = compose_mock_avatar_video(root)
            second = compose_mock_avatar_video(root)
            self.assertEqual(first.status, "mock_rendered")
            self.assertEqual(second.status, "idempotent")
            self.assertEqual(len(list((root / "renders").glob("revision_*"))), 1)
            self.assertEqual(attempts_before, sorted(path.read_bytes() for path in (root / "providers").glob("*.json")))

            corrupt = workspace / "corrupt-run"
            shutil.copytree(root, corrupt)
            corrupt_state = json.loads((corrupt / "workflow_state.json").read_text(encoding="utf-8"))
            corrupt_state["phase"] = "ready_for_composition"
            corrupt_state["status"] = "active"
            (corrupt / "workflow_state.json").write_text(json.dumps(corrupt_state), encoding="utf-8")
            (corrupt / corrupt_state["files"]["presenter_footage"]).write_bytes(b"corrupt")
            blocked = resume_avatar_video_run(corrupt)
            self.assertEqual(blocked.status, "incomplete")
            self.assertEqual(blocked.phase, "blocked")
            self.assertIn("presenter_footage", blocked.message)

    def test_secret_redaction_covers_headers_nested_values_and_url_query_parameters(self) -> None:
        secret = "do-not-persist"
        value = {
            "Authorization": f"Bearer {secret}",
            "nested": {"callback": f"https://example.test/result?token={secret}&page=1"},
            "cookie": secret,
        }
        serialized = json.dumps(redact_secrets(value))
        self.assertNotIn(secret, serialized)
        self.assertNotIn(secret, redact_text(f"failed: Bearer {secret} https://x.test?a=1&api_key={secret}"))

    def test_mock_english_run_reaches_valid_local_delivery_without_publish_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, image_path = _project_with_product_image(Path(tmp))
            run = create_avatar_video_run(
                paths,
                "Create a 30-second English presenter video",
                product_id="product/quartz_fiber_tape",
                language_version="en",
                duration_seconds=30,
                initial_brief=_complete_brief(),
                invoked_skill="$tuolin-avatar-video",
                test_mode=True,
                now=datetime(2026, 7, 29, 12, 0, 0),
            )
            self.assertEqual(run.phase, "ready_for_plan")
            root = Path(run.run_dir)

            _inspect_image(root, image_path)
            write_avatar_production_plan(root, _plan(image_path))
            confirm_avatar_production_plan(root)
            generate_mock_avatar_inputs(root)
            confirm_avatar_inputs(root)
            generate_mock_avatar_presenter(root)
            confirm_avatar_presenter(root)
            compose_mock_avatar_video(root)
            delivered = accept_mock_avatar_delivery(root)

            self.assertEqual(delivered.status, "mock_completed")
            state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["phase"], "completed")
            self.assertNotIn("publish", json.dumps(state, ensure_ascii=False).casefold())
            pack = json.loads((root / "delivery" / "delivery-pack.json").read_text(encoding="utf-8"))
            self.assertEqual(pack["status"], "mock_delivery")
            self.assertFalse(pack["publish_authorized"])
            self.assertIn("伪供应商", pack["warning"])
            output = Path(pack["files"][0])
            probe = probe_media(output)
            self.assertEqual((probe["width"], probe["height"]), (1080, 1920))
            self.assertTrue(probe["has_audio"])
            self.assertTrue(probe["has_video"])
            self.assertAlmostEqual(probe["duration_seconds"], 30.0, delta=1.0)
            contract_path = root / state["files"]["composition_contract"]
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            self.assertTrue(contract["captions"]["burned"])
            self.assertEqual(contract["captions"]["language"], "en")
            self.assertTrue(Path(contract["captions"]["path"]).is_file())
            self.assertIsNone(contract["bgm"])

    def test_explicit_invocation_and_duration_boundary_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _ = _project_with_product_image(Path(tmp))
            common = dict(
                paths=paths,
                request_text="avatar video",
                product_id="product/quartz_fiber_tape",
                language_version="en",
                duration_seconds=30,
                initial_brief=_complete_brief(),
                test_mode=True,
            )
            with self.assertRaisesRegex(ValueError, "显式调用"):
                create_avatar_video_run(**common)
            with self.assertRaisesRegex(ValueError, "30–90"):
                create_avatar_video_run(
                    **{**common, "invoked_skill": "$tuolin-avatar-video", "duration_seconds": 29}
                )

    def test_plan_rejects_image_not_declared_by_avatar_interface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, image_path = _project_with_product_image(Path(tmp))
            unrelated = paths.raw_dir / "unrelated.png"
            _make_image(unrelated, "blue")
            run = create_avatar_video_run(
                paths,
                "avatar video",
                product_id="product/quartz_fiber_tape",
                language_version="en",
                duration_seconds=30,
                initial_brief=_complete_brief(),
                invoked_skill="$tuolin-avatar-video",
                test_mode=True,
            )
            plan = _plan(image_path)
            plan["selected_visuals"][0]["path"] = str(unrelated)
            with self.assertRaisesRegex(ValueError, "专属知识接口声明"):
                write_avatar_production_plan(run.run_dir, plan)

    def test_plan_accepts_only_explicit_local_bgm_and_allows_preconfirmation_caption_opt_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, image_path = _project_with_product_image(Path(tmp))
            music_path = Path(tmp) / "user-music.wav"
            _make_audio(music_path)
            run = create_avatar_video_run(
                paths,
                "avatar video with supplied music",
                product_id="product/quartz_fiber_tape",
                language_version="en",
                duration_seconds=30,
                initial_brief=_complete_brief(),
                invoked_skill="$tuolin-avatar-video",
                test_mode=True,
            )
            root = Path(run.run_dir)
            _inspect_image(root, image_path)
            plan = _plan(image_path)
            plan["bgm"] = {"path": str(music_path), "volume": 0.1}
            plan["captions"] = {"burned": False}
            write_avatar_production_plan(root, plan)
            normalized = json.loads((root / "production_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(normalized["bgm"]["source"], "user_provided_local_file")
            self.assertEqual(normalized["bgm"]["path"], str(music_path.resolve()))
            self.assertFalse(normalized["captions"]["burned"])
            self.assertEqual(normalized["captions"]["language"], "en")

    def test_run_pins_interface_revision_and_blocks_resume_after_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _ = _project_with_product_image(Path(tmp))
            run = create_avatar_video_run(
                paths,
                "avatar video",
                product_id="product/quartz_fiber_tape",
                language_version="en",
                duration_seconds=30,
                initial_brief=_complete_brief(),
                invoked_skill="$tuolin-avatar-video",
                test_mode=True,
            )
            root = Path(run.run_dir)
            pinned = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))["interface"]["interface_revision"]
            _write_card(
                paths.knowledge_dir / "产品" / "second.md",
                [
                    "card_template_version: product-card-v1",
                    "type: product",
                    "id: product/second",
                    "title: Second product",
                    "aliases: []",
                    "status: official",
                    "usage_scope: external_allowed",
                    "product_line: Test",
                    "raw_partitions: []",
                    "tags: []",
                    "updated_at: 2026-07-29T00:00:00+00:00",
                    "last_reviewed_at: 2026-07-29T00:00:00+00:00",
                    "evidence_refs: []",
                    "related_refs: []",
                    "review_refs: []",
                ],
                "Second official product.",
            )
            rebuild_agent_interface(paths)

            resumed = resume_avatar_video_run(root)
            self.assertEqual(resumed.status, "blocked_stale_interface")
            state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["blocker"]["expected_revision"], pinned)
            self.assertNotEqual(state["blocker"]["current_revision"], pinned)

    def test_interview_asks_one_business_decision_and_contains_no_trend_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _ = _project_with_product_image(Path(tmp))
            run = create_avatar_video_run(
                paths,
                "Start an English avatar video interview",
                product_id="product/quartz_fiber_tape",
                language_version="en",
                duration_seconds=30,
                invoked_skill="$tuolin-avatar-video",
                test_mode=True,
            )
            proposal = {
                "decision_key": "audience",
                "question": "Who should this video address?",
                "recommendation": "European industrial buyers",
                "reason": "They need a concise product-selection introduction.",
            }
            asked = propose_avatar_interview_decision(run.run_dir, proposal)
            self.assertIn("European industrial buyers", asked.message)
            self.assertNotIn("trend", asked.message.casefold())
            with self.assertRaisesRegex(ValueError, "一次只能"):
                propose_avatar_interview_decision(run.run_dir, proposal)
            handled = handle_avatar_interview_reply(run.run_dir, "确认")
            self.assertEqual(handled.phase, "interview")
            interview = json.loads((Path(run.run_dir) / "interview.json").read_text(encoding="utf-8"))
            self.assertEqual(interview["decisions"]["audience"], "European industrial buyers")
            self.assertIsNone(interview["pending_decision"])
            with self.assertRaisesRegex(ValueError, "不属于"):
                propose_avatar_interview_decision(
                    run.run_dir,
                    {
                        "decision_key": "trend_scan",
                        "question": "Search trends?",
                        "recommendation": "Yes",
                        "reason": "Popularity",
                    },
                )

    def test_interview_completes_after_each_missing_business_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, _ = _project_with_product_image(Path(tmp))
            run = create_avatar_video_run(
                paths,
                "Interview",
                product_id="product/quartz_fiber_tape",
                language_version="en",
                duration_seconds=30,
                invoked_skill="$tuolin-avatar-video",
                test_mode=True,
            )
            for key, value in _complete_brief().items():
                propose_avatar_interview_decision(
                    run.run_dir,
                    {
                        "decision_key": key,
                        "question": f"Confirm {key}?",
                        "recommendation": value,
                        "reason": "This is the current most consequential unresolved decision.",
                    },
                )
                result = handle_avatar_interview_reply(run.run_dir, "按推荐")
            self.assertEqual(result.phase, "ready_for_plan")
            state = json.loads((Path(run.run_dir) / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["brief"], _complete_brief())

    def test_plan_confirmation_authorizes_disclosed_initial_operations_and_surfaces_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, image_path = _project_with_product_image(Path(tmp))
            run = create_avatar_video_run(
                paths,
                "Plan",
                product_id="product/quartz_fiber_tape",
                language_version="en",
                duration_seconds=30,
                initial_brief=_complete_brief(),
                invoked_skill="$tuolin-avatar-video",
                test_mode=True,
            )
            plan = _plan(image_path)
            plan["narration"] = "This product is certified to XYZ-999 and is always completely safe."
            plan["support_visual_batch"] = {
                "provider": "image-mock",
                "images": [{"purpose": "parameter layout", "reference": str(image_path)}],
            }
            _inspect_image(Path(run.run_dir), image_path)
            shown = write_avatar_production_plan(run.run_dir, plan)
            self.assertIn("高风险提示", shown.message)
            self.assertIn("认证或标准", shown.message)
            confirm_avatar_production_plan(run.run_dir)
            state = json.loads((Path(run.run_dir) / "workflow_state.json").read_text(encoding="utf-8"))
            authorization = state["execution_authorization"]
            self.assertEqual(authorization["plan_revision"], json.loads((Path(run.run_dir) / "production_plan.json").read_text(encoding="utf-8"))["revision"])
            self.assertEqual([item["provider"] for item in authorization["operations"]], ["fish_audio", "heygen", "support_images"])
            self.assertEqual(authorization["operations"][2]["provider_name"], "image-mock")

    def test_plan_requires_pixel_inspection_and_blocks_risky_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, image_path = _project_with_product_image(Path(tmp))
            run = create_avatar_video_run(
                paths,
                "Plan",
                product_id="product/quartz_fiber_tape",
                language_version="en",
                duration_seconds=30,
                initial_brief=_complete_brief(),
                invoked_skill="$tuolin-avatar-video",
                test_mode=True,
            )
            with self.assertRaisesRegex(ValueError, "像素检查"):
                write_avatar_production_plan(run.run_dir, _plan(image_path))
            record_avatar_material_inspection(
                run.run_dir,
                {
                    "path": str(image_path),
                    "subject": "official product roll",
                    "clarity": "clear",
                    "composition": "centered",
                    "vertical_crop": "usable",
                    "near_duplicate_group": "product-roll-01",
                    "status": "blocked",
                    "risks": ["unresolved product identity"],
                },
            )
            with self.assertRaisesRegex(ValueError, "未解决"):
                write_avatar_production_plan(run.run_dir, _plan(image_path))

    def test_material_capacity_requires_explicit_exception(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, image_path = _project_with_product_image(Path(tmp))
            run = create_avatar_video_run(
                paths,
                "Plan",
                product_id="product/quartz_fiber_tape",
                language_version="en",
                duration_seconds=30,
                initial_brief=_complete_brief(),
                invoked_skill="$tuolin-avatar-video",
                test_mode=True,
            )
            root = Path(run.run_dir)
            _inspect_image(root, image_path)
            plan = _plan(image_path)
            plan["timeline"] = [{"start_seconds": 0, "end_seconds": 30, "mode": "evidence", "purpose": "full evidence"}]
            with self.assertRaisesRegex(ValueError, "明确允许重复"):
                write_avatar_production_plan(root, plan)
            approve_avatar_material_exception(
                root,
                {"type": "deliberate_repetition", "reason": "User accepts a deliberate hold on the official image."},
            )
            written = write_avatar_production_plan(root, plan)
            self.assertEqual(written.phase, "awaiting_plan_confirmation")

    def test_provider_submission_is_idempotent_and_retry_preserves_rejected_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, image_path = _project_with_product_image(Path(tmp))
            run = create_avatar_video_run(
                paths,
                "Provider ledger",
                product_id="product/quartz_fiber_tape",
                language_version="en",
                duration_seconds=30,
                initial_brief=_complete_brief(),
                invoked_skill="$tuolin-avatar-video",
                test_mode=True,
            )
            root = Path(run.run_dir)
            _inspect_image(root, image_path)
            write_avatar_production_plan(root, _plan(image_path))
            confirm_avatar_production_plan(root)

            first = generate_mock_avatar_inputs(root)
            duplicate = generate_mock_avatar_inputs(root)
            self.assertEqual(duplicate.status, "idempotent")
            self.assertEqual(first.output_paths, duplicate.output_paths)
            self.assertEqual(len(read_provider_attempts(root, "fish_audio")), 1)

            rejected = reject_avatar_provider_attempt(root, "fish_audio", "Pronunciation needs adjustment")
            self.assertEqual(rejected.status, "rejected")
            authorize_avatar_provider_retry(
                root,
                "fish_audio",
                reason="User authorizes one paid retry",
                settings_changes={"speed": 0.95},
            )
            second = generate_mock_avatar_inputs(root)
            self.assertNotEqual(first.output_paths, second.output_paths)
            attempts = read_provider_attempts(root, "fish_audio")
            self.assertEqual(len(attempts), 2)
            self.assertEqual(attempts[0]["status"], "rejected")
            self.assertEqual(attempts[0]["review"]["reason"], "Pronunciation needs adjustment")
            self.assertEqual(attempts[1]["settings"]["speed"], 0.95)
            self.assertTrue(Path(attempts[0]["output"]).is_file())
            self.assertTrue(Path(attempts[1]["output"]).is_file())

    def test_support_images_generate_in_parallel_and_confirm_with_audio_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, image_path = _project_with_product_image(Path(tmp))
            run = create_avatar_video_run(
                paths,
                "Parallel inputs",
                product_id="product/quartz_fiber_tape",
                language_version="en",
                duration_seconds=30,
                initial_brief=_complete_brief(),
                invoked_skill="$tuolin-avatar-video",
                test_mode=True,
            )
            root = Path(run.run_dir)
            _inspect_image(root, image_path)
            plan = _plan(image_path)
            plan["support_visual_batch"] = {
                "provider": "image-mock",
                "count": 1,
                "images": [{"purpose": "parameter layout", "reference": str(image_path)}],
                "estimated_consumption": 0,
            }
            write_avatar_production_plan(root, plan)
            confirm_avatar_production_plan(root)
            generated = generate_mock_avatar_inputs(root)

            self.assertEqual(len(generated.output_paths), 2)
            state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["input_generation"]["strategy"], "parallel")
            self.assertEqual(state["input_generation"]["providers"], ["fish_audio", "support_images"])
            manifest = json.loads((root / state["files"]["support_visual_manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["count"], 1)
            self.assertFalse(manifest["viewer_facing_ai_label"])
            self.assertTrue(Path(manifest["images"][0]).is_file())
            confirmed = confirm_avatar_inputs(root)
            self.assertEqual(len(confirmed.output_paths), 2)
            attempts = read_provider_attempts(root)
            self.assertEqual({item["provider"] for item in attempts}, {"fish_audio", "support_images"})
            self.assertTrue(all(item["status"] == "accepted" for item in attempts))

    def test_real_replaceable_support_adapter_runs_concurrently_with_fish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths, image_path = _project_with_product_image(workspace)
            run = create_avatar_video_run(
                paths,
                "Real provider boundaries",
                product_id="product/quartz_fiber_tape",
                language_version="en",
                duration_seconds=30,
                initial_brief=_complete_brief(),
                invoked_skill="$tuolin-avatar-video",
                test_mode=False,
            )
            root = Path(run.run_dir)
            _inspect_image(root, image_path)
            plan = _plan(image_path)
            plan["support_visual_batch"] = {
                "provider": "connected-image-generator",
                "count": 1,
                "images": [{"purpose": "non-factual parameter layout", "reference": str(image_path)}],
                "estimated_consumption": 1,
            }
            write_avatar_production_plan(root, plan)
            confirm_avatar_production_plan(root)
            barrier = threading.Barrier(2, timeout=5)
            audio_fixture = workspace / "parallel.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=30", "-c:a", "pcm_s16le", str(audio_fixture)],
                capture_output=True,
                check=True,
            )

            def fish_transport(url, headers, payload, timeout):
                barrier.wait()
                return {"status": 200, "headers": {"x-request-id": "fish-parallel"}, "body": audio_fixture.read_bytes()}

            def image_executor(batch, output_dir):
                barrier.wait()
                return {"task_id": "image-parallel", "image_paths": [str(image_path)], "actual_consumption": 1}

            generated = generate_avatar_inputs(
                root,
                FishAudioAdapter(api_key="secret", transport=fish_transport),
                SupportVisualAdapter(image_executor),
            )
            self.assertEqual(generated.status, "completed_pending_review")
            self.assertEqual(len(generated.output_paths), 2)
            state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            manifest = json.loads((root / state["files"]["support_visual_manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "real")
            self.assertEqual(manifest["generation_provenance"], "provider_generated")
            attempts = read_provider_attempts(root)
            self.assertEqual({item["external_task_id"] for item in attempts}, {"fish-parallel", "image-parallel"})
            self.assertTrue(all(item["mode"] == "real" for item in attempts))
            self.assertEqual(confirm_avatar_inputs(root).status, "confirmed")

    def test_support_batch_requires_exact_count_and_inspected_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, image_path = _project_with_product_image(Path(tmp))
            run = create_avatar_video_run(
                paths,
                "Support batch",
                product_id="product/quartz_fiber_tape",
                language_version="en",
                duration_seconds=30,
                initial_brief=_complete_brief(),
                invoked_skill="$tuolin-avatar-video",
                test_mode=True,
            )
            root = Path(run.run_dir)
            _inspect_image(root, image_path)
            plan = _plan(image_path)
            plan["support_visual_batch"] = {
                "provider": "image-mock",
                "count": 2,
                "images": [{"purpose": "parameter layout", "reference": str(image_path)}],
            }
            with self.assertRaisesRegex(ValueError, "声明数量"):
                write_avatar_production_plan(root, plan)


def _complete_brief() -> dict[str, str]:
    return {
        "audience": "European industrial buyers",
        "reason_to_watch": "See the product and its key selection information quickly",
        "takeaway": "Quartz fiber tape is an available thermal-insulation option",
        "viewer_action": "Ask for the datasheet",
        "priority_information": "Product identity and application context",
        "exclusions": "No unsupported certification claims",
        "presenter_evidence_treatment": "Presenter introduces; product evidence may take full screen",
    }


def _ready_for_composition(paths, image_path: Path, *, language: str = "en") -> Path:
    run = create_avatar_video_run(
        paths,
        "Composition test",
        product_id="product/quartz_fiber_tape",
        language_version=language,
        duration_seconds=30,
        initial_brief=_complete_brief(),
        invoked_skill="$tuolin-avatar-video",
        test_mode=True,
    )
    root = Path(run.run_dir)
    _inspect_image(root, image_path)
    plan = _plan(image_path)
    if language == "zh":
        plan["narration"] = "这是拓霖产品介绍。请查看正式产品资料，并联系我们获取数据表。"
    write_avatar_production_plan(root, plan)
    confirm_avatar_production_plan(root)
    generate_mock_avatar_inputs(root)
    confirm_avatar_inputs(root)
    generate_mock_avatar_presenter(root)
    confirm_avatar_presenter(root)
    return root


def _plan(image_path: Path) -> dict:
    return {
        "narration": "This is a test narration for a Tuolin quartz fiber insulation tape product video.",
        "timeline": [
            {"start_seconds": 0, "end_seconds": 15, "mode": "presenter", "purpose": "introduce product"},
            {"start_seconds": 15, "end_seconds": 30, "mode": "evidence", "purpose": "show official product image"},
        ],
        "selected_visuals": [{"path": str(image_path), "purpose": "product_evidence"}],
        "fish_audio": {"voice_id": "fish-test-voice", "speed": 1.0},
        "heygen": {"avatar_id": "heygen-public-test-avatar"},
        "estimated_consumption": {"mode": "mock", "credits": 0},
        "high_risk_notes": [],
    }


def _project_with_product_image(root: Path):
    paths = resolve_paths(root, {})
    initialize_project(paths)
    _write_card(
        paths.knowledge_dir / "产品" / "quartz_fiber_tape.md",
        [
            "card_template_version: product-card-v1",
            "type: product",
            "id: product/quartz_fiber_tape",
            "title: Quartz Fiber Insulation Tape",
            "aliases: []",
            "status: official",
            "usage_scope: external_allowed",
            "product_line: Thermal insulation tape",
            "raw_partitions: []",
            "tags: []",
            "updated_at: 2026-07-29T00:00:00+00:00",
            "last_reviewed_at: 2026-07-29T00:00:00+00:00",
            "evidence_refs: []",
            "related_refs: []",
            "review_refs: []",
        ],
        "Official product definition.",
    )
    image_path = paths.raw_dir / "products" / "quartz-tape.png"
    _make_image(image_path, "0x445566")
    relative = image_path.relative_to(paths.project_dir).as_posix()
    _write_card(
        paths.knowledge_dir / "内容素材" / "quartz_tape_image.md",
        [
            "card_template_version: content-asset-card-v1",
            "type: content_asset",
            "id: content_asset/quartz_tape_image",
            "title: Quartz tape official image",
            "aliases: []",
            "status: official",
            "usage_scope: external_allowed",
            "raw_partitions: []",
            "tags: [product image]",
            "updated_at: 2026-07-29T00:00:00+00:00",
            "last_reviewed_at: 2026-07-29T00:00:00+00:00",
            "evidence_refs: []",
            "review_refs: []",
            "asset_category: product image",
            "media_types: [image]",
            "related_products: [product/quartz_fiber_tape]",
            f"files: [{relative}]",
            "usable_for: [avatar_video]",
        ],
        "Official product image for digital-avatar video.",
    )
    rebuild_agent_interface(paths)
    return paths, image_path


def _make_image(path: Path, color: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=640x640:d=0.1",
            "-frames:v",
            "1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr)


def _make_audio(path: Path) -> None:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=220:sample_rate=48000:duration=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr)


def _inspect_image(run_dir: Path, image_path: Path) -> None:
    record_avatar_material_inspection(
        run_dir,
        {
            "path": str(image_path),
            "subject": "official quartz tape product roll",
            "clarity": "clear",
            "composition": "centered square product image",
            "vertical_crop": "usable with padding",
            "near_duplicate_group": "quartz-product-roll-01",
            "status": "usable",
            "risks": [],
        },
    )


def _write_card(path: Path, frontmatter: list[str], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + "\n".join(frontmatter) + "\n---\n\n" + body + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()

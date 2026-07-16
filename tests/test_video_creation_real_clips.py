from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.video_creation.agent import (
    assemble_confirmed_video,
    confirm_dreamina_generation,
    confirm_storyboard,
    generate_dreamina_jobs,
    generate_storyboard,
    set_storyboard_shot_real_clip,
    submit_dreamina_jobs,
)
from tests.test_video_creation_agent import _create_plan_confirmed_run


class VideoCreationRealClipTests(unittest.TestCase):
    def test_storyboard_requires_exact_task_preview_for_real_clip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_real_clip_storyboard(Path(tmp))
            storyboard_path = run_dir / "storyboard.json"
            storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
            shot = next(item for item in storyboard["shots"] if item["shot_id"] == "02")
            replacement = run_dir / "storyboard_assets" / "representative-only.png"
            replacement.parent.mkdir(parents=True, exist_ok=True)
            replacement.write_bytes(b"representative frame")
            shot["real_video_clip"]["preview_path"] = str(replacement)
            storyboard_path.write_text(
                json.dumps(storyboard, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "exact task clip"):
                confirm_storyboard(run_dir)

    def test_storyboard_records_source_range_and_adaptations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_real_clip_storyboard(Path(tmp))
            storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
            shot = next(item for item in storyboard["shots"] if item["shot_id"] == "02")
            clip = shot["real_video_clip"]

            self.assertEqual(shot["material_mode"], "real_video_clip")
            self.assertFalse(shot["ai_generated"])
            self.assertEqual(clip["asset_id"], "video_asset_1234567890abcdef1234567890abcdef")
            self.assertEqual(clip["profile_revision"], "video_profile_rev_1234567890abcdef")
            self.assertEqual(clip["source_range"], {"start_seconds": 2.0, "end_seconds": 10.0})
            self.assertEqual(
                clip["adaptations"],
                {"resolution": "1080x1920", "frame_rate": 30},
            )
            self.assertEqual(clip["audio_policy"], "mute_confirmed")
            self.assertEqual(clip["preview_path"], clip["task_clip_path"])

    def test_real_task_clip_is_preferred_over_regeneration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_real_clip_storyboard(Path(tmp))
            confirm_storyboard(run_dir)
            generate_dreamina_jobs(run_dir)
            jobs = json.loads(
                (run_dir / "dreamina_generation" / "dreamina_jobs.json").read_text(
                    encoding="utf-8"
                )
            )

            self.assertNotIn("02", [item["shot_id"] for item in jobs["jobs"]])
            self.assertEqual(jobs["real_task_clips"][0]["shot_id"], "02")
            self.assertEqual(jobs["real_task_clips"][0]["selection_policy"], "prefer_real_over_regeneration")

    def test_assembly_uses_real_extracted_clip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_real_clip_storyboard(Path(tmp))
            confirm_storyboard(run_dir)
            generate_dreamina_jobs(run_dir)
            jobs_path = run_dir / "dreamina_generation" / "dreamina_jobs.json"
            jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
            results = []
            for job in jobs["jobs"]:
                output = run_dir / "dreamina_generation" / f"{job['shot_id']}.mp4"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"generated shot")
                results.append(
                    {
                        "shot_id": job["shot_id"],
                        "status": "succeeded",
                        "output_path": str(output),
                    }
                )
            results_path = run_dir / "dreamina_generation" / "dreamina_results.json"
            results_path.write_text(
                json.dumps({"results": results}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            state_path = run_dir / "workflow_state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["phase"] = "ready_for_video_assembly"
            state["confirmations"]["shots"] = True
            state["files"]["dreamina_results_json"] = str(results_path)
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            def runner(command, **kwargs):
                Path(command[-1]).write_bytes(b"assembled")
                return subprocess.CompletedProcess(command, 0, "", "")

            assemble_confirmed_video(run_dir, runner=runner)
            manifest = json.loads(
                (run_dir / "dreamina_generation" / "assembly_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            shot = next(item for item in manifest["shot_inputs"] if item["shot_id"] == "02")
            storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
            storyboard_shot = next(
                item for item in storyboard["shots"] if item["shot_id"] == "02"
            )

            self.assertEqual(shot["source_type"], "real_video_clip")
            self.assertEqual(
                shot["input_path"],
                storyboard_shot["real_video_clip"]["task_clip_path"],
            )

    def test_revoked_asset_blocks_submission_after_storyboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _create_real_clip_storyboard(Path(tmp))
            confirm_storyboard(run_dir)
            generate_dreamina_jobs(run_dir)
            confirm_dreamina_generation(run_dir)
            authorization_path = run_dir / "video_profile_authorizations.json"
            authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
            authorization["authorized_profiles"][0]["revoked"] = True
            authorization_path.write_text(
                json.dumps(authorization, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(PermissionError, "revoked"):
                submit_dreamina_jobs(run_dir)


def _create_real_clip_storyboard(root: Path) -> Path:
    run_dir = _create_plan_confirmed_run(root)
    generate_storyboard(run_dir)
    storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
    shot = next(item for item in storyboard["shots"] if item["shot_id"] == "02")
    task_clip = run_dir / "runtime-video-clips" / "tasks" / "shot_02" / "task.mp4"
    task_clip.parent.mkdir(parents=True, exist_ok=True)
    task_clip.write_bytes(b"real extracted task clip")
    interface_revision = "video_interface_1234567890abcdef"
    asset_id = "video_asset_1234567890abcdef1234567890abcdef"
    profile_revision = "video_profile_rev_1234567890abcdef"
    (run_dir / "video_profile_authorizations.json").write_text(
        json.dumps(
            {
                "schema_version": "video-profile-run-authorization-v1",
                "run_id": run_dir.name,
                "interface_revision": interface_revision,
                "raw_access": False,
                "authorized_profiles": [
                    {
                        "profile_id": f"video_profile/quartz_fiber_tape/{asset_id}",
                        "video_asset_id": asset_id,
                        "product_id": "product/quartz_fiber_tape",
                        "profile_revision": profile_revision,
                        "source_revision": "a" * 64,
                        "operations": ["frame", "clip"],
                        "revoked": False,
                        "segments": [
                            {
                                "segment_id": "segment_01",
                                "start_seconds": 0.0,
                                "end_seconds": 30.0,
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    set_storyboard_shot_real_clip(
        run_dir,
        "02",
        asset_id=asset_id,
        profile_revision=profile_revision,
        interface_revision=interface_revision,
        segment_id="segment_01",
        source_start_seconds=2.0,
        source_end_seconds=2.0 + float(shot["duration_seconds"]),
        task_clip_path=task_clip,
        adaptations={"resolution": "1080x1920", "frame_rate": 30},
        audio_policy="mute_confirmed",
        risk_notes=["original_audio_muted_by_confirmation"],
    )
    return run_dir

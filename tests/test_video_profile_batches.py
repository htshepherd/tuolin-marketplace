from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths
from scripts.tuolin_marketplace.video_profile_batches import (
    SystemicVideoBatchError,
    process_video_profile_batch,
)


class VideoProfileBatchTests(unittest.TestCase):
    def test_batch_preflight_blocks_when_ffprobe_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, folder = _batch_fixture(Path(tmp), count=1)

            def runner(command, **kwargs):
                if command[0] == "ffprobe":
                    raise FileNotFoundError("ffprobe")
                return subprocess.CompletedProcess(command, 0, "ok", "")

            result = process_video_profile_batch(
                folder,
                paths,
                product_id="product/quartz_fiber_tape",
                batch_id="batch-001",
                runner=runner,
                processor=_successful_processor,
            )

            self.assertEqual(result.status, "blocked_preflight")
            self.assertIn("ffprobe", result.blockers)
            self.assertEqual(result.completed_count, 0)

    def test_batch_preflight_blocks_when_ffmpeg_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, folder = _batch_fixture(Path(tmp), count=1)

            def runner(command, **kwargs):
                if command[0] == "ffmpeg":
                    raise FileNotFoundError("ffmpeg")
                return subprocess.CompletedProcess(command, 0, "ok", "")

            result = process_video_profile_batch(
                folder,
                paths,
                product_id="product/quartz_fiber_tape",
                batch_id="batch-001",
                runner=runner,
                processor=_successful_processor,
            )

            self.assertEqual(result.status, "blocked_preflight")
            self.assertIn("ffmpeg", result.blockers)

    def test_batch_preflight_blocks_when_codex_visual_review_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, folder = _batch_fixture(Path(tmp), count=1)

            result = process_video_profile_batch(
                folder,
                paths,
                product_id="product/quartz_fiber_tape",
                batch_id="batch-001",
                codex_visual_review_available=False,
                runner=_available_tool_runner,
                processor=_successful_processor,
            )

            self.assertEqual(result.status, "blocked_preflight")
            self.assertIn("codex_visual_review", result.blockers)

    def test_missing_optional_asr_does_not_block_visual_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, folder = _batch_fixture(Path(tmp), count=1)

            result = process_video_profile_batch(
                folder,
                paths,
                product_id="product/quartz_fiber_tape",
                batch_id="batch-001",
                optional_asr_available=False,
                runner=_available_tool_runner,
                processor=_successful_processor,
            )

            self.assertEqual(result.status, "completed")
            preflight = json.loads(result.preflight_path.read_text(encoding="utf-8"))
            self.assertEqual(preflight["optional_capabilities"]["asr"], "unavailable")

    def test_checkpoint_is_saved_after_each_valid_video(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, folder = _batch_fixture(Path(tmp), count=3)

            result = process_video_profile_batch(
                folder,
                paths,
                product_id="product/quartz_fiber_tape",
                batch_id="batch-001",
                runner=_available_tool_runner,
                processor=_successful_processor,
            )

            self.assertEqual(result.completed_count, 3)
            self.assertEqual(len(result.checkpoint_paths), 3)
            self.assertTrue(all(path.is_file() for path in result.checkpoint_paths))
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual([item["status"] for item in manifest["items"]], ["valid"] * 3)

    def test_resume_skips_unchanged_valid_checkpoints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, folder = _batch_fixture(Path(tmp), count=2)
            calls = []

            def processor(video, asset, context):
                calls.append(video.name)
                return _successful_processor(video, asset, context)

            process_video_profile_batch(
                folder,
                paths,
                product_id="product/quartz_fiber_tape",
                batch_id="batch-001",
                runner=_available_tool_runner,
                processor=processor,
            )
            resumed = process_video_profile_batch(
                folder,
                paths,
                product_id="product/quartz_fiber_tape",
                batch_id="batch-001",
                runner=_available_tool_runner,
                processor=processor,
            )

            self.assertEqual(len(calls), 2)
            self.assertEqual(resumed.skipped_count, 2)
            self.assertEqual(resumed.completed_count, 2)

    def test_resume_reprocesses_changed_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, folder = _batch_fixture(Path(tmp), count=1)
            calls = []

            def processor(video, asset, context):
                calls.append(asset.source_fingerprint)
                return _successful_processor(video, asset, context)

            process_video_profile_batch(
                folder,
                paths,
                product_id="product/quartz_fiber_tape",
                batch_id="batch-001",
                runner=_available_tool_runner,
                processor=processor,
            )
            video = next(folder.glob("*.mp4"))
            video.write_bytes(b"changed source")
            resumed = process_video_profile_batch(
                folder,
                paths,
                product_id="product/quartz_fiber_tape",
                batch_id="batch-001",
                runner=_available_tool_runner,
                processor=processor,
            )

            self.assertEqual(len(calls), 2)
            self.assertNotEqual(calls[0], calls[1])
            self.assertEqual(resumed.skipped_count, 0)

    def test_local_video_failure_does_not_rollback_other_checkpoints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, folder = _batch_fixture(Path(tmp), count=3)

            def processor(video, asset, context):
                if video.name == "video_02.mp4":
                    raise RuntimeError("local decode failure")
                return _successful_processor(video, asset, context)

            result = process_video_profile_batch(
                folder,
                paths,
                product_id="product/quartz_fiber_tape",
                batch_id="batch-001",
                runner=_available_tool_runner,
                processor=processor,
            )

            self.assertEqual(result.status, "completed_with_failures")
            self.assertEqual(result.completed_count, 2)
            self.assertEqual(result.failed_count, 1)
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                [item["status"] for item in manifest["items"]],
                ["valid", "failed", "valid"],
            )

    def test_systemic_failure_pauses_affected_batch_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths, folder = _batch_fixture(Path(tmp), count=3)
            calls = []

            def processor(video, asset, context):
                calls.append(video.name)
                if video.name == "video_02.mp4":
                    raise SystemicVideoBatchError("visual review environment unavailable")
                return _successful_processor(video, asset, context)

            result = process_video_profile_batch(
                folder,
                paths,
                product_id="product/quartz_fiber_tape",
                batch_id="batch-001",
                runner=_available_tool_runner,
                processor=processor,
            )

            self.assertEqual(result.status, "paused_systemic_failure")
            self.assertEqual(calls, ["video_01.mp4", "video_02.mp4"])
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                [item["status"] for item in manifest["items"]],
                ["valid", "systemic_failure", "paused"],
            )
            self.assertTrue(result.checkpoint_paths[0].is_file())


def _batch_fixture(root: Path, *, count: int):
    paths = resolve_paths(root, {})
    initialize_project(paths)
    folder = (
        paths.raw_dir
        / "01_产品"
        / "02_石英纤维隔热带"
        / "03_产品视频"
    )
    folder.mkdir(parents=True, exist_ok=True)
    for index in range(1, count + 1):
        (folder / f"video_{index:02d}.mp4").write_bytes(f"video {index}".encode())
    return paths, folder


def _available_tool_runner(command, **kwargs):
    return subprocess.CompletedProcess(command, 0, "available", "")


def _successful_processor(video, asset, context):
    report = context["checkpoint_root"] / "processor-reports" / f"{video.stem}.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(
            {
                "status": "valid",
                "asset_id": asset.asset_id,
                "source_fingerprint": asset.source_fingerprint,
            }
        ),
        encoding="utf-8",
    )
    return {"status": "valid", "report_path": str(report)}

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths
from scripts.tuolin_marketplace.video_profiles import (
    CodexVideoCandidateReview,
    ExtractedVideoFrame,
    VideoAnalysisChange,
    VideoMediaFacts,
    build_video_analysis_plan,
    confirm_video_tracer_candidate,
    detect_video_change_candidates,
    filter_video_frame_candidates,
    finalize_video_candidate_batch_recommendation,
    inspect_video_candidate,
    inspect_video_candidate_batch,
    prepare_video_analysis_clip,
    probe_video_media,
    record_codex_candidate_review,
    register_video_asset,
    stage_video_profile_draft,
)


class VideoProfileTests(unittest.TestCase):
    def test_video_asset_id_is_opaque_and_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            video = (
                paths.raw_dir
                / "01_产品"
                / "02_石英纤维隔热带"
                / "03_产品视频"
                / "operator-demo.mp4"
            )
            video.write_bytes(b"unchanged source video")
            raw_digest_before = hashlib.sha256(video.read_bytes()).hexdigest()
            raw_files_before = sorted(
                path.relative_to(paths.raw_dir).as_posix()
                for path in paths.raw_dir.rglob("*")
                if path.is_file()
            )

            first = register_video_asset(video, paths, product_id="product/quartz_fiber_tape")
            second = register_video_asset(video, paths, product_id="product/quartz_fiber_tape")

            self.assertEqual(first.asset_id, second.asset_id)
            self.assertRegex(first.asset_id, r"^video_asset_[0-9a-f]{32}$")
            self.assertNotIn("operator", first.asset_id)
            self.assertEqual(first.source_fingerprint, raw_digest_before)
            self.assertTrue(first.registry_path.is_relative_to(paths.generated_dir))
            self.assertEqual(hashlib.sha256(video.read_bytes()).hexdigest(), raw_digest_before)
            self.assertEqual(
                sorted(
                    path.relative_to(paths.raw_dir).as_posix()
                    for path in paths.raw_dir.rglob("*")
                    if path.is_file()
                ),
                raw_files_before,
            )

    def test_ffprobe_media_facts_are_not_model_inferred(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            video = (
                paths.raw_dir
                / "01_产品"
                / "02_石英纤维隔热带"
                / "03_产品视频"
                / "demo.mp4"
            )
            video.write_bytes(b"video fixture")
            commands: list[tuple[str, ...]] = []

            def runner(command, **kwargs):
                commands.append(tuple(command))
                payload = {
                    "format": {"duration": "18.750000"},
                    "streams": [
                        {
                            "codec_type": "video",
                            "codec_name": "h264",
                            "width": 1920,
                            "height": 1080,
                            "avg_frame_rate": "30000/1001",
                            "tags": {"rotate": "90"},
                        },
                        {"codec_type": "audio", "codec_name": "aac"},
                    ],
                }
                return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

            facts = probe_video_media(video, paths, ffprobe_path="/opt/bin/ffprobe", runner=runner)

            self.assertEqual(commands[0][0], "/opt/bin/ffprobe")
            self.assertIn("-show_streams", commands[0])
            self.assertIn("-show_format", commands[0])
            self.assertEqual(facts.duration_seconds, 18.75)
            self.assertEqual((facts.width, facts.height), (1920, 1080))
            self.assertAlmostEqual(facts.frame_rate, 29.97002997)
            self.assertEqual(facts.video_codec, "h264")
            self.assertEqual(facts.rotation_degrees, 90)
            self.assertTrue(facts.has_audio)
            self.assertEqual(facts.audio_codec, "aac")

    def test_adaptive_sampling_covers_beginning_middle_end(self) -> None:
        facts = VideoMediaFacts(
            duration_seconds=60.0,
            width=1920,
            height=1080,
            frame_rate=30.0,
            video_codec="h264",
            rotation_degrees=0,
            has_audio=False,
            audio_codec=None,
        )

        plan = build_video_analysis_plan(
            facts,
            detected_change_seconds=(20.0, 40.0),
            max_frames=24,
        )

        timestamps = [sample.timestamp_seconds for sample in plan.samples]
        self.assertLessEqual(timestamps[0], 1.0)
        self.assertTrue(any(27.0 <= timestamp <= 33.0 for timestamp in timestamps))
        self.assertGreaterEqual(timestamps[-1], 59.0)
        self.assertLessEqual(timestamps[-1], 59.9)
        self.assertTrue(any(abs(timestamp - 20.0) < 0.01 for timestamp in timestamps))
        self.assertTrue(any(abs(timestamp - 40.0) < 0.01 for timestamp in timestamps))
        self.assertTrue(any(sample.reason == "uniform_coverage" for sample in plan.samples))
        self.assertTrue(any(sample.reason == "detected_change" for sample in plan.samples))
        self.assertLessEqual(len(plan.samples), 24)

    def test_process_sampling_adds_before_action_after_candidates(self) -> None:
        facts = VideoMediaFacts(
            duration_seconds=30.0,
            width=1920,
            height=1080,
            frame_rate=30.0,
            video_codec="h264",
            rotation_degrees=0,
            has_audio=False,
            audio_codec=None,
        )

        plan = build_video_analysis_plan(
            facts,
            targeted_changes=(
                VideoAnalysisChange(timestamp_seconds=10.0, change_type="action_start"),
                VideoAnalysisChange(timestamp_seconds=20.0, change_type="process_state_change"),
            ),
        )

        samples = {(item.timestamp_seconds, item.reason) for item in plan.samples}
        self.assertIn((9.5, "action_start_before"), samples)
        self.assertIn((10.0, "action_start"), samples)
        self.assertIn((10.5, "action_start_after"), samples)
        self.assertIn((19.5, "process_state_change_before"), samples)
        self.assertIn((20.0, "process_state_change"), samples)
        self.assertIn((20.5, "process_state_change_after"), samples)

    def test_change_candidates_are_parsed_from_ffmpeg_scene_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            video = (
                paths.raw_dir
                / "01_产品"
                / "02_石英纤维隔热带"
                / "03_产品视频"
                / "demo.mp4"
            )
            video.write_bytes(b"video fixture")
            commands: list[tuple[str, ...]] = []

            def runner(command, **kwargs):
                commands.append(tuple(command))
                stderr = "\n".join(
                    [
                        "[Parsed_showinfo_1] n:0 pts:600 pts_time:1.25",
                        "[Parsed_showinfo_1] n:1 pts:4800 pts_time:10",
                        "[Parsed_showinfo_1] n:2 pts:9600 pts_time:20",
                        "[Parsed_showinfo_1] n:3 pts:9600 pts_time:20",
                    ]
                )
                return subprocess.CompletedProcess(command, 0, "", stderr)

            candidates = detect_video_change_candidates(
                video,
                paths,
                ffmpeg_path="/opt/bin/ffmpeg",
                runner=runner,
            )

            self.assertEqual(candidates, (1.25, 10.0, 20.0))
            self.assertEqual(commands[0][0], "/opt/bin/ffmpeg")
            self.assertTrue(any("gt(scene" in argument for argument in commands[0]))

    def test_black_blur_and_near_duplicate_frames_are_not_representatives(self) -> None:
        frames = tuple(
            ExtractedVideoFrame(timestamp_seconds=float(index), frame_path=Path(f"frame-{index}.jpg"))
            for index in range(5)
        )
        checkerboard = bytes(
            255 if (row + column) % 2 else 0
            for row in range(16)
            for column in range(16)
        )
        near_duplicate = bytearray(checkerboard)
        near_duplicate[0] = 8
        vertical_stripes = bytes(
            255 if column % 4 < 2 else 32
            for row in range(16)
            for column in range(16)
        )
        decoded = {
            frames[0].frame_path: bytes([0] * 256),
            frames[1].frame_path: bytes([128] * 256),
            frames[2].frame_path: checkerboard,
            frames[3].frame_path: bytes(near_duplicate),
            frames[4].frame_path: vertical_stripes,
        }

        result = filter_video_frame_candidates(frames, decoder=lambda path: decoded[path])

        self.assertEqual([item.frame.timestamp_seconds for item in result.accepted], [2.0, 4.0])
        self.assertEqual(
            {item.frame.timestamp_seconds: item.reason for item in result.rejected},
            {
                0.0: "black",
                1.0: "severely_blurred",
                3.0: "near_duplicate",
            },
        )

    def test_candidate_inspection_creates_a_reviewable_cache_package_without_publishing_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            video = (
                paths.raw_dir
                / "01_产品"
                / "02_石英纤维隔热带"
                / "03_产品视频"
                / "demo.mp4"
            )
            video.write_bytes(b"video fixture")

            def runner(command, **kwargs):
                if command[0] == "/opt/bin/ffprobe":
                    payload = {
                        "format": {"duration": "12.0"},
                        "streams": [
                            {
                                "codec_type": "video",
                                "codec_name": "h264",
                                "width": 1280,
                                "height": 720,
                                "avg_frame_rate": "30/1",
                            }
                        ],
                    }
                    return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
                if any("gt(scene" in argument for argument in command):
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        "",
                        "\n".join(
                            [
                                "[Parsed_showinfo_1] pts_time:4",
                                "[Parsed_showinfo_1] pts_time:8",
                            ]
                        ),
                    )
                output_path = Path(command[-1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"jpeg fixture")
                return subprocess.CompletedProcess(command, 0, "", "")

            def decoder(path: Path) -> bytes:
                index = int(path.stem.split("_")[1])
                return bytes(
                    (row * 31 + column * (index + 3) * 17 + index * 23) % 256
                    for row in range(16)
                    for column in range(16)
                )

            result = inspect_video_candidate(
                video,
                paths,
                product_id="product/quartz_fiber_tape",
                source_classification=("03_产品视频",),
                ffprobe_path="/opt/bin/ffprobe",
                ffmpeg_path="/opt/bin/ffmpeg",
                runner=runner,
                frame_decoder=decoder,
            )

            self.assertEqual(result.status, "awaiting_codex_review")
            self.assertGreaterEqual(len(result.representative_candidates), 3)
            self.assertLessEqual(len(result.representative_candidates), 6)
            self.assertTrue(result.report_path.is_file())
            self.assertTrue(result.report_path.is_relative_to(paths.generated_dir / "cache"))
            self.assertTrue(
                all(
                    item.frame.frame_path.is_relative_to(paths.generated_dir / "cache")
                    for item in result.accepted_frames
                )
            )
            self.assertTrue(
                all(item.frame.frame_path.suffix == ".png" for item in result.accepted_frames)
            )
            self.assertEqual(
                list((paths.knowledge_dir / "视频档案").rglob("*")),
                [],
            )
            report = json.loads(result.report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["asset"]["asset_id"], result.asset.asset_id)
            self.assertEqual(report["status"], "awaiting_codex_review")
            self.assertEqual(report["source_classification"], ["03_产品视频"])

    def test_candidate_batch_blocks_recommendation_when_the_fixed_folder_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            folder = (
                paths.raw_dir
                / "01_产品"
                / "02_石英纤维隔热带"
                / "03_产品视频"
            )
            (folder / "one.mp4").write_bytes(b"one")
            (folder / "two.mov").write_bytes(b"two")

            def runner(command, **kwargs):
                if command[0] == "ffprobe":
                    payload = {
                        "format": {"duration": "6.0"},
                        "streams": [
                            {
                                "codec_type": "video",
                                "codec_name": "h264",
                                "width": 1280,
                                "height": 720,
                                "avg_frame_rate": "30/1",
                            }
                        ],
                    }
                    return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
                if any("gt(scene" in argument for argument in command):
                    return subprocess.CompletedProcess(command, 0, "", "")
                output_path = Path(command[-1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"png")
                return subprocess.CompletedProcess(command, 0, "", "")

            result = inspect_video_candidate_batch(
                folder,
                paths,
                product_id="product/quartz_fiber_tape",
                expected_count=3,
                runner=runner,
                frame_decoder=lambda path: bytes(
                    (index * 37 + offset * 19) % 256
                    for index, offset in enumerate(range(256))
                ),
            )

            self.assertEqual(result.status, "blocked_source_count_mismatch")
            self.assertEqual(result.discovered_count, 2)
            self.assertEqual(result.expected_count, 3)
            self.assertFalse(result.recommendation_allowed)
            self.assertEqual(len(result.inspections), 2)
            self.assertTrue(result.report_path.is_file())

    def test_batch_recommendation_requires_all_codex_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            folder = (
                paths.raw_dir
                / "01_产品"
                / "02_石英纤维隔热带"
                / "03_产品视频"
            )
            (folder / "one.mp4").write_bytes(b"one")
            (folder / "two.mov").write_bytes(b"two")

            def runner(command, **kwargs):
                if command[0] == "ffprobe":
                    payload = {
                        "format": {"duration": "6.0"},
                        "streams": [
                            {
                                "codec_type": "video",
                                "codec_name": "h264",
                                "width": 1280,
                                "height": 720,
                                "avg_frame_rate": "30/1",
                            }
                        ],
                    }
                    return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
                if any("gt(scene" in argument for argument in command):
                    return subprocess.CompletedProcess(command, 0, "", "")
                output_path = Path(command[-1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"png")
                return subprocess.CompletedProcess(command, 0, "", "")

            batch = inspect_video_candidate_batch(
                folder,
                paths,
                product_id="product/quartz_fiber_tape",
                expected_count=2,
                runner=runner,
                frame_decoder=lambda path: bytes(
                    (row * 31 + column * (int(path.stem.split("_")[1]) + 3) * 17) % 256
                    for row in range(16)
                    for column in range(16)
                ),
            )
            review = CodexVideoCandidateReview(
                title="产品展示",
                visual_summary="画面展示白色编织带。",
                action_flow=("产品展示",),
                product_visibility="clear_identity_requires_source_context",
                observed_classifications=("product_display",),
                audio_observation="无音轨。",
                risks=("product_identity_not_confirmed_by_pixels",),
                tracer_suitability="possible",
                tracer_reason="画面清晰。",
                reviewed_representative_timestamps=(0.0, 2.0, 4.0),
            )

            self.assertEqual(batch.status, "awaiting_codex_review")
            self.assertFalse(batch.recommendation_allowed)
            record_codex_candidate_review(batch.inspections[0].report_path, paths, review)
            with self.assertRaisesRegex(ValueError, "all candidates"):
                finalize_video_candidate_batch_recommendation(
                    batch.report_path,
                    paths,
                    recommended_asset_id=batch.inspections[0].asset.asset_id,
                    reason="第一条画面更清晰。",
                )
            record_codex_candidate_review(batch.inspections[1].report_path, paths, review)
            recommendation = finalize_video_candidate_batch_recommendation(
                batch.report_path,
                paths,
                recommended_asset_id=batch.inspections[0].asset.asset_id,
                reason="第一条画面更清晰。",
            )

            self.assertEqual(recommendation.status, "awaiting_tracer_confirmation")
            updated = json.loads(batch.report_path.read_text(encoding="utf-8"))
            self.assertTrue(updated["recommendation_allowed"])
            self.assertEqual(
                updated["tracer_recommendation"]["recommended_asset_id"],
                batch.inspections[0].asset.asset_id,
            )

    def test_codex_candidate_review_is_persisted_only_in_inspection_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            report_path = (
                paths.generated_dir
                / "cache"
                / "video-tracer-inspection"
                / "fingerprint"
                / "inspection.json"
            )
            report_path.parent.mkdir(parents=True)
            report_path.write_text(
                json.dumps(
                    {
                        "status": "awaiting_codex_review",
                        "formal_profile_published": False,
                    }
                ),
                encoding="utf-8",
            )
            batch_report = (
                paths.generated_dir
                / "cache"
                / "video-tracer-inspection"
                / "batches"
                / "quartz_fiber_tape"
                / "candidate-batch.json"
            )
            batch_report.parent.mkdir(parents=True)
            batch_report.write_text(
                json.dumps(
                    {
                        "status": "blocked_source_count_mismatch",
                        "candidates": [
                            {
                                "inspection_report": str(report_path),
                                "status": "awaiting_codex_review",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            review = CodexVideoCandidateReview(
                title="卷装产品静态展示",
                visual_summary="画面持续展示一卷白色编织带，镜头逐步靠近产品。",
                action_flow=("全景展示", "靠近产品", "织纹细节展示"),
                product_visibility="clear",
                observed_classifications=("product_display",),
                audio_observation="存在音轨，语音内容尚未转录。",
                risks=("product_identity_not_confirmed_by_pixels",),
                tracer_suitability="possible",
                tracer_reason="产品清晰，但连续工艺动作有限。",
                reviewed_representative_timestamps=(0.0, 3.0, 6.0),
            )

            result = record_codex_candidate_review(report_path, paths, review)

            self.assertEqual(result.status, "codex_review_completed")
            updated = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["codex_review"]["title"], "卷装产品静态展示")
            self.assertFalse(updated["formal_profile_published"])
            updated_batch = json.loads(batch_report.read_text(encoding="utf-8"))
            self.assertEqual(updated_batch["candidates"][0]["status"], "codex_review_completed")
            self.assertEqual(
                updated_batch["candidates"][0]["codex_review"]["tracer_suitability"],
                "possible",
            )
            self.assertEqual(
                list((paths.knowledge_dir / "视频档案").rglob("*")),
                [],
            )

    def test_profile_schema_rejects_out_of_range_segments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            source = (
                paths.raw_dir
                / "01_产品"
                / "02_石英纤维隔热带"
                / "03_产品视频"
                / "demo.mp4"
            )
            source.write_bytes(b"source video bytes")
            source_fingerprint = hashlib.sha256(source.read_bytes()).hexdigest()
            report_path = (
                paths.generated_dir
                / "cache"
                / "video-tracer-inspection"
                / "fingerprint"
                / "inspection.json"
            )
            report_path.parent.mkdir(parents=True)
            report_path.write_text(
                json.dumps(
                    {
                        "status": "tracer_confirmed",
                        "asset": {
                            "asset_id": "video_asset_1234567890abcdef1234567890abcdef",
                            "product_id": "product/quartz_fiber_tape",
                            "source_relative_path": source.relative_to(paths.raw_dir).as_posix(),
                            "source_fingerprint": source_fingerprint,
                        },
                        "media_facts": {
                            "duration_seconds": 12.0,
                            "width": 1920,
                            "height": 1080,
                            "frame_rate": 30.0,
                            "video_codec": "h264",
                            "rotation_degrees": 0,
                            "has_audio": False,
                            "audio_codec": None,
                        },
                        "source_classification": ["01_产品", "02_石英纤维隔热带", "03_产品视频"],
                        "representative_candidates": [],
                        "codex_review": {"reviewer": "codex"},
                        "tracer_confirmation": {
                            "confirmed_asset_id": "video_asset_1234567890abcdef1234567890abcdef",
                        },
                        "formal_profile_published": False,
                    }
                ),
                encoding="utf-8",
            )
            proposal = {
                "title": "产品展示",
                "summary": "画面展示一卷白色编织隔热带。",
                "observed_classifications": ["product_display"],
                "product_visibility": "clear_identity_requires_source_context",
                "key_segments": [
                    {
                        "segment_id": "segment_01",
                        "start_seconds": 8.0,
                        "end_seconds": 13.0,
                        "description": "镜头靠近卷装产品。",
                        "action": "camera_approach",
                        "product_visibility": "clear_identity_requires_source_context",
                        "reuse_mode": "frame",
                        "editing_suitability": "reference-only",
                    }
                ],
                "anchor_moments": [],
                "representative_frames": [],
                "use_capabilities": ["product_detail_reference"],
                "audio_observations": [],
                "transcript_detail": {"status": "not_applicable"},
                "source_audio_use_policy": "mute-recommended",
                "observation_confidence": {"level": "medium", "reasons": [], "warnings": []},
                "risk_summary": ["product_identity_not_confirmed_by_pixels"],
                "evidence_links": [],
                "analysis_completeness": "visual_complete",
                "analysis_provenance": {
                    "semantic_reviewer": "codex",
                    "analysis_policy_revision": "video-analysis-v1",
                },
                "exclusions": [],
            }

            with self.assertRaisesRegex(ValueError, "outside video duration"):
                stage_video_profile_draft(
                    report_path,
                    paths,
                    batch_id="batch-001",
                    proposal=proposal,
                )

            self.assertFalse(
                (
                    paths.generated_dir
                    / "staging"
                    / "video-profiles"
                    / "batch-001"
                ).exists()
            )

    def test_profile_staging_rejects_changed_source_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            source = (
                paths.raw_dir
                / "01_产品"
                / "02_石英纤维隔热带"
                / "03_产品视频"
                / "demo.mp4"
            )
            source.write_bytes(b"replacement video bytes")
            report_path = (
                paths.generated_dir
                / "cache"
                / "video-tracer-inspection"
                / "fingerprint"
                / "inspection.json"
            )
            report_path.parent.mkdir(parents=True)
            report_path.write_text(
                json.dumps(
                    {
                        "status": "tracer_confirmed",
                        "asset": {
                            "asset_id": "video_asset_1234567890abcdef1234567890abcdef",
                            "product_id": "product/quartz_fiber_tape",
                            "source_relative_path": source.relative_to(paths.raw_dir).as_posix(),
                            "source_fingerprint": "a" * 64,
                        },
                        "media_facts": {"duration_seconds": 12.0},
                        "tracer_confirmation": {
                            "confirmed_asset_id": "video_asset_1234567890abcdef1234567890abcdef",
                        },
                        "formal_profile_published": False,
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "source revision no longer matches"):
                stage_video_profile_draft(
                    report_path,
                    paths,
                    batch_id="batch-001",
                    proposal={},
                )

            self.assertFalse(
                (
                    paths.generated_dir
                    / "staging"
                    / "video-profiles"
                    / "batch-001"
                ).exists()
            )

    def test_validated_profile_draft_writes_matching_markdown_and_json_to_staging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            source = (
                paths.raw_dir
                / "01_产品"
                / "02_石英纤维隔热带"
                / "03_产品视频"
                / "demo.mp4"
            )
            source.write_bytes(b"source video bytes")
            source_fingerprint = hashlib.sha256(source.read_bytes()).hexdigest()
            frame_dir = (
                paths.generated_dir
                / "cache"
                / "video-tracer-inspection"
                / "fingerprint"
                / "analysis-frames"
            )
            frame_dir.mkdir(parents=True)
            frame_paths = tuple(frame_dir / f"frame_{index:03d}.png" for index in range(3))
            for frame_path in frame_paths:
                frame_path.write_bytes(b"representative png")
            report_path = frame_dir.parent / "inspection.json"
            report_path.write_text(
                json.dumps(
                    {
                        "status": "codex_review_completed",
                        "asset": {
                            "asset_id": "video_asset_1234567890abcdef1234567890abcdef",
                            "product_id": "product/quartz_fiber_tape",
                            "source_relative_path": source.relative_to(paths.raw_dir).as_posix(),
                            "source_fingerprint": source_fingerprint,
                        },
                        "media_facts": {
                            "duration_seconds": 12.0,
                            "width": 1920,
                            "height": 1080,
                            "frame_rate": 30.0,
                            "video_codec": "h264",
                            "rotation_degrees": 0,
                            "has_audio": True,
                            "audio_codec": "aac",
                        },
                        "source_classification": ["01_产品", "02_石英纤维隔热带", "03_产品视频"],
                        "representative_candidates": [
                            {
                                "frame": {
                                    "timestamp_seconds": timestamp,
                                    "frame_path": str(frame_path),
                                },
                                "reason": "accepted",
                            }
                            for timestamp, frame_path in zip((1.0, 4.0, 9.0), frame_paths)
                        ],
                        "codex_review": {"reviewer": "codex"},
                        "formal_profile_published": False,
                    }
                ),
                encoding="utf-8",
            )
            proposal = {
                "title": "卷装石英纤维隔热带产品展示",
                "summary": "桌面上展示一卷白色编织隔热带。镜头逐步靠近，突出卷装形态和织纹。",
                "observed_classifications": ["product_display"],
                "product_visibility": "clear_identity_requires_source_context",
                "key_segments": [
                    {
                        "segment_id": "segment_01",
                        "start_seconds": 0.0,
                        "end_seconds": 11.9,
                        "description": "镜头由全景逐步靠近卷装产品。",
                        "action": "camera_approach",
                        "product_visibility": "clear_identity_requires_source_context",
                        "reuse_mode": "frame",
                        "editing_suitability": "reference-only",
                    }
                ],
                "anchor_moments": [
                    {
                        "anchor_id": f"anchor_{index:02d}",
                        "segment_id": "segment_01",
                        "timestamp_seconds": timestamp,
                        "description": "卷装产品和织纹较清晰。",
                    }
                    for index, timestamp in enumerate((1.0, 4.0, 9.0), start=1)
                ],
                "representative_frames": [
                    {
                        "anchor_id": f"anchor_{index:02d}",
                        "timestamp_seconds": timestamp,
                        "frame_path": str(frame_path),
                        "description": "卷装产品代表帧。",
                    }
                    for index, (timestamp, frame_path) in enumerate(
                        zip((1.0, 4.0, 9.0), frame_paths),
                        start=1,
                    )
                ],
                "use_capabilities": ["product_detail_reference"],
                "audio_observations": ["存在 AAC 音轨，内容尚未转录。"],
                "transcript_detail": {"status": "unavailable"},
                "source_audio_use_policy": "human-review-required",
                "observation_confidence": {
                    "level": "medium",
                    "reasons": ["多张有序画面一致"],
                    "warnings": ["产品身份需要来源上下文确认"],
                },
                "risk_summary": [
                    "product_identity_not_confirmed_by_pixels",
                    "original_audio_unreviewed",
                ],
                "evidence_links": [],
                "analysis_completeness": "visual_complete_audio_incomplete",
                "analysis_provenance": {
                    "semantic_reviewer": "codex",
                    "analysis_policy_revision": "video-analysis-v1",
                },
                "exclusions": [],
            }

            with self.assertRaisesRegex(ValueError, "explicit tracer confirmation"):
                stage_video_profile_draft(
                    report_path,
                    paths,
                    batch_id="batch-001",
                    proposal=proposal,
                )
            confirmation = confirm_video_tracer_candidate(
                report_path,
                paths,
                confirmed_asset_id="video_asset_1234567890abcdef1234567890abcdef",
            )
            unrelated_frame = (
                paths.generated_dir
                / "cache"
                / "video-tracer-inspection"
                / "other-video"
                / "analysis-frames"
                / "frame.png"
            )
            unrelated_frame.parent.mkdir(parents=True)
            unrelated_frame.write_bytes(b"unrelated frame")
            invalid_proposal = json.loads(json.dumps(proposal))
            invalid_proposal["representative_frames"][0]["frame_path"] = str(unrelated_frame)
            with self.assertRaisesRegex(ValueError, "inspected representative candidates"):
                stage_video_profile_draft(
                    report_path,
                    paths,
                    batch_id="batch-001",
                    proposal=invalid_proposal,
                )
            result = stage_video_profile_draft(
                report_path,
                paths,
                batch_id="batch-001",
                proposal=proposal,
            )

            self.assertEqual(confirmation.status, "tracer_confirmed")
            self.assertEqual(result.status, "staged_valid")
            self.assertTrue(result.markdown_path.is_file())
            self.assertTrue(result.structured_path.is_file())
            self.assertTrue(
                result.markdown_path.is_relative_to(
                    paths.generated_dir / "staging" / "video-profiles" / "batch-001"
                )
            )
            structured = json.loads(result.structured_path.read_text(encoding="utf-8"))
            markdown = result.markdown_path.read_text(encoding="utf-8")
            self.assertEqual(structured["profile_revision"], result.profile_revision)
            self.assertEqual(structured["content_digest"], result.content_digest)
            self.assertIn(f'profile_revision: "{result.profile_revision}"', markdown)
            self.assertIn(f'content_digest: "{result.content_digest}"', markdown)
            self.assertIn("视频讲了什么", markdown)
            self.assertIn("镜头由全景逐步靠近卷装产品", markdown)
            self.assertEqual(structured["processing_state"], "review_required")
            self.assertEqual(
                list((paths.knowledge_dir / "视频档案").rglob("*")),
                [],
            )

    def test_analysis_clip_is_created_only_for_temporal_need(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            video = (
                paths.raw_dir
                / "01_产品"
                / "02_石英纤维隔热带"
                / "03_产品视频"
                / "demo.mp4"
            )
            video.write_bytes(b"unchanged source video")
            commands: list[tuple[str, ...]] = []

            def runner(command, **kwargs):
                commands.append(tuple(command))
                output_path = Path(command[-1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"analysis clip")
                return subprocess.CompletedProcess(command, 0, "", "")

            skipped = prepare_video_analysis_clip(
                video,
                paths,
                start_seconds=2.0,
                end_seconds=6.0,
                temporal_need=False,
                runner=runner,
            )
            created = prepare_video_analysis_clip(
                video,
                paths,
                start_seconds=2.0,
                end_seconds=6.0,
                temporal_need=True,
                runner=runner,
            )

            self.assertIsNone(skipped)
            self.assertEqual(len(commands), 1)
            self.assertEqual(created.start_seconds, 2.0)
            self.assertEqual(created.end_seconds, 6.0)
            self.assertTrue(created.clip_path.is_file())
            self.assertTrue(
                created.clip_path.is_relative_to(
                    paths.generated_dir / "cache" / "video-analysis-clips"
                )
            )

    def test_raw_hash_is_unchanged_after_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            video = (
                paths.raw_dir
                / "01_产品"
                / "02_石英纤维隔热带"
                / "03_产品视频"
                / "demo.mp4"
            )
            video.write_bytes(b"immutable raw video bytes")
            digest_before = hashlib.sha256(video.read_bytes()).hexdigest()
            raw_files_before = sorted(
                item.relative_to(paths.raw_dir).as_posix()
                for item in paths.raw_dir.rglob("*")
                if item.is_file()
            )

            def runner(command, **kwargs):
                if command[0] == "ffprobe":
                    payload = {
                        "format": {"duration": "12.0"},
                        "streams": [
                            {
                                "codec_type": "video",
                                "codec_name": "h264",
                                "width": 1280,
                                "height": 720,
                                "avg_frame_rate": "30/1",
                            }
                        ],
                    }
                    return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
                if any("gt(scene" in argument for argument in command):
                    return subprocess.CompletedProcess(command, 0, "", "")
                output_path = Path(command[-1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"generated analysis artifact")
                return subprocess.CompletedProcess(command, 0, "", "")

            inspect_video_candidate(
                video,
                paths,
                product_id="product/quartz_fiber_tape",
                source_classification=("03_产品视频",),
                runner=runner,
                frame_decoder=lambda path: bytes(
                    (index * 29 + offset * 17) % 256
                    for index, offset in enumerate(range(256))
                ),
            )
            prepare_video_analysis_clip(
                video,
                paths,
                start_seconds=2.0,
                end_seconds=6.0,
                temporal_need=True,
                runner=runner,
            )

            self.assertEqual(hashlib.sha256(video.read_bytes()).hexdigest(), digest_before)
            self.assertEqual(
                sorted(
                    item.relative_to(paths.raw_dir).as_posix()
                    for item in paths.raw_dir.rglob("*")
                    if item.is_file()
                ),
                raw_files_before,
            )


if __name__ == "__main__":
    unittest.main()

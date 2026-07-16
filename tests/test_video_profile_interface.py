from __future__ import annotations

import json
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths
from scripts.tuolin_marketplace.video_profile_interface import (
    activate_tracer_video_profile_interface,
    authorize_video_profile_for_run,
    extract_runtime_video_clip,
    extract_runtime_video_frame,
    read_video_profile_interface_status,
    read_video_profile_catalog,
    read_video_profile_detail,
    read_runtime_video_audit,
    resolve_video_profile_media,
    search_video_profile_catalog,
)


class VideoProfileInterfaceTests(unittest.TestCase):
    def test_catalog_returns_summary_without_full_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_representative_frame(paths)
            staged_profile = (
                paths.generated_dir
                / "staging"
                / "video-profiles"
                / "batch-001"
                / "quartz_fiber_tape"
                / "video_asset_1234567890abcdef1234567890abcdef.json"
            )
            staged_profile.parent.mkdir(parents=True)
            staged_profile.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "profile_id": (
                            "video_profile/quartz_fiber_tape/"
                            "video_asset_1234567890abcdef1234567890abcdef"
                        ),
                        "video_asset_id": "video_asset_1234567890abcdef1234567890abcdef",
                        "product_id": "product/quartz_fiber_tape",
                        "profile_revision": "video_profile_rev_1234567890abcdef",
                        "source_revision": "a" * 64,
                        "content_digest": "sha256:" + "b" * 64,
                        "source_classification": [
                            "04_产品",
                            "01_石英纤维隔热带",
                            "03_视频",
                        ],
                        "observed_classifications": ["product_display"],
                        "title": "卷装石英纤维隔热带产品展示",
                        "summary": "画面展示一卷白色编织隔热带，镜头逐步靠近产品。",
                        "product_visibility": "clear_identity_requires_source_context",
                        "key_segments": [
                            {
                                "segment_id": "segment_01",
                                "start_seconds": 0.0,
                                "end_seconds": 10.0,
                                "description": "镜头由全景逐步靠近卷装产品。",
                                "reuse_mode": "frame",
                            }
                        ],
                        "representative_frames": [
                            {
                                "anchor_id": "anchor_01",
                                "timestamp_seconds": 4.0,
                                "generated_ref": (
                                    "cache/video-tracer-inspection/fingerprint/"
                                    "analysis-frames/frame.png"
                                ),
                                "description": "卷装产品代表帧。",
                            }
                        ],
                        "use_capabilities": ["product_detail_reference"],
                        "transcript_detail": {
                            "status": "available",
                            "language": "zh",
                            "segments": [
                                {
                                    "start_seconds": 0.0,
                                    "end_seconds": 2.0,
                                    "text": "这是完整转录，不应进入目录。",
                                }
                            ],
                        },
                        "source_audio_use_policy": "human-review-required",
                        "risk_summary": ["original_audio_unreviewed"],
                        "processing_state": "review_required",
                        "analysis_completeness": "visual_complete_audio_incomplete",
                        "analysis_provenance": {"semantic_reviewer": "codex"},
                        "evidence_links": [],
                        "exclusions": [],
                    }
                ),
                encoding="utf-8",
            )

            activation = activate_tracer_video_profile_interface(staged_profile, paths)
            catalog = read_video_profile_catalog(paths)

            self.assertEqual(activation.status, "active")
            self.assertEqual(len(catalog), 1)
            entry = catalog[0]
            self.assertEqual(entry["title"], "卷装石英纤维隔热带产品展示")
            self.assertEqual(
                entry["summary"],
                "画面展示一卷白色编织隔热带，镜头逐步靠近产品。",
            )
            self.assertEqual(entry["profile_revision"], "video_profile_rev_1234567890abcdef")
            self.assertNotIn("transcript_detail", entry)
            self.assertNotIn("key_segments", entry)
            self.assertNotIn("source_revision", entry)
            self.assertNotIn("这是完整转录", json.dumps(entry, ensure_ascii=False))
            self.assertEqual(
                entry["audio_summary"]["source_audio_use_policy"],
                "human-review-required",
            )

    def test_catalog_exposes_test_use_summary_without_claim_invention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            review = {
                field: "human_confirmed"
                for field in (
                    "product_identity",
                    "test_conditions",
                    "before_after_relationship",
                    "evidence_links",
                    "spoken_claims",
                    "misleading_edit_risk",
                )
            }
            _prepare_runtime_fixture(
                paths,
                test_profile={
                    "observed_classifications": ["test_validation"],
                    "summary": "画面显示带材接触热源后表面颜色发生变化。",
                    "test_context": {
                        "neutral_observation": "带材接触热源，表面颜色发生变化。",
                        "test_type": "heat_exposure",
                        "test_result_or_change": "surface_color_changed",
                    },
                    "test_risk_review": review,
                    "evidence_links": [
                        {
                            "status": "candidate",
                            "basis": "directory_proximity",
                            "supports_external_claims": False,
                            "confirmed_scope": [],
                        }
                    ],
                },
            )

            entry = read_video_profile_catalog(paths)[0]

            self.assertTrue(entry["test_summary"]["is_test_video"])
            self.assertEqual(
                entry["test_summary"]["visual_use_policy"],
                "reviewed_neutral_observation",
            )
            self.assertFalse(
                entry["test_summary"]["external_claims_allowed"]
            )
            self.assertNotIn("通过", entry["test_summary"]["neutral_observation"])

    def test_agent_detail_redacts_sensitive_transcript_segments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            profile_id = (
                "video_profile/quartz_fiber_tape/"
                "video_asset_1234567890abcdef1234567890abcdef"
            )
            staged_profile = (
                paths.generated_dir
                / "staging"
                / "video-profiles"
                / "batch-001"
                / "quartz_fiber_tape"
                / "video_asset_1234567890abcdef1234567890abcdef.json"
            )
            staged_profile.parent.mkdir(parents=True)
            staged_profile.write_text(
                json.dumps(
                    {
                        "profile_id": profile_id,
                        "video_asset_id": "video_asset_1234567890abcdef1234567890abcdef",
                        "product_id": "product/quartz_fiber_tape",
                        "profile_revision": "video_profile_rev_1234567890abcdef",
                        "source_revision": "a" * 64,
                        "content_digest": "sha256:" + "b" * 64,
                        "source_classification": ["04_应用场景素材", "汽车排气管"],
                        "observed_classifications": ["installation"],
                        "title": "安装现场",
                        "summary": "画面展示安装过程。",
                        "product_visibility": "clear",
                        "key_segments": [
                            {
                                "segment_id": "segment_01",
                                "start_seconds": 0.0,
                                "end_seconds": 10.0,
                                "description": "连续安装。",
                                "reuse_mode": "clip",
                            }
                        ],
                        "representative_frames": [],
                        "use_capabilities": ["installation_action"],
                        "transcript_detail": {
                            "status": "available",
                            "language": "zh",
                            "segments": [
                                {
                                    "start_seconds": 0.0,
                                    "end_seconds": 2.0,
                                    "text": "客户名称是星海工业。",
                                    "sensitive": True,
                                    "sensitivity_reason": "customer_identity",
                                }
                            ],
                        },
                        "source_audio_use_policy": "mute-required",
                        "audio_understanding_incomplete": False,
                        "risk_summary": ["customer_identity_in_audio"],
                        "processing_state": "review_required",
                    }
                ),
                encoding="utf-8",
            )
            activate_tracer_video_profile_interface(staged_profile, paths)

            detail = read_video_profile_detail(paths, profile_id)
            catalog = read_video_profile_catalog(paths)

            self.assertEqual(
                detail["transcript_detail"]["segments"][0]["text"],
                "[敏感内容已隐藏]",
            )
            self.assertNotIn("星海工业", json.dumps(detail, ensure_ascii=False))
            self.assertEqual(
                catalog[0]["audio_summary"]["sensitive_segment_count"],
                1,
            )

    def test_profile_detail_returns_revision_bound_representative_frames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_representative_frame(paths)
            profile_id = (
                "video_profile/quartz_fiber_tape/"
                "video_asset_1234567890abcdef1234567890abcdef"
            )
            revision = "video_profile_rev_1234567890abcdef"
            staged_profile = (
                paths.generated_dir
                / "staging"
                / "video-profiles"
                / "batch-001"
                / "quartz_fiber_tape"
                / "video_asset_1234567890abcdef1234567890abcdef.json"
            )
            staged_profile.parent.mkdir(parents=True)
            staged_profile.write_text(
                json.dumps(
                    {
                        "profile_id": profile_id,
                        "video_asset_id": "video_asset_1234567890abcdef1234567890abcdef",
                        "product_id": "product/quartz_fiber_tape",
                        "profile_revision": revision,
                        "source_revision": "a" * 64,
                        "content_digest": "sha256:" + "b" * 64,
                        "source_classification": ["04_产品", "01_石英纤维隔热带", "03_视频"],
                        "observed_classifications": ["product_display"],
                        "title": "卷装产品展示",
                        "summary": "画面展示卷装产品。",
                        "product_visibility": "clear_identity_requires_source_context",
                        "key_segments": [
                            {
                                "segment_id": "segment_01",
                                "start_seconds": 0.0,
                                "end_seconds": 10.0,
                                "description": "镜头靠近卷装产品。",
                                "reuse_mode": "frame",
                            }
                        ],
                        "representative_frames": [
                            {
                                "anchor_id": "anchor_01",
                                "timestamp_seconds": 4.0,
                                "generated_ref": (
                                    "cache/video-tracer-inspection/fingerprint/"
                                    "analysis-frames/frame.png"
                                ),
                                "description": "卷装产品代表帧。",
                            }
                        ],
                        "use_capabilities": ["product_detail_reference"],
                        "transcript_detail": {
                            "status": "available",
                            "segments": [{"text": "完整转录只在详情中出现。"}],
                        },
                        "source_audio_use_policy": "human-review-required",
                        "risk_summary": ["original_audio_unreviewed"],
                        "processing_state": "review_required",
                    }
                ),
                encoding="utf-8",
            )
            activate_tracer_video_profile_interface(staged_profile, paths)

            detail = read_video_profile_detail(paths, profile_id)

            self.assertEqual(detail["profile_revision"], revision)
            self.assertEqual(detail["key_segments"][0]["segment_id"], "segment_01")
            self.assertEqual(
                detail["transcript_detail"]["segments"][0]["text"],
                "完整转录只在详情中出现。",
            )
            frame = detail["representative_frames"][0]
            self.assertEqual(
                frame["media_ref"],
                f"video-profile-media://{revision}/01",
            )
            self.assertNotIn("generated_ref", frame)
            self.assertNotIn("cache/", json.dumps(detail["representative_frames"]))

    def test_catalog_does_not_expose_raw_or_cache_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_representative_frame(paths)
            staged_profile = (
                paths.generated_dir
                / "staging"
                / "video-profiles"
                / "batch-001"
                / "quartz_fiber_tape"
                / "video_asset_1234567890abcdef1234567890abcdef.json"
            )
            staged_profile.parent.mkdir(parents=True)
            staged_profile.write_text(
                json.dumps(
                    {
                        "profile_id": (
                            "video_profile/quartz_fiber_tape/"
                            "video_asset_1234567890abcdef1234567890abcdef"
                        ),
                        "video_asset_id": "video_asset_1234567890abcdef1234567890abcdef",
                        "product_id": "product/quartz_fiber_tape",
                        "profile_revision": "video_profile_rev_1234567890abcdef",
                        "source_revision": "a" * 64,
                        "content_digest": "sha256:" + "b" * 64,
                        "source_classification": ["04_产品", "01_石英纤维隔热带", "03_视频"],
                        "observed_classifications": ["product_display"],
                        "title": "卷装产品展示",
                        "summary": "画面展示卷装产品。",
                        "product_visibility": "clear_identity_requires_source_context",
                        "key_segments": [
                            {
                                "segment_id": "segment_01",
                                "start_seconds": 0.0,
                                "end_seconds": 10.0,
                                "description": "镜头靠近卷装产品。",
                                "reuse_mode": "frame",
                            }
                        ],
                        "representative_frames": [
                            {
                                "anchor_id": "anchor_01",
                                "timestamp_seconds": 4.0,
                                "generated_ref": (
                                    "cache/video-tracer-inspection/fingerprint/"
                                    "analysis-frames/frame.png"
                                ),
                                "description": "卷装产品代表帧。",
                            }
                        ],
                        "use_capabilities": ["product_detail_reference"],
                        "risk_summary": [],
                        "processing_state": "review_required",
                    }
                ),
                encoding="utf-8",
            )
            activate_tracer_video_profile_interface(staged_profile, paths)

            serialized = json.dumps(read_video_profile_catalog(paths), ensure_ascii=False)

            self.assertNotIn(str(paths.raw_dir), serialized)
            self.assertNotIn(str(paths.generated_dir), serialized)
            self.assertNotIn("cache/", serialized)
            self.assertNotIn("staging/", serialized)
            self.assertIn("video-profile-media://", serialized)

    def test_catalog_supports_structured_and_text_recall(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            fixture = _prepare_runtime_fixture(paths)

            matches = search_video_profile_catalog(
                paths,
                query="卷装 产品",
                product_id="product/quartz_fiber_tape",
                observed_classifications=["product_display"],
                use_capabilities=["product_detail_reference"],
            )
            misses = search_video_profile_catalog(
                paths,
                query="安装",
                product_id="product/quartz_fiber_tape",
            )

            self.assertEqual([item["profile_id"] for item in matches], [fixture["profile_id"]])
            self.assertEqual(misses, [])

    def test_representative_media_ref_resolves_without_catalog_path_leak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            frame_path = _write_representative_frame(paths)
            fixture = _prepare_runtime_fixture(paths, representative_frame=frame_path)
            detail = read_video_profile_detail(paths, fixture["profile_id"])

            resolved = resolve_video_profile_media(
                paths,
                fixture["profile_id"],
                detail["representative_frames"][0]["media_ref"],
            )

            self.assertEqual(resolved, frame_path.resolve())
            self.assertTrue(resolved.is_relative_to(paths.generated_dir.resolve()))
            self.assertNotIn(
                str(resolved),
                json.dumps(read_video_profile_catalog(paths), ensure_ascii=False),
            )

    def test_interface_reports_codex_visual_rerank_without_vector_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _prepare_runtime_fixture(paths)

            status = read_video_profile_interface_status(paths)

            self.assertIn("visual_vector_index_unavailable", status["capabilities"])
            self.assertIn("codex_visual_rerank_available", status["capabilities"])

    def test_runtime_frame_extraction_accepts_authorized_asset_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            asset_id = "video_asset_1234567890abcdef1234567890abcdef"
            profile_id = f"video_profile/quartz_fiber_tape/{asset_id}"
            source = (
                paths.raw_dir
                / "04_产品"
                / "01_石英纤维隔热带"
                / "03_视频"
                / "demo.mp4"
            )
            source.parent.mkdir(parents=True)
            source.write_bytes(b"immutable source video")
            source_revision = hashlib.sha256(source.read_bytes()).hexdigest()
            registry = paths.generated_dir / "cache" / "video-assets" / "registry.json"
            registry.parent.mkdir(parents=True)
            registry.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "assets": [
                            {
                                "asset_id": asset_id,
                                "product_id": "product/quartz_fiber_tape",
                                "source_relative_path": source.relative_to(paths.raw_dir).as_posix(),
                                "source_fingerprint": source_revision,
                                "registered_at": "2026-07-16T00:00:00+00:00",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            staged_profile = (
                paths.generated_dir
                / "staging"
                / "video-profiles"
                / "batch-001"
                / "quartz_fiber_tape"
                / f"{asset_id}.json"
            )
            staged_profile.parent.mkdir(parents=True)
            staged_profile.write_text(
                json.dumps(
                    {
                        "profile_id": profile_id,
                        "video_asset_id": asset_id,
                        "product_id": "product/quartz_fiber_tape",
                        "profile_revision": "video_profile_rev_1234567890abcdef",
                        "source_revision": source_revision,
                        "content_digest": "sha256:" + "b" * 64,
                        "source_classification": ["04_产品", "01_石英纤维隔热带", "03_视频"],
                        "observed_classifications": ["product_display"],
                        "title": "卷装产品展示",
                        "summary": "画面展示卷装产品。",
                        "product_visibility": "clear_identity_requires_source_context",
                        "key_segments": [
                            {
                                "segment_id": "segment_01",
                                "start_seconds": 2.0,
                                "end_seconds": 8.0,
                                "description": "镜头靠近卷装产品。",
                                "reuse_mode": "frame",
                            }
                        ],
                        "representative_frames": [],
                        "use_capabilities": ["product_detail_reference"],
                        "risk_summary": [],
                        "processing_state": "review_required",
                        "exclusions": [],
                    }
                ),
                encoding="utf-8",
            )
            activation = activate_tracer_video_profile_interface(staged_profile, paths)
            run_id = "run-001"
            run_dir = paths.generated_dir / "reports" / "video-creation" / run_id
            run_dir.mkdir(parents=True)
            authorize_video_profile_for_run(paths, run_id, profile_id)

            def runner(command, **kwargs):
                output_path = Path(command[-1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"runtime frame")
                return subprocess.CompletedProcess(command, 0, "", "")

            result = extract_runtime_video_frame(
                paths,
                run_id=run_id,
                interface_revision=activation.interface_revision,
                asset_id=asset_id,
                profile_revision="video_profile_rev_1234567890abcdef",
                segment_id="segment_01",
                timestamp_seconds=4.0,
                runner=runner,
            )

            self.assertEqual(result.status, "extracted")
            self.assertTrue(result.frame_path.is_file())
            self.assertTrue(result.frame_path.is_relative_to(run_dir))
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), source_revision)

    def test_runtime_frame_extraction_rejects_arbitrary_local_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            fixture = _prepare_runtime_fixture(paths)

            with self.assertRaisesRegex(PermissionError, "not authorized"):
                extract_runtime_video_frame(
                    paths,
                    run_id=fixture["run_id"],
                    interface_revision=fixture["interface_revision"],
                    asset_id=str(fixture["source"]),
                    profile_revision=fixture["profile_revision"],
                    segment_id="segment_01",
                    timestamp_seconds=4.0,
                )

            self.assertFalse(
                (
                    fixture["run_dir"]
                    / "runtime-video-frames"
                ).exists()
            )

    def test_runtime_frame_extraction_rejects_out_of_segment_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            fixture = _prepare_runtime_fixture(paths)

            with self.assertRaisesRegex(ValueError, "outside the authorized segment"):
                extract_runtime_video_frame(
                    paths,
                    run_id=fixture["run_id"],
                    interface_revision=fixture["interface_revision"],
                    asset_id=fixture["asset_id"],
                    profile_revision=fixture["profile_revision"],
                    segment_id="segment_01",
                    timestamp_seconds=9.0,
                )

            self.assertFalse(
                (
                    fixture["run_dir"]
                    / "runtime-video-frames"
                ).exists()
            )

    def test_runtime_frame_extraction_rejects_stale_profile_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            fixture = _prepare_runtime_fixture(paths)

            with self.assertRaisesRegex(ValueError, "profile revision is stale"):
                extract_runtime_video_frame(
                    paths,
                    run_id=fixture["run_id"],
                    interface_revision=fixture["interface_revision"],
                    asset_id=fixture["asset_id"],
                    profile_revision="video_profile_rev_stale0000000000",
                    segment_id="segment_01",
                    timestamp_seconds=4.0,
                )

            self.assertFalse(
                (
                    fixture["run_dir"]
                    / "runtime-video-frames"
                ).exists()
            )

    def test_runtime_frame_is_written_only_inside_video_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            fixture = _prepare_runtime_fixture(paths)

            with self.assertRaisesRegex(ValueError, "run_id"):
                extract_runtime_video_frame(
                    paths,
                    run_id="../outside",
                    interface_revision=fixture["interface_revision"],
                    asset_id=fixture["asset_id"],
                    profile_revision=fixture["profile_revision"],
                    segment_id="segment_01",
                    timestamp_seconds=4.0,
                )

            def runner(command, **kwargs):
                output_path = Path(command[-1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"runtime frame")
                return subprocess.CompletedProcess(command, 0, "", "")

            result = extract_runtime_video_frame(
                paths,
                run_id=fixture["run_id"],
                interface_revision=fixture["interface_revision"],
                asset_id=fixture["asset_id"],
                profile_revision=fixture["profile_revision"],
                segment_id="segment_01",
                timestamp_seconds=4.0,
                runner=runner,
            )

            self.assertTrue(result.frame_path.is_relative_to(fixture["run_dir"]))
            self.assertFalse((paths.generated_dir / "outside").exists())
            self.assertFalse((paths.raw_dir / "runtime-video-frames").exists())

    def test_every_runtime_extraction_attempt_is_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            fixture = _prepare_runtime_fixture(paths)

            with self.assertRaises(ValueError):
                extract_runtime_video_frame(
                    paths,
                    run_id=fixture["run_id"],
                    interface_revision=fixture["interface_revision"],
                    asset_id=fixture["asset_id"],
                    profile_revision=fixture["profile_revision"],
                    segment_id="segment_01",
                    timestamp_seconds=9.0,
                )

            def runner(command, **kwargs):
                output_path = Path(command[-1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"runtime frame")
                return subprocess.CompletedProcess(command, 0, "", "")

            extract_runtime_video_frame(
                paths,
                run_id=fixture["run_id"],
                interface_revision=fixture["interface_revision"],
                asset_id=fixture["asset_id"],
                profile_revision=fixture["profile_revision"],
                segment_id="segment_01",
                timestamp_seconds=4.0,
                runner=runner,
            )
            audit = read_runtime_video_audit(paths, fixture["run_id"])

            self.assertEqual(len(audit), 2)
            self.assertEqual([item["status"] for item in audit], ["rejected", "extracted"])
            self.assertIn("outside the authorized segment", audit[0]["reason"])
            self.assertIn("output_ref", audit[1])
            serialized = json.dumps(audit, ensure_ascii=False)
            self.assertNotIn(str(paths.raw_dir), serialized)
            self.assertNotIn("source_relative_path", serialized)

    def test_runtime_clip_extraction_rejects_unapproved_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            fixture = _prepare_runtime_fixture(paths)

            with self.assertRaisesRegex(PermissionError, "not authorized"):
                extract_runtime_video_clip(
                    paths,
                    run_id=fixture["run_id"],
                    interface_revision=fixture["interface_revision"],
                    asset_id="video_asset_ffffffffffffffffffffffffffffffff",
                    profile_revision=fixture["profile_revision"],
                    segment_id="segment_01",
                    planned_use_id="shot_02",
                    start_seconds=3.0,
                    end_seconds=6.0,
                    output_kind="candidate_preview",
                )

    def test_candidate_preview_limit_is_three_per_planned_use(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            fixture = _prepare_runtime_fixture(paths)

            def runner(command, **kwargs):
                output_path = Path(command[-1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"runtime clip")
                return subprocess.CompletedProcess(command, 0, "", "")

            for index in range(3):
                result = extract_runtime_video_clip(
                    paths,
                    run_id=fixture["run_id"],
                    interface_revision=fixture["interface_revision"],
                    asset_id=fixture["asset_id"],
                    profile_revision=fixture["profile_revision"],
                    segment_id="segment_01",
                    planned_use_id="shot_02",
                    start_seconds=2.0 + index,
                    end_seconds=4.0 + index,
                    output_kind="candidate_preview",
                    runner=runner,
                )
                self.assertEqual(result.status, "extracted")
            with self.assertRaisesRegex(ValueError, "three candidate previews"):
                extract_runtime_video_clip(
                    paths,
                    run_id=fixture["run_id"],
                    interface_revision=fixture["interface_revision"],
                    asset_id=fixture["asset_id"],
                    profile_revision=fixture["profile_revision"],
                    segment_id="segment_01",
                    planned_use_id="shot_02",
                    start_seconds=5.0,
                    end_seconds=7.0,
                    output_kind="candidate_preview",
                    runner=runner,
                )

    def test_task_clip_preserves_source_chronology(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            fixture = _prepare_runtime_fixture(paths)
            commands = []

            def runner(command, **kwargs):
                commands.append(command)
                output_path = Path(command[-1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"runtime clip")
                return subprocess.CompletedProcess(command, 0, "", "")

            result = extract_runtime_video_clip(
                paths,
                run_id=fixture["run_id"],
                interface_revision=fixture["interface_revision"],
                asset_id=fixture["asset_id"],
                profile_revision=fixture["profile_revision"],
                segment_id="segment_01",
                planned_use_id="shot_02",
                start_seconds=3.0,
                end_seconds=7.0,
                output_kind="task_clip",
                runner=runner,
            )

            command = list(commands[0])
            self.assertLess(command.index("-ss"), command.index("-i"))
            self.assertEqual(command[command.index("-ss") + 1], "3.000")
            self.assertEqual(command[command.index("-t") + 1], "4.000")
            self.assertNotIn("reverse", " ".join(command))
            self.assertEqual(result.start_seconds, 3.0)
            self.assertEqual(result.end_seconds, 7.0)
            self.assertTrue(result.clip_path.is_relative_to(fixture["run_dir"]))

    def test_only_meaning_preserving_adaptations_are_automatic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            fixture = _prepare_runtime_fixture(paths)

            with self.assertRaisesRegex(ValueError, "unsupported automatic adaptation"):
                extract_runtime_video_clip(
                    paths,
                    run_id=fixture["run_id"],
                    interface_revision=fixture["interface_revision"],
                    asset_id=fixture["asset_id"],
                    profile_revision=fixture["profile_revision"],
                    segment_id="segment_01",
                    planned_use_id="shot_02",
                    start_seconds=3.0,
                    end_seconds=7.0,
                    output_kind="task_clip",
                    adaptations={"reverse": True},
                )
            with self.assertRaisesRegex(ValueError, "crop must be explicitly confirmed"):
                extract_runtime_video_clip(
                    paths,
                    run_id=fixture["run_id"],
                    interface_revision=fixture["interface_revision"],
                    asset_id=fixture["asset_id"],
                    profile_revision=fixture["profile_revision"],
                    segment_id="segment_01",
                    planned_use_id="shot_02",
                    start_seconds=3.0,
                    end_seconds=7.0,
                    output_kind="task_clip",
                    adaptations={"crop": "1080:1920:0:0"},
                )

            commands = []

            def runner(command, **kwargs):
                commands.append(command)
                output_path = Path(command[-1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"runtime clip")
                return subprocess.CompletedProcess(command, 0, "", "")

            result = extract_runtime_video_clip(
                paths,
                run_id=fixture["run_id"],
                interface_revision=fixture["interface_revision"],
                asset_id=fixture["asset_id"],
                profile_revision=fixture["profile_revision"],
                segment_id="segment_01",
                planned_use_id="shot_02",
                start_seconds=3.0,
                end_seconds=7.0,
                output_kind="task_clip",
                adaptations={
                    "rotation_degrees": 90,
                    "resolution": "1080x1920",
                    "frame_rate": 30,
                    "crop": "1080:1920:0:0",
                    "crop_confirmed": True,
                },
                runner=runner,
            )

            self.assertEqual(result.adaptations["rotation_degrees"], 90)
            self.assertIn("transpose=1", " ".join(commands[0]))
            self.assertIn("crop=1080:1920:0:0", " ".join(commands[0]))
            self.assertNotIn("reverse", " ".join(commands[0]))

    def test_runtime_clip_enforces_profile_audio_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            fixture = _prepare_runtime_fixture(
                paths,
                source_audio_use_policy="mute-required",
            )

            with self.assertRaisesRegex(PermissionError, "original audio"):
                extract_runtime_video_clip(
                    paths,
                    run_id=fixture["run_id"],
                    interface_revision=fixture["interface_revision"],
                    asset_id=fixture["asset_id"],
                    profile_revision=fixture["profile_revision"],
                    segment_id="segment_01",
                    planned_use_id="shot_02",
                    start_seconds=3.0,
                    end_seconds=7.0,
                    output_kind="task_clip",
                    audio_policy="preserve",
                )

            commands = []

            def runner(command, **kwargs):
                commands.append(command)
                output_path = Path(command[-1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"runtime clip")
                return subprocess.CompletedProcess(command, 0, "", "")

            extract_runtime_video_clip(
                paths,
                run_id=fixture["run_id"],
                interface_revision=fixture["interface_revision"],
                asset_id=fixture["asset_id"],
                profile_revision=fixture["profile_revision"],
                segment_id="segment_01",
                planned_use_id="shot_02",
                start_seconds=3.0,
                end_seconds=7.0,
                output_kind="task_clip",
                audio_policy="mute_by_profile_policy",
                runner=runner,
            )

            self.assertIn("-an", commands[0])

    def test_runtime_test_clip_enforces_required_test_phases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            fixture = _prepare_runtime_fixture(
                paths,
                test_integrity={
                    "required_phases": [
                        {
                            "phase": "before",
                            "start_seconds": 2.0,
                            "end_seconds": 3.0,
                            "meaning_required": True,
                        },
                        {
                            "phase": "process",
                            "start_seconds": 3.0,
                            "end_seconds": 6.0,
                            "meaning_required": True,
                        },
                        {
                            "phase": "adverse_after_state",
                            "start_seconds": 6.0,
                            "end_seconds": 8.0,
                            "meaning_required": True,
                            "adverse": True,
                        },
                    ]
                },
            )

            with self.assertRaisesRegex(PermissionError, "adverse_after_state"):
                extract_runtime_video_clip(
                    paths,
                    run_id=fixture["run_id"],
                    interface_revision=fixture["interface_revision"],
                    asset_id=fixture["asset_id"],
                    profile_revision=fixture["profile_revision"],
                    segment_id="segment_01",
                    planned_use_id="shot_02",
                    start_seconds=2.0,
                    end_seconds=6.5,
                    output_kind="task_clip",
                )

            commands = []

            def runner(command, **kwargs):
                commands.append(command)
                output_path = Path(command[-1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"runtime clip")
                return subprocess.CompletedProcess(command, 0, "", "")

            result = extract_runtime_video_clip(
                paths,
                run_id=fixture["run_id"],
                interface_revision=fixture["interface_revision"],
                asset_id=fixture["asset_id"],
                profile_revision=fixture["profile_revision"],
                segment_id="segment_01",
                planned_use_id="shot_02",
                start_seconds=2.0,
                end_seconds=8.0,
                output_kind="task_clip",
                runner=runner,
            )

            self.assertEqual(result.status, "extracted")
            self.assertEqual(len(commands), 1)


def _prepare_runtime_fixture(
    paths,
    representative_frame=None,
    source_audio_use_policy="retain",
    test_integrity=None,
    test_profile=None,
):
    asset_id = "video_asset_1234567890abcdef1234567890abcdef"
    profile_id = f"video_profile/quartz_fiber_tape/{asset_id}"
    profile_revision = "video_profile_rev_1234567890abcdef"
    source = (
        paths.raw_dir
        / "04_产品"
        / "01_石英纤维隔热带"
        / "03_视频"
        / "demo.mp4"
    )
    source.parent.mkdir(parents=True)
    source.write_bytes(b"immutable source video")
    source_revision = hashlib.sha256(source.read_bytes()).hexdigest()
    registry = paths.generated_dir / "cache" / "video-assets" / "registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "assets": [
                    {
                        "asset_id": asset_id,
                        "product_id": "product/quartz_fiber_tape",
                        "source_relative_path": source.relative_to(paths.raw_dir).as_posix(),
                        "source_fingerprint": source_revision,
                        "registered_at": "2026-07-16T00:00:00+00:00",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    staged_profile = (
        paths.generated_dir
        / "staging"
        / "video-profiles"
        / "batch-001"
        / "quartz_fiber_tape"
        / f"{asset_id}.json"
    )
    staged_profile.parent.mkdir(parents=True)
    staged_profile.write_text(
        json.dumps(
            {
                "profile_id": profile_id,
                "video_asset_id": asset_id,
                "product_id": "product/quartz_fiber_tape",
                "profile_revision": profile_revision,
                "source_revision": source_revision,
                "content_digest": "sha256:" + "b" * 64,
                "source_classification": ["04_产品", "01_石英纤维隔热带", "03_视频"],
                "observed_classifications": ["product_display"],
                "title": "卷装产品展示",
                "summary": "画面展示卷装产品。",
                "product_visibility": "clear_identity_requires_source_context",
                "key_segments": [
                    {
                        "segment_id": "segment_01",
                        "start_seconds": 2.0,
                        "end_seconds": 8.0,
                        "description": "镜头靠近卷装产品。",
                        "reuse_mode": "frame",
                        **(
                            {"test_integrity": test_integrity}
                            if test_integrity is not None
                            else {}
                        ),
                    }
                ],
                "representative_frames": (
                    [
                        {
                            "anchor_id": "anchor_01",
                            "timestamp_seconds": 4.0,
                            "generated_ref": representative_frame.resolve()
                            .relative_to(paths.generated_dir.resolve())
                            .as_posix(),
                            "description": "卷装产品代表帧。",
                        }
                    ]
                    if representative_frame is not None
                    else []
                ),
                "use_capabilities": ["product_detail_reference"],
                "source_audio_use_policy": source_audio_use_policy,
                "risk_summary": [],
                "processing_state": "review_required",
                "exclusions": [],
                **(test_profile or {}),
            }
        ),
        encoding="utf-8",
    )
    activation = activate_tracer_video_profile_interface(staged_profile, paths)
    run_id = "run-001"
    run_dir = paths.generated_dir / "reports" / "video-creation" / run_id
    run_dir.mkdir(parents=True)
    authorize_video_profile_for_run(paths, run_id, profile_id)
    return {
        "asset_id": asset_id,
        "profile_id": profile_id,
        "profile_revision": profile_revision,
        "source": source,
        "source_revision": source_revision,
        "interface_revision": activation.interface_revision,
        "run_id": run_id,
        "run_dir": run_dir,
    }


def _write_representative_frame(paths):
    frame_path = (
        paths.generated_dir
        / "cache"
        / "video-tracer-inspection"
        / "fingerprint"
        / "analysis-frames"
        / "frame.png"
    )
    frame_path.parent.mkdir(parents=True, exist_ok=True)
    frame_path.write_bytes(b"representative frame")
    return frame_path


if __name__ == "__main__":
    unittest.main()

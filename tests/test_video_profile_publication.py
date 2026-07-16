from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.agent_interface import (
    knowledge_status,
    read_cards_by_type,
    rebuild_agent_interface,
)
from scripts.tuolin_marketplace.card_validator import (
    parse_frontmatter,
    validate_card_file,
)
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths
from scripts.tuolin_marketplace.video_profile_publication import (
    amend_published_video_profile,
    exclude_published_video_profile_use,
    publish_staged_video_profile,
    refresh_published_video_profile_audio,
    revoke_published_video_profile,
)
from scripts.tuolin_marketplace.video_profile_interface import (
    authorize_video_profile_for_run,
    extract_runtime_video_clip,
    read_video_profile_catalog,
    read_video_profile_detail,
)


class VideoProfilePublicationTests(unittest.TestCase):
    def test_audio_refresh_republishes_without_changing_visual_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            published = publish_staged_video_profile(
                _write_staged_profile(paths),
                paths,
            )
            before = json.loads(
                published.structured_path.read_text(encoding="utf-8")
            )
            before_interface = knowledge_status(paths)["manifest"][
                "interface_revision"
            ]

            refreshed = refresh_published_video_profile_audio(
                paths,
                before["profile_id"],
                transcript={
                    "status": "available",
                    "language": "zh",
                    "segments": [
                        {
                            "start_seconds": 0.0,
                            "end_seconds": 2.0,
                            "text": "从一端开始缠绕。",
                            "confidence": 0.92,
                        }
                    ],
                    "unrecognized_ranges": [],
                    "tool": "local-asr",
                    "model_version": "v1",
                },
                audio_observations=["清晰中文安装说明。"],
                source_audio_use_policy="retain",
            )
            after = json.loads(
                refreshed.structured_path.read_text(encoding="utf-8")
            )

            self.assertEqual(after["key_segments"], before["key_segments"])
            self.assertEqual(
                after["representative_frames"],
                before["representative_frames"],
            )
            self.assertEqual(
                after["observed_classifications"],
                before["observed_classifications"],
            )
            self.assertNotEqual(
                after["profile_revision"],
                before["profile_revision"],
            )
            self.assertNotEqual(
                refreshed.interface_revision,
                before_interface,
            )
            self.assertEqual(
                knowledge_status(paths)["manifest"]["interface_revision"],
                refreshed.interface_revision,
            )

    def test_local_profile_amendment_refreshes_interface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            published = publish_staged_video_profile(
                _write_staged_profile(paths),
                paths,
            )
            before = json.loads(
                published.structured_path.read_text(encoding="utf-8")
            )

            amended = amend_published_video_profile(
                paths,
                before["profile_id"],
                changes={
                    "summary": "画面展示卷装产品，并清楚呈现织纹细节。",
                    "risk_summary": [
                        "product_identity_requires_source_context"
                    ],
                },
                amendment_reason="补充人工复核后的画面描述",
                amended_by="reviewer",
            )
            after = json.loads(
                amended.structured_path.read_text(encoding="utf-8")
            )
            detail = json.loads(
                (
                    paths.generated_dir
                    / "agent-interface"
                    / "video-profiles"
                    / "details"
                    / f"{before['video_asset_id']}.json"
                ).read_text(encoding="utf-8")
            )

            self.assertNotEqual(
                amended.interface_revision,
                published.interface_revision,
            )
            self.assertNotEqual(
                after["profile_revision"],
                before["profile_revision"],
            )
            self.assertEqual(detail["summary"], after["summary"])
            self.assertEqual(
                after["amendments"][-1]["reason"],
                "补充人工复核后的画面描述",
            )

    def test_revocation_blocks_retrieval_extraction_and_submission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            published = publish_staged_video_profile(
                _write_staged_profile(paths),
                paths,
            )
            profile = json.loads(
                published.structured_path.read_text(encoding="utf-8")
            )
            run_id = "run-revocation"
            run_dir = paths.generated_dir / "reports" / "video-creation" / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            authorization = authorize_video_profile_for_run(
                paths,
                run_id,
                profile["profile_id"],
            )

            revoked = revoke_published_video_profile(
                paths,
                profile["profile_id"],
                reason="发现来源授权范围不清",
                revoked_by="reviewer",
            )

            self.assertEqual(revoked.status, "revoked")
            self.assertEqual(read_video_profile_catalog(paths), [])
            with self.assertRaises(KeyError):
                read_video_profile_detail(paths, profile["profile_id"])
            with self.assertRaisesRegex(PermissionError, "revoked"):
                extract_runtime_video_clip(
                    paths,
                    run_id=run_id,
                    interface_revision=authorization.interface_revision,
                    asset_id=profile["video_asset_id"],
                    profile_revision=profile["profile_revision"],
                    segment_id="segment_01",
                    planned_use_id="shot_02",
                    start_seconds=1.0,
                    end_seconds=4.0,
                    output_kind="task_clip",
                )
            authorization_data = json.loads(
                authorization.authorization_path.read_text(encoding="utf-8")
            )
            self.assertTrue(
                authorization_data["authorized_profiles"][0]["revoked"]
            )

    def test_profile_exclusion_removes_segment_from_new_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            published = publish_staged_video_profile(
                _write_staged_profile(paths),
                paths,
            )
            profile = json.loads(
                published.structured_path.read_text(encoding="utf-8")
            )

            exclude_published_video_profile_use(
                paths,
                profile["profile_id"],
                segment_ids=["segment_01"],
                reason="该片段含未获授权的客户标识",
                excluded_by="reviewer",
            )
            run_id = "run-exclusion"
            run_dir = paths.generated_dir / "reports" / "video-creation" / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            authorization = authorize_video_profile_for_run(
                paths,
                run_id,
                profile["profile_id"],
            )
            authorization_data = json.loads(
                authorization.authorization_path.read_text(encoding="utf-8")
            )

            self.assertEqual(
                authorization_data["authorized_profiles"][0]["segments"],
                [],
            )

    def test_video_profile_markdown_and_json_share_revision_and_digest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            staged = _write_staged_profile(paths)

            result = publish_staged_video_profile(staged, paths)
            frontmatter = parse_frontmatter(result.markdown_path.read_text(encoding="utf-8"))
            structured = json.loads(result.structured_path.read_text(encoding="utf-8"))

            self.assertEqual(frontmatter["profile_revision"], structured["profile_revision"])
            self.assertEqual(frontmatter["content_digest"], structured["content_digest"])
            self.assertEqual(frontmatter["id"], structured["profile_id"])

    def test_missing_profile_counterpart_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            markdown = (
                paths.knowledge_dir
                / "视频档案"
                / "quartz_fiber_tape"
                / "video_asset_1234567890abcdef1234567890abcdef.md"
            )
            markdown.parent.mkdir(parents=True, exist_ok=True)
            markdown.write_text(_formal_markdown(), encoding="utf-8")

            result = validate_card_file(markdown)

            self.assertFalse(result.valid)
            self.assertIn("missing video profile JSON counterpart", result.errors)

    def test_conflicting_profile_pair_is_not_indexed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            staged = _write_staged_profile(paths)
            result = publish_staged_video_profile(staged, paths)
            structured = json.loads(result.structured_path.read_text(encoding="utf-8"))
            structured["profile_revision"] = "video_profile_rev_conflicting"
            result.structured_path.write_text(
                json.dumps(structured, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            summary = rebuild_agent_interface(paths)

            self.assertEqual(read_cards_by_type(paths, "video_profile", include_non_official=True), [])
            self.assertGreater(summary["validation_error_count"], 0)

    def test_staged_profile_is_invisible_to_downstream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_staged_profile(paths)

            rebuild_agent_interface(paths)

            self.assertEqual(read_cards_by_type(paths, "video_profile", include_non_official=True), [])

    def test_successful_publication_activates_new_interface_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            rebuild_agent_interface(paths)
            previous_revision = knowledge_status(paths)["manifest"]["interface_revision"]
            staged = _write_staged_profile(paths)

            result = publish_staged_video_profile(staged, paths)
            current = knowledge_status(paths)
            catalog = json.loads(
                (
                    paths.generated_dir
                    / "agent-interface"
                    / "video-profiles"
                    / "catalog.json"
                ).read_text(encoding="utf-8")
            )

            self.assertEqual(result.status, "published")
            self.assertNotEqual(result.interface_revision, previous_revision)
            self.assertEqual(result.interface_revision, current["manifest"]["interface_revision"])
            self.assertEqual(catalog[0]["profile_id"], result.profile_id)
            self.assertFalse(catalog[0]["test_summary"]["is_test_video"])

    def test_test_video_publication_requires_completed_human_risk_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            staged = _write_staged_profile(paths)
            profile = json.loads(staged.read_text(encoding="utf-8"))
            profile.update(
                {
                    "source_classification": [
                        "01_产品",
                        "02_石英纤维隔热带",
                        "05_测试验证素材",
                    ],
                    "observed_classifications": ["test_validation"],
                    "test_context": {
                        "neutral_observation": "带材接触热源，表面颜色发生变化。",
                        "test_type": "heat_exposure",
                        "product_identity": "confirmed_from_source_context",
                        "test_conditions": "temperature_not_visible",
                        "before_after_relationship": "continuous_sequence",
                        "test_result_or_change": "surface_color_changed",
                    },
                    "test_risk_review": {
                        field: "machine_reviewed"
                        for field in (
                            "product_identity",
                            "test_conditions",
                            "before_after_relationship",
                            "evidence_links",
                            "spoken_claims",
                            "misleading_edit_risk",
                        )
                    },
                }
            )
            staged.write_text(
                json.dumps(profile, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "human review"):
                publish_staged_video_profile(staged, paths)

    def test_failed_interface_verification_keeps_previous_revision_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            rebuild_agent_interface(paths)
            previous_revision = knowledge_status(paths)["manifest"]["interface_revision"]
            staged = _write_staged_profile(paths)

            def fail_verification(_paths, _profile):
                raise RuntimeError("injected interface verification failure")

            with self.assertRaisesRegex(RuntimeError, "injected interface verification failure"):
                publish_staged_video_profile(
                    staged,
                    paths,
                    interface_verifier=fail_verification,
                )

            self.assertEqual(
                knowledge_status(paths)["manifest"]["interface_revision"],
                previous_revision,
            )
            formal_root = paths.knowledge_dir / "视频档案" / "quartz_fiber_tape"
            self.assertFalse(
                (formal_root / "video_asset_1234567890abcdef1234567890abcdef.md").exists()
            )
            self.assertFalse(
                (formal_root / "video_asset_1234567890abcdef1234567890abcdef.json").exists()
            )

    def test_video_profile_paths_use_asset_id_not_raw_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            result = publish_staged_video_profile(_write_staged_profile(paths), paths)

            self.assertEqual(
                result.markdown_path.name,
                "video_asset_1234567890abcdef1234567890abcdef.md",
            )
            self.assertNotIn("现场拍摄", str(result.markdown_path))
            self.assertTrue(result.markdown_path.is_relative_to(paths.knowledge_dir))

    def test_generated_analysis_media_is_not_scanned_as_formal_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            generated_markdown = (
                paths.generated_dir
                / "cache"
                / "video-tracer-inspection"
                / "analysis.md"
            )
            generated_markdown.parent.mkdir(parents=True, exist_ok=True)
            generated_markdown.write_text(_formal_markdown(), encoding="utf-8")

            summary = rebuild_agent_interface(paths)

            self.assertEqual(summary["counts_by_type"]["video_profile"], 0)
            self.assertEqual(read_cards_by_type(paths, "video_profile", include_non_official=True), [])


def _write_staged_profile(paths) -> Path:
    asset_id = "video_asset_1234567890abcdef1234567890abcdef"
    revision = "video_profile_rev_1234567890abcdef"
    digest = "sha256:" + "b" * 64
    frame = (
        paths.generated_dir
        / "cache"
        / "video-tracer-inspection"
        / "fingerprint"
        / "analysis-frames"
        / "frame.png"
    )
    frame.parent.mkdir(parents=True, exist_ok=True)
    frame.write_bytes(b"representative frame")
    root = (
        paths.generated_dir
        / "staging"
        / "video-profiles"
        / "batch-001"
        / "quartz_fiber_tape"
    )
    root.mkdir(parents=True, exist_ok=True)
    structured = {
        "schema_version": "1.0",
        "profile_id": f"video_profile/quartz_fiber_tape/{asset_id}",
        "video_asset_id": asset_id,
        "product_id": "product/quartz_fiber_tape",
        "profile_revision": revision,
        "content_digest": digest,
        "source_revision": "a" * 64,
        "source_classification": ["01_产品", "02_石英纤维隔热带", "03_产品视频"],
        "observed_classifications": ["product_display"],
        "title": "卷装石英纤维隔热带产品展示",
        "summary": "画面展示一卷白色编织隔热带，镜头逐步靠近产品。",
        "duration": 12.0,
        "media_facts": {"duration_seconds": 12.0, "width": 1920, "height": 1080},
        "product_visibility": "clear_identity_requires_source_context",
        "key_segments": [
            {
                "segment_id": "segment_01",
                "start_seconds": 0.0,
                "end_seconds": 10.0,
                "description": "镜头由全景逐步靠近卷装产品。",
                "action": "camera_approach",
                "product_visibility": "clear_identity_requires_source_context",
                "reuse_mode": "clip",
                "editing_suitability": "usable",
            }
        ],
        "anchor_moments": [
            {
                "anchor_id": "anchor_01",
                "segment_id": "segment_01",
                "timestamp_seconds": 4.0,
                "description": "卷装产品清晰可见。",
            }
        ],
        "representative_frames": [
            {
                "anchor_id": "anchor_01",
                "timestamp_seconds": 4.0,
                "generated_ref": frame.relative_to(paths.generated_dir).as_posix(),
                "description": "卷装产品代表帧。",
            }
        ],
        "use_capabilities": ["product_detail_reference"],
        "audio_observations": [],
        "transcript_detail": {"status": "unavailable"},
        "source_audio_use_policy": "human-review-required",
        "observation_confidence": {"level": "medium"},
        "risk_summary": ["original_audio_unreviewed"],
        "evidence_links": [],
        "processing_state": "review_required",
        "analysis_completeness": "visual_complete_audio_incomplete",
        "analysis_provenance": {"semantic_reviewer": "codex"},
        "exclusions": [],
    }
    structured_path = root / f"{asset_id}.json"
    structured_path.write_text(
        json.dumps(structured, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (root / f"{asset_id}.md").write_text(
        "\n".join(
            [
                "---",
                'type: "video_profile_draft"',
                f'id: "{structured["profile_id"]}"',
                f'profile_revision: "{revision}"',
                f'content_digest: "{digest}"',
                "---",
                "",
                structured["summary"],
            ]
        ),
        encoding="utf-8",
    )
    return structured_path


def _formal_markdown() -> str:
    return "\n".join(
        [
            "---",
            "card_template_version: video-profile-card-v1",
            "type: video_profile",
            "id: video_profile/quartz_fiber_tape/video_asset_1234567890abcdef1234567890abcdef",
            "title: 卷装产品展示",
            "aliases: []",
            "status: review_required",
            "usage_scope: review_before_external",
            "raw_partitions:",
            "  - raw/01_产品/02_石英纤维隔热带/03_产品视频/",
            "tags:",
            "  - 视频档案",
            "updated_at: 2026-07-16T00:00:00+08:00",
            "last_reviewed_at: 2026-07-16T00:00:00+08:00",
            "evidence_refs: []",
            "review_refs: []",
            "video_asset_id: video_asset_1234567890abcdef1234567890abcdef",
            "product_id: product/quartz_fiber_tape",
            "profile_revision: video_profile_rev_1234567890abcdef",
            "content_digest: sha256:" + "b" * 64,
            "processing_state: review_required",
            "use_capabilities:",
            "  - product_detail_reference",
            "---",
            "",
            "# 视频讲了什么",
            "",
            "画面展示卷装产品。",
        ]
    )

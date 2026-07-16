from __future__ import annotations

from datetime import datetime, timezone
import json
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.project_layout import (
    initialize_project,
    resolve_paths,
)
from scripts.tuolin_marketplace.video_profile_maintenance import (
    ReanalysisRequired,
    cleanup_video_profile_cache,
    migrate_video_profile_schema,
    reconcile_video_asset_identity,
    register_video_cache_entry,
    write_video_cache_manifest,
)
from scripts.tuolin_marketplace.video_profiles import register_video_asset


class VideoProfileMaintenanceTests(unittest.TestCase):
    def test_cache_cleanup_uses_manifest_and_live_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            stale = paths.generated_dir / "cache" / "video-analysis" / "stale.png"
            fresh = paths.generated_dir / "cache" / "video-analysis" / "fresh.png"
            unmanaged = (
                paths.generated_dir
                / "cache"
                / "video-analysis"
                / "unmanaged.png"
            )
            for path in (stale, fresh, unmanaged):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(path.name.encode("utf-8"))
            write_video_cache_manifest(
                paths,
                [
                    {
                        "cache_ref": stale.relative_to(
                            paths.generated_dir
                        ).as_posix(),
                        "kind": "analysis_frame",
                        "state": "complete",
                        "last_used_at": "2026-05-01T00:00:00+00:00",
                    },
                    {
                        "cache_ref": fresh.relative_to(
                            paths.generated_dir
                        ).as_posix(),
                        "kind": "analysis_frame",
                        "state": "complete",
                        "last_used_at": "2026-07-10T00:00:00+00:00",
                    },
                ],
            )

            result = cleanup_video_profile_cache(
                paths,
                now=datetime(2026, 7, 16, tzinfo=timezone.utc),
            )

            self.assertFalse(stale.exists())
            self.assertTrue(fresh.exists())
            self.assertTrue(unmanaged.exists())
            self.assertEqual(
                result["deleted_refs"],
                [stale.relative_to(paths.generated_dir).as_posix()],
            )

    def test_current_representative_frames_are_not_cleaned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            frame = (
                paths.generated_dir
                / "cache"
                / "video-tracer-inspection"
                / "fingerprint"
                / "analysis-frames"
                / "representative.png"
            )
            frame.parent.mkdir(parents=True, exist_ok=True)
            frame.write_bytes(b"current representative")
            profile = (
                paths.knowledge_dir
                / "视频档案"
                / "quartz_fiber_tape"
                / "video_asset_1234567890abcdef1234567890abcdef.json"
            )
            profile.parent.mkdir(parents=True, exist_ok=True)
            profile.write_text(
                json.dumps(
                    {
                        "profile_revision": "video_profile_rev_current0001",
                        "representative_frames": [
                            {
                                "generated_ref": frame.relative_to(
                                    paths.generated_dir
                                ).as_posix()
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            write_video_cache_manifest(
                paths,
                [
                    {
                        "cache_ref": frame.relative_to(
                            paths.generated_dir
                        ).as_posix(),
                        "kind": "representative_frame",
                        "state": "complete",
                        "profile_revision": "video_profile_rev_current0001",
                        "last_used_at": "2026-05-01T00:00:00+00:00",
                    }
                ],
            )

            result = cleanup_video_profile_cache(
                paths,
                now=datetime(2026, 7, 16, tzinfo=timezone.utc),
            )

            self.assertTrue(frame.exists())
            self.assertEqual(
                result["retained_refs"],
                [frame.relative_to(paths.generated_dir).as_posix()],
            )

    def test_disputed_cache_is_retained(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            disputed = (
                paths.generated_dir
                / "cache"
                / "video-analysis"
                / "disputed.png"
            )
            disputed.parent.mkdir(parents=True, exist_ok=True)
            disputed.write_bytes(b"disputed")
            write_video_cache_manifest(
                paths,
                [
                    {
                        "cache_ref": disputed.relative_to(
                            paths.generated_dir
                        ).as_posix(),
                        "kind": "analysis_frame",
                        "state": "disputed",
                        "last_used_at": "2026-01-01T00:00:00+00:00",
                    }
                ],
            )

            result = cleanup_video_profile_cache(
                paths,
                now=datetime(2026, 7, 16, tzinfo=timezone.utc),
            )

            self.assertTrue(disputed.exists())
            self.assertEqual(
                result["retained_refs"],
                [disputed.relative_to(paths.generated_dir).as_posix()],
            )

    def test_raw_video_is_never_classified_as_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            raw_video = paths.raw_dir / "产品视频" / "source.mp4"
            raw_video.parent.mkdir(parents=True, exist_ok=True)
            raw_video.write_bytes(b"immutable raw")

            with self.assertRaisesRegex(ValueError, "generated/cache"):
                register_video_cache_entry(
                    paths,
                    raw_video,
                    kind="analysis_source",
                    state="complete",
                    last_used_at="2026-07-16T00:00:00+00:00",
                )

    def test_verified_move_preserves_asset_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            original = paths.raw_dir / "旧目录" / "demo.mp4"
            moved = paths.raw_dir / "新目录" / "demo-renamed.mp4"
            original.parent.mkdir(parents=True, exist_ok=True)
            original.write_bytes(b"same video bytes")
            registered = register_video_asset(
                original,
                paths,
                product_id="product/quartz_fiber_tape",
            )
            moved.parent.mkdir(parents=True, exist_ok=True)
            original.rename(moved)

            reconciled = reconcile_video_asset_identity(
                moved,
                paths,
                product_id="product/quartz_fiber_tape",
            )

            self.assertEqual(reconciled["status"], "verified_move")
            self.assertEqual(reconciled["asset_id"], registered.asset_id)
            self.assertEqual(
                reconciled["source_relative_path"],
                moved.relative_to(paths.raw_dir).as_posix(),
            )

    def test_concurrent_copy_receives_new_asset_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            original = paths.raw_dir / "目录甲" / "demo.mp4"
            copied = paths.raw_dir / "目录乙" / "demo-copy.mp4"
            original.parent.mkdir(parents=True, exist_ok=True)
            original.write_bytes(b"same video bytes")
            registered = register_video_asset(
                original,
                paths,
                product_id="product/quartz_fiber_tape",
            )
            copied.parent.mkdir(parents=True, exist_ok=True)
            copied.write_bytes(original.read_bytes())

            reconciled = reconcile_video_asset_identity(
                copied,
                paths,
                product_id="product/quartz_fiber_tape",
            )

            self.assertEqual(reconciled["status"], "concurrent_copy")
            self.assertNotEqual(reconciled["asset_id"], registered.asset_id)
            self.assertIn(
                registered.asset_id,
                reconciled["duplicate_of_asset_ids"],
            )
            self.assertTrue(reconciled["asset_family_id"])

    def test_same_path_replacement_creates_new_source_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            source = paths.raw_dir / "产品视频" / "demo.mp4"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(b"old source revision")
            registered = register_video_asset(
                source,
                paths,
                product_id="product/quartz_fiber_tape",
            )
            source.write_bytes(b"new source revision")

            reconciled = reconcile_video_asset_identity(
                source,
                paths,
                product_id="product/quartz_fiber_tape",
            )

            self.assertEqual(reconciled["status"], "source_revised")
            self.assertEqual(reconciled["asset_id"], registered.asset_id)
            self.assertNotEqual(
                reconciled["source_fingerprint"],
                registered.source_fingerprint,
            )
            self.assertIn(
                registered.source_fingerprint,
                reconciled["source_revision_history"],
            )

    def test_ambiguous_move_or_copy_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            original = paths.raw_dir / "目录甲" / "demo.mp4"
            copied = paths.raw_dir / "目录乙" / "demo-copy.mp4"
            discovered = paths.raw_dir / "目录丙" / "demo-found.mp4"
            original.parent.mkdir(parents=True, exist_ok=True)
            original.write_bytes(b"same video bytes")
            register_video_asset(
                original,
                paths,
                product_id="product/quartz_fiber_tape",
            )
            copied.parent.mkdir(parents=True, exist_ok=True)
            copied.write_bytes(original.read_bytes())
            reconcile_video_asset_identity(
                copied,
                paths,
                product_id="product/quartz_fiber_tape",
            )
            payload = original.read_bytes()
            original.unlink()
            copied.unlink()
            discovered.parent.mkdir(parents=True, exist_ok=True)
            discovered.write_bytes(payload)

            reconciled = reconcile_video_asset_identity(
                discovered,
                paths,
                product_id="product/quartz_fiber_tape",
            )

            self.assertEqual(reconciled["status"], "review_required")
            self.assertEqual(
                reconciled["reason"],
                "ambiguous_move_or_copy",
            )
            self.assertEqual(len(reconciled["candidate_asset_ids"]), 2)

    def test_semantic_schema_change_requires_reanalysis_not_default_migration(self) -> None:
        profile = {
            "schema_version": "1.0",
            "profile_id": "video_profile/quartz_fiber_tape/video_asset_123",
            "summary": "画面展示带材。",
        }

        with self.assertRaisesRegex(ReanalysisRequired, "reanalysis"):
            migrate_video_profile_schema(
                profile,
                target_schema_version="2.0",
                required_new_semantic_fields=[
                    "test_conditions",
                    "before_after_relationship",
                ],
            )

        self.assertEqual(profile["schema_version"], "1.0")
        self.assertNotIn("test_conditions", profile)


if __name__ == "__main__":
    unittest.main()

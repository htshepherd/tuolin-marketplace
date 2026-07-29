from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.agent_interface import rebuild_agent_interface
from scripts.tuolin_marketplace.avatar_video_agent import (
    confirm_avatar_inputs,
    confirm_avatar_presenter,
    confirm_avatar_production_plan,
    create_avatar_video_run,
    generate_heygen_presenter,
    generate_mock_avatar_inputs,
    record_avatar_material_inspection,
    write_avatar_production_plan,
)
from scripts.tuolin_marketplace.avatar_video.provider_adapters import HeyGenAdapter
from scripts.tuolin_marketplace.avatar_video.providers import read_provider_attempts
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe required")
class HeyGenAdapterTests(unittest.TestCase):
    def test_adapter_uploads_confirmed_audio_uses_fixed_avatar_and_downloads_video(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths, image_path = _project(root)
            run = _run_ready_for_heygen(paths, image_path)
            video_bytes = _video_bytes(root)
            calls = []

            def transport(method, url, headers, body, timeout):
                calls.append({"method": method, "url": url, "headers": headers, "body": body})
                if url.endswith("/v1/asset"):
                    return {"status": 200, "json": {"data": {"id": "audio-asset-1"}}}
                if url.endswith("/v2/video/generate"):
                    return {"status": 200, "json": {"data": {"video_id": "video-1", "credits_used": 2}}}
                if "video_status.get" in url:
                    return {"status": 200, "json": {"data": {"status": "completed", "video_url": "https://download.test/video.mp4"}}}
                if url == "https://download.test/video.mp4":
                    return {"status": 200, "body": video_bytes}
                raise AssertionError(url)

            adapter = HeyGenAdapter(api_key="super-secret-heygen", transport=transport, sleep=lambda _: None)
            generated = generate_heygen_presenter(run, adapter)
            self.assertEqual(generated.status, "completed_pending_review")
            create_call = next(call for call in calls if call["url"].endswith("/v2/video/generate"))
            video_input = create_call["body"]["video_inputs"][0]
            self.assertEqual(video_input["character"]["avatar_id"], "fixed-public-avatar")
            self.assertEqual(video_input["voice"]["audio_asset_id"], "audio-asset-1")
            attempt_text = "\n".join(path.read_text(encoding="utf-8") for path in (Path(run) / "providers").glob("*.json"))
            self.assertNotIn("super-secret-heygen", attempt_text)
            confirmed = confirm_avatar_presenter(run)
            self.assertEqual(confirmed.phase, "ready_for_composition")
            attempt = read_provider_attempts(Path(run), "heygen")[0]
            self.assertEqual(attempt["external_task_id"], "video-1")
            self.assertEqual(attempt["settings"]["avatar_id"], "fixed-public-avatar")
            self.assertEqual(attempt["status"], "accepted")

    def test_failed_status_is_recorded_and_does_not_reach_composition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths, image_path = _project(root)
            run = _run_ready_for_heygen(paths, image_path)

            def transport(method, url, headers, body, timeout):
                if url.endswith("/v1/asset"):
                    return {"status": 200, "json": {"data": {"id": "audio-asset-1"}}}
                if url.endswith("/v2/video/generate"):
                    return {"status": 200, "json": {"data": {"video_id": "video-failed"}}}
                return {"status": 200, "json": {"data": {"status": "failed", "error": "moderation"}}}

            adapter = HeyGenAdapter(api_key="secret", transport=transport, sleep=lambda _: None)
            with self.assertRaisesRegex(RuntimeError, "任务失败"):
                generate_heygen_presenter(run, adapter)
            state = json.loads((Path(run) / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["phase"], "awaiting_retry_authorization")
            self.assertEqual(read_provider_attempts(Path(run), "heygen")[0]["status"], "failed")


def _run_ready_for_heygen(paths, image_path: Path) -> Path:
    run = create_avatar_video_run(
        paths,
        "HeyGen adapter",
        product_id="product/quartz_fiber_tape",
        language_version="en",
        duration_seconds=30,
        initial_brief={
            "audience": "Industrial buyers", "reason_to_watch": "Quick review", "takeaway": "Product identity",
            "viewer_action": "Ask for data", "priority_information": "Product appearance",
            "exclusions": "No unsupported claims", "presenter_evidence_treatment": "Presenter and evidence",
        },
        invoked_skill="$tuolin-avatar-video",
        test_mode=True,
    )
    root = Path(run.run_dir)
    record_avatar_material_inspection(
        root,
        {"path": str(image_path), "subject": "product", "clarity": "clear", "composition": "centered", "vertical_crop": "usable", "near_duplicate_group": "p1", "status": "usable", "risks": []},
    )
    write_avatar_production_plan(
        root,
        {
            "narration": "Exact approved narration.",
            "timeline": [
                {"start_seconds": 0, "end_seconds": 15, "mode": "presenter", "purpose": "intro"},
                {"start_seconds": 15, "end_seconds": 30, "mode": "evidence", "purpose": "product"},
            ],
            "selected_visuals": [{"path": str(image_path), "purpose": "product_evidence"}],
            "fish_audio": {"voice_id": "fish-voice"},
            "heygen": {"avatar_id": "fixed-public-avatar", "avatar_version": "public-v1", "commercial_use_basis": "paid_public_avatar"},
            "estimated_consumption": {"fish_audio": 0, "heygen": 2},
        },
    )
    confirm_avatar_production_plan(root)
    generate_mock_avatar_inputs(root)
    confirm_avatar_inputs(root)
    return root


def _project(root: Path):
    paths = resolve_paths(root, {})
    initialize_project(paths)
    _write_card(
        paths.knowledge_dir / "产品" / "product.md",
        [
            "card_template_version: product-card-v1", "type: product", "id: product/quartz_fiber_tape", "title: Quartz Tape",
            "aliases: []", "status: official", "usage_scope: external_allowed", "product_line: Tape", "raw_partitions: []", "tags: []",
            "updated_at: 2026-07-29T00:00:00+00:00", "last_reviewed_at: 2026-07-29T00:00:00+00:00", "evidence_refs: []", "related_refs: []", "review_refs: []",
        ],
        "Official product.",
    )
    image_path = paths.raw_dir / "product.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=gray:s=640x640:d=0.1", "-frames:v", "1", str(image_path)], capture_output=True, check=True)
    rel = image_path.relative_to(paths.project_dir).as_posix()
    _write_card(
        paths.knowledge_dir / "内容素材" / "image.md",
        [
            "card_template_version: content-asset-card-v1", "type: content_asset", "id: content_asset/product", "title: Product image",
            "aliases: []", "status: official", "usage_scope: external_allowed", "raw_partitions: []", "tags: []",
            "updated_at: 2026-07-29T00:00:00+00:00", "last_reviewed_at: 2026-07-29T00:00:00+00:00", "evidence_refs: []", "review_refs: []",
            "asset_category: product image", "human_face_risk: false", "media_types: [image]",
            "related_products: [product/quartz_fiber_tape]", f"files: [{rel}]", "usable_for: [avatar_video]",
        ],
        "Official image.",
    )
    rebuild_agent_interface(paths)
    return paths, image_path


def _video_bytes(root: Path) -> bytes:
    path = root / "heygen-fixture.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1080x1920:r=10:d=30",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "30", "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path),
        ],
        capture_output=True,
        check=True,
    )
    return path.read_bytes()


def _write_card(path: Path, frontmatter: list[str], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + "\n".join(frontmatter) + "\n---\n\n" + body + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()

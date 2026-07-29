from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.avatar_video_agent import (
    accept_avatar_delivery,
    compose_avatar_video,
    confirm_avatar_inputs,
    confirm_avatar_presenter,
    confirm_avatar_production_plan,
    create_avatar_video_run,
    generate_fish_audio_input,
    generate_heygen_presenter,
    get_avatar_final_review,
    record_avatar_material_inspection,
    write_avatar_production_plan,
)
from scripts.tuolin_marketplace.avatar_video.provider_adapters import FishAudioAdapter, HeyGenAdapter
from tests.test_avatar_video_heygen_adapter import _project, _video_bytes


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe required")
class AvatarVideoDeliveryTests(unittest.TestCase):
    def test_confirmed_real_adapter_outputs_create_immutable_local_delivery_without_publish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths, image_path = _project(workspace)
            run = create_avatar_video_run(
                paths,
                "Accepted local delivery",
                product_id="product/quartz_fiber_tape",
                language_version="en",
                duration_seconds=30,
                initial_brief={
                    "audience": "Industrial buyers",
                    "reason_to_watch": "Quick product review",
                    "takeaway": "Know the product identity",
                    "viewer_action": "Ask for data",
                    "priority_information": "Official product appearance",
                    "exclusions": "No unsupported claims",
                    "presenter_evidence_treatment": "Presenter and full-screen evidence",
                },
                invoked_skill="$tuolin-avatar-video",
                test_mode=False,
            )
            root = Path(run.run_dir)
            record_avatar_material_inspection(
                root,
                {"path": str(image_path), "subject": "product", "clarity": "clear", "composition": "centered", "vertical_crop": "usable", "near_duplicate_group": "p1", "status": "usable", "risks": []},
            )
            write_avatar_production_plan(
                root,
                {
                    "narration": "This is the exact approved product narration.",
                    "timeline": [
                        {"start_seconds": 0, "end_seconds": 15, "mode": "presenter", "purpose": "intro"},
                        {"start_seconds": 15, "end_seconds": 30, "mode": "evidence", "purpose": "product"},
                    ],
                    "selected_visuals": [{"path": str(image_path), "purpose": "product_evidence"}],
                    "fish_audio": {"voice_id": "fixed-fish-voice"},
                    "heygen": {"avatar_id": "fixed-public-avatar", "avatar_version": "public-v1", "commercial_use_basis": "paid_public_avatar"},
                    "estimated_consumption": {"fish_audio": 1, "heygen": 2},
                },
            )
            confirm_avatar_production_plan(root)
            audio_bytes = _audio_bytes(workspace)

            def fish_transport(url, headers, payload, timeout):
                return {"status": 200, "headers": {"x-request-id": "fish-real-contract"}, "body": audio_bytes}

            generate_fish_audio_input(root, FishAudioAdapter(api_key="fish-secret", transport=fish_transport))
            confirm_avatar_inputs(root)
            video_bytes = _video_bytes(workspace)

            def heygen_transport(method, url, headers, body, timeout):
                if url.endswith("/v1/asset"):
                    return {"status": 200, "json": {"data": {"id": "audio-asset"}}}
                if url.endswith("/v2/video/generate"):
                    return {"status": 200, "json": {"data": {"video_id": "heygen-real-contract", "credits_used": 2}}}
                if "video_status.get" in url:
                    return {"status": 200, "json": {"data": {"status": "completed", "video_url": "https://fixture/video.mp4"}}}
                return {"status": 200, "body": video_bytes}

            generate_heygen_presenter(root, HeyGenAdapter(api_key="heygen-secret", transport=heygen_transport, sleep=lambda _: None))
            confirm_avatar_presenter(root)
            compose_avatar_video(root)
            review = get_avatar_final_review(root)
            self.assertEqual(review.status, "awaiting_confirmation")
            self.assertFalse((root / "delivery" / "accepted").exists())

            conflict = root / "delivery" / "accepted"
            conflict.mkdir()
            with self.assertRaisesRegex(FileExistsError, "拒绝覆盖"):
                accept_avatar_delivery(root)
            state_after_conflict = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state_after_conflict["phase"], "awaiting_final_confirmation")
            shutil.rmtree(conflict)

            accepted = accept_avatar_delivery(root)
            self.assertEqual(accepted.status, "accepted")
            pack_path = root / "delivery" / "accepted" / "delivery-pack.json"
            pack = json.loads(pack_path.read_text(encoding="utf-8"))
            self.assertEqual(pack["status"], "accepted_local_delivery")
            self.assertFalse(pack["publish_authorized"])
            self.assertEqual(len(pack["files"]), 1)
            self.assertEqual(pack["composition_path"], "ffmpeg_fallback")
            self.assertEqual(set(pack["revisions"]["providers"]), {"fish_audio", "heygen"})
            self.assertNotIn("fish-secret", pack_path.read_text(encoding="utf-8"))
            self.assertNotIn("heygen-secret", pack_path.read_text(encoding="utf-8"))
            self.assertEqual(accept_avatar_delivery(root).status, "idempotent")


def _audio_bytes(root: Path) -> bytes:
    path = root / "fish-fixture.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=30", "-c:a", "pcm_s16le", str(path)],
        capture_output=True,
        check=True,
    )
    return path.read_bytes()


if __name__ == "__main__":
    unittest.main()

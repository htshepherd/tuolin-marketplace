from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.agent_interface import rebuild_agent_interface
from scripts.tuolin_marketplace.avatar_video_agent import (
    authorize_avatar_provider_retry,
    confirm_avatar_inputs,
    confirm_avatar_production_plan,
    create_avatar_video_run,
    generate_fish_audio_input,
    record_avatar_material_inspection,
    write_avatar_production_plan,
)
from scripts.tuolin_marketplace.avatar_video.provider_adapters import FishAudioAdapter
from scripts.tuolin_marketplace.avatar_video.providers import read_provider_attempts
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe required")
class FishAudioAdapterTests(unittest.TestCase):
    def test_real_adapter_contract_preserves_script_and_redacts_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths, image_path = _project(root)
            run = _confirmed_run(paths, image_path)
            captured = {}
            audio_bytes = _wav_bytes(root)

            def transport(url, headers, payload, timeout):
                captured.update({"url": url, "headers": headers, "payload": payload, "timeout": timeout})
                return {"status": 200, "headers": {"x-request-id": "fish-real-001", "x-credits-used": "1"}, "body": audio_bytes}

            adapter = FishAudioAdapter(api_key="super-secret-fish-key", transport=transport)
            generated = generate_fish_audio_input(run, adapter)
            self.assertEqual(generated.status, "completed_pending_review")
            plan = json.loads((Path(run) / "production_plan.json").read_text(encoding="utf-8"))
            self.assertIsInstance(captured["payload"], bytes)
            self.assertIn(plan["narration"].encode("utf-8"), captured["payload"])
            self.assertIn(b"reference_id", captured["payload"])
            self.assertIn(b"fish-real-voice", captured["payload"])
            self.assertIn(b"prosody", captured["payload"])
            self.assertNotIn(b'"text"', captured["payload"])
            self.assertEqual(captured["headers"]["Authorization"], "Bearer super-secret-fish-key")
            self.assertEqual(captured["headers"]["Content-Type"], "application/msgpack")
            self.assertEqual(captured["headers"]["model"], "s2-pro")
            attempts_text = "\n".join(path.read_text(encoding="utf-8") for path in (Path(run) / "providers").glob("*.json"))
            self.assertNotIn("super-secret-fish-key", attempts_text)
            confirmed = confirm_avatar_inputs(run)
            self.assertEqual(confirmed.phase, "ready_for_presenter_generation")
            attempt = read_provider_attempts(Path(run), "fish_audio")[0]
            self.assertEqual(attempt["external_task_id"], "fish-real-001")
            self.assertEqual(attempt["status"], "accepted")

    def test_adapter_surfaces_timeout_and_records_failed_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths, image_path = _project(root)
            run = _confirmed_run(paths, image_path)

            def timeout_transport(url, headers, payload, timeout):
                raise TimeoutError

            adapter = FishAudioAdapter(api_key="secret", transport=timeout_transport)
            with self.assertRaisesRegex(RuntimeError, "请求超时"):
                generate_fish_audio_input(run, adapter)
            attempt = read_provider_attempts(Path(run), "fish_audio")[0]
            self.assertEqual(attempt["status"], "failed")
            self.assertEqual(attempt["review"], None)
            state = json.loads((Path(run) / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["phase"], "awaiting_retry_authorization")
            with self.assertRaisesRegex(ValueError, "当前阶段"):
                generate_fish_audio_input(run, adapter)
            authorize_avatar_provider_retry(
                run,
                "fish_audio",
                reason="User explicitly authorizes retry after timeout",
            )
            audio_bytes = _wav_bytes(root)
            recovered = generate_fish_audio_input(
                run,
                FishAudioAdapter(
                    api_key="secret",
                    transport=lambda url, headers, payload, timeout: {
                        "status": 200,
                        "headers": {"x-request-id": "fish-retry-002"},
                        "body": audio_bytes,
                    },
                ),
            )
            self.assertEqual(recovered.status, "completed_pending_review")
            attempts = read_provider_attempts(Path(run), "fish_audio")
            self.assertEqual([item["status"] for item in attempts], ["failed", "completed_pending_review"])
            self.assertNotEqual(attempts[0]["authorization_id"], attempts[1]["authorization_id"])

    def test_adapter_rejects_empty_or_malformed_audio_response(self) -> None:
        adapter = FishAudioAdapter(
            api_key="secret",
            transport=lambda url, headers, payload, timeout: {"status": 200, "headers": {}, "body": b""},
        )
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "空或畸形"):
                adapter.synthesize(
                    narration="Exact text",
                    voice_id="voice",
                    settings={"format": "wav"},
                    output_path=Path(tmp) / "out.wav",
                )


def _confirmed_run(paths, image_path: Path) -> Path:
    run = create_avatar_video_run(
        paths,
        "Fish adapter",
        product_id="product/quartz_fiber_tape",
        language_version="en",
        duration_seconds=30,
        initial_brief={
            "audience": "Industrial buyers",
            "reason_to_watch": "Quick product review",
            "takeaway": "Product identity",
            "viewer_action": "Ask for data",
            "priority_information": "Product appearance",
            "exclusions": "No unsupported claims",
            "presenter_evidence_treatment": "Presenter plus full-screen evidence",
        },
        invoked_skill="$tuolin-avatar-video",
    )
    root = Path(run.run_dir)
    record_avatar_material_inspection(
        root,
        {
            "path": str(image_path),
            "subject": "official product",
            "clarity": "clear",
            "composition": "centered",
            "vertical_crop": "usable",
            "near_duplicate_group": "product-01",
            "status": "usable",
            "risks": [],
        },
    )
    write_avatar_production_plan(
        root,
        {
            "narration": "Exact approved narration for Fish Audio.",
            "narration_source": "user_supplied",
            "timeline": [
                {"start_seconds": 0, "end_seconds": 15, "mode": "presenter", "purpose": "intro"},
                {"start_seconds": 15, "end_seconds": 30, "mode": "evidence", "purpose": "product"},
            ],
            "selected_visuals": [{"path": str(image_path), "purpose": "product_evidence"}],
            "fish_audio": {"voice_id": "fish-real-voice", "speed": 1.0, "format": "wav"},
            "heygen": {"avatar_id": "heygen-public-avatar"},
            "estimated_consumption": {"fish_audio": 1, "heygen": 1},
        },
    )
    confirm_avatar_production_plan(root)
    return root


def _project(root: Path):
    paths = resolve_paths(root, {})
    initialize_project(paths)
    _write_card(
        paths.knowledge_dir / "产品" / "product.md",
        [
            "card_template_version: product-card-v1", "type: product", "id: product/quartz_fiber_tape",
            "title: Quartz Tape", "aliases: []", "status: official", "usage_scope: external_allowed",
            "product_line: Tape", "raw_partitions: []", "tags: []", "updated_at: 2026-07-29T00:00:00+00:00",
            "last_reviewed_at: 2026-07-29T00:00:00+00:00", "evidence_refs: []", "related_refs: []", "review_refs: []",
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
            "card_template_version: content-asset-card-v1", "type: content_asset", "id: content_asset/product",
            "title: Product image", "aliases: []", "status: official", "usage_scope: external_allowed",
            "raw_partitions: []", "tags: []", "updated_at: 2026-07-29T00:00:00+00:00",
            "last_reviewed_at: 2026-07-29T00:00:00+00:00", "evidence_refs: []", "review_refs: []",
            "asset_category: product image", "human_face_risk: false", "media_types: [image]",
            "related_products: [product/quartz_fiber_tape]", f"files: [{rel}]", "usable_for: [avatar_video]",
        ],
        "Official image.",
    )
    rebuild_agent_interface(paths)
    return paths, image_path


def _wav_bytes(root: Path) -> bytes:
    path = root / "fixture.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=330:sample_rate=48000:duration=30", "-c:a", "pcm_s16le", str(path)],
        capture_output=True,
        check=True,
    )
    return path.read_bytes()


def _write_card(path: Path, frontmatter: list[str], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + "\n".join(frontmatter) + "\n---\n\n" + body + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()

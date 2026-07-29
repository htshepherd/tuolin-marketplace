from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.avatar_video_agent import confirm_avatar_presenter, generate_heygen_presenter
from scripts.tuolin_marketplace.avatar_video.provider_adapters import HeyGenCLIAdapter
from scripts.tuolin_marketplace.avatar_video.providers import read_provider_attempts
from tests.test_avatar_video_heygen_adapter import _project, _run_ready_for_heygen, _video_bytes


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe required")
class HeyGenCLIAdapterTests(unittest.TestCase):
    def test_supported_v3_cli_uploads_fish_audio_and_creates_fixed_avatar_video(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths, image_path = _project(workspace)
            root = _run_ready_for_heygen(paths, image_path)
            video_bytes = _video_bytes(workspace)
            calls: list[list[str]] = []
            captured_request = {}

            def runner(command, environment):
                calls.append(list(command))
                operation = tuple(command[1:3])
                if operation == ("auth", "status"):
                    payload = {"data": {"authenticated": True, "mode": "oauth"}}
                elif operation == ("asset", "create"):
                    self.assertTrue(Path(command[command.index("--file") + 1]).is_file())
                    payload = {"data": {"asset_id": "fish-audio-asset", "url": "https://asset.test/audio.wav", "mime_type": "audio/wav", "size_bytes": 10}}
                elif operation == ("video", "create"):
                    request_path = Path(command[command.index("--data") + 1])
                    captured_request.update(json.loads(request_path.read_text(encoding="utf-8")))
                    payload = {"data": {"video_id": "v3-video-1", "status": "completed"}}
                elif operation == ("video", "get"):
                    payload = {"data": {"video_id": "v3-video-1", "status": "completed", "credits_used": 2}}
                elif operation == ("video", "download"):
                    Path(command[command.index("--output-path") + 1]).write_bytes(video_bytes)
                    payload = {"data": {"downloaded": True}}
                else:
                    raise AssertionError(command)
                return {"returncode": 0, "stdout": json.dumps(payload), "stderr": ""}

            generated = generate_heygen_presenter(
                root,
                HeyGenCLIAdapter(cli_path="/fake/heygen", command_runner=runner),
            )
            self.assertEqual(generated.status, "completed_pending_review")
            self.assertEqual([tuple(call[1:3]) for call in calls], [("auth", "status"), ("asset", "create"), ("video", "create"), ("video", "get"), ("video", "download")])
            self.assertEqual(captured_request["type"], "avatar")
            self.assertEqual(captured_request["avatar_id"], "fixed-public-avatar")
            self.assertEqual(captured_request["audio_asset_id"], "fish-audio-asset")
            self.assertEqual(captured_request["aspect_ratio"], "9:16")
            self.assertEqual(captured_request["resolution"], "1080p")
            self.assertEqual(captured_request["engine"], {"type": "avatar_iv"})
            self.assertNotIn("script", captured_request)
            self.assertNotIn("voice_id", captured_request)
            confirm_avatar_presenter(root)
            attempt = read_provider_attempts(root, "heygen")[0]
            self.assertEqual(attempt["external_task_id"], "v3-video-1")
            self.assertEqual(attempt["status"], "accepted")

    def test_cli_auth_failure_is_redacted_and_persisted_as_failed_without_submission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths, image_path = _project(workspace)
            root = _run_ready_for_heygen(paths, image_path)
            secret = "do-not-persist"

            def runner(command, environment):
                return {"returncode": 3, "stdout": "", "stderr": f"auth failed https://x.test/cb?token={secret}"}

            with self.assertRaisesRegex(RuntimeError, r"token=\*\*\*"):
                generate_heygen_presenter(root, HeyGenCLIAdapter(cli_path="/fake/heygen", command_runner=runner))
            self.assertEqual(read_provider_attempts(root, "heygen")[0]["status"], "failed")
            persisted = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.json"))
            self.assertNotIn(secret, persisted)

    def test_submitted_task_resumes_without_reupload_or_duplicate_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths, image_path = _project(workspace)
            root = _run_ready_for_heygen(paths, image_path)
            video_bytes = _video_bytes(workspace)
            calls: list[tuple[str, str]] = []
            status_queries = 0

            def runner(command, environment):
                nonlocal status_queries
                operation = tuple(command[1:3])
                calls.append(operation)
                if operation == ("auth", "status"):
                    payload = {"data": {"authenticated": True}}
                elif operation == ("asset", "create"):
                    payload = {"data": {"asset_id": "asset-once"}}
                elif operation == ("video", "create"):
                    self.assertNotIn("--wait", command)
                    payload = {"data": {"video_id": "resume-video-1", "status": "pending"}}
                elif operation == ("video", "get"):
                    status_queries += 1
                    payload = {
                        "data": {
                            "video_id": "resume-video-1",
                            "status": "processing" if status_queries == 1 else "completed",
                        }
                    }
                elif operation == ("video", "download"):
                    Path(command[command.index("--output-path") + 1]).write_bytes(video_bytes)
                    payload = {"data": {"downloaded": True}}
                else:
                    raise AssertionError(command)
                return {"returncode": 0, "stdout": json.dumps(payload), "stderr": ""}

            adapter = HeyGenCLIAdapter(
                cli_path="/fake/heygen",
                command_runner=runner,
                max_polls=1,
                sleep=lambda _: None,
            )
            first = generate_heygen_presenter(root, adapter)
            self.assertEqual(first.status, "in_progress")
            self.assertEqual(read_provider_attempts(root, "heygen")[0]["status"], "running")

            second = generate_heygen_presenter(root, adapter)
            self.assertEqual(second.status, "completed_pending_review")
            self.assertEqual(calls.count(("asset", "create")), 1)
            self.assertEqual(calls.count(("video", "create")), 1)
            attempts = read_provider_attempts(root, "heygen")
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0]["external_task_id"], "resume-video-1")
            self.assertEqual(attempts[0]["status"], "completed_pending_review")

    def test_provider_terminal_failure_requires_new_retry_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths, image_path = _project(workspace)
            root = _run_ready_for_heygen(paths, image_path)

            def runner(command, environment):
                operation = tuple(command[1:3])
                payload = {
                    ("auth", "status"): {"data": {"authenticated": True}},
                    ("asset", "create"): {"data": {"asset_id": "failed-asset"}},
                    ("video", "create"): {"data": {"video_id": "failed-video", "status": "pending"}},
                    ("video", "get"): {"data": {"video_id": "failed-video", "status": "failed", "error": "provider rejected input"}},
                }[operation]
                return {"returncode": 0, "stdout": json.dumps(payload), "stderr": ""}

            adapter = HeyGenCLIAdapter(cli_path="/fake/heygen", command_runner=runner, max_polls=1)
            with self.assertRaisesRegex(RuntimeError, "provider rejected input"):
                generate_heygen_presenter(root, adapter)
            attempts = read_provider_attempts(root, "heygen")
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0]["status"], "failed")
            state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["phase"], "awaiting_retry_authorization")
            with self.assertRaisesRegex(ValueError, "当前阶段"):
                generate_heygen_presenter(root, adapter)


if __name__ == "__main__":
    unittest.main()

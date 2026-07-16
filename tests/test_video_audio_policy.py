from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.video_audio_policy import (
    build_video_audio_analysis,
    decide_segment_audio_policy,
    redact_transcript_for_downstream,
    refresh_video_profile_audio,
    transcribe_video_audio,
)


class VideoAudioPolicyTests(unittest.TestCase):
    def test_asr_adapter_output_keeps_language_and_timestamps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "audio.wav"
            audio.write_bytes(b"audio")

            class LocalAdapter:
                is_local = True

                def transcribe(self, path):
                    return {
                        "language": "zh",
                        "segments": [
                            {
                                "start_seconds": 1.2,
                                "end_seconds": 3.4,
                                "text": "请确认客户名称。",
                                "confidence": 0.91,
                                "speaker": "speaker_1",
                            }
                        ],
                        "unrecognized_ranges": [
                            {"start_seconds": 5.0, "end_seconds": 5.8}
                        ],
                        "tool": "local-asr",
                        "model_version": "v1",
                    }

            result = transcribe_video_audio(audio, LocalAdapter())

            self.assertEqual(result["language"], "zh")
            self.assertEqual(result["segments"][0]["start_seconds"], 1.2)
            self.assertEqual(result["segments"][0]["end_seconds"], 3.4)
            self.assertEqual(result["segments"][0]["speaker"], "speaker_1")
            self.assertEqual(result["tool"], "local-asr")
            self.assertEqual(result["model_version"], "v1")

    def test_no_speech_video_may_skip_transcription(self) -> None:
        result = build_video_audio_analysis(
            has_audio=True,
            speech_presence="none",
            audio_observations=["持续机器运转声，无可辨识语音。"],
            transcript=None,
        )

        self.assertEqual(result["transcript_detail"]["status"], "not_applicable")
        self.assertEqual(result["analysis_completeness"], "complete")
        self.assertEqual(
            result["audio_observations"],
            ["持续机器运转声，无可辨识语音。"],
        )
        self.assertFalse(result["audio_understanding_incomplete"])

    def test_clear_speech_without_asr_marks_audio_incomplete(self) -> None:
        result = build_video_audio_analysis(
            has_audio=True,
            speech_presence="clear",
            audio_observations=["存在清晰中文语音，但当前 ASR 不可用。"],
            transcript=None,
        )

        self.assertTrue(result["audio_understanding_incomplete"])
        self.assertEqual(
            result["analysis_completeness"],
            "visual_complete_audio_incomplete",
        )
        self.assertEqual(result["transcript_detail"]["status"], "unavailable")

    def test_asr_unavailable_does_not_claim_no_important_speech(self) -> None:
        result = build_video_audio_analysis(
            has_audio=True,
            speech_presence="clear",
            audio_observations=["有人声，内容未转录。"],
            transcript=None,
        )

        self.assertEqual(result["important_speech_assessment"], "unknown")
        self.assertNotEqual(
            result.get("important_speech_assessment"),
            "none",
        )
        self.assertIn(
            result["source_audio_use_policy"],
            {"mute-recommended", "human-review-required"},
        )

    def test_sensitive_transcript_is_redacted_from_downstream(self) -> None:
        transcript = {
            "status": "available",
            "language": "zh",
            "segments": [
                {
                    "start_seconds": 0.0,
                    "end_seconds": 2.0,
                    "text": "客户名称是星海工业。",
                    "sensitive": True,
                    "sensitivity_reason": "customer_identity",
                },
                {
                    "start_seconds": 2.0,
                    "end_seconds": 4.0,
                    "text": "正在缠绕隔热带。",
                    "sensitive": False,
                },
            ],
        }

        downstream = redact_transcript_for_downstream(transcript)

        self.assertEqual(downstream["segments"][0]["text"], "[敏感内容已隐藏]")
        self.assertEqual(downstream["segments"][0]["start_seconds"], 0.0)
        self.assertEqual(downstream["segments"][1]["text"], "正在缠绕隔热带。")
        self.assertNotIn("星海工业", str(downstream))

    def test_original_audio_is_blocked_for_privacy_or_rights_risk(self) -> None:
        privacy = decide_segment_audio_policy(
            speech_understanding="complete",
            privacy_risk=True,
            rights_risk=False,
            spoken_claim_risk=False,
        )
        rights = decide_segment_audio_policy(
            speech_understanding="complete",
            privacy_risk=False,
            rights_risk=True,
            spoken_claim_risk=False,
        )

        self.assertEqual(privacy, "mute-required")
        self.assertEqual(rights, "mute-required")

    def test_transcript_refresh_does_not_regenerate_unrelated_visual_semantics(self) -> None:
        profile = {
            "profile_id": "video_profile/quartz_fiber_tape/video_asset_123",
            "profile_revision": "video_profile_rev_old",
            "content_digest": "sha256:old",
            "title": "安装过程",
            "summary": "工人将隔热带缠绕到管道。",
            "observed_classifications": ["installation"],
            "key_segments": [
                {
                    "segment_id": "segment_01",
                    "start_seconds": 0.0,
                    "end_seconds": 8.0,
                    "description": "连续缠绕动作。",
                }
            ],
            "representative_frames": [
                {
                    "anchor_id": "anchor_01",
                    "timestamp_seconds": 4.0,
                    "generated_ref": "cache/frame.png",
                }
            ],
            "audio_observations": ["存在语音，尚未转录。"],
            "transcript_detail": {"status": "unavailable"},
            "source_audio_use_policy": "human-review-required",
            "analysis_completeness": "visual_complete_audio_incomplete",
            "analysis_provenance": {
                "semantic_reviewer": "codex",
                "visual_policy_revision": "video-analysis-v1",
            },
        }
        transcript = {
            "status": "available",
            "language": "zh",
            "segments": [
                {
                    "start_seconds": 0.0,
                    "end_seconds": 2.0,
                    "text": "从管道一端开始缠绕。",
                    "confidence": 0.9,
                }
            ],
            "unrecognized_ranges": [],
            "tool": "local-asr",
            "model_version": "v1",
        }

        refreshed = refresh_video_profile_audio(
            profile,
            transcript=transcript,
            audio_observations=["清晰中文安装说明。"],
            source_audio_use_policy="retain",
        )

        self.assertEqual(
            refreshed["observed_classifications"],
            profile["observed_classifications"],
        )
        self.assertEqual(refreshed["key_segments"], profile["key_segments"])
        self.assertEqual(
            refreshed["representative_frames"],
            profile["representative_frames"],
        )
        self.assertEqual(
            refreshed["analysis_provenance"]["semantic_reviewer"],
            "codex",
        )
        self.assertNotEqual(
            refreshed["profile_revision"],
            profile["profile_revision"],
        )
        self.assertEqual(refreshed["transcript_detail"]["status"], "available")


if __name__ == "__main__":
    unittest.main()

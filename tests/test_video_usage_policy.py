from __future__ import annotations

import unittest

from scripts.tuolin_marketplace.video_usage_policy import evaluate_video_usage_policy


class VideoUsagePolicyTests(unittest.TestCase):
    def test_legacy_profile_defaults_to_review_before_external(self) -> None:
        result = evaluate_video_usage_policy(
            {"source_audio_use_policy": "human-review-required"}
        )

        self.assertFalse(result["may_appear_in_external_video"])
        self.assertIn("确认可对外使用前", result["user_message"])

    def test_external_visual_scope_requires_human_confirmation_record(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "external visual use requires confirmed_by and confirmed_at",
        ):
            evaluate_video_usage_policy(
                {"visual_usage_scope": "external_creative_allowed"}
            )

    def test_external_visuals_are_independent_from_audio_claims_and_publication(self) -> None:
        result = evaluate_video_usage_policy(
            {
                "visual_usage_scope": "external_creative_allowed",
                "source_audio_use_policy": "mute-required",
                "claim_use_policy": "visual_observation_only",
                "publication_gate": "final_human_confirmation_required",
                "visual_usage_confirmation": {
                    "confirmed_by": "user",
                    "confirmed_at": "2026-07-29T10:00:00+08:00",
                },
            }
        )

        self.assertTrue(result["may_appear_in_external_video"])
        self.assertFalse(result["may_use_original_audio"])
        self.assertFalse(result["may_support_external_claims"])
        self.assertFalse(result["may_publish_without_confirmation"])
        self.assertEqual(
            result["user_message"],
            "画面可以剪进 YouTube Shorts 和 TikTok 成片；必须删除原声；不能用画面证明耐温、隔热、安全或认证；最终发布前仍需人工确认。",
        )


if __name__ == "__main__":
    unittest.main()

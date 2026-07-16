from __future__ import annotations

import unittest

from scripts.tuolin_marketplace.video_test_evidence import (
    authorize_external_test_claim,
    build_downstream_test_summary,
    build_test_video_external_description,
    create_video_evidence_link,
    decide_test_spoken_conclusion_policy,
    evaluate_test_video_external_use,
    evaluate_test_video_risk_review,
    validate_test_video_profile_metadata,
    validate_test_video_trim,
)


class VideoTestEvidenceTests(unittest.TestCase):
    def test_directory_proximity_creates_candidate_not_confirmed_evidence_link(self) -> None:
        link = create_video_evidence_link(
            profile_id="video_profile/quartz_fiber_tape/video_asset_123",
            evidence_id="evidence/quartz_fiber_tape/report_001",
            basis="directory_proximity",
        )

        self.assertEqual(link["status"], "candidate")
        self.assertFalse(link["supports_external_claims"])
        self.assertEqual(link["basis"], "directory_proximity")

    def test_only_confirmed_evidence_link_supports_external_test_claim(self) -> None:
        candidate = create_video_evidence_link(
            profile_id="video_profile/quartz_fiber_tape/video_asset_123",
            evidence_id="evidence/quartz_fiber_tape/report_001",
            basis="directory_proximity",
        )
        confirmed = create_video_evidence_link(
            profile_id="video_profile/quartz_fiber_tape/video_asset_123",
            evidence_id="evidence/quartz_fiber_tape/report_001",
            basis="human_confirmed",
            confirmed_scope=["temperature_resistance"],
            confirmed_by="reviewer",
        )

        with self.assertRaisesRegex(PermissionError, "confirmed evidence"):
            authorize_external_test_claim(
                candidate,
                claim_scope="temperature_resistance",
            )
        allowed = authorize_external_test_claim(
            confirmed,
            claim_scope="temperature_resistance",
        )

        self.assertTrue(allowed["allowed"])
        self.assertEqual(allowed["evidence_id"], confirmed["evidence_id"])

    def test_test_clip_without_evidence_uses_neutral_observation_only(self) -> None:
        result = build_test_video_external_description(
            neutral_observation="画面显示带材接触热源，表面颜色发生变化。",
            proposed_claim="该产品已通过 1000°C 耐温测试。",
            evidence_links=[],
            claim_scope="temperature_resistance",
        )

        self.assertEqual(
            result["external_description"],
            "画面显示带材接触热源，表面颜色发生变化。",
        )
        self.assertFalse(result["claim_allowed"])
        self.assertNotIn("通过", result["external_description"])
        self.assertNotIn("1000", result["external_description"])

    def test_unclear_test_identity_or_conditions_block_external_use(self) -> None:
        evidence = create_video_evidence_link(
            profile_id="video_profile/quartz_fiber_tape/video_asset_123",
            evidence_id="evidence/quartz_fiber_tape/report_001",
            basis="human_confirmed",
            confirmed_scope=["temperature_resistance"],
            confirmed_by="reviewer",
        )

        for field in ("product_identity", "test_conditions"):
            statuses = {
                "product_identity": "confirmed",
                "test_conditions": "confirmed",
                "before_after_relationship": "confirmed",
            }
            statuses[field] = "unclear"
            with self.subTest(field=field):
                result = evaluate_test_video_external_use(
                    **statuses,
                    evidence_links=[evidence],
                    claim_scope="temperature_resistance",
                )

                self.assertFalse(result["external_use_allowed"])
                self.assertEqual(result["status"], "human_review_required")
                self.assertIn(field, result["blocking_fields"])

    def test_runtime_trim_cannot_hide_adverse_test_state(self) -> None:
        required_phases = [
            {
                "phase": "before",
                "start_seconds": 0,
                "end_seconds": 3,
                "meaning_required": True,
            },
            {
                "phase": "process",
                "start_seconds": 3,
                "end_seconds": 9,
                "meaning_required": True,
            },
            {
                "phase": "adverse_after_state",
                "start_seconds": 9,
                "end_seconds": 12,
                "meaning_required": True,
                "adverse": True,
            },
        ]

        with self.assertRaisesRegex(PermissionError, "adverse_after_state"):
            validate_test_video_trim(
                required_phases=required_phases,
                start_seconds=0,
                end_seconds=9.5,
            )
        allowed = validate_test_video_trim(
            required_phases=required_phases,
            start_seconds=0,
            end_seconds=12,
        )

        self.assertTrue(allowed["allowed"])
        self.assertIn("adverse_after_state", allowed["included_phases"])

    def test_unsupported_spoken_test_conclusion_is_muted_or_excluded(self) -> None:
        muted = decide_test_spoken_conclusion_policy(
            spoken_conclusion_present=True,
            evidence_supported=False,
            can_mute=True,
        )
        excluded = decide_test_spoken_conclusion_policy(
            spoken_conclusion_present=True,
            evidence_supported=False,
            can_mute=False,
        )

        self.assertEqual(muted["audio_policy"], "mute-required")
        self.assertTrue(muted["segment_usable"])
        self.assertEqual(excluded["audio_policy"], "exclude")
        self.assertFalse(excluded["segment_usable"])

    def test_all_test_risk_fields_require_human_review(self) -> None:
        fields = {
            "product_identity": "machine_reviewed",
            "test_conditions": "machine_reviewed",
            "before_after_relationship": "machine_reviewed",
            "evidence_links": "machine_reviewed",
            "spoken_claims": "machine_reviewed",
            "misleading_edit_risk": "machine_reviewed",
        }

        pending = evaluate_test_video_risk_review(fields)
        complete = evaluate_test_video_risk_review(
            {field: "human_confirmed" for field in fields}
        )

        self.assertFalse(pending["review_complete"])
        self.assertCountEqual(pending["pending_fields"], fields)
        self.assertFalse(pending["external_use_allowed"])
        self.assertTrue(complete["review_complete"])
        self.assertEqual(complete["pending_fields"], [])

    def test_downstream_test_summary_separates_visual_use_from_claims(self) -> None:
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
        profile = {
            "observed_classifications": ["test_validation"],
            "summary": "画面显示带材接触热源后表面颜色发生变化。",
            "test_context": {
                "neutral_observation": "带材接触热源，表面颜色发生变化。",
                "test_type": "heat_exposure",
                "test_result_or_change": "surface_color_changed",
            },
            "test_risk_review": review,
            "evidence_links": [
                create_video_evidence_link(
                    profile_id="video_profile/quartz_fiber_tape/video_asset_123",
                    evidence_id="evidence/quartz_fiber_tape/report_001",
                    basis="directory_proximity",
                )
            ],
        }

        summary = build_downstream_test_summary(profile)

        self.assertTrue(summary["is_test_video"])
        self.assertEqual(
            summary["visual_use_policy"],
            "reviewed_neutral_observation",
        )
        self.assertEqual(summary["external_claim_scopes"], [])
        self.assertEqual(
            summary["neutral_observation"],
            profile["test_context"]["neutral_observation"],
        )

    def test_test_profile_metadata_must_exist_before_human_review_gate(self) -> None:
        profile = {
            "source_classification": ["05_测试验证素材", "高温测试"],
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

        staged = validate_test_video_profile_metadata(
            profile,
            require_human_review=False,
        )
        with self.assertRaisesRegex(ValueError, "human review"):
            validate_test_video_profile_metadata(
                profile,
                require_human_review=True,
            )

        self.assertEqual(staged["test_context"], profile["test_context"])


if __name__ == "__main__":
    unittest.main()

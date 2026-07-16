from __future__ import annotations

from datetime import datetime, timezone


TEST_VIDEO_RISK_REVIEW_FIELDS = (
    "product_identity",
    "test_conditions",
    "before_after_relationship",
    "evidence_links",
    "spoken_claims",
    "misleading_edit_risk",
)
TEST_VIDEO_CONTEXT_FIELDS = (
    "neutral_observation",
    "test_type",
    "product_identity",
    "test_conditions",
    "before_after_relationship",
    "test_result_or_change",
)


def create_video_evidence_link(
    *,
    profile_id: str,
    evidence_id: str,
    basis: str,
    confirmed_scope: list[str] | tuple[str, ...] = (),
    confirmed_by: str | None = None,
) -> dict:
    if basis == "directory_proximity":
        status = "candidate"
        supports_external_claims = False
    elif basis == "human_confirmed":
        if not confirmed_by or not confirmed_scope:
            raise ValueError(
                "confirmed video evidence requires reviewer and claim scope"
            )
        status = "confirmed"
        supports_external_claims = True
    else:
        raise ValueError("unsupported video evidence link basis")
    return {
        "profile_id": profile_id,
        "evidence_id": evidence_id,
        "basis": basis,
        "status": status,
        "confirmed_scope": list(confirmed_scope),
        "confirmed_by": confirmed_by,
        "supports_external_claims": supports_external_claims,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def authorize_external_test_claim(
    link: dict,
    *,
    claim_scope: str,
) -> dict:
    if (
        link.get("status") != "confirmed"
        or not link.get("supports_external_claims")
    ):
        raise PermissionError(
            "external test claims require a confirmed evidence link"
        )
    if claim_scope not in link.get("confirmed_scope", []):
        raise PermissionError(
            "external test claim exceeds the confirmed evidence scope"
        )
    return {
        "allowed": True,
        "claim_scope": claim_scope,
        "profile_id": link.get("profile_id"),
        "evidence_id": link.get("evidence_id"),
    }


def build_test_video_external_description(
    *,
    neutral_observation: str,
    proposed_claim: str,
    evidence_links: list[dict] | tuple[dict, ...],
    claim_scope: str,
) -> dict:
    authorized_links: list[dict] = []
    for link in evidence_links:
        try:
            authorized_links.append(
                authorize_external_test_claim(
                    link,
                    claim_scope=claim_scope,
                )
            )
        except PermissionError:
            continue

    if authorized_links:
        return {
            "external_description": proposed_claim,
            "claim_allowed": True,
            "claim_scope": claim_scope,
            "evidence_ids": [
                item["evidence_id"] for item in authorized_links
            ],
        }
    return {
        "external_description": neutral_observation,
        "claim_allowed": False,
        "claim_scope": claim_scope,
        "evidence_ids": [],
        "reason": "no confirmed evidence supports this external claim",
    }


def evaluate_test_video_external_use(
    *,
    product_identity: str,
    test_conditions: str,
    before_after_relationship: str,
    evidence_links: list[dict] | tuple[dict, ...],
    claim_scope: str,
) -> dict:
    review_fields = {
        "product_identity": product_identity,
        "test_conditions": test_conditions,
        "before_after_relationship": before_after_relationship,
    }
    invalid = sorted(
        field
        for field, status in review_fields.items()
        if status != "confirmed"
    )
    if invalid:
        return {
            "status": "human_review_required",
            "external_use_allowed": False,
            "blocking_fields": invalid,
            "claim_scope": claim_scope,
            "evidence_ids": [],
        }

    authorized = []
    for link in evidence_links:
        try:
            authorized.append(
                authorize_external_test_claim(
                    link,
                    claim_scope=claim_scope,
                )
            )
        except PermissionError:
            continue
    if not authorized:
        return {
            "status": "neutral_observation_only",
            "external_use_allowed": False,
            "blocking_fields": ["confirmed_evidence_link"],
            "claim_scope": claim_scope,
            "evidence_ids": [],
        }
    return {
        "status": "external_use_allowed",
        "external_use_allowed": True,
        "blocking_fields": [],
        "claim_scope": claim_scope,
        "evidence_ids": [item["evidence_id"] for item in authorized],
    }


def validate_test_video_trim(
    *,
    required_phases: list[dict] | tuple[dict, ...],
    start_seconds: float,
    end_seconds: float,
) -> dict:
    start = float(start_seconds)
    end = float(end_seconds)
    if start < 0 or end <= start:
        raise ValueError("test video trim range is invalid")

    included_phases: list[str] = []
    for phase in required_phases:
        phase_name = str(phase.get("phase") or "").strip()
        phase_start = float(phase["start_seconds"])
        phase_end = float(phase["end_seconds"])
        if not phase_name or phase_start < 0 or phase_end <= phase_start:
            raise ValueError("test video phase is invalid")
        fully_included = start <= phase_start and end >= phase_end
        if fully_included:
            included_phases.append(phase_name)
        if phase.get("meaning_required") and not fully_included:
            raise PermissionError(
                f"runtime trim cannot omit required test phase: {phase_name}"
            )

    return {
        "allowed": True,
        "start_seconds": start,
        "end_seconds": end,
        "included_phases": included_phases,
    }


def decide_test_spoken_conclusion_policy(
    *,
    spoken_conclusion_present: bool,
    evidence_supported: bool,
    can_mute: bool,
) -> dict:
    if not spoken_conclusion_present:
        return {
            "audio_policy": "retain",
            "segment_usable": True,
            "reason": "no spoken test conclusion detected",
        }
    if evidence_supported:
        return {
            "audio_policy": "human-review-required",
            "segment_usable": True,
            "reason": "spoken conclusion has evidence but still requires review",
        }
    if can_mute:
        return {
            "audio_policy": "mute-required",
            "segment_usable": True,
            "reason": "unsupported spoken test conclusion must not be reused",
        }
    return {
        "audio_policy": "exclude",
        "segment_usable": False,
        "reason": "unsupported spoken conclusion cannot be removed safely",
    }


def evaluate_test_video_risk_review(review_statuses: dict) -> dict:
    pending = [
        field
        for field in TEST_VIDEO_RISK_REVIEW_FIELDS
        if review_statuses.get(field) != "human_confirmed"
    ]
    return {
        "review_complete": not pending,
        "pending_fields": pending,
        "external_use_allowed": not pending,
        "required_fields": list(TEST_VIDEO_RISK_REVIEW_FIELDS),
    }


def is_test_video_profile(profile: dict) -> bool:
    source_labels = {
        str(item) for item in profile.get("source_classification", [])
    }
    observed_labels = {
        str(item) for item in profile.get("observed_classifications", [])
    }
    return (
        "test_validation" in observed_labels
        or any("测试验证" in item for item in source_labels)
    )


def validate_test_video_profile_metadata(
    profile: dict,
    *,
    require_human_review: bool,
) -> dict:
    if not is_test_video_profile(profile):
        return {}
    context = dict(profile.get("test_context") or {})
    missing_context = [
        field
        for field in TEST_VIDEO_CONTEXT_FIELDS
        if not str(context.get(field) or "").strip()
    ]
    if missing_context:
        raise ValueError(
            "test video profile missing context fields: "
            + ", ".join(missing_context)
        )
    review_statuses = dict(profile.get("test_risk_review") or {})
    review = evaluate_test_video_risk_review(review_statuses)
    if require_human_review and not review["review_complete"]:
        raise ValueError(
            "test video profile human review is incomplete: "
            + ", ".join(review["pending_fields"])
        )
    return {
        "test_context": context,
        "test_risk_review": review_statuses,
    }


def build_downstream_test_summary(profile: dict) -> dict:
    if not is_test_video_profile(profile):
        return {"is_test_video": False}

    review = evaluate_test_video_risk_review(
        dict(profile.get("test_risk_review") or {})
    )
    confirmed_scopes = sorted(
        {
            str(scope)
            for link in profile.get("evidence_links", [])
            if isinstance(link, dict)
            and link.get("status") == "confirmed"
            and link.get("supports_external_claims")
            for scope in link.get("confirmed_scope", [])
            if str(scope).strip()
        }
    )
    test_context = dict(profile.get("test_context") or {})
    if not review["review_complete"]:
        visual_use_policy = "human_review_required"
    elif confirmed_scopes:
        visual_use_policy = "reviewed_with_confirmed_evidence"
    else:
        visual_use_policy = "reviewed_neutral_observation"
    return {
        "is_test_video": True,
        "test_type": test_context.get("test_type"),
        "neutral_observation": test_context.get(
            "neutral_observation",
            profile.get("summary", ""),
        ),
        "test_result_or_change": test_context.get(
            "test_result_or_change"
        ),
        "visual_use_policy": visual_use_policy,
        "risk_review_complete": review["review_complete"],
        "pending_review_fields": review["pending_fields"],
        "external_claim_scopes": confirmed_scopes,
        "external_claims_allowed": bool(
            review["review_complete"] and confirmed_scopes
        ),
    }

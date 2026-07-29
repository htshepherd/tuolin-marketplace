from __future__ import annotations

from typing import Any


VISUAL_USAGE_SCOPES = {
    "external_creative_allowed",
    "review_before_external",
    "internal_only",
}
CLAIM_USE_POLICIES = {
    "visual_observation_only",
    "confirmed_evidence_only",
}
PUBLICATION_GATES = {"final_human_confirmation_required"}


def evaluate_video_usage_policy(profile: dict[str, Any]) -> dict[str, Any]:
    visual_scope = str(profile.get("visual_usage_scope") or "review_before_external")
    claim_policy = str(profile.get("claim_use_policy") or "visual_observation_only")
    publication_gate = str(
        profile.get("publication_gate") or "final_human_confirmation_required"
    )
    if visual_scope not in VISUAL_USAGE_SCOPES:
        raise ValueError(f"unsupported visual usage scope: {visual_scope}")
    if claim_policy not in CLAIM_USE_POLICIES:
        raise ValueError(f"unsupported claim use policy: {claim_policy}")
    if publication_gate not in PUBLICATION_GATES:
        raise ValueError(f"unsupported publication gate: {publication_gate}")
    if visual_scope == "external_creative_allowed":
        confirmation = dict(profile.get("visual_usage_confirmation") or {})
        if not str(confirmation.get("confirmed_by") or "").strip() or not str(
            confirmation.get("confirmed_at") or ""
        ).strip():
            raise ValueError(
                "external visual use requires confirmed_by and confirmed_at"
            )

    source_audio_policy = str(
        profile.get("source_audio_use_policy") or "human-review-required"
    )
    result = {
        "visual_usage_scope": visual_scope,
        "claim_use_policy": claim_policy,
        "publication_gate": publication_gate,
        "may_appear_in_external_video": visual_scope == "external_creative_allowed",
        "may_use_original_audio": source_audio_policy == "retain",
        "may_support_external_claims": claim_policy == "confirmed_evidence_only",
        "may_publish_without_confirmation": False,
    }
    result["user_message"] = _user_message(result)
    return result


def _user_message(policy: dict[str, Any]) -> str:
    if policy["visual_usage_scope"] == "external_creative_allowed":
        audio = (
            "允许保留已审核原声"
            if policy["may_use_original_audio"]
            else "必须删除原声"
        )
        claims = (
            "对外声明只能引用已确认的独立证据"
            if policy["may_support_external_claims"]
            else "不能用画面证明耐温、隔热、安全或认证"
        )
        return (
            f"画面可以剪进 YouTube Shorts 和 TikTok 成片；{audio}；{claims}；"
            "最终发布前仍需人工确认。"
        )
    if policy["visual_usage_scope"] == "internal_only":
        return (
            "画面只能在公司内部查看和制作草稿；任何片段都不能剪进 YouTube、TikTok "
            "或发送给客户的视频。"
        )
    return (
        "画面目前只能用于内部策划和草稿；确认可对外使用前，不能剪进最终的 "
        "YouTube Shorts 或 TikTok 成片。"
    )

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


AVATAR_BRIEF_FIELDS = (
    "audience",
    "reason_to_watch",
    "takeaway",
    "viewer_action",
    "priority_information",
    "exclusions",
    "presenter_evidence_treatment",
)
FORBIDDEN_DECISION_TOKENS = {
    "trend",
    "viral",
    "shot_count",
    "camera_movement",
    "subtitle_style",
    "transition_style",
    "provider_prompt",
}


def build_avatar_interview(decisions: dict[str, str] | None = None) -> dict[str, Any]:
    values = {key: str(value).strip() for key, value in dict(decisions or {}).items() if key in AVATAR_BRIEF_FIELDS and str(value).strip()}
    return {
        "schema_version": "avatar-video-interview-v1",
        "decisions": values,
        "pending_decision": None,
        "history": [],
        "completed": all(values.get(key) for key in AVATAR_BRIEF_FIELDS),
    }


def propose_avatar_decision(interview: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(interview)
    if updated.get("completed"):
        raise ValueError("数字人口播访谈已经充分。")
    if updated.get("pending_decision"):
        raise ValueError("一次只能存在一个待确认的数字人口播访谈问题。")
    key = str(proposal.get("decision_key") or "").strip()
    lowered = key.casefold()
    if key not in AVATAR_BRIEF_FIELDS or any(token in lowered for token in FORBIDDEN_DECISION_TOKENS):
        raise ValueError("该问题不属于数字人口播业务访谈范围。")
    if str(updated.get("decisions", {}).get(key) or "").strip():
        raise ValueError("该访谈决策已经明确，不应重复询问。")
    question = str(proposal.get("question") or "").strip()
    recommendation = str(proposal.get("recommendation") or "").strip()
    reason = str(proposal.get("reason") or "").strip()
    if not question or not recommendation or not reason:
        raise ValueError("访谈问题必须包含一个问题、一个推荐和一个具体理由。")
    updated["pending_decision"] = {
        "decision_key": key,
        "question": question,
        "recommendation": recommendation,
        "reason": reason,
        "source_type": str(proposal.get("source_type") or "planning_inference"),
        "proposed_at": datetime.now(timezone.utc).isoformat(),
    }
    return updated


def answer_avatar_decision(interview: dict[str, Any], reply: str) -> dict[str, Any]:
    updated = deepcopy(interview)
    pending = dict(updated.get("pending_decision") or {})
    if not pending:
        raise ValueError("当前没有待回答的数字人口播访谈问题。")
    answer = str(reply).strip()
    if not answer:
        raise ValueError("访谈回复不能为空。")
    normalized = answer.casefold()
    if normalized in {"确认", "按推荐", "ok", "yes", "confirmed"}:
        value = str(pending["recommendation"])
        answer_type = "accepted_recommendation"
    elif normalized in {"剩下都按推荐", "你来决定并直接出策划"}:
        raise ValueError("数字人口播访谈不能用当前回复批量确认尚未展示的决策。")
    else:
        value = answer
        answer_type = "user_correction"
    key = str(pending["decision_key"])
    updated.setdefault("decisions", {})[key] = value
    updated.setdefault("history", []).append(
        {
            **pending,
            "answer": value,
            "answer_type": answer_type,
            "answered_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    updated["pending_decision"] = None
    updated["completed"] = all(str(updated["decisions"].get(field) or "").strip() for field in AVATAR_BRIEF_FIELDS)
    return updated


def render_pending_avatar_decision(interview: dict[str, Any]) -> str:
    pending = dict(interview.get("pending_decision") or {})
    if not pending:
        return ""
    return (
        f"{pending['question']}\n\n"
        f"推荐：{pending['recommendation']}\n\n"
        f"理由：{pending['reason']}\n\n"
        "是否确认？"
    )

from __future__ import annotations

from copy import deepcopy
from typing import Any


PLANNING_BRIEF_FIELDS = (
    "audience",
    "audience_problem_scenario",
    "viewing_motivation",
    "viewer_interest_direction",
    "intended_takeaway",
    "desired_action",
    "priority_messages",
    "excluded_content",
    "ai_simulation_scope",
)
FACT_GROUNDED_FIELDS = {"intended_takeaway", "priority_messages", "ai_simulation_scope"}
CONFIRM_REPLIES = {"确认", "同意", "可以", "确定", "按推荐", "ok", "yes"}


def build_planning_interview(initial_decisions: dict[str, str] | None = None) -> dict[str, Any]:
    decisions = {
        key: str(value).strip()
        for key, value in dict(initial_decisions or {}).items()
        if key in PLANNING_BRIEF_FIELDS and str(value).strip()
    }
    interview = {
        "schema_version": "video-planning-interview-v1",
        "decisions": decisions,
        "decision_sources": {key: "initial_request" for key in decisions},
        "decision_evidence": {},
        "pending_decision": None,
        "history": [],
    }
    refresh_planning_interview(interview)
    return interview


def refresh_planning_interview(interview: dict[str, Any]) -> dict[str, Any]:
    decisions = interview.setdefault("decisions", {})
    missing = [key for key in PLANNING_BRIEF_FIELDS if not str(decisions.get(key) or "").strip()]
    interview["remaining_fields"] = missing
    interview["completed"] = not missing
    pending = interview.get("pending_decision")
    if pending and pending.get("decision_key") not in missing:
        interview["pending_decision"] = None
    interview["current_field"] = str((interview.get("pending_decision") or {}).get("decision_key") or "")
    return interview


def propose_planning_decision(
    interview: dict[str, Any],
    *,
    decision_key: str,
    question: str,
    recommendation: str,
    reason: str,
    evidence: list[dict[str, Any]] | None = None,
    inference: bool = False,
) -> dict[str, Any]:
    updated = deepcopy(interview)
    refresh_planning_interview(updated)
    if updated.get("completed"):
        raise ValueError("视频策划访谈已经达到决策充分性。")
    if updated.get("pending_decision"):
        raise ValueError("当前已有一个待确认决策，不能批量提出问题。")
    if decision_key not in PLANNING_BRIEF_FIELDS:
        raise ValueError(f"未知视频策划决策：{decision_key}")
    if decision_key not in updated["remaining_fields"]:
        raise ValueError(f"视频策划决策已经存在：{decision_key}")
    for label, value in (("问题", question), ("建议", recommendation), ("理由", reason)):
        if not str(value).strip():
            raise ValueError(f"视频策划决策提案缺少{label}。")
    if decision_key in FACT_GROUNDED_FIELDS and not any(
        str(item.get("card_id") or "").strip() for item in (evidence or [])
    ):
        raise ValueError(f"{decision_key} 必须引用视频策划专属接口中的正式知识卡。")
    updated["pending_decision"] = {
        "decision_key": decision_key,
        "question": str(question).strip(),
        "recommendation": str(recommendation).strip(),
        "reason": str(reason).strip(),
        "evidence": list(evidence or []),
        "source_type": "planning_inference" if inference else "confirmed_recommendation",
    }
    refresh_planning_interview(updated)
    return updated


def answer_planning_interview(interview: dict[str, Any], reply: str) -> dict[str, Any]:
    updated = deepcopy(interview)
    refresh_planning_interview(updated)
    pending = dict(updated.get("pending_decision") or {})
    key = str(pending.get("decision_key") or "")
    if key not in PLANNING_BRIEF_FIELDS:
        raise ValueError("当前没有待确认的视频策划决策。")
    normalized = str(reply).strip().casefold()
    if not normalized:
        raise ValueError("请确认当前建议，或直接说明修改内容。")
    if normalized in {item.casefold() for item in CONFIRM_REPLIES}:
        value = str(pending["recommendation"])
        source = str(pending.get("source_type") or "confirmed_recommendation")
    else:
        value = str(reply).strip()
        source = "user_correction"
        if key in FACT_GROUNDED_FIELDS:
            updated.setdefault("unvalidated_fact_corrections", {})[key] = value
            updated["history"].append(
                {"event": "fact_correction_requires_validation", "decision_key": key, "value": value}
            )
            updated["pending_decision"] = None
            refresh_planning_interview(updated)
            return updated
    updated["decisions"][key] = value
    updated["decision_sources"][key] = source
    if pending.get("evidence"):
        updated["decision_evidence"][key] = list(pending["evidence"])
    updated["history"].append(
        {"event": "decision_confirmed", "decision_key": key, "value": value, "source": source}
    )
    updated["pending_decision"] = None
    refresh_planning_interview(updated)
    return updated


def validate_fact_correction(
    interview: dict[str, Any],
    *,
    decision_key: str,
    value: str,
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    updated = deepcopy(interview)
    pending = dict(updated.get("unvalidated_fact_corrections") or {})
    if pending.get(decision_key) != value:
        raise ValueError("找不到匹配的待核验事实修正。")
    if not any(str(item.get("card_id") or "").strip() for item in evidence):
        raise ValueError("事实修正必须引用正式知识卡。")
    updated["decisions"][decision_key] = value.strip()
    updated["decision_sources"][decision_key] = "validated_user_correction"
    updated["decision_evidence"][decision_key] = list(evidence)
    updated.setdefault("unvalidated_fact_corrections", {}).pop(decision_key, None)
    updated["history"].append(
        {"event": "fact_correction_validated", "decision_key": decision_key, "value": value}
    )
    refresh_planning_interview(updated)
    return updated


def confirmed_planning_brief(interview: dict[str, Any]) -> dict[str, str]:
    refresh_planning_interview(interview)
    if not interview.get("completed"):
        raise ValueError("视频策划访谈尚未达到决策充分性：" + "、".join(interview["remaining_fields"]))
    if interview.get("unvalidated_fact_corrections"):
        raise ValueError("视频策划访谈仍有未经正式知识核验的事实修正。")
    return {key: str(interview["decisions"][key]).strip() for key in PLANNING_BRIEF_FIELDS}

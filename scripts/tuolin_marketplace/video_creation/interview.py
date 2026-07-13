from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


# This is a semantic completion contract, not a questionnaire order.
CORE_VIDEO_BRIEF_FIELDS = (
    "audience",
    "audience_problem_scenario",
    "viewing_motivation",
    "trend_evidence",
    "trend_mechanism",
    "material_visual_direction",
    "viewer_interest_direction",
    "intended_takeaway",
    "desired_action",
    "priority_messages",
    "human_relevance_angle",
    "excluded_content",
    "ai_simulation_scope",
)

EVIDENCE_FIELDS = {"trend_evidence", "material_visual_direction"}
FACT_GROUNDED_DECISIONS = {"intended_takeaway", "priority_messages"}
CONFIRM_REPLIES = {"确认", "确认这个建议", "同意", "可以", "就这样", "确定"}
REMOVED_RECOMMENDATION_COMMANDS = {
    "按推荐",
    "采用推荐",
    "用推荐答案",
    "剩下都按推荐",
    "其余都按推荐",
    "你来决定并直接出策划",
    "你来决定，直接出策划",
}

DECISION_LABELS = {
    "audience": "可行动受众",
    "audience_problem_scenario": "受众问题或决策场景",
    "viewing_motivation": "开始并继续观看的理由",
    "trend_evidence": "公开 YouTube 趋势证据",
    "trend_mechanism": "适合本产品的短视频机制",
    "material_visual_direction": "素材支持的画面方向",
    "viewer_interest_direction": "观众兴趣方向",
    "intended_takeaway": "希望观众记住的信息",
    "desired_action": "希望观众采取的行动",
    "priority_messages": "优先产品事实",
    "human_relevance_angle": "人的关联角度",
    "excluded_content": "排除内容和声明风险",
    "ai_simulation_scope": "AI 模拟画面边界",
}


def build_initial_video_brief(
    request_text: str,
    target_audience: str = "",
    core_objective: str = "",
) -> dict[str, str]:
    brief: dict[str, str] = {}
    if target_audience.strip():
        brief["audience"] = target_audience.strip()
    # core_objective is retained in requirements_payload as user intent. It is not promoted
    # to a confirmed product claim until Codex checks it against formal knowledge and proposes
    # the fact-bearing decision explicitly.

    request = request_text.strip()
    action = _infer_desired_action(request)
    if action:
        brief["desired_action"] = action
    excluded = _infer_excluded_content(request)
    if excluded:
        brief["excluded_content"] = excluded
    ai_scope = _infer_ai_simulation_scope(request)
    if ai_scope:
        brief["ai_simulation_scope"] = ai_scope
    return brief


def build_video_interview(initial_brief: dict[str, str]) -> dict[str, Any]:
    decisions = {
        field: str(initial_brief.get(field) or "").strip()
        for field in CORE_VIDEO_BRIEF_FIELDS
        if _initial_decision_is_sufficient(field, str(initial_brief.get(field) or "").strip())
    }
    interview = {
        "schema_version": "video-creative-discovery-v2",
        "decisions": decisions,
        # answers remains a read-only compatibility alias for v1 callers.
        "answers": dict(decisions),
        "decision_sources": {field: "initial_request" for field in decisions},
        "decision_evidence": {},
        "history": [],
        "pending_decision": None,
        "completed": False,
        "remaining_fields": [],
        "internal_evidence_required": [],
    }
    refresh_video_interview(interview)
    return interview


def refresh_video_interview(interview: dict[str, Any]) -> dict[str, Any]:
    decisions = interview.setdefault("decisions", dict(interview.get("answers") or {}))
    interview["answers"] = dict(decisions)
    missing = [field for field in CORE_VIDEO_BRIEF_FIELDS if not str(decisions.get(field) or "").strip()]
    interview["completed"] = not missing
    interview["remaining_fields"] = missing
    interview["internal_evidence_required"] = [
        field
        for field in missing
        if field in EVIDENCE_FIELDS
        and all(str(decisions.get(item) or "").strip() for item in _decision_dependencies(field))
    ]
    pending = interview.get("pending_decision")
    if pending and pending.get("decision_key") not in missing:
        interview["pending_decision"] = None
        pending = None
    interview["current_field"] = str((pending or {}).get("decision_key") or "")
    return interview


def propose_video_interview_decision(
    interview: dict[str, Any],
    *,
    decision_key: str,
    question: str,
    recommendation: str,
    reason: str,
    evidence: list[dict[str, Any]] | None = None,
    proposal_source: str = "codex_reasoning",
) -> dict[str, Any]:
    updated = deepcopy(interview)
    refresh_video_interview(updated)
    if updated.get("completed"):
        raise ValueError("视频创作访谈已经满足决策充分性，不能继续提出问题。")
    if updated.get("pending_decision"):
        raise ValueError("当前已有一项待确认决策，必须先确认或纠正，不能批量提出问题。")
    if decision_key not in CORE_VIDEO_BRIEF_FIELDS:
        raise ValueError(f"未知视频创作决策：{decision_key}")
    if decision_key in EVIDENCE_FIELDS:
        raise ValueError(f"{DECISION_LABELS[decision_key]} 必须由 Codex 调研或素材检查写入，不能作为用户问答提案。")
    if decision_key not in updated.get("remaining_fields", []):
        raise ValueError(f"{DECISION_LABELS[decision_key]} 已有有效决策，不应重复询问。")
    dependencies = _decision_dependencies(decision_key)
    unresolved = [item for item in dependencies if not str(updated["decisions"].get(item) or "").strip()]
    if unresolved:
        raise ValueError("当前决策依赖尚未解决：" + "、".join(DECISION_LABELS[item] for item in unresolved))
    for label, value in {
        "问题": question,
        "建议": recommendation,
        "理由": reason,
    }.items():
        if not str(value).strip():
            raise ValueError(f"视频创作决策提案缺少{label}。")
    _validate_decision_value(decision_key, recommendation)
    if decision_key in FACT_GROUNDED_DECISIONS and not any(
        str(item.get("card_id") or "").strip() for item in (evidence or [])
    ):
        raise ValueError(f"{DECISION_LABELS[decision_key]}必须引用正式知识卡证据。")
    updated["pending_decision"] = {
        "decision_key": decision_key,
        "label": DECISION_LABELS[decision_key],
        "question": question.strip(),
        "recommendation": recommendation.strip(),
        "reason": reason.strip(),
        "evidence": list(evidence or []),
        "proposal_source": proposal_source,
    }
    updated["current_field"] = decision_key
    return updated


def answer_video_interview(interview: dict[str, Any], reply: str) -> dict[str, Any]:
    updated = deepcopy(interview)
    refresh_video_interview(updated)
    if updated.get("completed"):
        raise ValueError("视频创作访谈已经完成，不能继续写入访谈答案。")
    normalized = _normalize(reply)
    if not normalized:
        raise ValueError("请确认当前建议，或直接说明需要怎样修改。")
    if normalized in {_normalize(item) for item in REMOVED_RECOMMENDATION_COMMANDS}:
        raise ValueError("本视频工作流不使用“按推荐”或批量采用建议。请回复“确认”当前建议，或直接说明修改内容。")
    pending = updated.get("pending_decision") or {}
    decision_key = str(pending.get("decision_key") or "")
    if decision_key not in CORE_VIDEO_BRIEF_FIELDS:
        required = "、".join(DECISION_LABELS[item] for item in updated.get("internal_evidence_required", []))
        if required:
            raise ValueError(f"当前需要 Codex 先补充内部证据：{required}。")
        raise ValueError("当前没有可由用户确认的视频创作决策提案。")
    if normalized in {_normalize(item) for item in CONFIRM_REPLIES}:
        value = str(pending["recommendation"]).strip()
        source = "confirmed_recommendation"
    else:
        value = reply.strip()
        source = "user_correction"
    _validate_decision_value(decision_key, value)
    if source == "user_correction" and decision_key in FACT_GROUNDED_DECISIONS:
        updated.setdefault("unvalidated_corrections", {})[decision_key] = value
        updated["history"].append(
            {
                "event": "fact_correction_requires_validation",
                "decision_key": decision_key,
                "value": value,
                "source": source,
                "proposal": pending,
            }
        )
        updated["pending_decision"] = None
        refresh_video_interview(updated)
        return updated
    _store_decision(updated, decision_key, value, source, list(pending.get("evidence") or []))
    updated["history"].append(
        {
            "event": "decision_confirmed" if source == "confirmed_recommendation" else "decision_corrected",
            "decision_key": decision_key,
            "value": value,
            "source": source,
            "proposal": pending,
        }
    )
    updated["pending_decision"] = None
    refresh_video_interview(updated)
    return updated


def record_video_interview_evidence(
    interview: dict[str, Any],
    *,
    decision_key: str,
    value: str,
    evidence: list[dict[str, Any]],
    evidence_source: str,
) -> dict[str, Any]:
    updated = deepcopy(interview)
    refresh_video_interview(updated)
    if decision_key not in EVIDENCE_FIELDS:
        raise ValueError("只有趋势证据和素材画面方向可以通过内部证据接口写入。")
    dependencies = _decision_dependencies(decision_key)
    unresolved = [item for item in dependencies if not str(updated["decisions"].get(item) or "").strip()]
    if unresolved:
        raise ValueError("当前证据依赖尚未解决：" + "、".join(DECISION_LABELS[item] for item in unresolved))
    if not value.strip():
        raise ValueError(f"{DECISION_LABELS[decision_key]} 不能为空。")
    if not evidence and decision_key != "material_visual_direction":
        raise ValueError(f"{DECISION_LABELS[decision_key]} 必须包含可审计证据。")
    _validate_evidence(decision_key, evidence)
    _store_decision(updated, decision_key, value.strip(), evidence_source, evidence)
    updated.setdefault("decision_evidence", {})[decision_key] = list(evidence)
    updated["history"].append(
        {
            "event": "evidence_recorded",
            "decision_key": decision_key,
            "value": value.strip(),
            "source": evidence_source,
            "evidence": evidence,
        }
    )
    refresh_video_interview(updated)
    return updated


def _validate_evidence(decision_key: str, evidence: list[dict[str, Any]]) -> None:
    if decision_key == "trend_evidence":
        for index, item in enumerate(evidence, start=1):
            if item.get("degraded"):
                missing = [
                    key
                    for key in ("reason", "general_principle", "target_language", "target_region")
                    if not str(item.get(key) or "").strip()
                ]
                if missing:
                    raise ValueError(f"降级趋势证据 {index} 缺少字段：{'、'.join(missing)}")
                continue
            required = (
                "source_url",
                "scanned_at",
                "observed_signal",
                "why_it_worked",
                "mechanism",
                "transfer_to_product",
                "relevance_level",
                "target_language",
                "target_region",
            )
            missing = [key for key in required if not str(item.get(key) or "").strip()]
            if missing:
                raise ValueError(f"YouTube 趋势证据 {index} 缺少字段：{'、'.join(missing)}")
            source_url = str(item.get("source_url") or "").lower()
            if "youtube.com/" not in source_url and "youtu.be/" not in source_url:
                raise ValueError(f"YouTube 趋势证据 {index} 不是公开 YouTube 来源。")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(item.get("scanned_at") or "")):
                raise ValueError(f"YouTube 趋势证据 {index} 的扫描日期必须是 YYYY-MM-DD。")
            if item.get("relevance_level") not in {
                "comparable_industrial",
                "adjacent_engineering",
                "transferable_broader",
            }:
                raise ValueError(f"YouTube 趋势证据 {index} 的相关层级不符合相关性阶梯。")
            excluded = item.get("excluded_methods")
            if not isinstance(excluded, list):
                raise ValueError(f"YouTube 趋势证据 {index} 必须记录 excluded_methods 数组，可为空数组。")
    if decision_key == "material_visual_direction":
        required = ("material_id", "subject", "clarity", "composition", "vertical_crop", "near_duplicate_of")
        for index, item in enumerate(evidence, start=1):
            missing = [key for key in required if key not in item]
            if missing:
                raise ValueError(f"素材视觉证据 {index} 缺少字段：{'、'.join(missing)}")


def current_video_interview_prompt(interview: dict[str, Any]) -> str:
    refresh_video_interview(interview)
    if interview.get("completed"):
        return "视频创作决策已经充分，可以转换为正式策划。"
    pending = interview.get("pending_decision") or {}
    if pending:
        lines = [
            f"视频创作当前决策：{pending['label']}",
            "",
            f"问题：{pending['question']}",
            f"建议：{pending['recommendation']}",
            f"理由：{pending['reason']}",
        ]
        evidence = pending.get("evidence") or []
        if evidence:
            lines.extend(["", "依据："])
            for item in evidence[:4]:
                lines.append(f"- {item.get('summary') or item.get('title') or item.get('source') or item}")
        lines.extend(["", "是否确认？如需调整，直接说明修改内容即可。"])
        return "\n".join(lines)
    required = [DECISION_LABELS[item] for item in interview.get("internal_evidence_required", [])]
    if required:
        return "Codex 内部动作：先完成" + "、".join(required) + "，记录证据后再向用户提出下一项决策。"
    unvalidated = interview.get("unvalidated_corrections") or {}
    if unvalidated:
        labels = "、".join(DECISION_LABELS[item] for item in unvalidated)
        return f"Codex 内部动作：先用正式知识卡核验用户对{labels}的修改，再形成新的单一建议供确认。"
    return "Codex 内部动作：基于当前知识、证据和已确认决策，提出下一项最有价值的视频创作决策。"


def confirmed_video_brief(interview: dict[str, Any]) -> dict[str, str]:
    refresh_video_interview(interview)
    if not interview.get("completed"):
        missing = "、".join(DECISION_LABELS[item] for item in interview.get("remaining_fields", []))
        raise ValueError(f"视频创作决策尚未充分，不能生成策划。缺少：{missing}")
    brief = {field: str(interview["decisions"][field]).strip() for field in CORE_VIDEO_BRIEF_FIELDS}
    # Compatibility projection for existing planning helpers while they migrate to v2 names.
    brief["visual_balance"] = brief["material_visual_direction"]
    return brief


def _store_decision(
    interview: dict[str, Any],
    decision_key: str,
    value: str,
    source: str,
    evidence: list[dict[str, Any]],
) -> None:
    interview.setdefault("decisions", {})[decision_key] = value.strip()
    interview["answers"] = dict(interview["decisions"])
    interview.setdefault("decision_sources", {})[decision_key] = source
    interview.setdefault("unvalidated_corrections", {}).pop(decision_key, None)
    if evidence:
        interview.setdefault("decision_evidence", {})[decision_key] = evidence


def _next_askable_decision(interview: dict[str, Any]) -> str:
    missing = set(interview.get("remaining_fields", []))
    for decision_key in CORE_VIDEO_BRIEF_FIELDS:
        if decision_key not in missing or decision_key in EVIDENCE_FIELDS:
            continue
        dependencies = _decision_dependencies(decision_key)
        if all(str(interview["decisions"].get(item) or "").strip() for item in dependencies):
            return decision_key
    return ""


def _decision_dependencies(decision_key: str) -> tuple[str, ...]:
    dependencies = {
        "audience_problem_scenario": ("audience",),
        "viewing_motivation": ("audience", "audience_problem_scenario"),
        "trend_evidence": ("audience", "audience_problem_scenario"),
        "material_visual_direction": ("audience", "audience_problem_scenario"),
        "human_relevance_angle": ("audience", "audience_problem_scenario"),
        "trend_mechanism": ("audience", "audience_problem_scenario", "trend_evidence"),
        "viewer_interest_direction": (
            "audience",
            "audience_problem_scenario",
            "viewing_motivation",
            "trend_evidence",
            "trend_mechanism",
            "material_visual_direction",
        ),
    }
    return dependencies.get(decision_key, ())


def _initial_decision_is_sufficient(decision_key: str, value: str) -> bool:
    if not value:
        return False
    if decision_key == "audience":
        normalized = _normalize(value)
        generic_audiences = {
            "客户",
            "工业客户",
            "海外客户",
            "欧美客户",
            "采购商",
            "工业采购商",
            "欧美工业采购商",
            "工程师",
            "所有客户",
        }
        return normalized not in generic_audiences
    return True


def _validate_decision_value(decision_key: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{DECISION_LABELS[decision_key]}不能为空。")
    if decision_key == "audience" and not _initial_decision_is_sufficient(decision_key, value):
        raise ValueError("受众仍然过宽，必须具体到会被视频内容影响的角色、职责或决策场景。")


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().lower())


def _infer_desired_action(request_text: str) -> str:
    lowered = request_text.lower()
    if any(token in lowered for token in ["询盘", "询价", "报价", "样品", "contact", "inquiry", "quote", "sample"]):
        return "带着应用条件联系拓霖，索取规格、样品或报价。"
    return ""


def _infer_excluded_content(request_text: str) -> str:
    matches = re.findall(r"(?:不要|不需要|排除|避免)([^。；;\n]+)", request_text)
    return "；".join(item.strip(" ，,") for item in matches if item.strip(" ，,"))


def _infer_ai_simulation_scope(request_text: str) -> str:
    lowered = request_text.lower()
    if any(token in lowered for token in ["不要ai", "不使用ai", "no ai", "不允许模拟"]):
        return "不允许 AI 模拟应用场景，只使用正式官方图片。"
    return ""

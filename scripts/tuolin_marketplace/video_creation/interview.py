from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


CORE_VIDEO_BRIEF_FIELDS = (
    "audience",
    "intended_takeaway",
    "desired_action",
    "priority_messages",
    "visual_balance",
    "excluded_content",
)


INTERVIEW_QUESTIONS = {
    "audience": {
        "question": "这条视频最主要给哪类人看？",
        "recommendation": "欧美工业采购商",
        "reason": "采购角色更关心应用匹配、产品可信度和下一步询样或询价。",
    },
    "intended_takeaway": {
        "question": "观众看完后，最希望他们记住哪一件事？",
        "recommendation": "记住这是一款用于已确认工业隔热包覆场景的产品，并愿意进一步了解。",
        "reason": "一个清楚的核心认知比同时堆叠很多未经确认的卖点更容易形成记忆。",
    },
    "desired_action": {
        "question": "看完视频后，希望观众采取什么动作？",
        "recommendation": "带着应用条件联系拓霖，索取规格、样品或报价。",
        "reason": "这符合工业采购决策路径，也能避免视频只展示产品却没有下一步。",
    },
    "priority_messages": {
        "question": "这条视频必须优先讲清哪些产品信息？",
        "recommendation": "产品用途、真实外观与织纹、包覆方式，以及采购前需要确认的信息。",
        "reason": "这些信息可以由正式知识卡和真实图片共同支撑，适合采购沟通。",
    },
    "visual_balance": {
        "question": "画面更希望偏产品细节，还是偏实际应用场景？",
        "recommendation": "应用场景为主，产品细节为辅。",
        "reason": "应用画面先帮助采购商理解用途，产品细节再补足材料可信度。",
    },
    "excluded_content": {
        "question": "有哪些内容明确不希望出现在视频里？",
        "recommendation": "不出现未经知识卡确认的参数、认证、绝对化承诺、竞品攻击和虚构客户现场。",
        "reason": "这样能控制对外宣传风险，并确保每个事实都可追溯。",
    },
}


ACCEPT_CURRENT_RECOMMENDATION = {"按推荐", "采用推荐", "用推荐答案"}
ACCEPT_REMAINING_RECOMMENDATIONS = {
    "剩下都按推荐",
    "其余都按推荐",
    "你来决定并直接出策划",
    "你来决定，直接出策划",
}


def build_initial_video_brief(
    request_text: str,
    target_audience: str = "",
    core_objective: str = "",
) -> dict[str, str]:
    brief: dict[str, str] = {}
    if target_audience.strip():
        brief["audience"] = target_audience.strip()
    if core_objective.strip():
        objective = core_objective.strip()
        brief["intended_takeaway"] = objective
        brief["priority_messages"] = objective

    request = request_text.strip()
    if not brief.get("desired_action"):
        action = _infer_desired_action(request)
        if action:
            brief["desired_action"] = action
    visual_balance = _infer_visual_balance(request)
    if visual_balance:
        brief["visual_balance"] = visual_balance
    excluded = _infer_excluded_content(request)
    if excluded:
        brief["excluded_content"] = excluded
    return brief


def build_video_interview(initial_brief: dict[str, str]) -> dict[str, Any]:
    answers = {
        field: str(initial_brief.get(field) or "").strip()
        for field in CORE_VIDEO_BRIEF_FIELDS
        if str(initial_brief.get(field) or "").strip()
    }
    interview = {
        "schema_version": "video-creation-interview-v1",
        "answers": answers,
        "answer_sources": {field: "initial_request" for field in answers},
        "delegated_fields": [],
        "history": [],
        "completed": False,
        "current_field": "",
    }
    refresh_video_interview(interview)
    return interview


def refresh_video_interview(interview: dict[str, Any]) -> dict[str, Any]:
    answers = interview.setdefault("answers", {})
    missing = [field for field in CORE_VIDEO_BRIEF_FIELDS if not str(answers.get(field) or "").strip()]
    interview["completed"] = not missing
    interview["current_field"] = missing[0] if missing else ""
    interview["remaining_fields"] = missing
    return interview


def answer_video_interview(interview: dict[str, Any], reply: str) -> dict[str, Any]:
    updated = deepcopy(interview)
    refresh_video_interview(updated)
    if updated.get("completed"):
        raise ValueError("视频创作访谈已经完成，不能继续写入访谈答案。")

    normalized = re.sub(r"\s+", "", reply.strip().lower())
    if not normalized:
        raise ValueError("请回答当前视频创作问题，或回复“按推荐”。")

    if normalized in {re.sub(r"\s+", "", item.lower()) for item in ACCEPT_REMAINING_RECOMMENDATIONS}:
        for field in list(updated.get("remaining_fields", [])):
            _store_answer(updated, field, INTERVIEW_QUESTIONS[field]["recommendation"], "delegated_recommendation")
            updated.setdefault("delegated_fields", []).append(field)
        refresh_video_interview(updated)
        return updated

    field = str(updated.get("current_field") or "")
    if field not in INTERVIEW_QUESTIONS:
        raise ValueError("当前访谈问题状态无效，不能安全记录答案。")
    if normalized in {re.sub(r"\s+", "", item.lower()) for item in ACCEPT_CURRENT_RECOMMENDATION}:
        value = INTERVIEW_QUESTIONS[field]["recommendation"]
        source = "current_recommendation"
    else:
        value = reply.strip()
        source = "user"
    _store_answer(updated, field, value, source)
    refresh_video_interview(updated)
    return updated


def current_video_interview_prompt(interview: dict[str, Any]) -> str:
    refresh_video_interview(interview)
    if interview.get("completed"):
        return "视频创作核心信息已经完整，正在生成策划。"
    field = str(interview["current_field"])
    definition = INTERVIEW_QUESTIONS[field]
    answered = len(CORE_VIDEO_BRIEF_FIELDS) - len(interview.get("remaining_fields", []))
    current_number = answered + 1
    return "\n".join(
        [
            f"视频创作访谈（{current_number}/{len(CORE_VIDEO_BRIEF_FIELDS)}）",
            "",
            f"问题：{definition['question']}",
            f"建议：{definition['recommendation']}",
            f"理由：{definition['reason']}",
            "",
            "你可以直接回答，或回复 `按推荐`。如果希望剩余问题全部采用建议，可回复 `剩下都按推荐`。",
        ]
    )


def confirmed_video_brief(interview: dict[str, Any]) -> dict[str, str]:
    refresh_video_interview(interview)
    if not interview.get("completed"):
        raise ValueError("视频创作核心信息尚未完整，不能生成策划。")
    return {field: str(interview["answers"][field]).strip() for field in CORE_VIDEO_BRIEF_FIELDS}


def _store_answer(interview: dict[str, Any], field: str, value: str, source: str) -> None:
    interview.setdefault("answers", {})[field] = value.strip()
    interview.setdefault("answer_sources", {})[field] = source
    interview.setdefault("history", []).append({"field": field, "answer": value.strip(), "source": source})


def _infer_desired_action(request_text: str) -> str:
    lowered = request_text.lower()
    if any(token in lowered for token in ["询盘", "询价", "报价", "样品", "contact", "inquiry", "quote", "sample"]):
        return "带着应用条件联系拓霖，索取规格、样品或报价。"
    return ""


def _infer_visual_balance(request_text: str) -> str:
    lowered = request_text.lower()
    has_application = any(token in lowered for token in ["应用", "安装", "施工", "包覆", "缠绕", "application", "install", "wrap"])
    has_detail = any(token in lowered for token in ["细节", "织纹", "产品实拍", "detail", "texture", "product"])
    if has_application and has_detail:
        return "应用场景与产品细节均衡。"
    if has_application:
        return "应用场景为主，产品细节为辅。"
    if has_detail:
        return "产品细节为主，应用场景为辅。"
    return ""


def _infer_excluded_content(request_text: str) -> str:
    matches = re.findall(r"(?:不要|不需要|排除|避免)([^。；;\n]+)", request_text)
    return "；".join(item.strip(" ，,") for item in matches if item.strip(" ，,"))


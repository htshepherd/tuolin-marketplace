from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


INTERVIEW_ORDER = (
    "keywords",
    "sort_order",
    "publication_range",
    "invitation_note",
    "interval_seconds",
    "requested_limit",
)

QUESTION_NUMBERS = {key: index for index, key in enumerate(INTERVIEW_ORDER, start=1)}


def build_search_interview(request_text: str, context: dict[str, Any]) -> dict[str, Any]:
    answers = _extract_explicit_answers(request_text)
    recommendations = _build_recommendations(context, request_text)
    interview = {
        "schema_version": 1,
        "answers": answers,
        "recommendations": recommendations,
        "pending_question": None,
        "history": [],
        "completed": False,
    }
    return _advance(interview)


def answer_search_interview(interview: dict[str, Any], reply: str) -> dict[str, Any]:
    updated = deepcopy(interview)
    pending = dict(updated.get("pending_question") or {})
    if not pending:
        if updated.get("completed"):
            raise ValueError("LinkedIn 搜索访谈已经完成，不能继续记录答案。")
        raise ValueError("LinkedIn 搜索访谈没有待确认问题。")
    text = reply.strip()
    if not text:
        raise ValueError("访谈答案不能为空。")
    if _is_bulk_confirmation(text):
        raise ValueError("不支持一次确认所有剩余问题；请只回答当前问题。")

    field = str(pending["field"])
    accepted_recommendation = _is_current_confirmation(text)
    raw_value = pending["recommended_value"] if accepted_recommendation else text
    value = _normalize_answer(field, raw_value)
    source = "recommended_confirmed" if accepted_recommendation else "user_supplied"
    updated.setdefault("answers", {})[field] = value
    updated.setdefault("history", []).append(
        {
            "field": field,
            "value": value,
            "source": source,
            "question_number": pending["question_number"],
        }
    )
    updated["pending_question"] = None
    return _advance(updated)


def current_search_interview_prompt(interview: dict[str, Any]) -> str:
    if interview.get("completed"):
        return "LinkedIn 搜索访谈已完成。"
    pending = interview.get("pending_question") or {}
    if not pending:
        raise ValueError("LinkedIn 搜索访谈缺少待确认问题。")
    return (
        f"第{_chinese_number(int(pending['question_number']))}问：{pending['question']}\n\n"
        f"我的推荐答案：{pending['recommendation']}\n"
        f"推荐理由：{pending['reason']}\n\n"
        "是否确认？"
    )


def confirmed_search_brief(interview: dict[str, Any]) -> dict[str, Any]:
    if not interview.get("completed"):
        raise ValueError("LinkedIn 搜索访谈尚未完成。")
    answers = deepcopy(interview.get("answers") or {})
    keywords = list(answers.get("keywords") or [])
    history = list(interview.get("history") or [])
    keyword_history = next((item for item in history if item.get("field") == "keywords"), None)
    source = "knowledge_recommended" if keyword_history and keyword_history.get("source") == "recommended_confirmed" else "user_supplied"
    answers["search_terms"] = [
        {"term": term, "source": source, "formal_knowledge": False}
        for term in keywords
    ]
    answers["candidate_intent"] = "potential_customer"
    answers["search_surface"] = "linkedin_posts"
    answers["opened_post_limit_per_keyword"] = 50
    return answers


def _advance(interview: dict[str, Any]) -> dict[str, Any]:
    answers = interview.setdefault("answers", {})
    for field in INTERVIEW_ORDER:
        if field in answers:
            continue
        recommendation = dict(interview["recommendations"][field])
        interview["pending_question"] = {
            "field": field,
            "question_number": QUESTION_NUMBERS[field],
            "question": recommendation["question"],
            "recommendation": recommendation["display"],
            "recommended_value": recommendation["value"],
            "reason": recommendation["reason"],
        }
        interview["completed"] = False
        return interview
    interview["pending_question"] = None
    interview["completed"] = True
    return interview


def _extract_explicit_answers(text: str) -> dict[str, Any]:
    answers: dict[str, Any] = {}
    keywords = _extract_keywords(text)
    if keywords:
        answers["keywords"] = keywords
    lower = text.casefold()
    if any(token in lower for token in ("按最新", "排序最新", "latest")) or re.search(r"排序\s*[：:=]?\s*最新", lower):
        answers["sort_order"] = "latest"
    elif any(token in lower for token in ("最匹配", "best match")) or re.search(r"排序\s*[：:=]?\s*最匹配", lower):
        answers["sort_order"] = "best_match"
    if any(token in lower for token in ("近24小时", "过去24小时", "past 24 hours")):
        answers["publication_range"] = "past_24_hours"
    elif any(token in lower for token in ("近1周", "近一周", "过去一周", "past week")):
        answers["publication_range"] = "past_week"
    elif any(token in lower for token in ("近1个月", "近一个月", "过去一个月", "past month")):
        answers["publication_range"] = "past_month"
    if any(token in lower for token in ("不留言", "不用留言", "不使用留言", "无留言", "without note", "no note")):
        answers["invitation_note"] = False
    elif any(token in lower for token in ("使用留言", "加留言", "with note")):
        answers["invitation_note"] = True
    interval = re.search(r"(?:间隔|每隔)\s*(\d+)\s*分钟", text)
    if interval:
        answers["interval_seconds"] = int(interval.group(1)) * 60
    limit = re.search(r"(?:最多|上限|添加|邀请)\s*(\d+)\s*(?:人|个)", text)
    if limit:
        answers["requested_limit"] = int(limit.group(1))
    return answers


def _extract_keywords(text: str) -> list[str]:
    match = re.search(
        r"(?:关键词|keywords?)\s*[：:=]\s*(.+?)(?=(?:[，；;]\s*(?:排序|日期|时间|留言|间隔|数量|上限)(?:\s*[：:=])?)|$)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return []
    value = match.group(1).strip().strip("。.")
    parts = [part.strip(" \"'“”‘’") for part in re.split(r"[,，;；、\n]+", value)]
    return _dedupe_terms([part for part in parts if part])


def _build_recommendations(context: dict[str, Any], request_text: str) -> dict[str, dict[str, Any]]:
    keyword_values = _recommended_keywords(context, request_text)
    if not keyword_values:
        product_cards = context.get("cards_by_type", {}).get("product", [])
        product_id = str(product_cards[0].get("id") or "") if product_cards else ""
        derived = product_id.split("/", 1)[-1].replace("_", " ").strip()
        keyword_values = [derived] if derived else []
        keyword_reason = "该词由当前正式产品 ID 派生，仅作为 search-only 查询词；不会成为新的正式产品名称或声明。"
    else:
        keyword_reason = "这些英文词来自当前正式产品名称、别名或已确认应用场景，适合作为首轮 Posts 搜索词。"
    return {
        "keywords": {
            "question": "本次按什么顺序搜索 LinkedIn 贴文关键词？",
            "value": keyword_values,
            "display": "按顺序使用 " + "、".join(keyword_values),
            "reason": keyword_reason,
        },
        "sort_order": {
            "question": "贴文搜索使用什么排序？",
            "value": "latest",
            "display": "使用 Latest（最新）",
            "reason": "近期发布内容更能反映公司当前是否正在销售、推广或采购相关产品。",
        },
        "publication_range": {
            "question": "贴文发布日期范围使用什么条件？",
            "value": "past_month",
            "display": "使用 Past month（近一个月）",
            "reason": "近一个月兼顾时效性和候选数量，且能直接映射到 Posts 搜索条件。",
        },
        "invitation_note": {
            "question": "连接邀请是否使用 Add a note 留言？",
            "value": False,
            "display": "第一批不使用留言",
            "reason": "先验证搜索、候选审核和可靠发送主链路；如需留言，可直接回答使用留言。",
        },
        "interval_seconds": {
            "question": "批次内两次连接邀请之间使用多长固定间隔？",
            "value": 300,
            "display": "固定间隔 5 分钟",
            "reason": "这是已确认的推荐默认值，执行可预测且便于审计。",
        },
        "requested_limit": {
            "question": "本次任务最多发送多少个连接邀请？",
            "value": 10,
            "display": "最多 10 个",
            "reason": "10 是已确认的默认单次上限；它是 ceiling，不要求为了凑数放宽条件。",
        },
    }


def _recommended_keywords(context: dict[str, Any], request_text: str) -> list[str]:
    terms: list[str] = []
    for card_type in ("product", "application_scenario"):
        for card in context.get("cards_by_type", {}).get(card_type, []):
            values = [card.get("title"), *list(card.get("aliases") or []), *list(card.get("tags") or [])]
            for value in values:
                term = str(value or "").strip()
                if term and re.search(r"[A-Za-z]", term) and not re.search(r"[\u4e00-\u9fff]", term):
                    terms.append(term)
    for term in _extract_keywords(request_text):
        if re.search(r"[A-Za-z]", term):
            terms.insert(0, term)
    return _dedupe_terms(terms)[:6]


def _normalize_answer(field: str, value: Any) -> Any:
    if field == "keywords":
        if isinstance(value, list):
            terms = [str(item).strip() for item in value]
        else:
            text = str(value).strip()
            text = re.sub(
                r"^(?:使用|按顺序使用|搜索关键词(?:为|是|用)?|关键词(?:为|是|用)?)[：:\s]*",
                "",
                text,
            )
            terms = [part.strip(" \"'“”‘’") for part in re.split(r"[,，;；、\n]+", text)]
        result = _dedupe_terms([term for term in terms if term])
        if not result:
            raise ValueError("关键词至少需要一个非空值。")
        return result
    if field == "sort_order":
        text = str(value).casefold()
        if any(token in text for token in ("latest", "最新")):
            return "latest"
        if any(token in text for token in ("best_match", "best match", "最匹配")):
            return "best_match"
        raise ValueError("排序只支持 Latest（最新）或 Best match（最匹配）。")
    if field == "publication_range":
        text = str(value).casefold()
        if any(token in text for token in ("past_24_hours", "24", "近一天")):
            return "past_24_hours"
        if any(token in text for token in ("past_week", "一周", "1周", "week")):
            return "past_week"
        if any(token in text for token in ("past_month", "一个月", "1个月", "month")):
            return "past_month"
        raise ValueError("发布日期范围只支持近 24 小时、近 1 周或近 1 个月。")
    if field == "invitation_note":
        if isinstance(value, bool):
            return value
        text = str(value).casefold()
        if any(token in text for token in ("不使用", "不用", "不要", "无留言", "no note", "without")):
            return False
        if any(token in text for token in ("使用", "需要", "加留言", "with note")):
            return True
        raise ValueError("请明确回答使用留言或不使用留言。")
    if field == "interval_seconds":
        if isinstance(value, int):
            seconds = value
        else:
            text = str(value)
            minute_match = re.search(r"(\d+)\s*分钟", text)
            second_match = re.search(r"(\d+)\s*秒", text)
            seconds = int(minute_match.group(1)) * 60 if minute_match else int(second_match.group(1)) if second_match else 0
        if seconds <= 0:
            raise ValueError("固定间隔必须大于 0 秒。")
        return seconds
    if field == "requested_limit":
        if isinstance(value, int):
            limit = value
        else:
            match = re.search(r"\d+", str(value))
            limit = int(match.group(0)) if match else 0
        if limit <= 0:
            raise ValueError("本次邀请上限必须是正整数。")
        return limit
    raise ValueError(f"未知访谈字段：{field}")


def _is_current_confirmation(text: str) -> bool:
    return text.strip().casefold() in {"确认", "是", "yes", "confirm", "ok", "okay"}


def _is_bulk_confirmation(text: str) -> bool:
    compact = re.sub(r"\s+", "", text.casefold())
    return any(token in compact for token in ("剩下都按推荐", "全部按推荐", "一次确认所有", "全部确认"))


def _dedupe_terms(terms: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for term in terms:
        normalized = term.casefold().strip()
        if normalized and normalized not in seen:
            result.append(term.strip())
            seen.add(normalized)
    return result


def _chinese_number(value: int) -> str:
    mapping = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六"}
    return mapping.get(value, str(value))

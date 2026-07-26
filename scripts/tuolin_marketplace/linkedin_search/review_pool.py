from __future__ import annotations

from copy import deepcopy
from typing import Any


def allocate_first_pass_shares(target: int, keywords: list[str]) -> list[int]:
    """Allocate deterministic soft shares; earlier keywords receive remainders."""
    if not 1 <= int(target) <= 100:
        raise ValueError("人工审核人数必须是 1–100 的整数。")
    if not keywords:
        raise ValueError("至少需要一个关键词。")
    quotient, remainder = divmod(int(target), len(keywords))
    return [quotient + (1 if index < remainder else 0) for index in range(len(keywords))]


def initialize_review_pool(target: int, keywords: list[str]) -> dict[str, Any]:
    shares = allocate_first_pass_shares(target, keywords)
    return {
        "target": int(target),
        "new_contact_ids": [],
        "repeated_contact_ids": [],
        "current_keyword_index": 0,
        "pass": "first_pass",
        "keywords": [
            {
                "keyword": keyword,
                "first_pass_target": shares[index],
                "new_contact_ids": [],
                "first_pass_completed": False,
                "exhausted": False,
                "refill_eligible": True,
                "opened_post_count": 0,
                "evaluated_post_urls": [],
                "seen_result_urls": [],
                "scroll_cycles": [],
                "consecutive_bottom_no_growth_cycles": 0,
            }
            for index, keyword in enumerate(keywords)
        ],
    }


def register_contact(pool: dict[str, Any], candidate_id: str, *, is_new: bool) -> dict[str, Any]:
    updated = deepcopy(pool)
    key = "new_contact_ids" if is_new else "repeated_contact_ids"
    if candidate_id not in updated.setdefault(key, []):
        updated[key].append(candidate_id)
    if is_new:
        current = current_keyword_state(updated)
        if candidate_id not in current.setdefault("new_contact_ids", []):
            current["new_contact_ids"].append(candidate_id)
    return updated


def current_keyword_state(pool: dict[str, Any]) -> dict[str, Any]:
    index = int(pool.get("current_keyword_index") or 0)
    keywords = pool.get("keywords") or []
    if index < 0 or index >= len(keywords):
        raise ValueError("审核池关键词索引无效。")
    return keywords[index]


def pool_is_full(pool: dict[str, Any]) -> bool:
    return len(pool.get("new_contact_ids") or []) >= int(pool.get("target") or 0)


def keyword_can_finish(pool: dict[str, Any]) -> tuple[bool, str]:
    current = current_keyword_state(pool)
    if pool_is_full(pool):
        return True, "human_review_pool_full"
    if int(current.get("consecutive_bottom_no_growth_cycles") or 0) >= 3:
        return True, "verified_infinite_scroll_exhaustion"
    if pool.get("pass") == "first_pass" and len(current.get("new_contact_ids") or []) >= int(current.get("first_pass_target") or 0):
        return True, "first_pass_soft_share_reached"
    return False, "continue_scrolling"


def finish_keyword(pool: dict[str, Any]) -> tuple[dict[str, Any], str, str | None]:
    """Finish the current opportunity and return (pool, outcome, next keyword)."""
    updated = deepcopy(pool)
    allowed, reason = keyword_can_finish(updated)
    if not allowed:
        raise ValueError("当前关键词尚未达到软份额、审核池目标或可验证耗尽条件。")
    current = current_keyword_state(updated)
    if reason == "verified_infinite_scroll_exhaustion":
        current["exhausted"] = True
        current["refill_eligible"] = False
    if updated.get("pass") == "first_pass":
        current["first_pass_completed"] = True
    if pool_is_full(updated):
        return updated, "human_review_pool_full", None

    if updated.get("pass") == "first_pass":
        for index, item in enumerate(updated.get("keywords") or []):
            if not item.get("first_pass_completed"):
                updated["current_keyword_index"] = index
                return updated, reason, item["keyword"]
        updated["pass"] = "refill"

    for index, item in enumerate(updated.get("keywords") or []):
        if not item.get("exhausted") and item.get("refill_eligible", True):
            updated["current_keyword_index"] = index
            return updated, reason, item["keyword"]
    return updated, "all_keywords_verified_exhausted", None


def update_current_keyword_progress(pool: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(pool)
    current = current_keyword_state(updated)
    for key in (
        "opened_post_count",
        "evaluated_post_urls",
        "seen_result_urls",
        "scroll_cycles",
        "consecutive_bottom_no_growth_cycles",
    ):
        current[key] = deepcopy(progress.get(key))
    return updated


def progress_for_current_keyword(pool: dict[str, Any]) -> dict[str, Any]:
    current = current_keyword_state(pool)
    return {
        "opened_post_count": int(current.get("opened_post_count") or 0),
        "evaluated_post_urls": list(current.get("evaluated_post_urls") or []),
        "seen_result_urls": list(current.get("seen_result_urls") or []),
        "scroll_cycles": list(current.get("scroll_cycles") or []),
        "consecutive_bottom_no_growth_cycles": int(current.get("consecutive_bottom_no_growth_cycles") or 0),
    }

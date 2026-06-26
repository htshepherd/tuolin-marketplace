from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agent_interface import evidence_for_card, knowledge_status, open_reviews, read_cards_by_type, search_cards
from .project_layout import ProjectPaths


TASK_TYPES = {
    "youtube_video": {"audience": "external", "card_types": ["product", "application_scenario", "content_asset"]},
    "linkedin_post": {
        "audience": "external",
        "card_types": ["product", "application_scenario", "sales_material", "content_asset"],
    },
    "outreach_email": {"audience": "external", "card_types": ["product", "application_scenario", "sales_material"]},
    "follow_up_email": {"audience": "external", "card_types": ["product", "sales_material", "customer_question"]},
    "video_creation": {
        "audience": "external",
        "card_types": ["product", "content_asset"],
        "fixed_product_id": "product/quartz_fiber_tape",
        "no_keyword_expansion": True,
    },
    "customer_support": {"audience": "internal", "card_types": ["product", "customer_question", "sales_material"]},
}


def build_downstream_context(
    paths: ProjectPaths,
    task_type: str,
    product_id: str | None = None,
    query: str | None = None,
    include_review_items: bool = False,
) -> dict[str, Any]:
    if task_type not in TASK_TYPES:
        raise ValueError(f"Unsupported downstream task type: {task_type}")

    config = TASK_TYPES[task_type]
    fixed_product_id = config.get("fixed_product_id")
    if fixed_product_id:
        if product_id and product_id != fixed_product_id:
            raise ValueError(f"{task_type} only supports {fixed_product_id}")
        product_id = fixed_product_id

    audience = config["audience"]
    selected = _select_cards(
        paths,
        config["card_types"],
        audience,
        product_id,
        query,
        allow_query_expansion=not config.get("no_keyword_expansion", False),
    )
    evidence = _collect_evidence(paths, selected)
    risks = _review_risks(paths, selected, product_id) if include_review_items else []
    excluded_summary = _excluded_summary(
        paths,
        config["card_types"],
        audience,
        product_id,
        query,
        allow_query_expansion=not config.get("no_keyword_expansion", False),
    )
    status = knowledge_status(paths)
    context_id = _context_id(task_type, product_id, query)
    context = {
        "context_id": context_id,
        "task_type": task_type,
        "audience": audience,
        "product_id": product_id,
        "query": query,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "interface_revision": status["manifest"]["interface_revision"],
        "valid": True,
        "raw_access": False,
        "cards_by_type": _group_by_type(selected),
        "evidence": evidence,
        "risk_items": risks,
        "excluded_summary": excluded_summary,
        "policy": {
            "source_boundary": "generated/agent-interface only",
            "official_only": True,
            "external_requires": "external_allowed",
            "review_items_are_facts": False,
            "contexts_are_formal_knowledge": False,
            "content_assets_prove_product_facts": False,
            "no_keyword_expansion": bool(config.get("no_keyword_expansion", False)),
            "fixed_product_scope": fixed_product_id,
        },
        "note": "下游任务上下文只用于本次任务，不是正式知识；不得扫描 raw，也不得把上下文结论写回 knowledge/okf/。",
    }
    _write_context(paths, context)
    return context


def _select_cards(
    paths: ProjectPaths,
    card_types: list[str],
    audience: str,
    product_id: str | None,
    query: str | None,
    allow_query_expansion: bool = True,
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for card_type in card_types:
        for card in read_cards_by_type(paths, card_type, include_non_official=True):
            if not _usable_for_audience(card, audience):
                continue
            if product_id and not _relates_to_product(card, product_id):
                continue
            if query and _query_sensitive(card["type"]) and not _matches_query(card, query):
                continue
            cards.append(card)

    if query and allow_query_expansion:
        for card in search_cards(paths, query, include_non_official=True, limit=20):
            if card["type"] in card_types and _usable_for_audience(card, audience):
                if product_id and not _relates_to_product(card, product_id):
                    continue
                cards.append(card)
    return _dedupe(cards)


def _collect_evidence(paths: ProjectPaths, cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence = []
    for card in cards:
        evidence.extend(evidence_for_card(paths, card["id"]))
    return _dedupe(evidence)


def _review_risks(paths: ProjectPaths, cards: list[dict[str, Any]], product_id: str | None) -> list[dict[str, Any]]:
    selected_ids = {card["id"] for card in cards}
    risks = []
    for review in open_reviews(paths):
        affected = set(review["frontmatter"].get("affected_cards", []))
        if selected_ids & affected:
            risks.append(_risk_item(review))
            continue
        if product_id and (product_id in affected or any(product_id in item for item in affected)):
            risks.append(_risk_item(review))
    return risks


def _excluded_summary(
    paths: ProjectPaths,
    card_types: list[str],
    audience: str,
    product_id: str | None,
    query: str | None,
    allow_query_expansion: bool = True,
) -> dict[str, int]:
    counts = {"draft": 0, "review_required": 0, "archived": 0, "usage_scope_blocked": 0}
    for card_type in card_types:
        for card in read_cards_by_type(paths, card_type, include_non_official=True):
            if product_id and not _relates_to_product(card, product_id):
                continue
            if allow_query_expansion and query and _query_sensitive(card_type) and not _matches_query(card, query):
                continue
            status = card.get("status")
            if status in counts:
                counts[status] += 1
            elif not _usable_for_audience(card, audience):
                counts["usage_scope_blocked"] += 1
    return counts


def _usable_for_audience(card: dict[str, Any], audience: str) -> bool:
    if card.get("status") != "official":
        return False
    scope = card.get("usage_scope")
    if scope in {"evidence_only", "not_answerable"}:
        return False
    if audience == "external":
        return scope == "external_allowed"
    return scope in {"external_allowed", "internal_only"}


def _relates_to_product(card: dict[str, Any], product_id: str) -> bool:
    if card["id"] == product_id:
        return True
    frontmatter = card.get("frontmatter", {})
    return product_id in frontmatter.get("related_products", []) or product_id in frontmatter.get("related_refs", [])


def _matches_query(card: dict[str, Any], query: str) -> bool:
    if not query:
        return True
    text = " ".join(
        [
            card.get("title", ""),
            " ".join(card.get("aliases", [])),
            " ".join(card.get("tags", [])),
            card.get("body_excerpt", ""),
        ]
    )
    return any(token in text for token in _tokens(query))


def _query_sensitive(card_type: str) -> bool:
    return card_type in {"application_scenario", "customer_question", "market_intelligence"}


def _tokens(query: str) -> list[str]:
    return [token for token in re.split(r"[\s，。；、,.!?！？:：]+", query.strip()) if token]


def _group_by_type(cards: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for card in cards:
        grouped.setdefault(card["type"], []).append(card)
    return grouped


def _risk_item(review: dict[str, Any]) -> dict[str, Any]:
    frontmatter = review.get("frontmatter", {})
    return {
        "id": review["id"],
        "title": review["title"],
        "review_reason": frontmatter.get("review_reason", ""),
        "affected_cards": frontmatter.get("affected_cards", []),
        "blocking_level": frontmatter.get("blocking_level", ""),
        "status": review.get("status"),
    }


def _dedupe(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for card in cards:
        if card["id"] in seen:
            continue
        seen.add(card["id"])
        result.append(card)
    return result


def _context_id(task_type: str, product_id: str | None, query: str | None) -> str:
    raw = "_".join(part for part in [task_type, product_id, query] if part)
    safe = re.sub(r"[^a-z0-9_-]+", "_", raw.lower()).strip("_")
    return safe or task_type


def _write_context(paths: ProjectPaths, context: dict[str, Any]) -> Path:
    path = paths.generated_dir / "agent-interface" / "contexts" / f"{context['context_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .card_validator import PROFILE
from .generated_index import rebuild_generated_indexes
from .project_layout import ProjectPaths


DEFAULT_ALLOWED_STATUSES = {"official"}
DEFAULT_ALLOWED_SCOPES = {"external_allowed", "internal_only", "evidence_only"}


def rebuild_agent_interface(paths: ProjectPaths) -> dict[str, Any]:
    return rebuild_generated_indexes(paths)


def knowledge_status(paths: ProjectPaths) -> dict[str, Any]:
    return {
        "manifest": _read_json(paths.generated_dir / "agent-interface" / "manifest.json"),
        "manifest_summary": _read_json(paths.generated_dir / "agent-interface" / "manifest_summary.json"),
    }


def read_cards_by_type(paths: ProjectPaths, card_type: str, include_non_official: bool = False) -> list[dict[str, Any]]:
    if card_type not in PROFILE["card_types"]:
        raise ValueError(f"Unsupported card type: {card_type}")
    cards = _read_json(paths.generated_dir / "agent-interface" / "cards" / f"{card_type}.json")
    if include_non_official:
        return cards
    return [card for card in cards if _is_default_readable(card)]


def search_cards(paths: ProjectPaths, query: str, include_non_official: bool = False, limit: int = 10) -> list[dict[str, Any]]:
    query_tokens = _tokens(query)
    if not query_tokens:
        return []
    index = _read_json(paths.generated_dir / "indexes" / "search_index.json")
    cards_by_id = {card["id"]: card for card in _read_json(paths.generated_dir / "indexes" / "cards.json")}
    scored = []
    for item in index:
        card = cards_by_id.get(item["id"])
        if card is None:
            continue
        if not include_non_official and not _is_default_readable(card):
            continue
        text = item.get("text", "").lower()
        score = sum(1 for token in query_tokens if token in text)
        if score:
            scored.append((score, item["id"], card))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [card for _, _, card in scored[:limit]]


def evidence_for_card(paths: ProjectPaths, card_id: str) -> list[dict[str, Any]]:
    cards = _read_json(paths.generated_dir / "indexes" / "cards.json")
    cards_by_id = {card["id"]: card for card in cards}
    card = cards_by_id.get(card_id)
    if card is None:
        return []
    evidence = []
    for evidence_id in card.get("evidence_refs", []):
        evidence_card = cards_by_id.get(evidence_id)
        if evidence_card and evidence_card["type"] == "evidence":
            evidence.append(evidence_card)
    return evidence


def open_reviews(paths: ProjectPaths) -> list[dict[str, Any]]:
    reviews = _read_json(paths.generated_dir / "agent-interface" / "cards" / "review_item.json")
    return [review for review in reviews if review["status"] != "archived"]


def generate_task_context(
    paths: ProjectPaths,
    context_id: str,
    card_ids: list[str],
    task_type: str = "generic",
) -> dict[str, Any]:
    status = knowledge_status(paths)
    interface_revision = status["manifest"]["interface_revision"]
    cards_by_id = {card["id"]: card for card in _read_json(paths.generated_dir / "indexes" / "cards.json")}
    selected = []
    evidence = []
    review_refs = []
    for card_id in card_ids:
        card = cards_by_id.get(card_id)
        if not card or not _is_default_readable(card):
            continue
        selected.append(card)
        review_refs.extend(card.get("review_refs", []))
        for evidence_id in card.get("evidence_refs", []):
            evidence_card = cards_by_id.get(evidence_id)
            if evidence_card:
                evidence.append(evidence_card)

    context = {
        "context_id": context_id,
        "task_type": task_type,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "interface_revision": interface_revision,
        "valid": True,
        "cards": selected,
        "evidence": evidence,
        "review_refs": sorted(set(review_refs)),
        "note": "临时任务上下文，不是正式知识；不得反向写入 knowledge/okf/。",
    }
    path = paths.generated_dir / "agent-interface" / "contexts" / f"{_safe_id(context_id)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    return context


def _is_default_readable(card: dict[str, Any]) -> bool:
    return card.get("status") in DEFAULT_ALLOWED_STATUSES and card.get("usage_scope") in DEFAULT_ALLOWED_SCOPES


def _tokens(query: str) -> list[str]:
    lowered = query.lower().strip()
    if not lowered:
        return []
    ascii_tokens = re.findall(r"[a-z0-9_/-]+", lowered)
    cjk_tokens = [part for part in re.split(r"[\s，。；、,.!?！？:：]+", lowered) if part and part not in ascii_tokens]
    return ascii_tokens + cjk_tokens


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^a-z0-9_-]+", "_", value.lower()).strip("_")
    return safe or "context"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

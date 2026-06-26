from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .agent_interface import evidence_for_card, knowledge_status, read_cards_by_type, search_cards
from ..shared.project_layout import ProjectPaths


@dataclass(frozen=True)
class AnswerResult:
    answerable: bool
    answer: str
    reason: str | None
    next_step: str | None
    citations: tuple[dict[str, str], ...]
    used_cards: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def answer_question(paths: ProjectPaths, question: str, audience: str = "internal") -> AnswerResult:
    normalized = question.strip()
    if not normalized:
        return _unable("问题为空。", "请重新输入一个具体业务问题。")

    relevant_products = _product_slugs_in_text(normalized)
    stale_partition = _first_stale_partition(paths, relevant_products)
    if stale_partition:
        return _unable(
            f"「{stale_partition['name']}」资料已经变化，当前不适合直接回答。",
            f"建议先回复：确认，先更新{stale_partition['name']}资料。",
        )

    if "适合哪些客户场景" in normalized or "适合哪些场景" in normalized:
        return _answer_scenarios(paths, normalized, audience)
    if "哪些产品适合" in normalized:
        return _answer_products_for_scenario(paths, normalized, audience)
    if "区别" in normalized or "对比" in normalized:
        return _answer_product_difference(paths, normalized, audience)
    if "产品介绍" in normalized:
        return _answer_product_intro(paths, normalized, audience)

    return _answer_search_based(paths, normalized, audience)


def _answer_scenarios(paths: ProjectPaths, question: str, audience: str) -> AnswerResult:
    product_slug = _first_product_slug(question)
    if product_slug is None:
        return _unable("没有识别到具体产品。", "请指定产品，例如：石英纤维隔热带适合哪些客户场景？")
    scenario_cards = [
        card
        for card in read_cards_by_type(paths, "application_scenario", include_non_official=True)
        if _can_use_fact_card(card, audience) and f"product/{product_slug}" in card["frontmatter"].get("related_products", [])
    ]
    if not scenario_cards:
        return _unable(
            "当前没有已确认的应用场景卡可以回答这个问题。",
            f"建议先补充或复核 {PRODUCT_LABELS[product_slug]} 的应用场景资料。",
        )
    citations = _citations_for_cards(paths, scenario_cards)
    titles = "、".join(card["title"] for card in scenario_cards)
    return AnswerResult(
        answerable=True,
        answer=f"根据已确认知识卡片，{PRODUCT_LABELS[product_slug]} 当前可用于：{titles}。",
        reason=None,
        next_step=None,
        citations=tuple(citations),
        used_cards=tuple(card["id"] for card in scenario_cards),
    )


def _answer_products_for_scenario(paths: ProjectPaths, question: str, audience: str) -> AnswerResult:
    scenario_cards = [
        card
        for card in read_cards_by_type(paths, "application_scenario", include_non_official=True)
        if _can_use_fact_card(card, audience) and _matches_question(card, question)
    ]
    product_ids = []
    for card in scenario_cards:
        product_ids.extend(card["frontmatter"].get("related_products", []))
    product_ids = sorted(set(product_ids))
    products = _cards_by_id(read_cards_by_type(paths, "product", include_non_official=True), product_ids, audience)
    if not products:
        return _unable(
            "当前没有已确认的产品场景匹配关系可以回答这个问题。",
            "建议先补充或复核相关应用场景资料。",
        )
    citations = _citations_for_cards(paths, scenario_cards + products)
    product_names = "、".join(card["title"] for card in products)
    return AnswerResult(
        answerable=True,
        answer=f"根据已确认知识卡片，适合该场景的产品包括：{product_names}。",
        reason=None,
        next_step=None,
        citations=tuple(citations),
        used_cards=tuple(card["id"] for card in scenario_cards + products),
    )


def _answer_product_difference(paths: ProjectPaths, question: str, audience: str) -> AnswerResult:
    slugs = _product_slugs_in_text(question)
    if len(slugs) < 2:
        return _unable("没有识别到两个可对比产品。", "请明确两个产品，例如：陶瓷纤维隔热带和玄武岩纤维隔热带有什么区别？")
    products = _cards_by_id(read_cards_by_type(paths, "product", include_non_official=True), [f"product/{slug}" for slug in slugs[:2]], audience)
    if len(products) < 2:
        return _unable("对比所需的产品卡不是已确认可用状态。", "建议先整理并复核这两个产品的产品卡。")
    citations = _citations_for_cards(paths, products)
    names = " 和 ".join(card["title"] for card in products)
    return AnswerResult(
        answerable=True,
        answer=f"当前已确认资料中可以确认的是：{names} 都属于已整理产品卡。具体差异需要查看已确认的对比卡或补充产品对比资料。",
        reason=None,
        next_step="建议补充或复核产品对比资料后再生成详细差异。",
        citations=tuple(citations),
        used_cards=tuple(card["id"] for card in products),
    )


def _answer_product_intro(paths: ProjectPaths, question: str, audience: str) -> AnswerResult:
    product_slug = _first_product_slug(question)
    if product_slug is None:
        return _unable("没有识别到具体产品。", "请指定产品，例如：根据现有资料，帮我写一段石英纤维隔热带产品介绍。")
    products = _cards_by_id(read_cards_by_type(paths, "product", include_non_official=True), [f"product/{product_slug}"], audience)
    if not products:
        return _unable("该产品没有已确认且允许使用的产品卡。", f"建议先整理并复核 {PRODUCT_LABELS[product_slug]} 产品卡。")
    product = products[0]
    product_line = product["frontmatter"].get("product_line", "相关产品")
    citations = _citations_for_cards(paths, [product])
    return AnswerResult(
        answerable=True,
        answer=f"{product['title']} 是拓霖已整理的{product_line}产品。当前介绍只能使用已确认产品卡内容；涉及参数、认证、耐温、安全或对外承诺时，应继续引用检测报告、标准或人工确认记录。",
        reason=None,
        next_step=None,
        citations=tuple(citations),
        used_cards=(product["id"],),
    )


def _answer_search_based(paths: ProjectPaths, question: str, audience: str) -> AnswerResult:
    cards = [card for card in search_cards(paths, question, include_non_official=True) if _can_use_fact_card(card, audience)]
    if not cards:
        return _unable(
            "没有找到可作为确定事实回答的已确认知识卡片。",
            "建议先补充资料、整理对应分区，或查看是否存在待复核内容。",
        )
    citations = _citations_for_cards(paths, cards)
    titles = "、".join(card["title"] for card in cards[:3])
    return AnswerResult(
        answerable=True,
        answer=f"根据已确认知识卡片，相关资料包括：{titles}。",
        reason=None,
        next_step=None,
        citations=tuple(citations),
        used_cards=tuple(card["id"] for card in cards[:3]),
    )


def _can_use_fact_card(card: dict[str, Any], audience: str) -> bool:
    if card.get("status") != "official":
        return False
    scope = card.get("usage_scope")
    if scope in {"evidence_only", "not_answerable"}:
        return False
    if audience == "external":
        return scope == "external_allowed"
    return scope in {"external_allowed", "internal_only"}


def _cards_by_id(cards: list[dict[str, Any]], card_ids: list[str], audience: str) -> list[dict[str, Any]]:
    cards_by_id = {card["id"]: card for card in cards}
    return [cards_by_id[card_id] for card_id in card_ids if card_id in cards_by_id and _can_use_fact_card(cards_by_id[card_id], audience)]


def _citations_for_cards(paths: ProjectPaths, cards: list[dict[str, Any]]) -> list[dict[str, str]]:
    citations = []
    seen = set()
    for card in cards:
        if card["id"] not in seen:
            citations.append({"card_id": card["id"], "title": card["title"], "path": card["path"]})
            seen.add(card["id"])
        for evidence in evidence_for_card(paths, card["id"]):
            if evidence["id"] not in seen:
                citations.append({"card_id": evidence["id"], "title": evidence["title"], "path": evidence["path"]})
                seen.add(evidence["id"])
    return citations


def _first_stale_partition(paths: ProjectPaths, product_slugs: list[str]) -> dict[str, Any] | None:
    if not product_slugs:
        return None
    status = knowledge_status(paths)
    for partition in status["manifest"].get("partitions", []):
        if partition["slug"] in product_slugs and partition["status"] == "needs_update":
            return partition
    return None


def _matches_question(card: dict[str, Any], question: str) -> bool:
    text = " ".join(
        [
            card.get("title", ""),
            " ".join(card.get("tags", [])),
            card.get("body_excerpt", ""),
            " ".join(card.get("frontmatter", {}).get("aliases", [])),
        ]
    )
    return any(token in text for token in _tokens(question))


def _first_product_slug(text: str) -> str | None:
    slugs = _product_slugs_in_text(text)
    return slugs[0] if slugs else None


def _product_slugs_in_text(text: str) -> list[str]:
    found = []
    for slug, label in PRODUCT_LABELS.items():
        if label in text:
            found.append(slug)
    if "有背胶" in text and "高硅氧" in text:
        found.append("high_silica_fiber_tape_adhesive")
    if "无背胶" in text and "高硅氧" in text:
        found.append("high_silica_fiber_tape_non_adhesive")
    return sorted(set(found), key=found.index)


def _tokens(text: str) -> list[str]:
    return [token for token in ["排气管", "客户场景", "应用", "隔热", "介绍"] if token in text]


def _unable(reason: str, next_step: str) -> AnswerResult:
    return AnswerResult(
        answerable=False,
        answer="无法给出已确认答案。",
        reason=reason,
        next_step=next_step,
        citations=(),
        used_cards=(),
    )


PRODUCT_LABELS = {
    "ceramic_fiber_tape": "陶瓷纤维隔热带",
    "quartz_fiber_tape": "石英纤维隔热带",
    "basalt_fiber_tape": "玄武岩纤维隔热带",
    "high_silica_fiber_tape_adhesive": "高硅氧纤维隔热带_有背胶",
    "high_silica_fiber_tape_non_adhesive": "高硅氧纤维隔热带_无背胶",
}

from __future__ import annotations

import json
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
    sections: tuple[dict[str, Any], ...] = ()
    read_status: str = "success"
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def answer_question(paths: ProjectPaths, question: str, audience: str = "internal") -> AnswerResult:
    try:
        return _answer_question(paths, question, audience)
    except (FileNotFoundError, json.JSONDecodeError, KeyError, OSError, TypeError, ValueError) as exc:
        return _read_failed(exc)


def _answer_question(paths: ProjectPaths, question: str, audience: str) -> AnswerResult:
    normalized = question.strip()
    if not normalized:
        return _unable("问题为空。", "请重新输入一个具体业务问题。", error_code="invalid_question")

    relevant_products = _product_slugs_in_text(paths, normalized)
    stale_partition = _first_stale_partition(paths, relevant_products)
    if stale_partition:
        return _unable(
            f"「{stale_partition['name']}」资料已经变化，当前不适合直接回答。",
            f"建议先回复：确认，先更新{stale_partition['name']}资料。",
            error_code="stale_knowledge",
        )

    if "适合哪些客户场景" in normalized or "适合哪些场景" in normalized:
        return _answer_scenarios(paths, normalized, audience)
    if "哪些产品适合" in normalized:
        return _answer_products_for_scenario(paths, normalized, audience)
    if "区别" in normalized or "对比" in normalized:
        return _answer_product_difference(paths, normalized, audience)
    if _is_product_profile_question(normalized):
        return _answer_product_profile(paths, normalized, audience)
    if "产品介绍" in normalized:
        return _answer_product_intro(paths, normalized, audience)

    return _answer_search_based(paths, normalized, audience)


def _answer_scenarios(paths: ProjectPaths, question: str, audience: str) -> AnswerResult:
    product_slug = _first_product_slug(paths, question)
    if product_slug is None:
        return _unable("没有识别到具体产品。", "请指定产品，例如：石英纤维隔热带适合哪些客户场景？", error_code="product_not_found")
    scenario_cards = [
        card
        for card in read_cards_by_type(paths, "application_scenario", include_non_official=True)
        if _can_use_fact_card(card, audience)
        and any(product_id in _product_ids_for_slug(product_slug) for product_id in card["frontmatter"].get("related_products", []))
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
    product_slugs = sorted({_canonical_product_slug(product_id) for product_id in product_ids})
    products = _product_cards_by_slugs(paths, product_slugs, audience)
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
    slugs = _product_slugs_in_text(paths, question)
    if len(slugs) < 2:
        return _unable("没有识别到两个可对比产品。", "请明确两个产品，例如：陶瓷纤维隔热带和玄武岩纤维隔热带有什么区别？", error_code="product_not_found")
    products = _product_cards_by_slugs(paths, slugs[:2], audience)
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
    product_slug = _first_product_slug(paths, question)
    if product_slug is None:
        return _unable("没有识别到具体产品。", "请指定产品，例如：根据现有资料，帮我写一段石英纤维隔热带产品介绍。", error_code="product_not_found")
    products = _product_cards_by_slugs(paths, [product_slug], audience)
    if not products:
        return _unable("该产品没有已确认且允许使用的产品卡。", f"建议先整理并复核 {PRODUCT_LABELS[product_slug]} 产品卡。")
    product = products[0]
    product_line = product["frontmatter"].get("product_line", "相关产品")
    citations = _citations_for_cards(paths, [product])
    scope_note = ""
    if product.get("usage_scope") == "review_before_external":
        scope_note = "该知识卡可用于内部总结，对外使用前需要复核。"
    return AnswerResult(
        answerable=True,
        answer=f"{product['title']} 是拓霖已整理的{product_line}产品。当前介绍只能使用已确认产品卡内容；涉及参数、认证、耐温、安全或对外承诺时，应继续引用检测报告、标准或人工确认记录。{scope_note}",
        reason=None,
        next_step=None,
        citations=tuple(citations),
        used_cards=(product["id"],),
    )


def _answer_product_profile(paths: ProjectPaths, question: str, audience: str) -> AnswerResult:
    product_slug = _first_product_slug(paths, question)
    if product_slug is None:
        return _unable("没有识别到具体产品。", "请明确需要总结的产品名称。", error_code="product_not_found")
    products = _product_cards_by_slugs(paths, [product_slug], audience)
    if not products:
        return _unable(
            "该产品没有已确认且允许用于当前场景的产品卡。",
            f"建议先检查或复核 {PRODUCT_LABELS[product_slug]} 产品卡。",
        )

    product = products[0]
    related = _related_profile_cards(paths, product_slug, product, audience)
    scenarios = related["application_scenario"]
    sales_materials = related["sales_material"]
    customer_questions = related["customer_question"]
    reviews = related["review_item"]

    sections = [
        _profile_section(
            "definition",
            "产品定义与正式名称",
            _unique_items(
                [product["title"]]
                + [f"正式别名：{alias}" for alias in product.get("frontmatter", {}).get("aliases", [])]
                + _section_items(product, {"产品定义", "产品定位"})
            ),
            [product],
        ),
        _profile_section(
            "parameters",
            "规格与关键参数",
            _section_items(product, {"关键参数", "规格", "规格参数", "技术参数"}),
            [product],
        ),
        _profile_section(
            "features",
            "产品特点",
            _section_items(product, {"产品特点", "特点", "核心特点"}),
            [product],
        ),
        _profile_section(
            "advantages",
            "已确认优点",
            _section_items(product, {"优点", "优势", "产品优势"}),
            [product],
        ),
        _profile_section(
            "disadvantages",
            "已确认缺点",
            _section_items(product, {"缺点", "局限", "产品局限"}),
            [product],
            empty_text="当前正式知识卡未记录明确缺点；这不等于产品不存在缺点。",
        ),
        _profile_section(
            "selling_points",
            "核心卖点",
            _unique_items(
                _section_items(product, {"核心卖点", "卖点"})
                + [item for card in sales_materials for item in _body_items(card)]
            ),
            [product, *sales_materials],
        ),
        _profile_section(
            "applications",
            "应用场景",
            _unique_items([card["title"] for card in scenarios]),
            scenarios,
        ),
        _profile_section(
            "procurement_notes",
            "采购注意事项",
            _unique_items(
                _section_items(product, {"采购注意事项", "采购判断", "选型注意事项"})
                + [card["title"] for card in customer_questions]
            ),
            [product, *customer_questions],
        ),
        _profile_section(
            "safety_notes",
            "使用与安全注意事项",
            _section_items(product, {"使用与安全注意事项", "使用注意事项", "安全注意事项", "注意事项"}),
            [product],
        ),
        _profile_section(
            "publicity_boundary",
            "对外宣传边界",
            _unique_items(
                [_usage_scope_note(product)]
                + _section_items(product, {"对外宣传边界", "对外注意事项", "宣传注意事项"})
            ),
            [product],
        ),
        _profile_section(
            "reviews",
            "待复核内容",
            _unique_items(
                [card.get("frontmatter", {}).get("review_reason", card["title"]) for card in reviews]
            ),
            reviews,
        ),
    ]

    used_cards = _unique_cards([product, *scenarios, *sales_materials, *customer_questions, *reviews])
    citations = _citations_for_cards(paths, [product, *scenarios, *sales_materials, *customer_questions])
    used_card_ids = {card["id"] for card in used_cards}
    source_items = [_source_item(card) for card in used_cards]
    source_items.extend(
        f"{citation['title']}（{citation['card_id']}；仅作证据引用）"
        for citation in citations
        if citation["card_id"] not in used_card_ids
    )
    sections.append(
        _profile_section(
            "sources",
            "本次知识来源",
            source_items,
            used_cards,
        )
    )
    answer = _render_product_profile_answer(product["title"], sections)
    return AnswerResult(
        answerable=True,
        answer=answer,
        reason=None,
        next_step=None,
        citations=tuple(citations),
        used_cards=tuple(card["id"] for card in used_cards),
        sections=tuple(sections),
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


def _is_product_profile_question(question: str) -> bool:
    profile_terms = {"所有特点", "全部特点", "优点", "缺点", "卖点", "注意事项", "完整知识", "全面总结"}
    return any(term in question for term in profile_terms)


def _related_profile_cards(
    paths: ProjectPaths,
    product_slug: str,
    product: dict[str, Any],
    audience: str,
) -> dict[str, list[dict[str, Any]]]:
    product_ids = set(_product_ids_for_slug(product_slug)) | {product["id"]}
    related_refs = set(product.get("frontmatter", {}).get("related_refs", []))
    result: dict[str, list[dict[str, Any]]] = {}
    for card_type in ("application_scenario", "sales_material", "customer_question"):
        cards = []
        for card in read_cards_by_type(paths, card_type, include_non_official=True):
            linked_products = set(card.get("frontmatter", {}).get("related_products", []))
            if card["id"] not in related_refs and not linked_products.intersection(product_ids):
                continue
            if _can_use_fact_card(card, audience):
                cards.append(card)
        result[card_type] = cards

    product_review_refs = set(product.get("review_refs", [])) | set(product.get("frontmatter", {}).get("review_refs", []))
    reviews = []
    for card in read_cards_by_type(paths, "review_item", include_non_official=True):
        if card.get("status") == "archived":
            continue
        affected = set(card.get("frontmatter", {}).get("affected_cards", []))
        if card["id"] in product_review_refs or affected.intersection(product_ids):
            reviews.append(card)
    result["review_item"] = reviews
    return result


def _profile_section(
    key: str,
    title: str,
    items: list[str],
    cards: list[dict[str, Any]],
    empty_text: str = "当前正式知识卡未记录。",
) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "items": tuple(items) if items else (empty_text,),
        "card_ids": tuple(card["id"] for card in _unique_cards(cards)),
        "sources": tuple(_source_metadata(card) for card in _unique_cards(cards)),
        "has_confirmed_content": bool(items),
    }


def _section_items(card: dict[str, Any], headings: set[str]) -> list[str]:
    body = card.get("body_markdown") or card.get("body_excerpt", "")
    items = []
    collecting = False
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            collecting = heading in headings
            continue
        if collecting and line:
            items.append(_clean_markdown_item(line))
    return _unique_items([item for item in items if item])


def _body_items(card: dict[str, Any]) -> list[str]:
    body = card.get("body_markdown") or card.get("body_excerpt", "")
    return _unique_items(
        [_clean_markdown_item(line.strip()) for line in body.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    )


def _clean_markdown_item(value: str) -> str:
    return value.removeprefix("- ").strip()


def _usage_scope_note(card: dict[str, Any]) -> str:
    scope = card.get("usage_scope")
    if scope == "external_allowed":
        return "当前产品卡允许用于对外业务表达。"
    if scope == "review_before_external":
        return "当前产品卡可用于内部总结，对外使用前需要复核。"
    if scope == "internal_only":
        return "当前产品卡仅限内部使用，不得直接用于对外宣传。"
    return "当前产品卡不能直接形成对外宣传结论。"


def _source_item(card: dict[str, Any]) -> str:
    return f"{card['title']}（{card['id']}；{_usage_scope_label(card)}）"


def _source_metadata(card: dict[str, Any]) -> dict[str, str]:
    return {
        "card_id": card["id"],
        "title": card["title"],
        "status": card.get("status", ""),
        "usage_scope": card.get("usage_scope", ""),
        "usage_label": _usage_scope_label(card),
    }


def _usage_scope_label(card: dict[str, Any]) -> str:
    if card.get("type") == "review_item":
        return "待复核，不作为已确认事实"
    return {
        "external_allowed": "允许对外使用",
        "review_before_external": "对外前需复核",
        "internal_only": "仅限内部使用",
        "evidence_only": "仅作证据引用",
        "not_answerable": "不得作为事实回答",
    }.get(card.get("usage_scope"), "使用范围未确认")


def _render_product_profile_answer(product_title: str, sections: list[dict[str, Any]]) -> str:
    lines = [f"# {product_title}产品知识全景总结", "", "以下内容只来自本次成功读取的已生成知识卡。", ""]
    for section in sections:
        lines.extend([f"## {section['title']}", ""])
        lines.extend(f"- {item}" for item in section["items"])
        lines.append("")
    return "\n".join(lines).rstrip()


def _unique_items(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in items if item and item.strip()))


def _unique_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list({card["id"]: card for card in cards}.values())


def _can_use_fact_card(card: dict[str, Any], audience: str) -> bool:
    if card.get("status") != "official":
        return False
    scope = card.get("usage_scope")
    if scope in {"evidence_only", "not_answerable"}:
        return False
    if audience == "external":
        return scope == "external_allowed"
    return scope in {"external_allowed", "review_before_external", "internal_only"}


def _cards_by_id(cards: list[dict[str, Any]], card_ids: list[str], audience: str) -> list[dict[str, Any]]:
    cards_by_id = {card["id"]: card for card in cards}
    return [cards_by_id[card_id] for card_id in card_ids if card_id in cards_by_id and _can_use_fact_card(cards_by_id[card_id], audience)]


def _product_cards_by_slugs(paths: ProjectPaths, slugs: list[str], audience: str) -> list[dict[str, Any]]:
    requested = set(slugs)
    selected = []
    for card in read_cards_by_type(paths, "product", include_non_official=True):
        if _canonical_product_slug(card.get("id", "")) not in requested:
            continue
        if _can_use_fact_card(card, audience):
            selected.append(card)
    return selected


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


def _first_product_slug(paths: ProjectPaths, text: str) -> str | None:
    slugs = _product_slugs_in_text(paths, text)
    return slugs[0] if slugs else None


def _product_slugs_in_text(paths: ProjectPaths, text: str) -> list[str]:
    found = []
    for slug, label in PRODUCT_LABELS.items():
        if label in text:
            found.append(slug)
        if any(product_id in text for product_id in _product_ids_for_slug(slug)):
            found.append(slug)
    for card in read_cards_by_type(paths, "product", include_non_official=True):
        terms = [card.get("id", ""), card.get("title", "")]
        terms.extend(card.get("frontmatter", {}).get("aliases", []))
        if any(term and term.lower() in text.lower() for term in terms):
            found.append(_canonical_product_slug(card.get("id", "")))
    if "有背胶" in text and "高硅氧" in text:
        found.append("high_silica_fiber_tape_adhesive")
    if "无背胶" in text and "高硅氧" in text:
        found.append("high_silica_fiber_tape_non_adhesive")
    return sorted(set(found), key=found.index)


def _canonical_product_slug(product_id: str) -> str:
    for slug, product_ids in PRODUCT_ID_ALIASES.items():
        if product_id in product_ids:
            return slug
    return product_id.removeprefix("product/")


def _product_ids_for_slug(slug: str) -> tuple[str, ...]:
    return PRODUCT_ID_ALIASES.get(slug, (f"product/{slug}",))


def _tokens(text: str) -> list[str]:
    return [token for token in ["排气管", "客户场景", "应用", "隔热", "介绍"] if token in text]


def _unable(reason: str, next_step: str, error_code: str = "no_usable_cards") -> AnswerResult:
    return AnswerResult(
        answerable=False,
        answer="无法给出已确认答案。",
        reason=reason,
        next_step=next_step,
        citations=(),
        used_cards=(),
        error_code=error_code,
    )


def _read_failed(error: Exception) -> AnswerResult:
    return AnswerResult(
        answerable=False,
        answer=(
            "本次未成功读取知识库，因此不能提供产品事实总结。"
            "本次没有使用当前会话中的视频策划、LinkedIn 内容、旧查询结果或行业常识补全，"
            "也没有继续生成产品特点清单。"
        ),
        reason=f"知识库 Agent 读取接口失败：{type(error).__name__}",
        next_step="请先检查知识库项目和 Agent 读取接口是否可用，然后重新提问。",
        citations=(),
        used_cards=(),
        read_status="failed",
        error_code="read_failed",
    )


PRODUCT_LABELS = {
    "ceramic_fiber_tape": "陶瓷纤维隔热带",
    "quartz_fiber_tape": "石英纤维隔热带",
    "basalt_fiber_tape": "玄武岩纤维隔热带",
    "high_silica_fiber_tape_adhesive": "高硅氧纤维隔热带_有背胶",
    "high_silica_fiber_tape_non_adhesive": "高硅氧纤维隔热带_无背胶",
}


PRODUCT_ID_ALIASES = {
    "quartz_fiber_tape": (
        "product/quartz_fiber_tape",
        "product/quartz_fiber_exhaust_wrap",
    ),
}

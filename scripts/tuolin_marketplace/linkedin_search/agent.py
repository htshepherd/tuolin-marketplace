from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ..kb.agent_interface import read_cards_by_type
from ..shared.downstream_context import build_downstream_context
from ..shared.project_layout import ProjectPaths
from .interview import (
    answer_search_interview,
    build_search_interview,
    confirmed_search_brief,
    current_search_interview_prompt,
)


RUN_ROOT_NAME = "linkedin-search"
DEFAULT_STATUS = "search_interview_required"
DEFAULT_PHASE = "awaiting_search_interview"


@dataclass(frozen=True)
class LinkedInSearchProjectValidation:
    valid: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class LinkedInSearchRunResult:
    run_dir: str
    requirements_path: str
    workflow_state_path: str
    context_id: str | None
    product_id: str | None
    status: str
    phase: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LinkedInSearchStepResult:
    run_dir: str
    workflow_state_path: str
    status: str
    phase: str
    output_paths: tuple[str, ...]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def is_linkedin_search_request(text: str) -> bool:
    utterance = text.strip().lower()
    if not utterance:
        return False
    mentions_linkedin = any(token in utterance for token in ("linkedin", "领英"))
    search_intent = any(
        token in utterance
        for token in (
            "搜索客户",
            "搜索潜客",
            "找客户",
            "找潜客",
            "潜在客户",
            "潜在买家",
            "搜索贴文",
            "搜索动态",
            "通过贴文",
            "加好友",
            "连接邀请",
            "connection invitation",
            "find prospect",
            "find customer",
            "prospect search",
        )
    )
    return mentions_linkedin and search_intent


def validate_linkedin_search_project(paths: ProjectPaths) -> LinkedInSearchProjectValidation:
    manifest_path = paths.generated_dir / "agent-interface" / "manifest.json"
    summary_path = paths.generated_dir / "agent-interface" / "manifest_summary.json"
    cards_path = paths.generated_dir / "agent-interface" / "cards"
    errors: list[str] = []
    for path in (manifest_path, summary_path, cards_path):
        if not path.exists():
            errors.append(f"缺少知识库 Agent读取接口文件：{_display_path(paths.project_dir, path)}")
    if not errors:
        try:
            manifest = _read_json(manifest_path)
            summary = _read_json(summary_path)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            manifest_revision = str(manifest.get("interface_revision") or "")
            summary_revision = str(summary.get("interface_revision") or "")
            if not manifest_revision or manifest_revision != summary_revision:
                errors.append("知识库 Agent读取接口版本不一致或缺少 revision，必须先用知识库 Agent 强制刷新并验证。")
            if int(summary.get("validation_error_count") or 0) > 0:
                errors.append("知识库 Agent读取接口仍包含校验错误，不能供领英搜索 Agent 消费。")
    return LinkedInSearchProjectValidation(valid=not errors, errors=tuple(errors))


def create_linkedin_search_run(
    paths: ProjectPaths,
    request_text: str,
    *,
    product_id: str | None = None,
    now: datetime | None = None,
) -> LinkedInSearchRunResult:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    validation = validate_linkedin_search_project(paths)
    if not validation.valid:
        return _create_blocked_run(
            paths,
            request_text,
            timestamp,
            product_id=product_id,
            reason="；".join(validation.errors),
            blocker="agent_interface_unavailable",
        )

    try:
        product = _resolve_product(paths, request_text, product_id)
    except ValueError as exc:
        return _create_blocked_run(
            paths,
            request_text,
            timestamp,
            product_id=product_id,
            reason=str(exc),
            blocker="product_resolution_failed",
        )

    resolved_product_id = str(product["id"])
    try:
        context = build_downstream_context(
            paths,
            "linkedin_search",
            product_id=resolved_product_id,
            query=request_text,
            include_review_items=False,
        )
    except (ValueError, FileNotFoundError, KeyError) as exc:
        return _create_blocked_run(
            paths,
            request_text,
            timestamp,
            product_id=resolved_product_id,
            reason=f"无法创建 linkedin_search 正式产品上下文：{exc}",
            blocker="product_context_unavailable",
        )

    product_cards = context.get("cards_by_type", {}).get("product", [])
    if len(product_cards) != 1 or str(product_cards[0].get("id") or "") != resolved_product_id:
        return _create_blocked_run(
            paths,
            request_text,
            timestamp,
            product_id=resolved_product_id,
            reason="linkedin_search 上下文没有且仅有一个匹配的正式产品，不能进入访谈。",
            blocker="product_context_ambiguous",
        )

    run_dir = _create_run_dir(paths, timestamp, _product_slug(resolved_product_id))
    requirements_path = run_dir / "requirements.md"
    workflow_state_path = run_dir / "workflow_state.json"
    change_log_path = run_dir / "change_log.md"
    context_path = paths.generated_dir / "agent-interface" / "contexts" / f"{context['context_id']}.json"
    interview = build_search_interview(request_text, context)
    interview_completed = bool(interview.get("completed"))
    initial_status = "search_brief_confirmed" if interview_completed else DEFAULT_STATUS
    initial_phase = "awaiting_browser_account_binding" if interview_completed else DEFAULT_PHASE
    requirements = {
        "request_text": request_text,
        "product": {
            "id": resolved_product_id,
            "title": product.get("title"),
            "aliases": list(product.get("aliases") or []),
            "usage_scope": product.get("usage_scope"),
        },
        "search_terms": [],
        "interview": interview,
        "confirmed_search_brief": confirmed_search_brief(interview) if interview.get("completed") else None,
        "knowledge_context": {
            "context_id": context["context_id"],
            "interface_revision": context["interface_revision"],
            "raw_access": context["raw_access"],
            "policy": context["policy"],
        },
    }
    state = {
        "workflow": "tuolin-linkedin-search",
        "schema_version": 1,
        "run_id": run_dir.name,
        "status": initial_status,
        "phase": initial_phase,
        "created_at": timestamp,
        "updated_at": timestamp,
        "request_text": request_text,
        "product": requirements["product"],
        "knowledge_context": requirements["knowledge_context"],
        "account_binding": None,
        "interview": interview,
        "confirmed_search_brief": requirements["confirmed_search_brief"],
        "files": {
            "requirements": str(requirements_path),
            "workflow_state": str(workflow_state_path),
            "change_log": str(change_log_path),
            "knowledge_context": str(context_path),
        },
        "blockers": [],
        "warnings": [
            "LinkedIn 可能限制自动化或异常操作；本工作流不承诺规避检测或账号安全。",
            "本地运行上限只统计本 Skill 记录的成功邀请，不统计人工或其他工具操作。",
        ],
        "status_history": [{"status": initial_status, "phase": initial_phase, "at": timestamp}],
    }
    requirements_path.write_text(_render_requirements(requirements), encoding="utf-8")
    workflow_state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    change_log_path.write_text(
        f"# LinkedIn 搜索任务变更记录\n\n- {timestamp}: 创建运行并绑定正式产品 {resolved_product_id}。\n",
        encoding="utf-8",
    )
    return LinkedInSearchRunResult(
        run_dir=str(run_dir),
        requirements_path=str(requirements_path),
        workflow_state_path=str(workflow_state_path),
        context_id=str(context["context_id"]),
        product_id=resolved_product_id,
        status=initial_status,
        phase=initial_phase,
        message=(
            f"已创建产品绑定的 LinkedIn 搜索任务：{product.get('title') or resolved_product_id}。"
            + (
                "已根据请求形成 Confirmed Search Brief。下一步绑定浏览器中的 LinkedIn 账号。"
                if interview_completed
                else "\n\n" + current_search_interview_prompt(interview)
            )
        ),
    )


def continue_linkedin_search_interview(
    run_dir: Path,
    reply: str,
    *,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _read_json(state_path)
    if state.get("phase") != DEFAULT_PHASE:
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能继续 LinkedIn 搜索访谈。")
    interview = answer_search_interview(dict(state.get("interview") or {}), reply)
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    state["interview"] = interview
    completed = bool(interview.get("completed"))
    if completed:
        state["confirmed_search_brief"] = confirmed_search_brief(interview)
        state["status"] = "search_brief_confirmed"
        state["phase"] = "awaiting_browser_account_binding"
    else:
        state["status"] = DEFAULT_STATUS
        state["phase"] = DEFAULT_PHASE
    state["updated_at"] = timestamp
    state.setdefault("status_history", []).append(
        {"status": state["status"], "phase": state["phase"], "at": timestamp}
    )
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    requirements_path = Path(state["files"]["requirements"])
    requirements = {
        "request_text": state.get("request_text"),
        "product": state.get("product"),
        "interview": interview,
        "confirmed_search_brief": state.get("confirmed_search_brief"),
        "knowledge_context": state.get("knowledge_context"),
    }
    requirements_path.write_text(_render_requirements(requirements), encoding="utf-8")
    change_log_path = Path(state["files"]["change_log"])
    with change_log_path.open("a", encoding="utf-8") as handle:
        answered = interview.get("history", [{}])[-1].get("field", "unknown")
        handle.write(f"- {timestamp}: 记录访谈答案 {answered}；完成={completed}。\n")
    message = (
        "LinkedIn 搜索访谈已完成，已生成 Confirmed Search Brief。下一步绑定浏览器中的 LinkedIn 账号。"
        if completed
        else current_search_interview_prompt(interview)
    )
    return LinkedInSearchStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(requirements_path), str(state_path)),
        message=message,
    )


def _resolve_product(paths: ProjectPaths, request_text: str, product_id: str | None) -> dict[str, Any]:
    cards = read_cards_by_type(paths, "product", include_non_official=True)
    official = [
        card
        for card in cards
        if card.get("status") == "official" and card.get("usage_scope") == "external_allowed"
    ]
    if product_id:
        matches = [card for card in official if str(card.get("id") or "") == product_id]
        if len(matches) != 1:
            raise ValueError(f"未找到可对外使用的正式产品：{product_id}。请先用 $tuolin-kb 整理并刷新 Agent 接口。")
        return matches[0]

    normalized_request = request_text.casefold()
    matches = []
    for card in official:
        terms = [str(card.get("id") or ""), str(card.get("title") or ""), *[str(item) for item in card.get("aliases", [])]]
        if any(term and term.casefold() in normalized_request for term in terms):
            matches.append(card)
    matches = _dedupe_cards(matches)
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError("请求中没有可唯一解析的正式拓霖产品。请明确产品名称后重新开始任务。")
    raise ValueError("请求同时匹配多个正式产品。请每个任务只指定一个产品。")


def _create_blocked_run(
    paths: ProjectPaths,
    request_text: str,
    timestamp: str,
    *,
    product_id: str | None,
    reason: str,
    blocker: str,
) -> LinkedInSearchRunResult:
    run_dir = _create_run_dir(paths, timestamp, _product_slug(product_id or "unresolved"))
    requirements_path = run_dir / "requirements.md"
    workflow_state_path = run_dir / "workflow_state.json"
    change_log_path = run_dir / "change_log.md"
    requirements = {
        "request_text": request_text,
        "product": {"id": product_id},
        "blocked_reason": reason,
        "confirmed_search_brief": None,
    }
    state = {
        "workflow": "tuolin-linkedin-search",
        "schema_version": 1,
        "run_id": run_dir.name,
        "status": "blocked",
        "phase": "blocked_before_interview",
        "created_at": timestamp,
        "updated_at": timestamp,
        "request_text": request_text,
        "product": {"id": product_id},
        "knowledge_context": None,
        "account_binding": None,
        "interview": None,
        "files": {
            "requirements": str(requirements_path),
            "workflow_state": str(workflow_state_path),
            "change_log": str(change_log_path),
        },
        "blockers": [{"code": blocker, "message": reason}],
        "warnings": [],
        "status_history": [{"status": "blocked", "phase": "blocked_before_interview", "at": timestamp}],
    }
    requirements_path.write_text(_render_requirements(requirements), encoding="utf-8")
    workflow_state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    change_log_path.write_text(
        f"# LinkedIn 搜索任务变更记录\n\n- {timestamp}: 任务在访谈前阻断：{reason}\n",
        encoding="utf-8",
    )
    return LinkedInSearchRunResult(
        run_dir=str(run_dir),
        requirements_path=str(requirements_path),
        workflow_state_path=str(workflow_state_path),
        context_id=None,
        product_id=product_id,
        status="blocked",
        phase="blocked_before_interview",
        message=reason,
    )


def _create_run_dir(paths: ProjectPaths, timestamp: str, slug: str) -> Path:
    root = paths.generated_dir / "reports" / RUN_ROOT_NAME
    root.mkdir(parents=True, exist_ok=True)
    base = root / f"{timestamp}_{slug}"
    candidate = base
    suffix = 2
    while candidate.exists():
        candidate = root / f"{base.name}_{suffix}"
        suffix += 1
    candidate.mkdir(parents=True)
    return candidate


def _product_slug(product_id: str) -> str:
    value = product_id.split("/", 1)[-1]
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")
    return value or "unresolved"


def _dedupe_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for card in cards:
        card_id = str(card.get("id") or "")
        if card_id and card_id not in seen:
            result.append(card)
            seen.add(card_id)
    return result


def _render_requirements(requirements: dict[str, Any]) -> str:
    product = requirements.get("product") or {}
    lines = [
        "# LinkedIn 搜索任务需求",
        "",
        f"- 原始请求：{requirements.get('request_text') or ''}",
        f"- 正式产品 ID：{product.get('id') or '未解析'}",
        f"- 正式产品名称：{product.get('title') or '未解析'}",
    ]
    if requirements.get("blocked_reason"):
        lines.append(f"- 阻断原因：{requirements['blocked_reason']}")
    context = requirements.get("knowledge_context") or {}
    if context:
        lines.extend(
            [
                f"- Agent 接口修订：{context.get('interface_revision')}",
                f"- 下游上下文：{context.get('context_id')}",
                f"- raw_access：{str(bool(context.get('raw_access'))).lower()}",
            ]
        )
    brief = requirements.get("confirmed_search_brief")
    if brief:
        lines.extend(
            [
                "",
                "## Confirmed Search Brief",
                "",
                f"- 关键词：{'、'.join(brief.get('keywords') or [])}",
                f"- 排序：{brief.get('sort_order')}",
                f"- 发布日期：{brief.get('publication_range')}",
                f"- 使用留言：{str(bool(brief.get('invitation_note'))).lower()}",
                f"- 固定间隔秒数：{brief.get('interval_seconds')}",
                f"- 本次上限：{brief.get('requested_limit')}",
            ]
        )
    else:
        pending = (requirements.get("interview") or {}).get("pending_question") or {}
        lines.extend(
            [
                "",
                "当前尚未形成 Confirmed Search Brief。",
                f"当前待确认字段：{pending.get('field') or '无'}",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取有效 JSON：{_display_path(path.parent, path)}：{exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON 顶层必须是对象：{path}")
    return value


def _display_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)

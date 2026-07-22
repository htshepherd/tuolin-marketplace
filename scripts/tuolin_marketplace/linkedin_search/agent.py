from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ..shared.project_layout import ProjectPaths
from .interview import answer_search_interview, build_search_interview, confirmed_search_brief, current_search_interview_prompt


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
    search_intent = any(token in utterance for token in (
        "搜索客户", "搜索潜客", "找客户", "找潜客", "潜在客户", "潜在买家", "搜索贴文", "搜索动态",
        "通过贴文", "加好友", "连接邀请", "connection invitation", "find prospect", "find customer", "prospect search",
    ))
    return mentions_linkedin and search_intent


def validate_linkedin_search_project(paths: ProjectPaths) -> LinkedInSearchProjectValidation:
    """A search run needs a writable operational workspace, not a knowledge interface."""
    errors: list[str] = []
    try:
        paths.generated_dir.mkdir(parents=True, exist_ok=True)
        probe = paths.generated_dir / ".linkedin-search-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        errors.append(f"LinkedIn 搜索工作目录不可写：{exc}")
    return LinkedInSearchProjectValidation(valid=not errors, errors=tuple(errors))


def create_linkedin_search_run(
    paths: ProjectPaths,
    request_text: str,
    *,
    now: datetime | None = None,
) -> LinkedInSearchRunResult:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    validation = validate_linkedin_search_project(paths)
    if not validation.valid:
        raise ValueError("；".join(validation.errors))

    interview = build_search_interview(request_text)
    completed = bool(interview.get("completed"))
    status = "search_brief_confirmed" if completed else DEFAULT_STATUS
    phase = "awaiting_browser_account_binding" if completed else DEFAULT_PHASE
    keywords = list((interview.get("answers") or {}).get("keywords") or [])
    slug = _keyword_slug(keywords[0] if keywords else "keywords")
    run_dir = _create_run_dir(paths, timestamp, slug)
    requirements_path = run_dir / "requirements.md"
    workflow_state_path = run_dir / "workflow_state.json"
    change_log_path = run_dir / "change_log.md"
    brief = confirmed_search_brief(interview) if completed else None
    requirements = {"request_text": request_text, "interview": interview, "confirmed_search_brief": brief}
    state = {
        "workflow": "tuolin-linkedin-search",
        "schema_version": 2,
        "run_id": run_dir.name,
        "status": status,
        "phase": phase,
        "created_at": timestamp,
        "updated_at": timestamp,
        "request_text": request_text,
        "account_binding": None,
        "interview": interview,
        "confirmed_search_brief": brief,
        "candidate_ids": [],
        "unresolved_lead_ids": [],
        "files": {
            "requirements": str(requirements_path),
            "workflow_state": str(workflow_state_path),
            "change_log": str(change_log_path),
        },
        "blockers": [],
        "warnings": [
            "LinkedIn 可能限制自动化或异常操作；本工作流不承诺规避检测或账号安全。",
            "本地运行上限只统计本 Skill 记录的成功邀请，不统计人工或其他工具操作。",
            "候选相关性是基于 LinkedIn 可见内容的暂定判断，必须由人工批量审核。",
        ],
        "status_history": [{"status": status, "phase": phase, "at": timestamp}],
    }
    requirements_path.write_text(_render_requirements(requirements), encoding="utf-8")
    workflow_state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    change_log_path.write_text(f"# LinkedIn 搜索任务变更记录\n\n- {timestamp}: 创建关键词驱动运行；未读取产品知识库。\n", encoding="utf-8")
    return LinkedInSearchRunResult(
        str(run_dir), str(requirements_path), str(workflow_state_path), status, phase,
        "已创建关键词驱动的 LinkedIn 搜索任务。" + ("下一步绑定浏览器中的 LinkedIn 账号。" if completed else "\n\n" + current_search_interview_prompt(interview)),
    )


def continue_linkedin_search_interview(run_dir: Path, reply: str, *, now: datetime | None = None) -> LinkedInSearchStepResult:
    run_dir = run_dir.expanduser().resolve()
    state_path = run_dir / "workflow_state.json"
    state = _read_json(state_path)
    if state.get("phase") != DEFAULT_PHASE:
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能继续 LinkedIn 搜索访谈。")
    interview = answer_search_interview(dict(state.get("interview") or {}), reply)
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    completed = bool(interview.get("completed"))
    state["interview"] = interview
    state["status"] = "search_brief_confirmed" if completed else DEFAULT_STATUS
    state["phase"] = "awaiting_browser_account_binding" if completed else DEFAULT_PHASE
    state["confirmed_search_brief"] = confirmed_search_brief(interview) if completed else None
    state["updated_at"] = timestamp
    state.setdefault("status_history", []).append({"status": state["status"], "phase": state["phase"], "at": timestamp})
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    requirements_path = Path(state["files"]["requirements"])
    requirements_path.write_text(_render_requirements({"request_text": state.get("request_text"), "interview": interview, "confirmed_search_brief": state.get("confirmed_search_brief")}), encoding="utf-8")
    with Path(state["files"]["change_log"]).open("a", encoding="utf-8") as handle:
        answered = interview.get("history", [{}])[-1].get("field", "unknown")
        handle.write(f"- {timestamp}: 记录访谈答案 {answered}；完成={completed}。\n")
    message = "LinkedIn 搜索访谈已完成，已生成 Confirmed Search Brief。下一步绑定浏览器中的 LinkedIn 账号。" if completed else current_search_interview_prompt(interview)
    return LinkedInSearchStepResult(str(run_dir), str(state_path), state["status"], state["phase"], (str(requirements_path), str(state_path)), message)


def _create_run_dir(paths: ProjectPaths, timestamp: str, slug: str) -> Path:
    root = paths.generated_dir / "reports" / RUN_ROOT_NAME
    root.mkdir(parents=True, exist_ok=True)
    base = root / f"{timestamp}_{slug}"
    candidate = base; suffix = 2
    while candidate.exists():
        candidate = root / f"{base.name}_{suffix}"; suffix += 1
    candidate.mkdir(parents=True)
    return candidate


def _keyword_slug(keyword: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", keyword).strip("-")
    return (value or "keywords")[:48]


def _render_requirements(requirements: dict[str, Any]) -> str:
    lines = ["# LinkedIn 搜索任务需求", "", f"- 原始请求：{requirements.get('request_text') or ''}", "- 产品知识库：不读取", "- 关键词来源：操作员输入"]
    brief = requirements.get("confirmed_search_brief")
    if brief:
        lines.extend(["", "## Confirmed Search Brief", "", f"- 关键词数量：{len(brief.get('keywords') or [])}", f"- 关键词（按序原样搜索）：{'、'.join(brief.get('keywords') or [])}", f"- 排序：{brief.get('sort_order')}", f"- 发布日期：{brief.get('publication_range')}", f"- 使用留言：{str(bool(brief.get('invitation_note'))).lower()}", f"- 固定间隔秒数：{brief.get('interval_seconds')}", f"- 本次上限：{brief.get('requested_limit')}"])
    else:
        pending = (requirements.get("interview") or {}).get("pending_question") or {}
        lines.extend(["", "当前尚未形成 Confirmed Search Brief。", f"当前待回答字段：{pending.get('field') or '无'}"])
    return "\n".join(lines) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取有效 JSON：{path}：{exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON 顶层必须是对象：{path}")
    return value

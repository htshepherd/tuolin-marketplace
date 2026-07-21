from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .agent import LinkedInSearchStepResult


@dataclass(frozen=True)
class LinkedInAccountObservation:
    signed_in: bool
    member_name: str
    profile_url: str
    dedicated_tab_group: bool


@dataclass(frozen=True)
class LinkedInPostSearchObservation:
    keyword: str
    search_surface: str
    sort_order: str
    publication_range: str
    visible_result_count: int
    dedicated_tab_group: bool
    applied_filters: dict[str, Any]


def bind_linkedin_account(
    run_dir: Path,
    observation: LinkedInAccountObservation,
    *,
    browser_authorized: bool,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "awaiting_browser_account_binding":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能绑定 LinkedIn 账号。")
    if not browser_authorized:
        raise ValueError("必须先获得用户对当前任务只读 Chrome 操作的明确授权。")
    if not observation.signed_in:
        raise ValueError("当前 Chrome 中的 LinkedIn 未登录；请由用户完成登录后重试。")
    name = observation.member_name.strip()
    profile_url = normalize_linkedin_url(observation.profile_url)
    if not name or not profile_url:
        raise ValueError("无法读取当前 LinkedIn 会员姓名或 profile URL，不能绑定账号。")
    if not observation.dedicated_tab_group:
        raise ValueError("LinkedIn 搜索必须在专用 Codex Chrome 任务标签组中进行。")
    timestamp = _timestamp(now)
    from .ledger import acquire_account_run_lock, release_account_run_lock, rolling_capacity

    lock_path = acquire_account_run_lock(run_dir, profile_url, now=now)
    state["account_binding"] = {
        "member_name": name,
        "profile_url": profile_url,
        "bound_at": timestamp,
        "browser_surface": "official_codex_chrome_extension",
    }
    state["browser_authorization"] = {
        "scope": "readonly_linkedin_post_discovery",
        "confirmed": True,
        "confirmed_at": timestamp,
    }
    state.setdefault("files", {})["account_run_lock"] = str(lock_path)
    capacity = rolling_capacity(run_dir, account_profile_url=profile_url, now=now)
    requested_limit = int((state.get("confirmed_search_brief") or {}).get("requested_limit") or 10)
    effective_limit = min(requested_limit, capacity["remaining_capacity"])
    state["capacity_at_account_binding"] = {
        **capacity,
        "requested_limit": requested_limit,
        "effective_limit": effective_limit,
        "manual_linkedin_actions_counted": False,
    }
    if effective_limit <= 0:
        state["status"] = "blocked_rolling_capacity"
        state["phase"] = "blocked_before_discovery"
        release_account_run_lock(run_dir, profile_url)
    elif effective_limit < requested_limit:
        state["status"] = "effective_limit_confirmation_required"
        state["phase"] = "awaiting_effective_limit_confirmation"
    else:
        state["status"] = "linkedin_account_bound"
        state["phase"] = "awaiting_first_posts_search"
    state["updated_at"] = timestamp
    _append_history(state, timestamp)
    _write_json_atomic(state_path, state)
    _append_change(run_dir, timestamp, f"绑定 LinkedIn 账号：{name} ({profile_url})；授权范围=只读贴文发现。")
    return LinkedInSearchStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(state_path),),
        message=(
            f"已绑定 LinkedIn 账号：{name}（{profile_url}）。"
            + (
                "本 Skill 的滚动 168 小时记录容量为零，已在浏览器发现前阻断。"
                if effective_limit <= 0
                else (
                    f"请求上限 {requested_limit} 已降为有效上限 {effective_limit}；必须确认后才能搜索。"
                    if effective_limit < requested_limit
                    else "下一步按已确认的第一个关键词执行 Posts 搜索。"
                )
            )
        ),
    )


def confirm_effective_limit(
    run_dir: Path,
    *,
    confirmed: bool,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "awaiting_effective_limit_confirmation":
        raise ValueError("当前没有待确认的有效运行上限。")
    if not confirmed:
        raise ValueError("用户未确认降低后的有效上限，不能开始浏览器搜索。")
    timestamp = _timestamp(now)
    state["capacity_at_account_binding"]["confirmed_at"] = timestamp
    state["status"] = "linkedin_account_bound"
    state["phase"] = "awaiting_first_posts_search"
    state["updated_at"] = timestamp
    _append_history(state, timestamp)
    _write_json_atomic(state_path, state)
    effective = state["capacity_at_account_binding"]["effective_limit"]
    return LinkedInSearchStepResult(
        str(run_dir),
        str(state_path),
        state["status"],
        state["phase"],
        (str(state_path),),
        f"已确认本次有效上限 {effective}；可以开始第一个关键词的 Posts 搜索。",
    )


def record_first_posts_search(
    run_dir: Path,
    observation: LinkedInPostSearchObservation,
    *,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "awaiting_first_posts_search":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能记录首次 Posts 搜索。")
    if not state.get("account_binding"):
        raise ValueError("运行尚未绑定 LinkedIn 账号。")
    if observation.search_surface.casefold() not in {"posts", "linkedin_posts"}:
        raise ValueError("第一版只支持 LinkedIn Posts 搜索。")
    if not observation.dedicated_tab_group:
        raise ValueError("Posts 搜索必须在已绑定的专用任务标签组中进行。")
    brief = state.get("confirmed_search_brief") or {}
    keywords = list(brief.get("keywords") or [])
    if not keywords or observation.keyword != keywords[0]:
        raise ValueError("首次 Posts 搜索必须使用 Confirmed Search Brief 中的第一个关键词。")
    if observation.sort_order != brief.get("sort_order"):
        raise ValueError("Posts 搜索排序与 Confirmed Search Brief 不一致。")
    if observation.publication_range != brief.get("publication_range"):
        raise ValueError("Posts 搜索发布日期范围与 Confirmed Search Brief 不一致。")
    if "geography" in observation.applied_filters:
        raise ValueError("LinkedIn Posts 搜索不支持本工作流中的地区筛选。")
    if observation.visible_result_count < 0:
        raise ValueError("可见搜索结果数量不能为负数。")
    timestamp = _timestamp(now)
    search_dir = run_dir / "discovery"
    search_dir.mkdir(parents=True, exist_ok=True)
    search_path = search_dir / "search-progress.json"
    progress = {
        "search_surface": "linkedin_posts",
        "ordered_keywords": keywords,
        "current_keyword_index": 0,
        "current_keyword": observation.keyword,
        "sort_order": observation.sort_order,
        "publication_range": observation.publication_range,
        "applied_filters": observation.applied_filters,
        "visible_result_count": observation.visible_result_count,
        "opened_post_count": 0,
        "recorded_at": timestamp,
        "browser_surface": "official_codex_chrome_extension",
    }
    _write_json_atomic(search_path, progress)
    state["search_progress"] = progress
    state["status"] = "posts_search_active"
    state["phase"] = "discovering_posts"
    state["updated_at"] = timestamp
    state.setdefault("files", {})["search_progress"] = str(search_path)
    _append_history(state, timestamp)
    _write_json_atomic(state_path, state)
    _append_change(run_dir, timestamp, f"记录首次 Posts 搜索：{observation.keyword}；可见结果={observation.visible_result_count}。")
    return LinkedInSearchStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(search_path), str(state_path)),
        message=(
            f"已在账号 {state['account_binding']['member_name']} 下按关键词 {observation.keyword} 完成只读 Posts 搜索；"
            f"当前可见结果 {observation.visible_result_count} 条，尚未发送连接邀请。"
        ),
    )


def record_next_posts_search(
    run_dir: Path,
    observation: LinkedInPostSearchObservation,
    *,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "awaiting_next_keyword_search":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能记录下一关键词搜索。")
    pending_keyword = state.get("pending_keyword")
    brief = state.get("confirmed_search_brief") or {}
    if observation.keyword != pending_keyword:
        raise ValueError("下一次 Posts 搜索必须使用运行状态中的 pending keyword。")
    if observation.search_surface.casefold() not in {"posts", "linkedin_posts"}:
        raise ValueError("第一版只支持 LinkedIn Posts 搜索。")
    if observation.sort_order != brief.get("sort_order") or observation.publication_range != brief.get("publication_range"):
        raise ValueError("下一关键词搜索条件必须与 Confirmed Search Brief 一致。")
    if not observation.dedicated_tab_group or "geography" in observation.applied_filters:
        raise ValueError("下一关键词必须在专用任务标签组中执行，且不能使用地区筛选。")
    progress = dict(state.get("search_progress") or {})
    timestamp = _timestamp(now)
    progress.update(
        {
            "current_keyword": observation.keyword,
            "visible_result_count": observation.visible_result_count,
            "opened_post_count": 0,
            "applied_filters": observation.applied_filters,
            "recorded_at": timestamp,
        }
    )
    search_path = Path(state["files"]["search_progress"])
    _write_json_atomic(search_path, progress)
    state["search_progress"] = progress
    state["pending_keyword"] = None
    state["status"] = "posts_search_active"
    state["phase"] = "discovering_posts"
    state["updated_at"] = timestamp
    _append_history(state, timestamp)
    _write_json_atomic(state_path, state)
    _append_change(run_dir, timestamp, f"记录下一关键词 Posts 搜索：{observation.keyword}。")
    return LinkedInSearchStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(search_path), str(state_path)),
        message=f"已开始关键词 {observation.keyword} 的 Posts 搜索。",
    )


def finish_current_keyword(
    run_dir: Path,
    *,
    exhausted: bool,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "discovering_posts":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能结束当前关键词。")
    progress = dict(state.get("search_progress") or {})
    opened = int(progress.get("opened_post_count") or 0)
    if not exhausted and opened < 50:
        raise ValueError("当前关键词未耗尽且尚未达到 50 条打开贴文上限，不能提前切换关键词。")
    timestamp = _timestamp(now)
    completed = state.setdefault("completed_keywords", [])
    completed.append(
        {
            "keyword": progress.get("current_keyword"),
            "opened_post_count": opened,
            "stop_reason": "exhausted" if exhausted else "opened_post_limit_reached",
            "completed_at": timestamp,
        }
    )
    keywords = list(progress.get("ordered_keywords") or [])
    next_index = int(progress.get("current_keyword_index") or 0) + 1
    candidate_count = len(state.get("candidate_ids") or [])
    requested_limit = int((state.get("confirmed_search_brief") or {}).get("requested_limit") or 10)
    if candidate_count >= requested_limit or next_index >= len(keywords):
        state["status"] = "completed_no_candidates" if candidate_count == 0 else "candidate_discovery_complete"
        state["phase"] = "completed" if candidate_count == 0 else "awaiting_candidate_batch_review"
        state["pending_keyword"] = None
        reason = "candidate_limit_reached" if candidate_count >= requested_limit else "all_keywords_exhausted"
        state["discovery_stop_reason"] = reason
        message = f"候选发现已结束：{reason}；实际候选 {candidate_count} 人。不会自动扩词或找补。"
        if candidate_count == 0:
            from .ledger import release_account_run_lock

            release_account_run_lock(run_dir, state["account_binding"]["profile_url"])
    else:
        progress["current_keyword_index"] = next_index
        progress["current_keyword"] = None
        progress["opened_post_count"] = 0
        state["search_progress"] = progress
        state["pending_keyword"] = keywords[next_index]
        state["status"] = "next_keyword_required"
        state["phase"] = "awaiting_next_keyword_search"
        message = f"当前关键词已结束；下一关键词是 {keywords[next_index]}。不会重复或放宽上一搜索。"
    state["updated_at"] = timestamp
    _append_history(state, timestamp)
    _write_json_atomic(state_path, state)
    search_path = Path(state["files"]["search_progress"])
    _write_json_atomic(search_path, state["search_progress"])
    _append_change(run_dir, timestamp, message)
    return LinkedInSearchStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(search_path), str(state_path)),
        message=message,
    )


def normalize_linkedin_url(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    parts = urlsplit(text)
    if parts.scheme not in {"http", "https"} or not parts.netloc.casefold().endswith("linkedin.com"):
        raise ValueError("LinkedIn URL 必须使用 linkedin.com 的 http/https 地址。")
    path = "/" + "/".join(segment for segment in parts.path.split("/") if segment)
    if path == "/":
        raise ValueError("LinkedIn URL 缺少可识别路径。")
    return urlunsplit(("https", "www.linkedin.com", path, "", ""))


def _load_run(run_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    resolved = run_dir.expanduser().resolve()
    state_path = resolved / "workflow_state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 LinkedIn 搜索运行状态：{exc}") from exc
    if state.get("workflow") != "tuolin-linkedin-search":
        raise ValueError("运行目录不属于 tuolin-linkedin-search。")
    return resolved, state_path, state


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _append_history(state: dict[str, Any], timestamp: str) -> None:
    state.setdefault("status_history", []).append(
        {"status": state["status"], "phase": state["phase"], "at": timestamp}
    )


def _append_change(run_dir: Path, timestamp: str, message: str) -> None:
    with (run_dir / "change_log.md").open("a", encoding="utf-8") as handle:
        handle.write(f"- {timestamp}: {message}\n")


def _timestamp(now: datetime | None) -> str:
    return (now or datetime.now()).strftime("%Y%m%d_%H%M%S")

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .agent import LinkedInSearchStepResult
from .browser_contract import _append_change, _append_history, _load_run, _timestamp, _write_json_atomic, normalize_linkedin_url
from .ledger import release_candidate_reservation, rolling_capacity


def prepare_candidate_batch_review(run_dir: Path, *, now: datetime | None = None) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "awaiting_candidate_batch_review":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能准备候选批次审核。")
    cards = _active_candidate_cards(run_dir, state)
    if not cards:
        raise ValueError("当前没有候选人可封闭为发送批次；任务应以零候选正常结束。")
    timestamp = _timestamp(now)
    payload = {
        "status": "candidate_batch_review",
        "candidate_ids": [card["candidate_id"] for card in cards],
        "candidate_count": len(cards),
        "candidates": cards,
        "no_backfill": True,
        "prepared_at": timestamp,
    }
    review_dir = run_dir / "batch"
    review_dir.mkdir(parents=True, exist_ok=True)
    json_path = review_dir / "candidate-batch-review.json"
    markdown_path = review_dir / "candidate-batch-review.md"
    _write_json_atomic(json_path, payload)
    markdown_path.write_text(_render_batch(payload, "候选批次审核"), encoding="utf-8")
    state["candidate_batch_review"] = {"candidate_ids": payload["candidate_ids"], "prepared_at": timestamp}
    state.setdefault("files", {})["candidate_batch_review"] = [str(markdown_path), str(json_path)]
    state["status"] = "candidate_batch_review_ready"
    state["updated_at"] = timestamp
    _append_history(state, timestamp)
    _write_json_atomic(state_path, state)
    _append_change(run_dir, timestamp, f"生成候选批次审核视图：{len(cards)} 人；不自动找补。")
    return _result(run_dir, state_path, state, (markdown_path, json_path, state_path), markdown_path.read_text(encoding="utf-8"))


def remove_candidates_from_batch(
    run_dir: Path,
    identifiers: list[str],
    *,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "awaiting_candidate_batch_review" or state.get("status") != "candidate_batch_review_ready":
        raise ValueError("只有待审核且尚未封闭的候选批次可以删除候选。")
    wanted = {item.strip().casefold() for item in identifiers if item.strip()}
    if not wanted:
        raise ValueError("至少提供一个要删除的候选标识。")
    account_url = state["account_binding"]["profile_url"]
    removed: list[str] = []
    for card in _active_candidate_cards(run_dir, state):
        member = card["selected_member"]
        keys = {card["candidate_id"].casefold(), member["name"].casefold(), member["profile_url"].casefold()}
        if not wanted.intersection(keys):
            continue
        card["approval"] = "removed_by_user"
        card["removed_at"] = _timestamp(now)
        _persist_card(run_dir, card)
        release_candidate_reservation(
            run_dir,
            account_profile_url=account_url,
            member_profile_url=member["profile_url"],
            candidate_id=card["candidate_id"],
        )
        removed.append(card["candidate_id"])
    if not removed:
        raise ValueError("没有找到与删除标识匹配的候选。")
    state["candidate_ids"] = [item for item in state.get("candidate_ids", []) if item not in removed]
    state["candidate_batch_review"] = None
    state["status"] = "candidate_discovery_complete"
    state["updated_at"] = _timestamp(now)
    _write_json_atomic(state_path, state)
    _append_change(run_dir, state["updated_at"], f"用户删除候选：{removed}；不自动找补。")
    return LinkedInSearchStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(state_path),),
        message=f"已删除 {len(removed)} 名候选，不会自动找补。请重新生成候选批次审核视图。",
    )


def confirm_candidate_batch(run_dir: Path, *, now: datetime | None = None) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "awaiting_candidate_batch_review" or state.get("status") != "candidate_batch_review_ready":
        raise ValueError("当前没有可确认的候选批次审核视图。")
    cards = _active_candidate_cards(run_dir, state)
    if not cards:
        raise ValueError("当前没有候选人可封闭为发送批次。")
    timestamp = _timestamp(now)
    candidate_ids = [card["candidate_id"] for card in cards]
    digest = _digest({"candidate_ids": candidate_ids, "cards": cards})
    payload = {
        "status": "closed_candidate_batch",
        "candidate_ids": candidate_ids,
        "candidate_count": len(cards),
        "candidates": cards,
        "batch_digest": digest,
        "closed_at": timestamp,
        "immutable": True,
        "no_backfill": True,
    }
    batch_dir = run_dir / "batch"
    json_path = batch_dir / "closed-candidate-batch.json"
    markdown_path = batch_dir / "closed-candidate-batch.md"
    _write_json_atomic(json_path, payload)
    markdown_path.write_text(_render_batch(payload, "Closed Candidate Batch"), encoding="utf-8")
    state["closed_candidate_batch"] = {
        "candidate_ids": candidate_ids,
        "candidate_count": len(cards),
        "batch_digest": digest,
        "closed_at": timestamp,
    }
    state.setdefault("files", {})["closed_candidate_batch"] = [str(markdown_path), str(json_path)]
    state["status"] = "closed_candidate_batch_confirmed"
    state["phase"] = "awaiting_dispatch_brief"
    state["updated_at"] = timestamp
    _append_history(state, timestamp)
    _write_json_atomic(state_path, state)
    _append_change(run_dir, timestamp, f"用户确认 Closed Candidate Batch：{len(cards)} 人；digest={digest}。")
    return _result(
        run_dir,
        state_path,
        state,
        (markdown_path, json_path, state_path),
        f"候选批次已封闭，共 {len(cards)} 人。后续不能增加或自动找补；下一步准备留言和最终发送授权。",
    )


def prepare_dispatch_authorization(
    run_dir: Path,
    *,
    note_text: str | None = None,
    note_review_confirmed: bool = False,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "awaiting_dispatch_brief":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能准备最终发送授权。")
    closed_path = Path(state["files"]["closed_candidate_batch"][1])
    closed = json.loads(closed_path.read_text(encoding="utf-8"))
    if closed.get("batch_digest") != state["closed_candidate_batch"]["batch_digest"]:
        raise ValueError("Closed Candidate Batch 内容摘要不一致，不能准备授权。")
    brief = state.get("confirmed_search_brief") or {}
    note_enabled = bool(brief.get("invitation_note"))
    if note_enabled:
        if not note_review_confirmed:
            raise ValueError("使用留言时，AI 英文留言必须先由用户确认或修改。")
        frozen_note = _validate_note(note_text)
        note_mode = "fixed_note"
    else:
        if note_text:
            raise ValueError("当前简报确认不使用留言，不能添加留言文本。")
        frozen_note = None
        note_mode = "no_note"
    account = state.get("account_binding") or {}
    capacity = rolling_capacity(run_dir, account_profile_url=account["profile_url"], now=now)
    requested_limit = int(brief.get("requested_limit") or 10)
    effective_limit = min(requested_limit, capacity["remaining_capacity"])
    if effective_limit <= 0:
        raise ValueError("当前账号在本 Skill 的滚动 168 小时记录中没有剩余发送容量。")
    dispatch_cards = list(closed.get("candidates") or [])[:effective_limit]
    for card in dispatch_cards:
        card["note_decision"] = {"mode": note_mode, "text": frozen_note}
        _persist_card(run_dir, card)
    timestamp = _timestamp(now)
    payload = {
        "status": "dispatch_authorization_required",
        "account": account,
        "closed_batch_digest": closed["batch_digest"],
        "dispatch_candidates": dispatch_cards,
        "dispatch_candidate_ids": [card["candidate_id"] for card in dispatch_cards],
        "count": len(dispatch_cards),
        "note_mode": note_mode,
        "note_text": frozen_note,
        "note_digest": _digest(frozen_note) if frozen_note is not None else None,
        "interval_seconds": int(brief.get("interval_seconds") or 300),
        "requested_limit": requested_limit,
        "recorded_successes_in_168_hours": capacity["recorded_successes"],
        "remaining_recorded_capacity": capacity["remaining_capacity"],
        "effective_limit": effective_limit,
        "manual_linkedin_actions_counted": False,
        "prepared_at": timestamp,
    }
    payload["authorization_digest"] = _digest(payload)
    batch_dir = run_dir / "batch"
    json_path = batch_dir / "dispatch-authorization-brief.json"
    markdown_path = batch_dir / "dispatch-authorization-brief.md"
    _write_json_atomic(json_path, payload)
    markdown_path.write_text(_render_dispatch_brief(payload), encoding="utf-8")
    state["dispatch_authorization_brief"] = {
        "authorization_digest": payload["authorization_digest"],
        "dispatch_candidate_ids": payload["dispatch_candidate_ids"],
        "prepared_at": timestamp,
    }
    state.setdefault("files", {})["dispatch_authorization_brief"] = [str(markdown_path), str(json_path)]
    state["status"] = "dispatch_authorization_required"
    state["phase"] = "awaiting_dispatch_authorization"
    state["updated_at"] = timestamp
    _append_history(state, timestamp)
    _write_json_atomic(state_path, state)
    _append_change(run_dir, timestamp, f"生成最终发送授权简报：{len(dispatch_cards)} 人；有效上限={effective_limit}。")
    return _result(run_dir, state_path, state, (markdown_path, json_path, state_path), markdown_path.read_text(encoding="utf-8"))


def authorize_dispatch_batch(
    run_dir: Path,
    *,
    confirmed: bool,
    observed_member_name: str,
    observed_profile_url: str,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "awaiting_dispatch_authorization":
        raise ValueError("当前没有待确认的最终发送授权简报。")
    if not confirmed:
        raise ValueError("只有用户明确确认最终发送授权后才能进入执行阶段。")
    account = state.get("account_binding") or {}
    if observed_member_name.strip() != account.get("member_name") or normalize_linkedin_url(observed_profile_url) != account.get("profile_url"):
        raise ValueError("最终授权时可见 LinkedIn 账号与运行绑定账号不一致。")
    brief_path = Path(state["files"]["dispatch_authorization_brief"][1])
    payload = json.loads(brief_path.read_text(encoding="utf-8"))
    digest = payload.pop("authorization_digest")
    if _digest(payload) != digest or digest != state["dispatch_authorization_brief"]["authorization_digest"]:
        raise ValueError("最终发送授权简报已变化，必须重新生成并确认。")
    payload["authorization_digest"] = digest
    timestamp = _timestamp(now)
    state["authorized_dispatch_batch"] = {
        "authorization_digest": digest,
        "dispatch_candidate_ids": payload["dispatch_candidate_ids"],
        "account_profile_url": account["profile_url"],
        "confirmed_at": timestamp,
    }
    state["status"] = "dispatch_batch_authorized"
    state["phase"] = "ready_to_dispatch"
    state["updated_at"] = timestamp
    _append_history(state, timestamp)
    _write_json_atomic(state_path, state)
    _append_change(run_dir, timestamp, f"用户最终授权连接邀请批次：{len(payload['dispatch_candidate_ids'])} 人。")
    return _result(
        run_dir,
        state_path,
        state,
        (state_path,),
        f"已授权精确批次 {len(payload['dispatch_candidate_ids'])} 人；可以按固定间隔顺序执行，无需逐人再次确认。",
    )


def _active_candidate_cards(run_dir: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    cards = []
    for candidate_id in state.get("candidate_ids") or []:
        path = run_dir / "candidates" / f"{candidate_id}.json"
        if not path.exists():
            raise ValueError(f"候选卡缺失：{candidate_id}")
        card = json.loads(path.read_text(encoding="utf-8"))
        if card.get("approval") == "pending_batch_review":
            cards.append(card)
    return cards


def _persist_card(run_dir: Path, card: dict[str, Any]) -> None:
    json_path = run_dir / "candidates" / f"{card['candidate_id']}.json"
    _write_json_atomic(json_path, card)
    markdown_path = run_dir / "candidates" / f"{card['candidate_id']}.md"
    markdown_path.write_text(_render_card(card), encoding="utf-8")


def _render_card(card: dict[str, Any]) -> str:
    member = card["selected_member"]
    return "\n".join(
        [
            f"## 候选卡：{member['name']}",
            "",
            f"- 来源关键词：{card['source_keyword']}",
            f"- 贴文：{card['post_text']}",
            f"- 贴文 URL：{card['post_url']}",
            f"- 相关理由：{card['relevance_reason']}",
            f"- 公司：{card['company']['name']}",
            f"- 联系人：{member['name']}",
            f"- 职位：{member['title']}",
            f"- Profile：{member['profile_url']}",
            f"- 审核状态：{card['approval']}",
            "",
        ]
    )


def _render_batch(payload: dict[str, Any], title: str) -> str:
    lines = [f"# {title}", "", f"候选人数：{payload['candidate_count']}", "", "确认前可以删除候选；删除后不会自动找补。", ""]
    for index, card in enumerate(payload.get("candidates") or [], start=1):
        member = card["selected_member"]
        lines.extend(
            [
                f"## {index}. {member['name']}",
                f"- 关键词：{card['source_keyword']}",
                f"- 贴文：{card['post_text']}",
                f"- 贴文 URL：{card['post_url']}",
                f"- 相关理由：{card['relevance_reason']}",
                f"- 公司：{member['company']}",
                f"- 职位：{member['title']}",
                f"- Profile：{member['profile_url']}",
                "",
            ]
        )
    return "\n".join(lines)


def _render_dispatch_brief(payload: dict[str, Any]) -> str:
    account = payload["account"]
    lines = [
        "# 最终连接邀请授权简报",
        "",
        f"- LinkedIn 账号：{account['member_name']}（{account['profile_url']}）",
        f"- 精确候选人数：{payload['count']}",
        f"- 留言方式：{payload['note_mode']}",
        f"- 固定留言：{payload['note_text'] if payload['note_text'] is not None else '不使用留言'}",
        f"- 固定间隔：{payload['interval_seconds']} 秒",
        f"- 请求上限：{payload['requested_limit']}",
        f"- 过去 168 小时本 Skill 记录成功数：{payload['recorded_successes_in_168_hours']}",
        f"- 剩余记录容量：{payload['remaining_recorded_capacity']}",
        f"- 有效上限：{payload['effective_limit']}",
        "- 手工 LinkedIn 操作：不计入本地统计",
        "",
        "## 将要发送的精确候选",
        "",
    ]
    for index, card in enumerate(payload["dispatch_candidates"], start=1):
        member = card["selected_member"]
        lines.append(f"{index}. {member['name']} — {member['title']} — {member['company']} — {member['profile_url']}")
    lines.extend(["", "确认本简报后才可开始顺序发送。", ""])
    return "\n".join(lines)


def _validate_note(value: str | None) -> str:
    text = value if value is not None else ""
    if not text.strip():
        raise ValueError("使用留言时必须提供非空英文留言。")
    if len(text) > 300:
        raise ValueError("LinkedIn 邀请留言过长；第一版限制为 300 个字符以内。")
    if not re.search(r"[A-Za-z]", text):
        raise ValueError("邀请留言必须使用英文。")
    return text


def _digest(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _result(
    run_dir: Path,
    state_path: Path,
    state: dict[str, Any],
    output_paths: tuple[Path, ...],
    message: str,
) -> LinkedInSearchStepResult:
    return LinkedInSearchStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=tuple(str(path) for path in output_paths),
        message=message,
    )

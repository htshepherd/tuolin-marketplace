from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .agent import LinkedInSearchStepResult
from .browser_contract import _append_change, _append_history, _load_run, _timestamp, _write_json_atomic, normalize_linkedin_url
from .cards import (
    candidate_identity_digest,
    candidate_review_digest,
    persist_candidate_card,
    render_candidate_batch,
    verify_candidate_identity,
    verify_candidate_review,
)
from .ledger import release_account_run_lock, release_candidate_reservation, reserve_candidate, rolling_capacity
from .workbook import append_dispatch_records, read_current_selections, set_boss_decision
from .feedback import capture_workbook_feedback


def prepare_candidate_batch_review(run_dir: Path, *, now: datetime | None = None) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "awaiting_candidate_batch_review":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能准备候选批次审核。")
    feedback = capture_workbook_feedback(run_dir, state["account_binding"]["profile_url"], now=now)
    state.setdefault("files", {})["prospect_feedback"] = feedback["feedback_path"]
    cards = _workbook_selected_cards(run_dir, state, now=now)
    if not cards:
        raise ValueError("累计潜客表中没有标记为“发送”的可行动联系人；请先由老板筛选。")
    timestamp = _timestamp(now)
    payload = {
        "status": "candidate_batch_review",
        "candidate_ids": [card["candidate_id"] for card in cards],
        "candidate_count": len(cards),
        "candidates": cards,
        "selection_source": "account_prospect_workbook",
        "no_backfill": True,
        "prepared_at": timestamp,
    }
    review_dir = run_dir / "batch"
    review_dir.mkdir(parents=True, exist_ok=True)
    json_path = review_dir / "candidate-batch-review.json"
    markdown_path = review_dir / "candidate-batch-review.md"
    _write_json_atomic(json_path, payload)
    markdown_path.write_text(render_candidate_batch(payload, "候选批次审核"), encoding="utf-8")
    state["candidate_batch_review"] = {"candidate_ids": payload["candidate_ids"], "prepared_at": timestamp}
    state.setdefault("files", {})["candidate_batch_review"] = [str(markdown_path), str(json_path)]
    state["status"] = "candidate_batch_review_ready"
    state["updated_at"] = timestamp
    _append_history(state, timestamp)
    _write_json_atomic(state_path, state)
    _append_change(run_dir, timestamp, f"从账号累计潜客表生成当前发送选择：{len(cards)} 人。")
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
        persist_candidate_card(run_dir, card)
        release_candidate_reservation(
            run_dir,
            account_profile_url=account_url,
            member_profile_url=member["profile_url"],
            candidate_id=card["candidate_id"],
        )
        set_boss_decision(run_dir, account_url, member["profile_url"], "排除", "在当前任务中由用户明确移除。")
        removed.append(card["candidate_id"])
    if not removed:
        raise ValueError("没有找到与删除标识匹配的候选。")
    state["candidate_ids"] = [item for item in state.get("candidate_ids", []) if item not in removed]
    state["candidate_batch_review"] = None
    if state["candidate_ids"]:
        state["status"] = "candidate_discovery_complete"
    else:
        state["status"] = "completed_no_candidates_after_review"
        state["phase"] = "completed"
        release_account_run_lock(run_dir, account_url)
    state["updated_at"] = _timestamp(now)
    _write_json_atomic(state_path, state)
    _append_change(run_dir, state["updated_at"], f"用户删除候选：{removed}；不自动找补。")
    return LinkedInSearchStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(state_path),),
        message=(
            f"已删除 {len(removed)} 名候选，不会自动找补。请重新生成候选批次审核视图。"
            if state["candidate_ids"]
            else "已删除全部候选；任务以零候选结束，账号运行锁已释放。"
        ),
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
    identity_digests = {card["candidate_id"]: candidate_identity_digest(card) for card in cards}
    review_digests = {card["candidate_id"]: candidate_review_digest(card) for card in cards}
    digest = _digest({"candidate_ids": candidate_ids, "candidate_identity_digests": identity_digests, "cards": cards})
    payload = {
        "status": "closed_candidate_batch",
        "candidate_ids": candidate_ids,
        "candidate_count": len(cards),
        "candidates": cards,
        "batch_digest": digest,
        "candidate_identity_digests": identity_digests,
        "candidate_review_digests": review_digests,
        "closed_at": timestamp,
        "immutable": True,
        "no_backfill": True,
    }
    batch_dir = run_dir / "batch"
    json_path = batch_dir / "closed-candidate-batch.json"
    markdown_path = batch_dir / "closed-candidate-batch.md"
    _write_json_atomic(json_path, payload)
    markdown_path.write_text(render_candidate_batch(payload, "Closed Candidate Batch"), encoding="utf-8")
    state["closed_candidate_batch"] = {
        "candidate_ids": candidate_ids,
        "candidate_count": len(cards),
        "batch_digest": digest,
        "candidate_identity_digests": identity_digests,
        "candidate_review_digests": review_digests,
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
    recomputed_batch_digest = _digest(
        {
            "candidate_ids": closed.get("candidate_ids"),
            "candidate_identity_digests": closed.get("candidate_identity_digests"),
            "cards": closed.get("candidates"),
        }
    )
    if (
        closed.get("batch_digest") != state["closed_candidate_batch"]["batch_digest"]
        or recomputed_batch_digest != closed.get("batch_digest")
    ):
        raise ValueError("Closed Candidate Batch 内容摘要不一致，不能准备授权。")
    current_cards = {card["candidate_id"]: card for card in _load_candidate_cards(run_dir, closed.get("candidate_ids") or [])}
    for candidate_id, expected in (closed.get("candidate_identity_digests") or {}).items():
        if candidate_id not in current_cards:
            raise ValueError(f"Closed Candidate Batch 候选卡缺失：{candidate_id}")
        verify_candidate_identity(current_cards[candidate_id], expected)
        verify_candidate_review(current_cards[candidate_id], closed["candidate_review_digests"][candidate_id])
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
    dispatch_cards = list(closed.get("candidates") or [])
    approved_count = len(dispatch_cards)
    if capacity["remaining_capacity"] <= 0:
        raise ValueError("当前发送容量为 0；搜索、工作簿和审核结果保持有效，但不能创建 Connect 授权快照。")
    if capacity["remaining_capacity"] < approved_count:
        raise ValueError(
            f"老板选择了 {approved_count} 人，但当前只剩 {capacity['remaining_capacity']} 个本地记录容量。"
            "系统不会自动截取前 N 人；请在累计潜客表中重新选择精确子集后再次生成快照。"
        )
    for card in dispatch_cards:
        card["note_decision"] = {"mode": note_mode, "text": frozen_note}
        persist_candidate_card(run_dir, card)
    timestamp = _timestamp(now)
    payload = {
        "status": "dispatch_authorization_required",
        "account": account,
        "closed_batch_digest": closed["batch_digest"],
        "dispatch_candidates": dispatch_cards,
        "dispatch_candidate_ids": [card["candidate_id"] for card in dispatch_cards],
        "candidate_identity_digests": {
            card["candidate_id"]: candidate_identity_digest(card) for card in dispatch_cards
        },
        "candidate_review_digests": {
            card["candidate_id"]: candidate_review_digest(card) for card in dispatch_cards
        },
        "deferred_candidate_ids": [],
        "count": len(dispatch_cards),
        "note_mode": note_mode,
        "note_text": frozen_note,
        "note_digest": _digest(frozen_note) if frozen_note is not None else None,
        "interval_seconds": int(brief.get("interval_seconds") or 120),
        "approved_dispatch_count": approved_count,
        "recorded_successes_in_168_hours": capacity["recorded_successes"],
        "remaining_recorded_capacity": capacity["remaining_capacity"],
        "effective_limit": approved_count,
        "manual_linkedin_actions_counted": False,
        "prepared_at": timestamp,
    }
    payload["authorization_digest"] = _digest(payload)
    batch_dir = run_dir / "batch"
    json_path = batch_dir / "final-dispatch-snapshot.json"
    markdown_path = batch_dir / "final-dispatch-snapshot.md"
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
    _append_change(run_dir, timestamp, f"生成不可变最终发送快照：{len(dispatch_cards)} 人；容量充足。")
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
    deferred_ids: list[str] = []
    append_dispatch_records(
        run_dir,
        account_profile_url=account["profile_url"],
        records=[
            {
                "batch_digest": digest,
                "contact_id": "contact_" + hashlib.sha256(card["selected_member"]["profile_url"].encode("utf-8")).hexdigest()[:16],
                "authorized_at": timestamp,
                "note": payload.get("note_text") or "",
                "interval_seconds": int(payload.get("interval_seconds") or 0),
                "result": "authorized",
            }
            for card in payload.get("dispatch_candidates") or []
        ],
    )
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
        (
            f"已授权精确批次 {len(payload['dispatch_candidate_ids'])} 人；可以按固定间隔顺序执行，无需逐人再次确认。"
            + " 最终快照已冻结，批次执行期间不会自动改写成员、留言或间隔。"
        ),
    )


def _active_candidate_cards(run_dir: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    cards = []
    for candidate_id in state.get("candidate_ids") or []:
        path = run_dir / "candidates" / f"{candidate_id}.json"
        if not path.exists():
            raise ValueError(f"候选卡缺失：{candidate_id}")
        card = json.loads(path.read_text(encoding="utf-8"))
        if card.get("identity_digest"):
            verify_candidate_identity(card, card["identity_digest"])
        if card.get("approval") == "pending_batch_review":
            cards.append(card)
    return cards


def _workbook_selected_cards(run_dir: Path, state: dict[str, Any], *, now: datetime | None = None) -> list[dict[str, Any]]:
    account_url = state["account_binding"]["profile_url"]
    selections = read_current_selections(run_dir, account_url)
    restart_ids = set((state.get("restart_source") or {}).get("candidate_ids") or [])
    if restart_ids:
        selections = [
            item for item in selections
            if "candidate_" + hashlib.sha256(normalize_linkedin_url(str(item["LinkedIn主页"])).encode("utf-8")).hexdigest()[:16] in restart_ids
        ]
    selected_profiles = {normalize_linkedin_url(str(item["LinkedIn主页"])) for item in selections}
    current_cards = {card["selected_member"]["profile_url"]: card for card in _active_candidate_cards(run_dir, state)}
    cards: list[dict[str, Any]] = []
    for selection in selections:
        profile_url = normalize_linkedin_url(str(selection["LinkedIn主页"]))
        card = current_cards.get(profile_url)
        if card is None:
            evidence = selection.get("最新证据") or {}
            company_url = normalize_linkedin_url(str(selection.get("公司主页") or "")) if selection.get("公司主页") else ""
            post_url = normalize_linkedin_url(str(evidence.get("贴文链接") or "")) if evidence.get("贴文链接") else ""
            candidate_id = "candidate_" + hashlib.sha256(profile_url.encode("utf-8")).hexdigest()[:16]
            reservation = reserve_candidate(
                run_dir,
                account_profile_url=account_url,
                member_profile_url=profile_url,
                company_url=company_url,
                source_post_url=post_url,
                candidate_id=candidate_id,
                live_state="none",
                now=now,
            )
            if not reservation["eligible"]:
                raise ValueError(f"历史待定联系人 {profile_url} 重新校验失败：{reservation['reason']}")
            card = {
                "candidate_id": candidate_id,
                "source_keyword": evidence.get("关键词") or "",
                "post_text": evidence.get("完整贴文") or "",
                "post_url": post_url,
                "relevance_decision": "continue",
                "relevance_reason": evidence.get("Codex初步判断") or "历史待定联系人由老板本次明确选择。",
                "fit_status": "provisional_candidate_fit",
                "business_role": evidence.get("商业角色") or "ambiguous",
                "supporting_evidence": evidence.get("支持证据") or "",
                "material_doubts": evidence.get("不确定性") or "",
                "preliminary_assessment": {
                    "summary": evidence.get("Codex初步判断") or "",
                    "business_role": evidence.get("商业角色") or "ambiguous",
                    "supporting_evidence": evidence.get("支持证据") or "",
                    "uncertainty": evidence.get("不确定性") or "",
                    "recommendation": evidence.get("Codex建议") or "保留给老板判断",
                    "provisional": "true",
                },
                "author": {"name": "", "type": "historical_workbook", "profile_url": profile_url},
                "company": {"name": selection.get("公司") or "", "url": company_url},
                "selected_member": {"name": selection.get("姓名") or "", "title": selection.get("职位") or "", "company": selection.get("公司") or "", "profile_url": profile_url},
                "connect_path": "standard_connect",
                "approval": "pending_batch_review",
                "note_decision": None,
                "final_outcome": None,
                "created_at": _timestamp(now),
                "selection_source": "historical_pending_explicitly_selected",
            }
            persist_candidate_card(run_dir, card)
        cards.append(card)
    for profile_url, card in current_cards.items():
        if profile_url in selected_profiles:
            continue
        release_candidate_reservation(run_dir, account_profile_url=account_url, member_profile_url=profile_url, candidate_id=card["candidate_id"])
        card["approval"] = "not_selected_in_workbook"
        persist_candidate_card(run_dir, card)
    state["candidate_ids"] = [card["candidate_id"] for card in cards]
    return cards


def _load_candidate_cards(run_dir: Path, candidate_ids: list[str]) -> list[dict[str, Any]]:
    cards = []
    for candidate_id in candidate_ids:
        path = run_dir / "candidates" / f"{candidate_id}.json"
        if not path.exists():
            raise ValueError(f"候选卡缺失：{candidate_id}")
        cards.append(json.loads(path.read_text(encoding="utf-8")))
    return cards


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
        f"- 老板批准发送人数：{payload['approved_dispatch_count']}",
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
        lines.extend([
            f"### {index}. {member['name']} — {member['title']}",
            "",
            f"- 公司：{member['company']}",
            f"- Profile：{member['profile_url']}",
            f"- 来源关键词：{card.get('source_keyword')}",
            f"- 贴文链接：{card.get('post_url')}",
            f"- Codex 初步判断：{card.get('relevance_reason')}",
            f"- 支持证据：{card.get('supporting_evidence')}",
            f"- 不确定性：{card.get('material_doubts') or '无额外说明'}",
            "",
            "完整贴文：",
            "",
            str(card.get("post_text") or ""),
            "",
        ])
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

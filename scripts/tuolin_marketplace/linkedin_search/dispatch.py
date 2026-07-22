from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .agent import LinkedInSearchStepResult
from .browser_contract import _append_change, _append_history, _load_run, _write_json_atomic, normalize_linkedin_url
from .cards import persist_candidate_card, verify_candidate_identity, verify_candidate_review
from .ledger import (
    pre_dispatch_eligibility,
    record_contact_outcome,
    release_account_run_lock,
    release_run_reservations,
    rolling_capacity,
)


PLATFORM_STOP_RESULTS = {"platform_restriction", "security_checkpoint", "captcha", "logged_out"}
LOCAL_FAILURE_RESULTS = {"no_connect_button", "profile_unavailable", "no_dispatch_failure"}


@dataclass(frozen=True)
class InvitationPreflightObservation:
    account_member_name: str
    account_profile_url: str
    candidate_id: str
    candidate_profile_url: str
    live_connection_state_before: str
    standard_connect_available: bool
    add_note_available: bool
    profile_accessible: bool = True
    requires_email_or_extra_identity: bool = False


@dataclass(frozen=True)
class InvitationResultObservation:
    attempt_id: str
    account_member_name: str
    account_profile_url: str
    candidate_id: str
    candidate_profile_url: str
    result: str
    visible_confirmation: str = ""


def prepare_dispatch_attempt(
    run_dir: Path,
    observation: InvitationPreflightObservation,
    *,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") not in {"ready_to_dispatch", "awaiting_dispatch_interval"}:
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能准备连接邀请预检。")
    current = _aware(now)
    _validate_interval_gate(state, current)
    authorization = _load_authorization(run_dir, state)
    account = state.get("account_binding") or {}
    if observation.account_member_name.strip() != account.get("member_name"):
        return _stop_for_account_change(run_dir, state_path, state, current, "可见 LinkedIn 会员姓名已变化。")
    if normalize_linkedin_url(observation.account_profile_url) != account.get("profile_url"):
        return _stop_for_account_change(run_dir, state_path, state, current, "可见 LinkedIn profile URL 已变化。")
    results = state.setdefault("dispatch_results", [])
    completed_ids = {item["candidate_id"] for item in results if item.get("terminal")}
    remaining_ids = [item for item in authorization["dispatch_candidate_ids"] if item not in completed_ids]
    if not remaining_ids:
        return _complete_dispatch(run_dir, state_path, state, current)
    expected_id = remaining_ids[0]
    if observation.candidate_id != expected_id:
        raise ValueError(f"必须严格按授权顺序处理候选 {expected_id}。")
    card = _load_card(run_dir, expected_id)
    expected_digest = (authorization.get("candidate_identity_digests") or {}).get(expected_id)
    if not expected_digest:
        raise ValueError("授权简报缺少候选身份摘要，不能执行。")
    verify_candidate_identity(card, expected_digest)
    verify_candidate_review(card, authorization["candidate_review_digests"][expected_id])
    member = card["selected_member"]
    if normalize_linkedin_url(observation.candidate_profile_url) != member["profile_url"]:
        raise ValueError("浏览器中的候选 profile 与授权候选不一致。")

    capacity = rolling_capacity(run_dir, account_profile_url=account["profile_url"], now=current)
    if capacity["remaining_capacity"] <= 0:
        return _stop_batch(run_dir, state_path, state, current, "rolling_capacity_exhausted", "发送前重新计算发现滚动容量为零。")
    live_state = observation.live_connection_state_before.casefold()
    if live_state not in {"none", "pending", "connected", "ambiguous"}:
        raise ValueError(f"未知的发送前实时连接状态：{observation.live_connection_state_before}")
    if live_state in {"pending", "connected"}:
        outcome = "skipped_live_" + live_state
        record_contact_outcome(
            run_dir,
            account_profile_url=account["profile_url"],
            member_profile_url=member["profile_url"],
            company_url=card["company"]["url"],
            candidate_id=expected_id,
            outcome=live_state,
            source_post_url=card["post_url"],
            batch_digest=authorization["closed_batch_digest"],
            now=current,
        )
        _record_result(state, card, outcome, current, terminal=True)
        card["final_outcome"] = outcome
        persist_candidate_card(run_dir, card)
        return _advance_after_non_send(run_dir, state_path, state, current, outcome)
    if live_state == "ambiguous":
        return _stop_batch(run_dir, state_path, state, current, "ambiguous_pre_send_state", "发送前连接状态不明确。", ambiguous_candidate=expected_id)
    ledger_check = pre_dispatch_eligibility(
        run_dir,
        account_profile_url=account["profile_url"],
        member_profile_url=member["profile_url"],
        company_url=card["company"]["url"],
        source_post_url=card["post_url"],
        candidate_id=expected_id,
    )
    if not ledger_check["eligible"]:
        return _stop_batch(
            run_dir,
            state_path,
            state,
            current,
            "ledger_pre_send_mismatch",
            f"发送前共享账本不允许执行：{ledger_check['reason']}。",
            ambiguous_candidate=expected_id,
        )
    if not observation.profile_accessible:
        _record_result(state, card, "failed_profile_unavailable", current, terminal=True)
        record_contact_outcome(
            run_dir,
            account_profile_url=account["profile_url"],
            member_profile_url=member["profile_url"],
            company_url=card["company"]["url"],
            source_post_url=card["post_url"],
            candidate_id=expected_id,
            outcome="failed_no_dispatch",
            now=current,
        )
        card["final_outcome"] = "failed_profile_unavailable"
        persist_candidate_card(run_dir, card)
        return _advance_after_non_send(run_dir, state_path, state, current, "failed_profile_unavailable")
    if not observation.standard_connect_available:
        _record_result(state, card, "failed_no_connect_button", current, terminal=True)
        record_contact_outcome(
            run_dir,
            account_profile_url=account["profile_url"],
            member_profile_url=member["profile_url"],
            company_url=card["company"]["url"],
            candidate_id=expected_id,
            outcome="failed_no_dispatch",
            source_post_url=card["post_url"],
            now=current,
        )
        card["final_outcome"] = "failed_no_connect_button"
        persist_candidate_card(run_dir, card)
        return _advance_after_non_send(run_dir, state_path, state, current, "failed_no_connect_button")
    if observation.requires_email_or_extra_identity:
        _record_result(state, card, "failed_extra_identity_required", current, terminal=True)
        record_contact_outcome(
            run_dir,
            account_profile_url=account["profile_url"],
            member_profile_url=member["profile_url"],
            company_url=card["company"]["url"],
            candidate_id=expected_id,
            outcome="failed_no_dispatch",
            source_post_url=card["post_url"],
            now=current,
        )
        card["final_outcome"] = "failed_extra_identity_required"
        persist_candidate_card(run_dir, card)
        return _advance_after_non_send(run_dir, state_path, state, current, "failed_extra_identity_required")
    if authorization["note_mode"] == "fixed_note" and not observation.add_note_available:
        state["status"] = "note_unavailable_reauthorization_required"
        state["phase"] = "awaiting_note_unavailable_decision"
        state["note_unavailable_candidate_id"] = expected_id
        state["updated_at"] = current.isoformat()
        _append_history(state, current.isoformat())
        _write_json_atomic(state_path, state)
        _append_change(run_dir, current.isoformat(), "Add a note 不可用；暂停并要求用户选择无留言重新授权或结束。")
        return _result(run_dir, state_path, state, "Add a note 当前不可用。不得静默移除留言；请选择改为无留言并重新确认整个发送简报，或结束任务。")
    attempt_id = hashlib.sha256(
        f"{authorization['authorization_digest']}:{expected_id}:{current.isoformat()}".encode("utf-8")
    ).hexdigest()
    attempt = {
        "attempt_id": attempt_id,
        "candidate_id": expected_id,
        "candidate_profile_url": member["profile_url"],
        "account_profile_url": account["profile_url"],
        "authorization_digest": authorization["authorization_digest"],
        "closed_batch_digest": authorization["closed_batch_digest"],
        "note_mode": authorization["note_mode"],
        "note_text": authorization["note_text"],
        "note_digest": authorization.get("note_digest"),
        "prepared_at": current.isoformat(),
        "browser_action_completed": False,
    }
    attempt_path = run_dir / "batch" / "pending-dispatch-attempt.json"
    _write_json_atomic(attempt_path, attempt)
    state["pending_dispatch_attempt"] = attempt
    state["status"] = "dispatch_preflight_passed"
    state["phase"] = "awaiting_dispatch_result"
    state["updated_at"] = current.isoformat()
    state.setdefault("files", {})["pending_dispatch_attempt"] = str(attempt_path)
    _append_history(state, current.isoformat())
    _write_json_atomic(state_path, state)
    _append_change(run_dir, current.isoformat(), f"发送前预检通过：{expected_id}；attempt={attempt_id}。")
    note_instruction = (
        f"使用冻结留言：{authorization['note_text']}"
        if authorization["note_mode"] == "fixed_note"
        else "不打开 Add a note，按无留言路径发送"
    )
    return LinkedInSearchStepResult(
        str(run_dir),
        str(state_path),
        state["status"],
        state["phase"],
        (str(attempt_path), str(state_path)),
        f"发送前预检已通过。仅允许对 {member['name']}（{member['profile_url']}）执行一次 Connect；{note_instruction}。完成后必须记录 attempt {attempt_id} 的可见结果。",
    )


def record_dispatch_result(
    run_dir: Path,
    observation: InvitationResultObservation,
    *,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "awaiting_dispatch_result":
        raise ValueError("当前没有通过预检且等待结果的连接邀请。")
    current = _aware(now)
    attempt = dict(state.get("pending_dispatch_attempt") or {})
    if not attempt or observation.attempt_id != attempt.get("attempt_id"):
        raise ValueError("发送结果没有匹配当前一次性 dispatch attempt。")
    authorization = _load_authorization(run_dir, state)
    if attempt.get("authorization_digest") != authorization.get("authorization_digest"):
        raise ValueError("dispatch attempt 与当前授权摘要不一致。")
    account = state.get("account_binding") or {}
    expected_id = str(attempt["candidate_id"])
    if observation.candidate_id != expected_id:
        raise ValueError("发送结果候选与预检候选不一致。")
    if observation.account_member_name.strip() != account.get("member_name") or normalize_linkedin_url(observation.account_profile_url) != account.get("profile_url"):
        return _stop_for_account_change(run_dir, state_path, state, current, "结果记录时可见 LinkedIn 账号已变化。")
    card = _load_card(run_dir, expected_id)
    verify_candidate_identity(card, authorization["candidate_identity_digests"][expected_id])
    verify_candidate_review(card, authorization["candidate_review_digests"][expected_id])
    member = card["selected_member"]
    if normalize_linkedin_url(observation.candidate_profile_url) != member["profile_url"]:
        raise ValueError("发送结果中的候选 profile 与预检候选不一致。")
    attempt["browser_action_completed"] = True
    attempt["result_observed_at"] = current.isoformat()
    result = observation.result.casefold()
    attempt["observed_result"] = result
    attempt["visible_confirmation"] = observation.visible_confirmation
    attempt_path_value = (state.get("files") or {}).get("pending_dispatch_attempt")
    if not attempt_path_value:
        raise ValueError("pending dispatch attempt 文件路径缺失。")
    attempt_path = Path(attempt_path_value)
    _write_json_atomic(attempt_path, attempt)
    state["pending_dispatch_attempt"] = attempt
    if result == "success":
        if not observation.visible_confirmation.strip():
            return _stop_batch(run_dir, state_path, state, current, "ambiguous_dispatch", "点击后没有可见的邀请成功确认。", ambiguous_candidate=expected_id)
        try:
            record_contact_outcome(
                run_dir,
                account_profile_url=account["profile_url"],
                member_profile_url=member["profile_url"],
                company_url=card["company"]["url"],
                candidate_id=expected_id,
                outcome="sent",
                source_post_url=card["post_url"],
                batch_digest=authorization["closed_batch_digest"],
                now=current,
            )
        except (OSError, ValueError) as exc:
            state["status"] = "reconciliation_required"
            state["phase"] = "reconciliation_required"
            state["reconciliation"] = {
                "candidate_id": expected_id,
                "reason": "linkedin_success_ledger_write_failed",
                "visible_confirmation": observation.visible_confirmation,
                "error": str(exc),
            }
            state["updated_at"] = current.isoformat()
            _write_json_atomic(state_path, state)
            return _result(run_dir, state_path, state, "LinkedIn 已显示邀请成功，但共享账本写入失败。已停止，必须先人工对账。")
        _record_result(state, card, "invitation_dispatch_success", current, terminal=True, detail=observation.visible_confirmation)
        card["final_outcome"] = "invitation_dispatch_success"
        persist_candidate_card(run_dir, card)
        attempt["ledger_recorded"] = True
        _write_json_atomic(attempt_path, attempt)
        state["pending_dispatch_attempt"] = None
        return _advance_after_success(run_dir, state_path, state, current, authorization)
    if result in LOCAL_FAILURE_RESULTS:
        record_contact_outcome(
            run_dir,
            account_profile_url=account["profile_url"],
            member_profile_url=member["profile_url"],
            company_url=card["company"]["url"],
            candidate_id=expected_id,
            outcome="failed_no_dispatch",
            source_post_url=card["post_url"],
            now=current,
        )
        outcome = "failed_" + result
        _record_result(state, card, outcome, current, terminal=True)
        card["final_outcome"] = outcome
        persist_candidate_card(run_dir, card)
        attempt["ledger_recorded"] = True
        _write_json_atomic(attempt_path, attempt)
        state["pending_dispatch_attempt"] = None
        return _advance_after_non_send(run_dir, state_path, state, current, outcome)
    if result in PLATFORM_STOP_RESULTS:
        try:
            record_contact_outcome(
                run_dir,
                account_profile_url=account["profile_url"],
                member_profile_url=member["profile_url"],
                company_url=card["company"]["url"],
                candidate_id=expected_id,
                outcome="ambiguous",
                source_post_url=card["post_url"],
                batch_digest=authorization["closed_batch_digest"],
                now=current,
            )
            attempt["ledger_recorded"] = True
            _write_json_atomic(attempt_path, attempt)
        except (OSError, ValueError) as exc:
            state["reconciliation"] = {
                "candidate_id": expected_id,
                "reason": "platform_stop_ambiguous_ledger_write_failed",
                "error": str(exc),
            }
        outcome = "ambiguous_after_" + result
        _record_result(state, card, outcome, current, terminal=True, detail=observation.visible_confirmation)
        card["final_outcome"] = outcome
        persist_candidate_card(run_dir, card)
        state["pending_dispatch_attempt"] = None
        return _stop_batch(run_dir, state_path, state, current, result, f"检测到平台级停止：{result}。")
    return _stop_batch(run_dir, state_path, state, current, "ambiguous_dispatch", "邀请结果不明确，禁止重试。", ambiguous_candidate=expected_id)


def dispatch_next_candidate(*args: Any, **kwargs: Any) -> LinkedInSearchStepResult:
    raise ValueError("dispatch-next 已停用。必须先 prepare-dispatch，再由 Chrome 执行动作，最后 record-dispatch-result。")


def resolve_note_unavailable(
    run_dir: Path,
    *,
    send_without_note: bool,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "awaiting_note_unavailable_decision":
        raise ValueError("当前没有 Add a note 不可用的待决策状态。")
    timestamp = _aware(now).isoformat()
    if not send_without_note:
        state["status"] = "ended_by_user_note_unavailable"
        state["phase"] = "completed"
        message = "用户选择不在无留言条件下继续，本次任务已结束。"
        release_run_reservations(run_dir, state["account_binding"]["profile_url"])
        release_account_run_lock(run_dir, state["account_binding"]["profile_url"])
    else:
        state["confirmed_search_brief"]["invitation_note"] = False
        state["dispatch_authorization_brief"] = None
        state["authorized_dispatch_batch"] = None
        state["status"] = "closed_candidate_batch_confirmed"
        state["phase"] = "awaiting_dispatch_brief"
        message = "已选择改为无留言；必须重新生成并确认最终发送授权简报。"
    state["updated_at"] = timestamp
    _append_history(state, timestamp)
    _write_json_atomic(state_path, state)
    _append_change(run_dir, timestamp, message)
    return _result(run_dir, state_path, state, message)


def prepare_interruption_recovery(
    run_dir: Path,
    *,
    observed_member_name: str,
    observed_profile_url: str,
    last_candidate_live_state: str,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") in {"platform_stopped", "reconciliation_required"}:
        raise ValueError("平台级停止或待对账运行不能原地恢复；必须新建任务并重新授权。")
    if state.get("phase") not in {
        "ready_to_dispatch",
        "awaiting_dispatch_interval",
        "awaiting_dispatch_result",
        "dispatch_interrupted",
    }:
        raise ValueError(f"当前阶段 {state.get('phase')!r} 不支持发送中断恢复。")
    account = state.get("account_binding") or {}
    if observed_member_name.strip() != account.get("member_name") or normalize_linkedin_url(observed_profile_url) != account.get("profile_url"):
        raise ValueError("恢复时可见 LinkedIn 账号与绑定账号不一致。")
    live = last_candidate_live_state.casefold()
    if live not in {"none", "pending", "connected", "ambiguous"}:
        raise ValueError("last_candidate_live_state 必须是 none、pending、connected 或 ambiguous。")
    if live == "ambiguous":
        state["status"] = "reconciliation_required"
        state["phase"] = "reconciliation_required"
        state["reconciliation"] = {"reason": "last_action_ambiguous_during_recovery"}
        state["updated_at"] = _aware(now).isoformat()
        _write_json_atomic(state_path, state)
        return _result(run_dir, state_path, state, "最后一次外部动作状态不明确，已停止并要求人工对账。")
    authorization = _load_authorization(run_dir, state)
    pending_attempt = dict(state.get("pending_dispatch_attempt") or {})
    if pending_attempt:
        candidate_id = str(pending_attempt.get("candidate_id") or "")
        if not candidate_id:
            raise ValueError("中断运行中的 pending dispatch attempt 缺少 candidate_id。")
        card = _load_card(run_dir, candidate_id)
        verify_candidate_identity(card, authorization["candidate_identity_digests"][candidate_id])
        verify_candidate_review(card, authorization["candidate_review_digests"][candidate_id])
        if live in {"pending", "connected"}:
            record_contact_outcome(
                run_dir,
                account_profile_url=account["profile_url"],
                member_profile_url=card["selected_member"]["profile_url"],
                company_url=card["company"]["url"],
                candidate_id=candidate_id,
                outcome=live,
                source_post_url=card["post_url"],
                batch_digest=authorization["closed_batch_digest"],
                now=now,
            )
            outcome = "recovered_live_" + live
            _record_result(state, card, outcome, _aware(now), terminal=True)
            card["final_outcome"] = outcome
            persist_candidate_card(run_dir, card)
        state["pending_dispatch_attempt"] = None
    completed = {item["candidate_id"] for item in state.get("dispatch_results", []) if item.get("terminal")}
    remaining = [item for item in authorization["dispatch_candidate_ids"] if item not in completed]
    if not remaining:
        return _complete_dispatch(run_dir, state_path, state, _aware(now))
    timestamp = _aware(now).isoformat()
    remaining_cards = [_load_card(run_dir, candidate_id) for candidate_id in remaining]
    for card in remaining_cards:
        verify_candidate_identity(card, authorization["candidate_identity_digests"][card["candidate_id"]])
        verify_candidate_review(card, authorization["candidate_review_digests"][card["candidate_id"]])
    capacity = rolling_capacity(run_dir, account_profile_url=account["profile_url"], now=now)
    recovery = {
        "account": account,
        "remaining_candidate_ids": remaining,
        "remaining_candidates": remaining_cards,
        "candidate_identity_digests": {
            candidate_id: authorization["candidate_identity_digests"][candidate_id]
            for candidate_id in remaining
        },
        "candidate_review_digests": {
            candidate_id: authorization["candidate_review_digests"][candidate_id]
            for candidate_id in remaining
        },
        "last_candidate_live_state": live,
        "reconciled_pending_attempt_id": pending_attempt.get("attempt_id"),
        "note_mode": authorization["note_mode"],
        "note_text": authorization["note_text"],
        "note_digest": authorization.get("note_digest"),
        "interval_seconds": authorization["interval_seconds"],
        "next_dispatch_not_before": state.get("next_dispatch_not_before"),
        "rolling_capacity": capacity,
        "effective_remaining_count": min(len(remaining), capacity["remaining_capacity"]),
        "closed_batch_digest": authorization["closed_batch_digest"],
        "original_authorization_digest": authorization["authorization_digest"],
        "prepared_at": timestamp,
        "requires_fresh_authorization": True,
        "new_search_allowed": False,
    }
    recovery["recovery_digest"] = _digest(recovery)
    json_path = run_dir / "batch" / "dispatch-recovery-brief.json"
    markdown_path = run_dir / "batch" / "dispatch-recovery-brief.md"
    _write_json_atomic(json_path, recovery)
    markdown_path.write_text(_render_recovery_brief(recovery), encoding="utf-8")
    state["dispatch_recovery"] = {
        "recovery_digest": recovery["recovery_digest"],
        "remaining_candidate_ids": remaining,
        "prepared_at": timestamp,
    }
    state["status"] = "dispatch_reauthorization_required"
    state["phase"] = "awaiting_dispatch_reauthorization"
    state["updated_at"] = timestamp
    state.setdefault("files", {})["dispatch_recovery_brief"] = [str(markdown_path), str(json_path)]
    _append_history(state, timestamp)
    _write_json_atomic(state_path, state)
    return LinkedInSearchStepResult(
        str(run_dir),
        str(state_path),
        state["status"],
        state["phase"],
        (str(markdown_path), str(json_path), str(state_path)),
        _render_recovery_brief(recovery),
    )


def authorize_interruption_recovery(
    run_dir: Path,
    *,
    confirmed: bool,
    observed_member_name: str,
    observed_profile_url: str,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "awaiting_dispatch_reauthorization" or not confirmed:
        raise ValueError("必须在恢复简报上获得新的明确授权。")
    account = state.get("account_binding") or {}
    if observed_member_name.strip() != account.get("member_name") or normalize_linkedin_url(observed_profile_url) != account.get("profile_url"):
        raise ValueError("恢复授权时可见 LinkedIn 账号与绑定账号不一致。")
    paths = (state.get("files") or {}).get("dispatch_recovery_brief") or []
    if len(paths) != 2:
        raise ValueError("恢复简报文件缺失。")
    recovery = json.loads(Path(paths[1]).read_text(encoding="utf-8"))
    expected_digest = (state.get("dispatch_recovery") or {}).get("recovery_digest")
    actual_payload = {key: value for key, value in recovery.items() if key != "recovery_digest"}
    if not expected_digest or recovery.get("recovery_digest") != expected_digest or _digest(actual_payload) != expected_digest:
        raise ValueError("恢复简报摘要不一致，必须重新准备。")
    authorization = _load_authorization(run_dir, state)
    if recovery.get("original_authorization_digest") != authorization.get("authorization_digest"):
        raise ValueError("恢复简报与原发送授权不一致。")
    for candidate_id in recovery.get("remaining_candidate_ids") or []:
        verify_candidate_identity(
            _load_card(run_dir, candidate_id),
            recovery["candidate_identity_digests"][candidate_id],
        )
        verify_candidate_review(
            _load_card(run_dir, candidate_id),
            recovery["candidate_review_digests"][candidate_id],
        )
    capacity = rolling_capacity(run_dir, account_profile_url=account["profile_url"], now=now)
    if capacity["remaining_capacity"] < len(recovery.get("remaining_candidate_ids") or []):
        raise ValueError("恢复授权时滚动容量已不足以覆盖剩余批次，必须重新准备恢复简报。")
    current = _aware(now)
    timestamp = current.isoformat()
    next_not_before = recovery.get("next_dispatch_not_before")
    interval_still_active = bool(next_not_before) and current < _parse_datetime(str(next_not_before))
    state["status"] = "dispatch_interval_wait" if interval_still_active else "dispatch_batch_reauthorized"
    state["phase"] = "awaiting_dispatch_interval" if interval_still_active else "ready_to_dispatch"
    state["next_dispatch_not_before"] = next_not_before if interval_still_active else None
    state["updated_at"] = timestamp
    state["dispatch_recovery"]["reauthorized_at"] = timestamp
    state["dispatch_recovery"]["reauthorized_account_profile_url"] = account["profile_url"]
    _append_history(state, timestamp)
    _write_json_atomic(state_path, state)
    return _result(
        run_dir,
        state_path,
        state,
        (
            f"剩余封闭批次已重新授权；固定间隔仍有效，下一次不得早于 {next_not_before}。"
            if interval_still_active
            else "剩余封闭批次已重新授权，可以继续顺序发送。"
        ),
    )


def prepare_platform_restart_handoff(
    run_dir: Path,
    *,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "platform_stopped":
        raise ValueError("只有 Platform-Level Stop 运行可以生成新任务重启交接。")
    authorization = _load_authorization(run_dir, state)
    completed = {item["candidate_id"] for item in state.get("dispatch_results", []) if item.get("terminal")}
    remaining_ids = [item for item in authorization["dispatch_candidate_ids"] if item not in completed]
    cards = [_load_card(run_dir, item) for item in remaining_ids]
    timestamp = _aware(now).isoformat()
    payload = {
        "source_run_id": run_dir.name,
        "source_run_dir": str(run_dir),
        "keywords": list((state.get("confirmed_search_brief") or {}).get("keywords") or []),
        "account": state.get("account_binding"),
        "remaining_candidate_ids": remaining_ids,
        "remaining_candidates": cards,
        "created_at": timestamp,
        "requires_new_run": True,
        "requires_fresh_account_binding": True,
        "requires_fresh_batch_authorization": True,
        "automatic_resume_allowed": False,
    }
    path = run_dir / "batch" / "authorized-dispatch-restart-handoff.json"
    _write_json_atomic(path, payload)
    state.setdefault("files", {})["dispatch_restart_handoff"] = str(path)
    state["restart_handoff"] = {
        "remaining_candidate_ids": remaining_ids,
        "created_at": timestamp,
        "requires_new_run": True,
    }
    state["updated_at"] = timestamp
    _write_json_atomic(state_path, state)
    return LinkedInSearchStepResult(
        str(run_dir),
        str(state_path),
        state["status"],
        state["phase"],
        (str(path), str(state_path)),
        f"已保存 {len(remaining_ids)} 名未执行候选的重启交接。必须新建任务并重新绑定账号、对账和授权；不会自动恢复。",
    )


def create_platform_restart_run(
    source_run_dir: Path,
    *,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    source_run, source_state_path, source = _load_run(source_run_dir)
    if source.get("phase") != "platform_stopped":
        raise ValueError("只有 Platform-Level Stop 运行可以创建独立重启任务。")
    existing_restart = (source.get("restart_handoff") or {}).get("restart_run_dir")
    if existing_restart:
        raise ValueError(f"源运行已经创建过独立重启任务：{existing_restart}")
    handoff_path_value = (source.get("files") or {}).get("dispatch_restart_handoff")
    if not handoff_path_value:
        raise ValueError("源运行尚未生成 restart handoff。")
    handoff = json.loads(Path(handoff_path_value).read_text(encoding="utf-8"))
    candidate_ids = list(handoff.get("remaining_candidate_ids") or [])
    if not candidate_ids:
        raise ValueError("restart handoff 没有未执行候选。")
    current = _aware(now)
    first_keyword = str(((source.get("confirmed_search_brief") or {}).get("keywords") or ["keywords"])[0])
    slug = "".join(character if character.isalnum() or character in "-_" else "-" for character in first_keyword).strip("-") or "keywords"
    base = source_run.parent / f"{current.strftime('%Y%m%d_%H%M%S')}_{slug}-restart"
    run_dir = base
    suffix = 2
    while run_dir.exists():
        run_dir = source_run.parent / f"{base.name}_{suffix}"
        suffix += 1
    run_dir.mkdir(parents=True)
    (run_dir / "batch").mkdir()
    cards = []
    for value in handoff.get("remaining_candidates") or []:
        card = dict(value)
        card["approval"] = "pending_batch_review"
        card["note_decision"] = None
        card["final_outcome"] = None
        persist_candidate_card(run_dir, card)
        cards.append(card)
    timestamp = current.isoformat()
    requirements_path = run_dir / "requirements.md"
    state_path = run_dir / "workflow_state.json"
    change_log_path = run_dir / "change_log.md"
    state = {
        "workflow": "tuolin-linkedin-search",
        "schema_version": 2,
        "run_id": run_dir.name,
        "status": "restart_account_binding_required",
        "phase": "awaiting_browser_account_binding",
        "created_at": timestamp,
        "updated_at": timestamp,
        "request_text": f"Authorized Dispatch Restart from {source_run.name}",
        "account_binding": None,
        "confirmed_search_brief": source.get("confirmed_search_brief"),
        "candidate_ids": candidate_ids,
        "restart_source": {
            "run_id": source_run.name,
            "run_dir": str(source_run),
            "account_profile_url": (source.get("account_binding") or {}).get("profile_url"),
            "candidate_ids": candidate_ids,
            "handoff_path": str(handoff_path_value),
        },
        "files": {
            "requirements": str(requirements_path),
            "workflow_state": str(state_path),
            "change_log": str(change_log_path),
            "candidate_cards": [
                str(path)
                for candidate_id in candidate_ids
                for path in (run_dir / "candidates" / f"{candidate_id}.md", run_dir / "candidates" / f"{candidate_id}.json")
            ],
        },
        "blockers": [],
        "warnings": list(source.get("warnings") or []),
        "status_history": [{"status": "restart_account_binding_required", "phase": "awaiting_browser_account_binding", "at": timestamp}],
    }
    requirements_path.write_text(
        "\n".join(
            [
                "# LinkedIn Authorized Dispatch Restart",
                "",
                f"- 源运行：{source_run}",
                f"- 搜索关键词：{'、'.join((source.get('confirmed_search_brief') or {}).get('keywords') or [])}",
                f"- 保留候选：{len(candidate_ids)}",
                "- 必须重新绑定相同 LinkedIn 账号、审核候选并完成新的最终授权。",
                "- 不允许重新搜索、增加候选或自动找补。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _write_json_atomic(state_path, state)
    change_log_path.write_text(
        f"# LinkedIn 搜索任务变更记录\n\n- {timestamp}: 从 Platform-Level Stop 运行 {source_run.name} 创建独立重启任务。\n",
        encoding="utf-8",
    )
    source.setdefault("restart_handoff", {})["restart_run_dir"] = str(run_dir)
    source["restart_handoff"]["restart_created_at"] = timestamp
    source["updated_at"] = timestamp
    _write_json_atomic(source_state_path, source)
    return LinkedInSearchStepResult(
        str(run_dir),
        str(state_path),
        state["status"],
        state["phase"],
        (str(requirements_path), str(state_path), str(change_log_path)),
        f"已创建独立 Authorized Dispatch Restart：{run_dir}。保留 {len(candidate_ids)} 人；下一步必须重新绑定源账号并审核，不会重新搜索。",
    )


def _advance_after_success(run_dir: Path, state_path: Path, state: dict[str, Any], current: datetime, authorization: dict[str, Any]) -> LinkedInSearchStepResult:
    if _remaining_ids(state, authorization):
        interval = int(authorization["interval_seconds"])
        state["status"] = "dispatch_interval_wait"
        state["phase"] = "awaiting_dispatch_interval"
        state["last_dispatch_success_at"] = current.isoformat()
        state["next_dispatch_not_before"] = (current + timedelta(seconds=interval)).isoformat()
        message = f"邀请已成功发出并记账。下一次不得早于 {state['next_dispatch_not_before']}。"
    else:
        return _complete_dispatch(run_dir, state_path, state, current)
    return _persist_and_report(run_dir, state_path, state, current, message)


def _advance_after_non_send(run_dir: Path, state_path: Path, state: dict[str, Any], current: datetime, outcome: str) -> LinkedInSearchStepResult:
    authorization = _load_authorization(run_dir, state)
    if _remaining_ids(state, authorization):
        state["status"] = "dispatch_in_progress"
        state["phase"] = "ready_to_dispatch"
        state["next_dispatch_not_before"] = None
        return _persist_and_report(run_dir, state_path, state, current, f"候选结果已记录：{outcome}；可以继续下一名。")
    return _complete_dispatch(run_dir, state_path, state, current)


def _stop_for_account_change(run_dir: Path, state_path: Path, state: dict[str, Any], current: datetime, reason: str) -> LinkedInSearchStepResult:
    return _stop_batch(run_dir, state_path, state, current, "account_changed", reason)


def _stop_batch(
    run_dir: Path,
    state_path: Path,
    state: dict[str, Any],
    current: datetime,
    code: str,
    reason: str,
    *,
    ambiguous_candidate: str | None = None,
) -> LinkedInSearchStepResult:
    if ambiguous_candidate:
        card = _load_card(run_dir, ambiguous_candidate)
        try:
            record_contact_outcome(
                run_dir,
                account_profile_url=state["account_binding"]["profile_url"],
                member_profile_url=card["selected_member"]["profile_url"],
                company_url=card["company"]["url"],
                candidate_id=ambiguous_candidate,
                outcome="ambiguous",
                now=current,
            )
        except (OSError, ValueError) as exc:
            state["reconciliation"] = {
                "candidate_id": ambiguous_candidate,
                "reason": "ambiguous_state_ledger_write_failed",
                "error": str(exc),
            }
        _record_result(state, card, code, current, terminal=False, detail=reason)
    state["status"] = "platform_stopped" if code in PLATFORM_STOP_RESULTS else "dispatch_stopped"
    state["phase"] = "platform_stopped" if code in PLATFORM_STOP_RESULTS else "reconciliation_required"
    state["stop"] = {"code": code, "reason": reason, "stopped_at": current.isoformat(), "auto_resume": False}
    if code in PLATFORM_STOP_RESULTS:
        release_account_run_lock(run_dir, state["account_binding"]["profile_url"])
    return _persist_and_report(run_dir, state_path, state, current, reason + " 当前批次已停止，不会自动恢复。")


def _complete_dispatch(run_dir: Path, state_path: Path, state: dict[str, Any], current: datetime) -> LinkedInSearchStepResult:
    state["status"] = "dispatch_complete"
    state["phase"] = "completed"
    state["completed_at"] = current.isoformat()
    release_run_reservations(run_dir, state["account_binding"]["profile_url"])
    release_account_run_lock(run_dir, state["account_binding"]["profile_url"])
    return _persist_and_report(run_dir, state_path, state, current, "授权批次已经执行完毕。")


def _persist_and_report(run_dir: Path, state_path: Path, state: dict[str, Any], current: datetime, message: str) -> LinkedInSearchStepResult:
    state["updated_at"] = current.isoformat()
    _append_history(state, current.isoformat())
    report_path = _write_report(run_dir, state)
    state.setdefault("files", {})["dispatch_report"] = str(report_path)
    _write_json_atomic(state_path, state)
    _append_change(run_dir, current.isoformat(), message)
    return LinkedInSearchStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=(str(report_path), str(state_path)),
        message=message,
    )


def _write_report(run_dir: Path, state: dict[str, Any]) -> Path:
    authorization = _load_authorization(run_dir, state)
    results = list(state.get("dispatch_results") or [])
    observed_ids = {item["candidate_id"] for item in results}
    unexecuted = [item for item in authorization["dispatch_candidate_ids"] if item not in observed_ids]
    categories = {
        "succeeded": [item for item in results if item["outcome"] == "invitation_dispatch_success"],
        "skipped": [item for item in results if item["outcome"].startswith("skipped_")],
        "failed": [item for item in results if item["outcome"].startswith("failed_")],
        "ambiguous": [item for item in results if "ambiguous" in item["outcome"]],
        "unexecuted": unexecuted,
    }
    payload = {"status": state["status"], "phase": state["phase"], "categories": categories, "stop": state.get("stop")}
    path = run_dir / "batch" / "dispatch-report.json"
    _write_json_atomic(path, payload)
    return path


def _load_authorization(run_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    authorized = state.get("authorized_dispatch_batch")
    if not authorized:
        raise ValueError("运行没有有效的 Authorized Dispatch Batch。")
    path = Path(state["files"]["dispatch_authorization_brief"][1])
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("authorization_digest") != authorized.get("authorization_digest"):
        raise ValueError("授权摘要不一致，必须重新授权。")
    return payload


def _validate_interval_gate(state: dict[str, Any], current: datetime) -> None:
    value = state.get("next_dispatch_not_before")
    if not value:
        return
    threshold = datetime.fromisoformat(value)
    if threshold.tzinfo is None:
        threshold = threshold.astimezone()
    if current < threshold:
        raise ValueError(f"固定发送间隔尚未结束；下一次不得早于 {threshold.isoformat()}。")


def _remaining_ids(state: dict[str, Any], authorization: dict[str, Any]) -> list[str]:
    completed = {item["candidate_id"] for item in state.get("dispatch_results", []) if item.get("terminal")}
    return [item for item in authorization["dispatch_candidate_ids"] if item not in completed]


def _record_result(
    state: dict[str, Any],
    card: dict[str, Any],
    outcome: str,
    current: datetime,
    *,
    terminal: bool,
    detail: str = "",
) -> None:
    state.setdefault("dispatch_results", []).append(
        {
            "candidate_id": card["candidate_id"],
            "member_profile_url": card["selected_member"]["profile_url"],
            "outcome": outcome,
            "detail": detail,
            "occurred_at": current.isoformat(),
            "terminal": terminal,
        }
    )


def _load_card(run_dir: Path, candidate_id: str) -> dict[str, Any]:
    return json.loads((run_dir / "candidates" / f"{candidate_id}.json").read_text(encoding="utf-8"))


def _aware(now: datetime | None) -> datetime:
    value = now or datetime.now().astimezone()
    return value.astimezone() if value.tzinfo is None else value


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed.astimezone() if parsed.tzinfo is None else parsed


def _result(run_dir: Path, state_path: Path, state: dict[str, Any], message: str) -> LinkedInSearchStepResult:
    return LinkedInSearchStepResult(str(run_dir), str(state_path), state["status"], state["phase"], (str(state_path),), message)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _render_recovery_brief(recovery: dict[str, Any]) -> str:
    note = recovery.get("note_text") if recovery.get("note_mode") == "fixed_note" else "不使用留言"
    lines = [
        "# LinkedIn 发送中断恢复简报",
        "",
        f"- 账号：{recovery['account']['member_name']}（{recovery['account']['profile_url']}）",
        f"- 最后动作对账结果：{recovery['last_candidate_live_state']}",
        f"- 剩余候选：{len(recovery['remaining_candidate_ids'])} 人",
        f"- 固定间隔：{recovery['interval_seconds']} 秒",
        f"- 下一次最早发送时间：{recovery.get('next_dispatch_not_before') or '当前无等待门禁'}",
        f"- 当前滚动容量：{recovery['rolling_capacity']['remaining_capacity']}",
        f"- 留言：{note}",
        "- 不会重新搜索或找补，也不会新增候选。",
        "",
        "## 剩余候选",
        "",
    ]
    for index, card in enumerate(recovery["remaining_candidates"], start=1):
        member = card["selected_member"]
        lines.extend(
            [
                f"### {index}. {member['name']}",
                f"- LinkedIn：{member['profile_url']}",
                f"- 公司：{card['company']['name']}（{card['company']['url']}）",
                f"- 来源贴文：{card['post_url']}",
                f"- 入选理由：{card.get('selection_reason') or card.get('relevance_reason') or '未记录'}",
                "",
            ]
        )
    lines.extend(["请核对后明确确认，才能继续发送。", ""])
    return "\n".join(lines)

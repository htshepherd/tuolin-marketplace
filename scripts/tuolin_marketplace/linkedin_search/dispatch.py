from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .agent import LinkedInSearchStepResult
from .browser_contract import _append_change, _append_history, _load_run, _write_json_atomic, normalize_linkedin_url
from .ledger import pre_dispatch_eligibility, record_contact_outcome, release_account_run_lock, rolling_capacity


PLATFORM_STOP_RESULTS = {"platform_restriction", "security_checkpoint", "captcha", "logged_out"}
LOCAL_FAILURE_RESULTS = {"no_connect_button", "profile_unavailable", "no_dispatch_failure"}


@dataclass(frozen=True)
class InvitationDispatchObservation:
    account_member_name: str
    account_profile_url: str
    candidate_id: str
    candidate_profile_url: str
    live_connection_state_before: str
    standard_connect_available: bool
    add_note_available: bool
    result: str
    visible_confirmation: str = ""


def dispatch_next_candidate(
    run_dir: Path,
    observation: InvitationDispatchObservation,
    *,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") not in {"ready_to_dispatch", "awaiting_dispatch_interval"}:
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能执行连接邀请。")
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
    member = card["selected_member"]
    if normalize_linkedin_url(observation.candidate_profile_url) != member["profile_url"]:
        raise ValueError("浏览器中的候选 profile 与授权候选不一致。")

    capacity = rolling_capacity(run_dir, account_profile_url=account["profile_url"], now=current)
    if capacity["remaining_capacity"] <= 0:
        return _stop_batch(run_dir, state_path, state, current, "rolling_capacity_exhausted", "发送前重新计算发现滚动容量为零。")
    live_state = observation.live_connection_state_before.casefold()
    if live_state in {"pending", "connected"}:
        outcome = "skipped_live_" + live_state
        record_contact_outcome(
            run_dir,
            account_profile_url=account["profile_url"],
            member_profile_url=member["profile_url"],
            company_url=card["company"]["url"],
            candidate_id=expected_id,
            outcome=live_state,
            now=current,
        )
        _record_result(state, card, outcome, current, terminal=True)
        card["final_outcome"] = outcome
        _persist_card(run_dir, card)
        return _advance_after_non_send(run_dir, state_path, state, current, outcome)
    if live_state == "ambiguous":
        return _stop_batch(run_dir, state_path, state, current, "ambiguous_pre_send_state", "发送前连接状态不明确。", ambiguous_candidate=expected_id)
    ledger_check = pre_dispatch_eligibility(
        run_dir,
        account_profile_url=account["profile_url"],
        member_profile_url=member["profile_url"],
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
    if not observation.standard_connect_available:
        _record_result(state, card, "failed_no_connect_button", current, terminal=True)
        record_contact_outcome(
            run_dir,
            account_profile_url=account["profile_url"],
            member_profile_url=member["profile_url"],
            company_url=card["company"]["url"],
            candidate_id=expected_id,
            outcome="failed_no_dispatch",
            now=current,
        )
        card["final_outcome"] = "failed_no_connect_button"
        _persist_card(run_dir, card)
        return _advance_after_non_send(run_dir, state_path, state, current, "failed_no_connect_button")
    if authorization["note_mode"] == "fixed_note" and not observation.add_note_available:
        state["status"] = "note_unavailable_reauthorization_required"
        state["phase"] = "awaiting_note_unavailable_decision"
        state["note_unavailable_candidate_id"] = expected_id
        state["updated_at"] = current.isoformat()
        _append_history(state, current.isoformat())
        _write_json_atomic(state_path, state)
        _append_change(run_dir, current.isoformat(), "Add a note 不可用；暂停并要求用户选择无留言重新授权或结束。")
        return _result(run_dir, state_path, state, "Add a note 当前不可用。不得静默移除留言；请选择改为无留言并重新确认整个发送简报，或结束任务。")

    result = observation.result.casefold()
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
        _persist_card(run_dir, card)
        return _advance_after_success(run_dir, state_path, state, current, authorization)
    if result in LOCAL_FAILURE_RESULTS:
        record_contact_outcome(
            run_dir,
            account_profile_url=account["profile_url"],
            member_profile_url=member["profile_url"],
            company_url=card["company"]["url"],
            candidate_id=expected_id,
            outcome="failed_no_dispatch",
            now=current,
        )
        outcome = "failed_" + result
        _record_result(state, card, outcome, current, terminal=True)
        card["final_outcome"] = outcome
        _persist_card(run_dir, card)
        return _advance_after_non_send(run_dir, state_path, state, current, outcome)
    if result in PLATFORM_STOP_RESULTS:
        return _stop_batch(run_dir, state_path, state, current, result, f"检测到平台级停止：{result}。")
    return _stop_batch(run_dir, state_path, state, current, "ambiguous_dispatch", "邀请结果不明确，禁止重试。", ambiguous_candidate=expected_id)


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
    if state.get("phase") not in {"ready_to_dispatch", "awaiting_dispatch_interval", "dispatch_interrupted"}:
        raise ValueError(f"当前阶段 {state.get('phase')!r} 不支持发送中断恢复。")
    account = state.get("account_binding") or {}
    if observed_member_name.strip() != account.get("member_name") or normalize_linkedin_url(observed_profile_url) != account.get("profile_url"):
        raise ValueError("恢复时可见 LinkedIn 账号与绑定账号不一致。")
    live = last_candidate_live_state.casefold()
    if live == "ambiguous":
        state["status"] = "reconciliation_required"
        state["phase"] = "reconciliation_required"
        state["reconciliation"] = {"reason": "last_action_ambiguous_during_recovery"}
        state["updated_at"] = _aware(now).isoformat()
        _write_json_atomic(state_path, state)
        return _result(run_dir, state_path, state, "最后一次外部动作状态不明确，已停止并要求人工对账。")
    authorization = _load_authorization(run_dir, state)
    completed = {item["candidate_id"] for item in state.get("dispatch_results", []) if item.get("terminal")}
    remaining = [item for item in authorization["dispatch_candidate_ids"] if item not in completed]
    timestamp = _aware(now).isoformat()
    recovery = {
        "account": account,
        "remaining_candidate_ids": remaining,
        "last_candidate_live_state": live,
        "prepared_at": timestamp,
        "requires_fresh_authorization": True,
        "new_search_allowed": False,
    }
    path = run_dir / "batch" / "dispatch-recovery-brief.json"
    _write_json_atomic(path, recovery)
    state["dispatch_recovery"] = recovery
    state["status"] = "dispatch_reauthorization_required"
    state["phase"] = "awaiting_dispatch_reauthorization"
    state["updated_at"] = timestamp
    state.setdefault("files", {})["dispatch_recovery_brief"] = str(path)
    _append_history(state, timestamp)
    _write_json_atomic(state_path, state)
    return _result(run_dir, state_path, state, f"已重新验证账号并对账最后动作；剩余 {len(remaining)} 人。必须重新确认后才能继续，不会重新搜索或找补。")


def authorize_interruption_recovery(
    run_dir: Path,
    *,
    confirmed: bool,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "awaiting_dispatch_reauthorization" or not confirmed:
        raise ValueError("必须在恢复简报上获得新的明确授权。")
    timestamp = _aware(now).isoformat()
    state["status"] = "dispatch_batch_reauthorized"
    state["phase"] = "ready_to_dispatch"
    state["next_dispatch_not_before"] = None
    state["updated_at"] = timestamp
    state["dispatch_recovery"]["reauthorized_at"] = timestamp
    _append_history(state, timestamp)
    _write_json_atomic(state_path, state)
    return _result(run_dir, state_path, state, "剩余封闭批次已重新授权，可以继续顺序发送。")


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
        "product": state.get("product"),
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


def _persist_card(run_dir: Path, card: dict[str, Any]) -> None:
    _write_json_atomic(run_dir / "candidates" / f"{card['candidate_id']}.json", card)
    member = card["selected_member"]
    markdown = "\n".join(
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
            f"- 留言决策：{card['note_decision']}",
            f"- 最终结果：{card['final_outcome']}",
            "",
        ]
    )
    (run_dir / "candidates" / f"{card['candidate_id']}.md").write_text(markdown, encoding="utf-8")


def _aware(now: datetime | None) -> datetime:
    value = now or datetime.now().astimezone()
    return value.astimezone() if value.tzinfo is None else value


def _result(run_dir: Path, state_path: Path, state: dict[str, Any], message: str) -> LinkedInSearchStepResult:
    return LinkedInSearchStepResult(str(run_dir), str(state_path), state["status"], state["phase"], (str(state_path),), message)

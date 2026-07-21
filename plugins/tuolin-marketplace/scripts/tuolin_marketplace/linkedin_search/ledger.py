from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .browser_contract import normalize_linkedin_url


BLOCKING_CONTACT_STATES = {"reserved", "pending", "sent", "connected", "ambiguous"}


def acquire_account_run_lock(run_dir: Path, account_profile_url: str, *, now: datetime | None = None) -> Path:
    run_dir = run_dir.expanduser().resolve()
    account_url = normalize_linkedin_url(account_profile_url)
    lock_path = _shared_dir(run_dir) / "active-run-locks" / f"{_key(account_url)}.json"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        existing = _read_json(lock_path)
        if existing.get("run_id") != run_dir.name:
            raise ValueError(
                f"账号已有活动 LinkedIn 搜索运行：{existing.get('run_id')}。"
                "必须先完成对账，不能并行启动同账号任务。"
            )
        return lock_path
    _write_json_atomic(
        lock_path,
        {
            "account_profile_url": account_url,
            "run_id": run_dir.name,
            "run_dir": str(run_dir),
            "acquired_at": _iso(now),
            "status": "active",
        },
    )
    return lock_path


def release_account_run_lock(run_dir: Path, account_profile_url: str) -> None:
    run_dir = run_dir.expanduser().resolve()
    account_url = normalize_linkedin_url(account_profile_url)
    lock_path = _shared_dir(run_dir) / "active-run-locks" / f"{_key(account_url)}.json"
    if not lock_path.exists():
        return
    existing = _read_json(lock_path)
    if existing.get("run_id") != run_dir.name:
        raise ValueError("不能释放其他运行持有的账号锁。")
    lock_path.unlink()


def reserve_candidate(
    run_dir: Path,
    *,
    account_profile_url: str,
    member_profile_url: str,
    company_url: str,
    candidate_id: str,
    live_state: str = "none",
    now: datetime | None = None,
) -> dict[str, Any]:
    run_dir = run_dir.expanduser().resolve()
    account_url = normalize_linkedin_url(account_profile_url)
    member_url = normalize_linkedin_url(member_profile_url)
    normalized_company = normalize_linkedin_url(company_url) if company_url else ""
    live = live_state.strip().casefold()
    if live not in {"none", "pending", "connected", "ambiguous"}:
        raise ValueError(f"未知 LinkedIn 实时连接状态：{live_state}")
    if live != "none":
        return {"eligible": False, "reason": f"live_{live}", "state": live}
    ledger_path = _ledger_path(run_dir)
    ledger = _load_ledger(ledger_path)
    account = ledger.setdefault("accounts", {}).setdefault(
        account_url,
        {"contacts": {}, "companies": {}, "dispatch_successes": []},
    )
    existing = account["contacts"].get(member_url)
    if existing and existing.get("state") in BLOCKING_CONTACT_STATES:
        return {"eligible": False, "reason": f"ledger_{existing['state']}", "state": existing["state"]}
    company_existing = account["companies"].get(normalized_company) if normalized_company else None
    if company_existing and company_existing.get("state") in {"sent", "connected", "pending"}:
        return {"eligible": False, "reason": "company_already_contacted", "state": company_existing["state"]}
    account["contacts"][member_url] = {
        "candidate_id": candidate_id,
        "company_url": normalized_company,
        "state": "reserved",
        "run_id": run_dir.name,
        "updated_at": _iso(now),
    }
    _write_json_atomic(ledger_path, ledger)
    return {"eligible": True, "reason": "reserved", "state": "reserved", "ledger_path": str(ledger_path)}


def pre_dispatch_eligibility(
    run_dir: Path,
    *,
    account_profile_url: str,
    member_profile_url: str,
    candidate_id: str,
) -> dict[str, Any]:
    run_dir = Path(run_dir).expanduser().resolve()
    account_url = normalize_linkedin_url(account_profile_url)
    member_url = normalize_linkedin_url(member_profile_url)
    ledger = _load_ledger(_ledger_path(run_dir))
    contact = ledger.get("accounts", {}).get(account_url, {}).get("contacts", {}).get(member_url)
    if not contact:
        return {"eligible": False, "reason": "missing_reservation"}
    if contact.get("candidate_id") != candidate_id or contact.get("run_id") != run_dir.name:
        return {"eligible": False, "reason": "reserved_by_other_candidate_or_run"}
    if contact.get("state") == "reserved":
        return {"eligible": True, "reason": "reserved_for_current_run"}
    if contact.get("state") == "failed_no_dispatch":
        return {"eligible": True, "reason": "proven_no_dispatch_retry"}
    return {"eligible": False, "reason": f"ledger_{contact.get('state')}"}


def release_candidate_reservation(
    run_dir: Path,
    *,
    account_profile_url: str,
    member_profile_url: str,
    candidate_id: str,
) -> None:
    ledger_path = _ledger_path(run_dir)
    ledger = _load_ledger(ledger_path)
    account_url = normalize_linkedin_url(account_profile_url)
    member_url = normalize_linkedin_url(member_profile_url)
    contact = ledger.get("accounts", {}).get(account_url, {}).get("contacts", {}).get(member_url)
    if not contact:
        return
    if contact.get("candidate_id") != candidate_id or contact.get("run_id") != Path(run_dir).resolve().name:
        raise ValueError("不能释放其他候选或其他运行的联系人 reservation。")
    if contact.get("state") != "reserved":
        raise ValueError("只有 reserved 联系人可以在候选审核阶段释放。")
    del ledger["accounts"][account_url]["contacts"][member_url]
    _write_json_atomic(ledger_path, ledger)


def rolling_capacity(
    run_dir: Path,
    *,
    account_profile_url: str,
    now: datetime | None = None,
    window_hours: int = 168,
    success_limit: int = 100,
) -> dict[str, int]:
    current = now or datetime.now().astimezone()
    if current.tzinfo is None:
        current = current.astimezone()
    cutoff = current - timedelta(hours=window_hours)
    ledger = _load_ledger(_ledger_path(run_dir))
    account_url = normalize_linkedin_url(account_profile_url)
    successes = ledger.get("accounts", {}).get(account_url, {}).get("dispatch_successes", [])
    count = 0
    for item in successes:
        try:
            occurred = datetime.fromisoformat(str(item["occurred_at"]))
        except (KeyError, TypeError, ValueError):
            continue
        if occurred.tzinfo is None:
            occurred = occurred.astimezone()
        if occurred >= cutoff:
            count += 1
    return {"recorded_successes": count, "success_limit": success_limit, "remaining_capacity": max(0, success_limit - count)}


def record_contact_outcome(
    run_dir: Path,
    *,
    account_profile_url: str,
    member_profile_url: str,
    company_url: str,
    candidate_id: str,
    outcome: str,
    now: datetime | None = None,
) -> Path:
    allowed = {"sent", "pending", "connected", "ambiguous", "failed_no_dispatch"}
    if outcome not in allowed:
        raise ValueError(f"不支持的联系人账本结果：{outcome}")
    run_dir = Path(run_dir).expanduser().resolve()
    account_url = normalize_linkedin_url(account_profile_url)
    member_url = normalize_linkedin_url(member_profile_url)
    normalized_company = normalize_linkedin_url(company_url) if company_url else ""
    ledger_path_value = _ledger_path(run_dir)
    ledger = _load_ledger(ledger_path_value)
    account = ledger.setdefault("accounts", {}).setdefault(
        account_url,
        {"contacts": {}, "companies": {}, "dispatch_successes": []},
    )
    contact = account["contacts"].get(member_url)
    if not contact or contact.get("candidate_id") != candidate_id or contact.get("run_id") != run_dir.name:
        raise ValueError("联系人没有属于当前运行的有效 reservation，不能记录发送结果。")
    if contact.get("state") not in {"reserved", "failed_no_dispatch"}:
        raise ValueError(f"联系人当前账本状态 {contact.get('state')!r} 不允许写入发送结果。")
    occurred_at = _iso(now)
    contact.update({"state": outcome, "updated_at": occurred_at})
    if normalized_company and outcome in {"sent", "pending", "connected"}:
        account["companies"][normalized_company] = {
            "state": outcome,
            "candidate_id": candidate_id,
            "member_profile_url": member_url,
            "updated_at": occurred_at,
        }
    if outcome == "sent":
        account["dispatch_successes"].append(
            {
                "candidate_id": candidate_id,
                "member_profile_url": member_url,
                "company_url": normalized_company,
                "occurred_at": occurred_at,
                "run_id": run_dir.name,
            }
        )
    _write_json_atomic(ledger_path_value, ledger)
    return ledger_path_value


def ledger_path(run_dir: Path) -> Path:
    return _ledger_path(run_dir)


def _shared_dir(run_dir: Path) -> Path:
    path = Path(run_dir).expanduser().resolve().parent / "shared"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ledger_path(run_dir: Path) -> Path:
    return _shared_dir(run_dir) / "prospecting-contact-ledger.json"


def _load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "accounts": {}}
    value = _read_json(path)
    if value.get("schema_version") != 1 or not isinstance(value.get("accounts"), dict):
        raise ValueError("Prospecting Contact Ledger 格式无效。")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON 顶层必须是对象：{path}")
    return value


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _iso(now: datetime | None) -> str:
    value = now or datetime.now().astimezone()
    if value.tzinfo is None:
        value = value.astimezone()
    return value.isoformat()

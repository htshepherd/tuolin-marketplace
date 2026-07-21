from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .browser_contract import normalize_linkedin_url


BLOCKING_CONTACT_STATES = {"reserved", "pending", "sent", "connected", "ambiguous"}
BLOCKING_COMPANY_STATES = BLOCKING_CONTACT_STATES
BLOCKING_POST_STATES = BLOCKING_CONTACT_STATES


def acquire_account_run_lock(run_dir: Path, account_profile_url: str, *, now: datetime | None = None) -> Path:
    run_dir = run_dir.expanduser().resolve()
    account_url = normalize_linkedin_url(account_profile_url)
    lock_path = _shared_dir(run_dir) / "active-run-locks" / f"{_key(account_url)}.json"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "account_profile_url": account_url,
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "acquired_at": _iso(now),
        "status": "active",
    }
    try:
        descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        existing = _read_json(lock_path)
        if existing.get("run_id") != run_dir.name:
            raise ValueError(
                f"账号已有活动 LinkedIn 搜索运行：{existing.get('run_id')}。"
                "必须先完成对账，不能并行启动同账号任务。"
            )
        return lock_path
    try:
        os.write(descriptor, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
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
    source_post_url: str = "",
    candidate_id: str,
    live_state: str = "none",
    now: datetime | None = None,
) -> dict[str, Any]:
    run_dir = run_dir.expanduser().resolve()
    account_url = normalize_linkedin_url(account_profile_url)
    member_url = normalize_linkedin_url(member_profile_url)
    normalized_company = normalize_linkedin_url(company_url) if company_url else ""
    normalized_post = normalize_linkedin_url(source_post_url) if source_post_url else ""
    live = live_state.strip().casefold()
    if live not in {"none", "pending", "connected", "ambiguous"}:
        raise ValueError(f"未知 LinkedIn 实时连接状态：{live_state}")
    if live != "none":
        return {"eligible": False, "reason": f"live_{live}", "state": live}
    ledger_path = _ledger_path(run_dir)
    with _ledger_write_lock(ledger_path):
        ledger = _load_ledger(ledger_path)
        account = _ensure_account(ledger, account_url)
        existing = account["contacts"].get(member_url)
        if existing and existing.get("state") in BLOCKING_CONTACT_STATES:
            return {"eligible": False, "reason": f"ledger_{existing['state']}", "state": existing["state"]}
        company_existing = account["companies"].get(normalized_company) if normalized_company else None
        if company_existing and company_existing.get("state") in BLOCKING_COMPANY_STATES:
            return {"eligible": False, "reason": "company_already_reserved_or_contacted", "state": company_existing["state"]}
        post_existing = account["posts"].get(normalized_post) if normalized_post else None
        if post_existing and post_existing.get("state") in BLOCKING_POST_STATES:
            return {"eligible": False, "reason": "source_post_already_reserved_or_used", "state": post_existing["state"]}
        record = {
            "candidate_id": candidate_id,
            "company_url": normalized_company,
            "source_post_url": normalized_post,
            "state": "reserved",
            "run_id": run_dir.name,
            "updated_at": _iso(now),
        }
        account["contacts"][member_url] = record
        if normalized_company:
            account["companies"][normalized_company] = {
                "candidate_id": candidate_id,
                "member_profile_url": member_url,
                "state": "reserved",
                "run_id": run_dir.name,
                "updated_at": record["updated_at"],
            }
        if normalized_post:
            account["posts"][normalized_post] = {
                "candidate_id": candidate_id,
                "member_profile_url": member_url,
                "state": "reserved",
                "run_id": run_dir.name,
                "updated_at": record["updated_at"],
            }
        _write_json_atomic(ledger_path, ledger)
    return {"eligible": True, "reason": "reserved", "state": "reserved", "ledger_path": str(ledger_path)}


def pre_dispatch_eligibility(
    run_dir: Path,
    *,
    account_profile_url: str,
    member_profile_url: str,
    company_url: str,
    source_post_url: str,
    candidate_id: str,
) -> dict[str, Any]:
    run_dir = Path(run_dir).expanduser().resolve()
    account_url = normalize_linkedin_url(account_profile_url)
    member_url = normalize_linkedin_url(member_profile_url)
    ledger = _load_ledger(_ledger_path(run_dir))
    account = ledger.get("accounts", {}).get(account_url, {})
    contact = account.get("contacts", {}).get(member_url)
    if not contact:
        return {"eligible": False, "reason": "missing_reservation"}
    if contact.get("candidate_id") != candidate_id or contact.get("run_id") != run_dir.name:
        return {"eligible": False, "reason": "reserved_by_other_candidate_or_run"}
    if contact.get("state") == "reserved":
        company_key = normalize_linkedin_url(company_url)
        post_key = normalize_linkedin_url(source_post_url)
        for label, record in (
            ("company", account.get("companies", {}).get(company_key)),
            ("source_post", account.get("posts", {}).get(post_key)),
        ):
            if not record:
                return {"eligible": False, "reason": f"missing_{label}_reservation"}
            if record.get("candidate_id") != candidate_id or record.get("run_id") != run_dir.name:
                return {"eligible": False, "reason": f"{label}_reserved_by_other_candidate_or_run"}
            if record.get("state") != "reserved":
                return {"eligible": False, "reason": f"{label}_ledger_{record.get('state')}"}
        return {"eligible": True, "reason": "contact_company_post_reserved_for_current_run"}
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
    with _ledger_write_lock(ledger_path):
        ledger = _load_ledger(ledger_path)
        account_url = normalize_linkedin_url(account_profile_url)
        member_url = normalize_linkedin_url(member_profile_url)
        account = ledger.get("accounts", {}).get(account_url, {})
        contact = account.get("contacts", {}).get(member_url)
        if not contact:
            return
        if contact.get("candidate_id") != candidate_id or contact.get("run_id") != Path(run_dir).resolve().name:
            raise ValueError("不能释放其他候选或其他运行的联系人 reservation。")
        if contact.get("state") != "reserved":
            raise ValueError("只有 reserved 联系人可以在候选审核阶段释放。")
        del account["contacts"][member_url]
        _remove_matching_reservation(account.get("companies", {}), contact.get("company_url"), candidate_id, Path(run_dir).resolve().name)
        _remove_matching_reservation(account.get("posts", {}), contact.get("source_post_url"), candidate_id, Path(run_dir).resolve().name)
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
    source_post_url: str = "",
    batch_digest: str = "",
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
    with _ledger_write_lock(ledger_path_value):
        ledger = _load_ledger(ledger_path_value)
        account = _ensure_account(ledger, account_url)
        contact = account["contacts"].get(member_url)
        if not contact or contact.get("candidate_id") != candidate_id or contact.get("run_id") != run_dir.name:
            raise ValueError("联系人没有属于当前运行的有效 reservation，不能记录发送结果。")
        if contact.get("state") not in {"reserved", "failed_no_dispatch"}:
            raise ValueError(f"联系人当前账本状态 {contact.get('state')!r} 不允许写入发送结果。")
        normalized_post = normalize_linkedin_url(source_post_url) if source_post_url else str(contact.get("source_post_url") or "")
        occurred_at = _iso(now)
        contact.update({"state": outcome, "updated_at": occurred_at, "source_post_url": normalized_post})
        if outcome == "failed_no_dispatch":
            _remove_matching_reservation(account["companies"], normalized_company, candidate_id, run_dir.name)
            _remove_matching_reservation(account["posts"], normalized_post, candidate_id, run_dir.name)
        else:
            if normalized_company:
                account["companies"][normalized_company] = {
                    "state": outcome,
                    "candidate_id": candidate_id,
                    "member_profile_url": member_url,
                    "run_id": run_dir.name,
                    "updated_at": occurred_at,
                }
            if normalized_post:
                account["posts"][normalized_post] = {
                    "state": outcome,
                    "candidate_id": candidate_id,
                    "member_profile_url": member_url,
                    "run_id": run_dir.name,
                    "updated_at": occurred_at,
                }
        if outcome == "sent":
            account["dispatch_successes"].append(
                {
                    "account_profile_url": account_url,
                    "candidate_id": candidate_id,
                    "member_profile_url": member_url,
                    "company_url": normalized_company,
                    "source_post_url": normalized_post,
                    "batch_digest": batch_digest,
                    "result": "sent",
                    "occurred_at": occurred_at,
                    "run_id": run_dir.name,
                }
            )
        _write_json_atomic(ledger_path_value, ledger)
    return ledger_path_value


def release_run_reservations(run_dir: Path, account_profile_url: str) -> int:
    run_dir = Path(run_dir).expanduser().resolve()
    account_url = normalize_linkedin_url(account_profile_url)
    ledger_path_value = _ledger_path(run_dir)
    released = 0
    with _ledger_write_lock(ledger_path_value):
        ledger = _load_ledger(ledger_path_value)
        account = ledger.get("accounts", {}).get(account_url)
        if not account:
            return 0
        for member_url, contact in list(account.get("contacts", {}).items()):
            if contact.get("run_id") != run_dir.name or contact.get("state") != "reserved":
                continue
            del account["contacts"][member_url]
            _remove_matching_reservation(account.get("companies", {}), contact.get("company_url"), contact.get("candidate_id"), run_dir.name)
            _remove_matching_reservation(account.get("posts", {}), contact.get("source_post_url"), contact.get("candidate_id"), run_dir.name)
            released += 1
        _write_json_atomic(ledger_path_value, ledger)
    return released


def transfer_run_reservations(
    source_run_dir: Path,
    target_run_dir: Path,
    account_profile_url: str,
    candidate_ids: list[str],
) -> int:
    source_run = Path(source_run_dir).expanduser().resolve()
    target_run = Path(target_run_dir).expanduser().resolve()
    if source_run.parent != target_run.parent:
        raise ValueError("重启运行必须位于同一个 LinkedIn 搜索运行根目录。")
    account_url = normalize_linkedin_url(account_profile_url)
    ledger_path_value = _ledger_path(source_run)
    wanted = set(candidate_ids)
    transferred = 0
    with _ledger_write_lock(ledger_path_value):
        ledger = _load_ledger(ledger_path_value)
        account = ledger.get("accounts", {}).get(account_url)
        if not account:
            raise ValueError("共享账本中没有可转移的账号记录。")
        contacts = [item for item in account.get("contacts", {}).values() if item.get("candidate_id") in wanted]
        if len(contacts) != len(wanted):
            raise ValueError("重启候选 reservation 不完整，不能创建新任务。")
        for contact in contacts:
            if contact.get("run_id") not in {source_run.name, target_run.name} or contact.get("state") != "reserved":
                raise ValueError("只有源运行或当前重启运行持有的 reserved 候选可以完成转移。")
        timestamp = _iso(None)
        for contact in contacts:
            if contact.get("run_id") == source_run.name:
                contact.update({"run_id": target_run.name, "updated_at": timestamp})
                transferred += 1
            for collection_name, key_name in (("companies", "company_url"), ("posts", "source_post_url")):
                key = contact.get(key_name)
                record = account.get(collection_name, {}).get(key) if key else None
                if record and record.get("candidate_id") == contact.get("candidate_id"):
                    record.update({"run_id": target_run.name, "updated_at": timestamp})
        _write_json_atomic(ledger_path_value, ledger)
    return transferred


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


def _ensure_account(ledger: dict[str, Any], account_url: str) -> dict[str, Any]:
    account = ledger.setdefault("accounts", {}).setdefault(account_url, {})
    account.setdefault("contacts", {})
    account.setdefault("companies", {})
    account.setdefault("posts", {})
    account.setdefault("dispatch_successes", [])
    return account


def _remove_matching_reservation(
    collection: dict[str, Any],
    key: str | None,
    candidate_id: str | None,
    run_id: str,
) -> None:
    if not key:
        return
    record = collection.get(key)
    if record and record.get("candidate_id") == candidate_id and record.get("run_id") == run_id and record.get("state") == "reserved":
        del collection[key]


@contextmanager
def _ledger_write_lock(path: Path, *, timeout_seconds: float = 5.0):
    lock_dir = path.with_suffix(path.suffix + ".lock")
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            lock_dir.mkdir(parents=True)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise ValueError(
                    f"共享账本写锁已被占用：{lock_dir}。不得盲目删除；请先确认持有写锁的任务状态。"
                )
            time.sleep(0.05)
    try:
        (lock_dir / "owner.json").write_text(
            json.dumps({"pid": os.getpid(), "acquired_at": _iso(None)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        yield
    finally:
        owner = lock_dir / "owner.json"
        if owner.exists():
            owner.unlink()
        lock_dir.rmdir()


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

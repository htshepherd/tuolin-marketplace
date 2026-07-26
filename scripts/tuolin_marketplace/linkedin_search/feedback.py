from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .browser_contract import normalize_linkedin_url
from .workbook import read_all_contacts


def capture_workbook_feedback(run_dir: Path, account_profile_url: str, *, now: datetime | None = None) -> dict[str, Any]:
    account = normalize_linkedin_url(account_profile_url)
    path = _feedback_path(run_dir, account)
    store = _read_store(path, account)
    timestamp = _iso(now)
    existing = {item["feedback_id"] for item in store["feedback"]}
    added: list[str] = []
    for contact in read_all_contacts(run_dir, account):
        decision = str(contact.get("老板判断") or "待定")
        note = str(contact.get("老板备注") or "").strip()
        seed = f"{contact.get('联系人ID')}|{decision}|{note}"
        feedback_id = "feedback_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]
        if feedback_id in existing:
            continue
        store["feedback"].append(
            {
                "feedback_id": feedback_id,
                "contact_id": contact.get("联系人ID"),
                "profile_url": contact.get("LinkedIn主页"),
                "company": contact.get("公司"),
                "decision": decision,
                "boss_note": note,
                "evidence_strength": "explicit_boss_note" if note else "weak_decision_inference",
                "captured_at": timestamp,
            }
        )
        added.append(feedback_id)
    store["updated_at"] = timestamp
    _write_json_atomic(path, store)
    return {"feedback_path": str(path), "added_feedback_ids": added, "total": len(store["feedback"])}


def relevant_feedback(run_dir: Path, account_profile_url: str, *, company_name: str = "") -> list[dict[str, Any]]:
    account = normalize_linkedin_url(account_profile_url)
    store = _read_store(_feedback_path(run_dir, account), account)
    company = company_name.strip().casefold()
    if not company:
        return []
    return [item for item in store["feedback"] if str(item.get("company") or "").strip().casefold() == company][-5:]


def propose_screening_rule(
    run_dir: Path,
    account_profile_url: str,
    *,
    wording: str,
    scope: str,
    supporting_feedback_ids: list[str],
    conflicting_feedback_ids: list[str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not wording.strip() or not scope.strip() or not supporting_feedback_ids:
        raise ValueError("规则提案必须包含措辞、范围和至少一个支持反馈。")
    account = normalize_linkedin_url(account_profile_url)
    path = _feedback_path(run_dir, account)
    store = _read_store(path, account)
    known = {item["feedback_id"] for item in store["feedback"]}
    referenced = set(supporting_feedback_ids) | set(conflicting_feedback_ids or [])
    if not referenced.issubset(known):
        raise ValueError("规则提案引用了不存在的老板反馈。")
    timestamp = _iso(now)
    rule_id = "rule_" + hashlib.sha256(f"{wording}|{scope}|{timestamp}".encode("utf-8")).hexdigest()[:20]
    proposal = {
        "rule_id": rule_id,
        "version": 1,
        "wording": wording.strip(),
        "scope": scope.strip(),
        "supporting_feedback_ids": list(supporting_feedback_ids),
        "conflicting_feedback_ids": list(conflicting_feedback_ids or []),
        "status": "proposed_not_active",
        "proposed_at": timestamp,
    }
    store["rules"].append(proposal)
    store["updated_at"] = timestamp
    _write_json_atomic(path, store)
    return proposal


def confirm_screening_rule(
    run_dir: Path,
    account_profile_url: str,
    *,
    rule_id: str,
    confirmed: bool,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not confirmed:
        raise ValueError("只有老板明确确认后筛选规则才能激活。")
    account = normalize_linkedin_url(account_profile_url)
    path = _feedback_path(run_dir, account)
    store = _read_store(path, account)
    rule = next((item for item in store["rules"] if item.get("rule_id") == rule_id), None)
    if rule is None:
        raise ValueError("找不到待确认的筛选规则提案。")
    timestamp = _iso(now)
    rule["status"] = "confirmed_active"
    rule["confirmed_at"] = timestamp
    store["updated_at"] = timestamp
    _write_json_atomic(path, store)
    return dict(rule)


def _feedback_path(run_dir: Path, account_profile_url: str) -> Path:
    key = hashlib.sha256(account_profile_url.encode("utf-8")).hexdigest()[:20]
    path = Path(run_dir).expanduser().resolve().parent / "shared" / "prospect-feedback" / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _read_store(path: Path, account: str) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "account_profile_url": account, "feedback": [], "rules": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"老板反馈记录无法读取：{path}：{exc}") from exc
    if value.get("schema_version") != 1 or value.get("account_profile_url") != account:
        raise ValueError("老板反馈记录账号或 schema 不匹配。")
    value.setdefault("feedback", [])
    value.setdefault("rules", [])
    return value


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _iso(now: datetime | None) -> str:
    value = now or datetime.now().astimezone()
    if value.tzinfo is None:
        value = value.astimezone()
    return value.isoformat()

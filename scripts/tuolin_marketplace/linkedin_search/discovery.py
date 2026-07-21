from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .agent import LinkedInSearchStepResult
from .browser_contract import _append_change, _append_history, _load_run, _timestamp, _write_json_atomic, normalize_linkedin_url
from .cards import persist_candidate_card, render_candidate_card
from .ledger import reserve_candidate


@dataclass(frozen=True)
class LinkedInPostObservation:
    keyword: str
    post_url: str
    post_text: str
    author_name: str
    author_type: str
    author_profile_url: str
    company_name: str
    company_url: str


@dataclass(frozen=True)
class IndividualCandidateObservation:
    member_name: str
    title: str
    company_name: str
    profile_url: str
    standard_connect_available: bool
    requires_email_or_extra_identity: bool = False
    live_connection_state: str = "none"


@dataclass(frozen=True)
class CompanyContactObservation:
    member_name: str
    title: str
    company_name: str
    profile_url: str
    standard_connect_available: bool
    requires_email_or_extra_identity: bool = False
    live_connection_state: str = "none"


def record_individual_post_evaluation(
    run_dir: Path,
    post: LinkedInPostObservation,
    *,
    decision: str,
    reason: str,
    candidate: IndividualCandidateObservation | None = None,
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "discovering_posts":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能记录贴文判断。")
    normalized_decision = decision.strip().casefold()
    if normalized_decision not in {"continue", "skip"}:
        raise ValueError("贴文判断只支持 Continue 或 Skip。")
    reason_text = reason.strip()
    if not reason_text:
        raise ValueError("贴文判断必须包含一个基于可见内容的理由。")
    if post.author_type.casefold() not in {"individual", "person"}:
        raise ValueError("此入口只处理个人作者贴文；公司作者应进入公司联系人解析流程。")
    progress = state.get("search_progress") or {}
    _ensure_discovery_capacity(state)
    if post.keyword != progress.get("current_keyword"):
        raise ValueError("贴文来源关键词与当前搜索进度不一致。")
    if int(progress.get("opened_post_count") or 0) >= 50:
        raise ValueError("当前关键词已经达到 50 条打开贴文上限，必须结束或进入下一关键词。")
    post_url = normalize_linkedin_url(post.post_url)
    author_profile_url = normalize_linkedin_url(post.author_profile_url)
    company_url = normalize_linkedin_url(post.company_url) if post.company_url else ""
    timestamp = _timestamp(now)
    evaluation = {
        **asdict(post),
        "post_url": post_url,
        "author_profile_url": author_profile_url,
        "company_url": company_url,
        "decision": normalized_decision,
        "reason": reason_text,
        "recorded_at": timestamp,
    }
    discovery_dir = run_dir / "discovery"
    discovery_dir.mkdir(parents=True, exist_ok=True)
    log_path = discovery_dir / "post-evaluations.jsonl"
    progress["opened_post_count"] = int(progress.get("opened_post_count") or 0) + 1
    state["search_progress"] = progress

    output_paths = [str(log_path)]
    if normalized_decision == "skip":
        message = f"Skip：{reason_text}"
    else:
        if candidate is None:
            raise ValueError("Continue 的个人作者贴文必须提供候选人观察。")
        if candidate.requires_email_or_extra_identity:
            evaluation["candidate_outcome"] = "skipped_extra_identity_required"
            message = "Skip：连接路径要求邮箱或额外身份信息。"
        elif not candidate.standard_connect_available:
            evaluation["candidate_outcome"] = "skipped_no_standard_connect"
            message = "Skip：没有标准 Connect 路径。"
        else:
            profile_url = normalize_linkedin_url(candidate.profile_url)
            if profile_url != author_profile_url:
                raise ValueError("个人作者候选必须保持为原贴文作者，不能自动替换为其他员工。")
            candidate_id = "candidate_" + hashlib.sha256(profile_url.encode("utf-8")).hexdigest()[:16]
            reservation = reserve_candidate(
                run_dir,
                account_profile_url=state["account_binding"]["profile_url"],
                member_profile_url=profile_url,
                company_url=company_url,
                source_post_url=post_url,
                candidate_id=candidate_id,
                live_state=candidate.live_connection_state,
                now=now,
            )
            if not reservation["eligible"]:
                evaluation["candidate_outcome"] = reservation["reason"]
                message = f"Skip：联系人去重或实时状态不允许进入候选卡（{reservation['reason']}）。"
                candidate = None
            else:
                evaluation["candidate_outcome"] = "candidate_reserved"
        if candidate is not None and normalized_decision == "continue" and evaluation.get("candidate_outcome") == "candidate_reserved":
            card = {
                "candidate_id": candidate_id,
                "source_keyword": post.keyword,
                "post_text": post.post_text,
                "post_url": post_url,
                "relevance_decision": "continue",
                "relevance_reason": reason_text,
                "author": {
                    "name": post.author_name,
                    "type": "individual",
                    "profile_url": author_profile_url,
                },
                "company": {"name": candidate.company_name or post.company_name, "url": company_url},
                "selected_member": {
                    "name": candidate.member_name,
                    "title": candidate.title,
                    "company": candidate.company_name,
                    "profile_url": profile_url,
                },
                "connect_path": "standard_connect",
                "approval": "pending_batch_review",
                "note_decision": None,
                "final_outcome": None,
                "created_at": timestamp,
            }
            markdown_path, json_path = persist_candidate_card(run_dir, card)
            state.setdefault("candidate_ids", []).append(candidate_id)
            state.setdefault("files", {}).setdefault("candidate_cards", []).extend([str(markdown_path), str(json_path)])
            output_paths.extend([str(markdown_path), str(json_path)])
            message = render_candidate_card(card)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(evaluation, ensure_ascii=False) + "\n")
    state["updated_at"] = timestamp
    _write_json_atomic(state_path, state)
    _append_change(run_dir, timestamp, f"记录贴文判断：{normalized_decision}；{reason_text}")
    output_paths.append(str(state_path))
    return LinkedInSearchStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=tuple(output_paths),
        message=message,
    )


def record_company_post_evaluation(
    run_dir: Path,
    post: LinkedInPostObservation,
    *,
    decision: str,
    reason: str,
    contacts: list[CompanyContactObservation],
    now: datetime | None = None,
) -> LinkedInSearchStepResult:
    run_dir, state_path, state = _load_run(run_dir)
    if state.get("phase") != "discovering_posts":
        raise ValueError(f"当前阶段是 {state.get('phase')!r}，不能记录公司贴文判断。")
    if post.author_type.casefold() not in {"company", "organization"}:
        raise ValueError("此入口只处理公司作者贴文。")
    normalized_decision = decision.strip().casefold()
    if normalized_decision not in {"continue", "skip"}:
        raise ValueError("贴文判断只支持 Continue 或 Skip。")
    reason_text = reason.strip()
    if not reason_text:
        raise ValueError("公司贴文判断必须包含一个理由。")
    progress = state.get("search_progress") or {}
    _ensure_discovery_capacity(state)
    if post.keyword != progress.get("current_keyword"):
        raise ValueError("贴文来源关键词与当前搜索进度不一致。")
    if int(progress.get("opened_post_count") or 0) >= 50:
        raise ValueError("当前关键词已经达到 50 条打开贴文上限。")
    timestamp = _timestamp(now)
    post_url = normalize_linkedin_url(post.post_url)
    company_url = normalize_linkedin_url(post.company_url or post.author_profile_url)
    evaluation = {
        **asdict(post),
        "post_url": post_url,
        "company_url": company_url,
        "decision": normalized_decision,
        "reason": reason_text,
        "recorded_at": timestamp,
    }
    progress["opened_post_count"] = int(progress.get("opened_post_count") or 0) + 1
    state["search_progress"] = progress
    discovery_dir = run_dir / "discovery"
    discovery_dir.mkdir(parents=True, exist_ok=True)
    log_path = discovery_dir / "post-evaluations.jsonl"
    output_paths = [str(log_path)]
    message = f"Skip：{reason_text}"
    if normalized_decision == "continue":
        eligible_contacts = [
            contact
            for contact in contacts
            if contact.standard_connect_available and not contact.requires_email_or_extra_identity and _role_rank(contact.title) is not None
        ]
        eligible_contacts.sort(key=lambda item: (_role_rank(item.title), item.member_name.casefold()))
        selected = eligible_contacts[0] if eligible_contacts else None
        if selected is None:
            evaluation["candidate_outcome"] = "skipped_no_eligible_company_contact"
            message = "Skip：公司内没有符合优先角色且具备标准 Connect 路径的联系人。"
        else:
            profile_url = normalize_linkedin_url(selected.profile_url)
            candidate_id = "candidate_" + hashlib.sha256(profile_url.encode("utf-8")).hexdigest()[:16]
            reservation = reserve_candidate(
                run_dir,
                account_profile_url=state["account_binding"]["profile_url"],
                member_profile_url=profile_url,
                company_url=company_url,
                source_post_url=post_url,
                candidate_id=candidate_id,
                live_state=selected.live_connection_state,
                now=now,
            )
            if not reservation["eligible"]:
                evaluation["candidate_outcome"] = reservation["reason"]
                message = f"Skip：联系人去重或实时状态不允许进入候选卡（{reservation['reason']}）。"
            else:
                card = {
                    "candidate_id": candidate_id,
                    "source_keyword": post.keyword,
                    "post_text": post.post_text,
                    "post_url": post_url,
                    "relevance_decision": "continue",
                    "relevance_reason": reason_text,
                    "author": {"name": post.author_name, "type": "company", "profile_url": company_url},
                    "company": {"name": selected.company_name or post.company_name, "url": company_url},
                    "selected_member": {
                        "name": selected.member_name,
                        "title": selected.title,
                        "company": selected.company_name,
                        "profile_url": profile_url,
                    },
                    "selection_reason": f"公司贴文联系人按角色优先级选择：{selected.title}",
                    "connect_path": "standard_connect",
                    "approval": "pending_batch_review",
                    "note_decision": None,
                    "final_outcome": None,
                    "created_at": timestamp,
                }
                markdown_path, json_path = persist_candidate_card(run_dir, card)
                state.setdefault("candidate_ids", []).append(candidate_id)
                state.setdefault("files", {}).setdefault("candidate_cards", []).extend([str(markdown_path), str(json_path)])
                output_paths.extend([str(markdown_path), str(json_path)])
                evaluation["candidate_outcome"] = "candidate_reserved"
                evaluation["selected_member"] = card["selected_member"]
                message = render_candidate_card(card)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(evaluation, ensure_ascii=False) + "\n")
    state["updated_at"] = timestamp
    _write_json_atomic(state_path, state)
    _append_change(run_dir, timestamp, f"记录公司贴文判断：{normalized_decision}；{reason_text}")
    output_paths.append(str(state_path))
    return LinkedInSearchStepResult(
        run_dir=str(run_dir),
        workflow_state_path=str(state_path),
        status=state["status"],
        phase=state["phase"],
        output_paths=tuple(output_paths),
        message=message,
    )


def _role_rank(title: str) -> int | None:
    value = title.casefold()
    groups = (
        ("owner", "founder", "co-founder", "cofounder"),
        ("procurement", "purchasing", "sourcing", "buyer"),
        ("managing director", "general manager"),
        ("product manager",),
    )
    for index, terms in enumerate(groups):
        if any(term in value for term in terms):
            return index
    return None


def _ensure_discovery_capacity(state: dict[str, Any]) -> None:
    effective_limit = int((state.get("capacity_at_account_binding") or {}).get("effective_limit") or 0)
    requested_limit = int((state.get("confirmed_search_brief") or {}).get("requested_limit") or 10)
    limit = effective_limit or requested_limit
    if len(state.get("candidate_ids") or []) >= limit:
        raise ValueError(f"候选数量已经达到本次有效上限 {limit}；必须结束发现阶段，不能继续打开贴文。")

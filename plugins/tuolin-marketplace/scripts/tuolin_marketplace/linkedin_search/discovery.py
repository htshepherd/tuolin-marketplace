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


@dataclass(frozen=True)
class ProspectClassificationObservation:
    outcome: str
    business_role: str
    supporting_evidence: str
    material_doubts: str = ""


def record_individual_post_evaluation(
    run_dir: Path,
    post: LinkedInPostObservation,
    *,
    decision: str,
    reason: str,
    candidate: IndividualCandidateObservation | None = None,
    classification: ProspectClassificationObservation | None = None,
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
    _register_unique_opened_post(progress, post_url)
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
    state["search_progress"] = progress
    classification_data = _validated_classification(classification, normalized_decision, reason_text)
    evaluation["classification"] = classification_data

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
                "fit_status": classification_data["outcome"],
                "business_role": classification_data["business_role"],
                "supporting_evidence": classification_data["supporting_evidence"],
                "material_doubts": classification_data["material_doubts"],
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
    _write_json_atomic(Path(state["files"]["search_progress"]), progress)
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
    classification: ProspectClassificationObservation | None = None,
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
    _register_unique_opened_post(progress, post_url)
    company_url = normalize_linkedin_url(post.company_url or post.author_profile_url)
    evaluation = {
        **asdict(post),
        "post_url": post_url,
        "company_url": company_url,
        "decision": normalized_decision,
        "reason": reason_text,
        "recorded_at": timestamp,
    }
    state["search_progress"] = progress
    classification_data = _validated_classification(classification, normalized_decision, reason_text)
    evaluation["classification"] = classification_data
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
            unresolved_id = "lead_" + hashlib.sha256(company_url.encode("utf-8")).hexdigest()[:16]
            unresolved = {
                "lead_id": unresolved_id,
                "source_keyword": post.keyword,
                "post_text": post.post_text,
                "post_url": post_url,
                "author": {"name": post.author_name, "type": "company", "profile_url": company_url},
                "company": {"name": post.company_name, "url": company_url},
                "relevance_reason": reason_text,
                "classification": {**classification_data, "outcome": "unresolved_relevant_lead"},
                "reason": "没有可验证的优先角色标准 Connect 联系人",
                "created_at": timestamp,
            }
            unresolved_path = discovery_dir / "unresolved-relevant-leads.jsonl"
            with unresolved_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(unresolved, ensure_ascii=False) + "\n")
            state.setdefault("unresolved_lead_ids", []).append(unresolved_id)
            state.setdefault("files", {})["unresolved_relevant_leads"] = str(unresolved_path)
            output_paths.append(str(unresolved_path))
            evaluation["candidate_outcome"] = "unresolved_relevant_lead"
            message = "已记录未解析相关线索：业务相关，但没有可验证的标准 Connect 联系人；不计入候选人数。"
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
                    "fit_status": classification_data["outcome"],
                    "business_role": classification_data["business_role"],
                    "supporting_evidence": classification_data["supporting_evidence"],
                    "material_doubts": classification_data["material_doubts"],
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
    _write_json_atomic(Path(state["files"]["search_progress"]), progress)
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


def _register_unique_opened_post(progress: dict[str, Any], post_url: str) -> None:
    evaluated = list(progress.get("evaluated_post_urls") or [])
    if post_url in evaluated:
        raise ValueError("该 LinkedIn 贴文已经打开并判断过；重复结果不能计入 50 条上限。")
    evaluated.append(post_url)
    progress["evaluated_post_urls"] = evaluated
    progress["opened_post_count"] = len(evaluated)


def _validated_classification(
    classification: ProspectClassificationObservation | None,
    decision: str,
    fallback_reason: str,
) -> dict[str, str]:
    if classification is None:
        classification = ProspectClassificationObservation(
            outcome="provisional_candidate_fit" if decision == "continue" else "obvious_skip",
            business_role="ambiguous" if decision == "continue" else "unrelated",
            supporting_evidence=fallback_reason,
            material_doubts="需要人工依据完整贴文和作者信息复核。" if decision == "continue" else "",
        )
    allowed_outcomes = {"obvious_skip", "provisional_candidate_fit", "unresolved_relevant_lead"}
    allowed_roles = {"direct_category_manufacturer", "downstream_material_user", "same_category_channel_prospect", "unrelated", "ambiguous"}
    if classification.outcome not in allowed_outcomes or classification.business_role not in allowed_roles:
        raise ValueError("候选分类字段不在允许范围内。")
    if not classification.supporting_evidence.strip():
        raise ValueError("候选分类必须包含基于可见 LinkedIn 内容的支持证据。")
    if classification.business_role == "direct_category_manufacturer" and decision != "skip":
        raise ValueError("直接制造或供应同类/基础材料的主体必须 Skip，不能形成候选。")
    if classification.business_role == "unrelated" and decision != "skip":
        raise ValueError("与业务无关的贴文必须 Skip。")
    if decision == "continue" and classification.outcome == "obvious_skip":
        raise ValueError("Continue 不能同时标记为 obvious_skip。")
    return asdict(classification)

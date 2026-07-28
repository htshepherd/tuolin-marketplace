from __future__ import annotations

import hashlib
import json
import re
import shutil
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..kb.agent_specific_interfaces import (
    read_video_planner_card,
    read_video_planner_manifest,
    read_video_planner_products,
    read_video_planner_video_detail,
)
from ..shared.project_layout import ProjectPaths
from .assets import revalidate_video_planning_material
from .interview import (
    FACT_GROUNDED_FIELDS,
    PLANNING_BRIEF_FIELDS,
    answer_planning_interview,
    build_planning_interview,
    confirmed_planning_brief,
    propose_planning_decision,
    refresh_planning_interview,
    validate_fact_correction,
)


SUPPORTED_PLATFORMS = {"youtube_shorts", "tiktok"}
SUPPORTED_LANGUAGES = {"zh", "en"}
MIN_DURATION_SECONDS = 15
MAX_DURATION_SECONDS = 90
DEFAULT_DURATION_SECONDS = 30
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
FORBIDDEN_PLAN_FIELD_TOKENS = {
    "dreamina",
    "jimeng",
    "prompt",
    "generation_job",
    "provider_task",
    "assembly",
    "subtitle_style",
    "cta_overlay",
    "safe_area",
}


@dataclass(frozen=True)
class VideoPlanningResult:
    run_dir: str
    status: str
    phase: str
    output_paths: tuple[str, ...]
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_video_planning_run(
    paths: ProjectPaths,
    request_text: str,
    *,
    product_id: str,
    platforms: list[str] | tuple[str, ...],
    language_version: str,
    duration_seconds: int = DEFAULT_DURATION_SECONDS,
    initial_decisions: dict[str, str] | None = None,
    initial_decision_evidence: dict[str, list[dict[str, Any]]] | None = None,
    invoked_skill: str | None = None,
    now: datetime | None = None,
) -> VideoPlanningResult:
    if invoked_skill != "$tuolin-video-planner":
        raise ValueError("视频策划任务必须显式调用 $tuolin-video-planner。")
    manifest = read_video_planner_manifest(paths)
    if manifest.get("agent_id") != "tuolin-video-planner" or manifest.get("raw_access") is not False:
        raise ValueError("视频策划专属知识接口无效。")
    products = read_video_planner_products(paths)
    product = next((item for item in products if item.get("id") == product_id), None)
    if product is None:
        raise ValueError("产品未发布到视频策划专属知识接口。")
    normalized_platforms = _normalize_platforms(platforms)
    language = _normalize_language(language_version)
    product = {**product, "display_title": _select_product_title(product, language)}
    duration = _normalize_duration(duration_seconds)
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^a-z0-9_]+", "_", product_id.split("/", 1)[-1].casefold()).strip("_") or "product"
    root = paths.generated_dir / "reports" / "video-planning"
    run_dir = _unique_run_dir(root, f"{timestamp}_{slug}_{language}")
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "material-previews").mkdir()
    (run_dir / "revisions").mkdir()
    decisions = dict(initial_decisions or {})
    evidence_by_key = dict(initial_decision_evidence or {})
    validated_evidence: dict[str, list[dict[str, Any]]] = {}
    for key in FACT_GROUNDED_FIELDS:
        if str(decisions.get(key) or "").strip():
            evidence = list(evidence_by_key.get(key) or [])
            if not evidence:
                decisions.pop(key, None)
                continue
            validated_evidence[key] = _validate_planning_evidence(paths, evidence, product_id)
    interview = build_planning_interview(decisions)
    interview["decision_evidence"].update(validated_evidence)
    phase = "ready_for_shot_plan" if interview["completed"] else "interview"
    state = {
        "schema_version": "video-planning-state-v1",
        "run_id": run_dir.name,
        "status": "active",
        "phase": phase,
        "request_text": request_text.strip(),
        "product": product,
        "platforms": normalized_platforms,
        "language_version": language,
        "duration_seconds": duration,
        "aspect_ratio": "9:16",
        "interface": {
            "agent_id": manifest["agent_id"],
            "interface_revision": manifest["interface_revision"],
            "source_knowledge_revision": manifest["source_knowledge_revision"],
            "product_fingerprint": product["projection_fingerprint"],
        },
        "project_paths": {
            "project_dir": str(paths.project_dir),
            "raw_dir": str(paths.raw_dir),
            "knowledge_dir": str(paths.knowledge_dir),
            "generated_dir": str(paths.generated_dir),
        },
        "current_revision": 0,
        "confirmations": {"shot_plan": False},
        "files": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(run_dir / "interview.json", interview)
    _write_json(run_dir / "workflow_state.json", state)
    requirements = _render_requirements(state)
    _write_text(run_dir / "requirements.md", requirements)
    _append_change(run_dir, "创建独立视频策划运行；固定专属知识接口 revision。")
    return VideoPlanningResult(
        run_dir=str(run_dir),
        status="created",
        phase=phase,
        output_paths=(str(run_dir / "requirements.md"), str(run_dir / "workflow_state.json")),
        message="视频策划运行已创建。" if phase == "interview" else "访谈信息已充分，可以生成逐镜头方案。",
    )


def propose_video_planning_decision(run_dir: Path | str, proposal: dict[str, Any]) -> VideoPlanningResult:
    root = Path(run_dir).expanduser().resolve()
    state = _load_state(root)
    if state["phase"] != "interview":
        raise ValueError("当前阶段不能提出视频策划访谈问题。")
    interview = _read_json(root / "interview.json")
    evidence = list(proposal.get("evidence") or [])
    if evidence:
        evidence = _validate_planning_evidence(
            _paths_from_state(state),
            evidence,
            state["product"]["id"],
        )
    updated = propose_planning_decision(
        interview,
        decision_key=str(proposal.get("decision_key") or ""),
        question=str(proposal.get("question") or ""),
        recommendation=str(proposal.get("recommendation") or ""),
        reason=str(proposal.get("reason") or ""),
        evidence=evidence,
        inference=bool(proposal.get("inference")),
    )
    _write_json(root / "interview.json", updated)
    _append_change(root, f"提出访谈决策：{proposal.get('decision_key')}。")
    return VideoPlanningResult(str(root), "awaiting_confirmation", "interview", (str(root / "interview.json"),), _render_pending_decision(updated))


def handle_video_planning_reply(
    run_dir: Path | str,
    reply: str,
    *,
    remaining_recommendations: dict[str, dict[str, Any]] | None = None,
) -> VideoPlanningResult:
    root = Path(run_dir).expanduser().resolve()
    state = _load_state(root)
    if state["phase"] != "interview":
        raise ValueError("当前阶段没有待回答的视频策划问题。")
    interview = _read_json(root / "interview.json")
    normalized_reply = str(reply).strip().casefold()
    all_remaining_replies = {"剩下都按推荐", "你来决定并直接出策划"}
    if normalized_reply in all_remaining_replies and remaining_recommendations is None:
        return VideoPlanningResult(
            str(root),
            "recommendations_required",
            "interview",
            (str(root / "interview.json"),),
            "用户已授权采用全部剩余建议；请基于当前 brief 和正式证据生成完整剩余建议后一次写入。",
        )
    if normalized_reply in all_remaining_replies:
        updated = _accept_remaining_recommendations(
            _paths_from_state(state),
            interview,
            remaining_recommendations or {},
            state["product"]["id"],
        )
    else:
        updated = answer_planning_interview(interview, reply)
    _write_json(root / "interview.json", updated)
    if updated["completed"] and not updated.get("unvalidated_fact_corrections"):
        state["phase"] = "ready_for_shot_plan"
        state["brief"] = confirmed_planning_brief(updated)
        _save_state(root, state)
        message = "视频策划访谈已充分，请直接生成完整逐镜头方案与逐字旁白。"
    elif updated.get("unvalidated_fact_corrections"):
        message = "用户修改涉及产品事实，必须先通过视频策划专属知识接口核验。"
    else:
        message = "当前决策已记录；请基于已确认内容提出下一项最有价值的单一决策。"
    _append_change(root, "处理一项视频策划访谈回复。")
    return VideoPlanningResult(str(root), "updated", state["phase"], (str(root / "interview.json"),), message)


def validate_video_planning_fact_correction(
    run_dir: Path | str,
    *,
    decision_key: str,
    value: str,
    evidence: list[dict[str, Any]],
) -> VideoPlanningResult:
    root = Path(run_dir).expanduser().resolve()
    state = _load_state(root)
    if state["phase"] != "interview":
        raise ValueError("当前阶段不能核验访谈事实修正。")
    validated = _validate_planning_evidence(
        _paths_from_state(state),
        evidence,
        state["product"]["id"],
    )
    interview = validate_fact_correction(
        _read_json(root / "interview.json"),
        decision_key=decision_key,
        value=value,
        evidence=validated,
    )
    _write_json(root / "interview.json", interview)
    if interview["completed"]:
        state["phase"] = "ready_for_shot_plan"
        state["brief"] = confirmed_planning_brief(interview)
        _save_state(root, state)
    _append_change(root, f"通过专属知识接口核验事实修正：{decision_key}。")
    return VideoPlanningResult(str(root), "validated", state["phase"], (str(root / "interview.json"),), "事实修正已核验。")


def write_video_shot_plan(run_dir: Path | str, plan: dict[str, Any]) -> VideoPlanningResult:
    root = Path(run_dir).expanduser().resolve()
    state = _load_state(root)
    if state.get("status") == "blocked_stale_reference":
        raise ValueError(str(state.get("blocker", {}).get("message") or "引用已过期，必须新建视频策划运行。"))
    if state["phase"] not in {"ready_for_shot_plan", "awaiting_shot_plan_confirmation", "completed"}:
        raise ValueError("当前阶段不能写入逐镜头方案。")
    interview = _read_json(root / "interview.json")
    brief = confirmed_planning_brief(interview)
    normalized = _normalize_and_validate_plan(root, state, plan, brief)
    normalized["decision_evidence"] = deepcopy(interview.get("decision_evidence") or {})
    if state["phase"] == "completed":
        _archive_current_delivery(root, state)
        state["confirmations"]["shot_plan"] = False
        state["phase"] = "ready_for_shot_plan"
        state["status"] = "active"
        state["files"].pop("srt", None)
        srt_path = root / "storyboard.srt"
        if srt_path.exists():
            srt_path.unlink()
    state["current_revision"] = int(state.get("current_revision") or 0) + 1
    normalized["revision"] = state["current_revision"]
    normalized["status"] = "draft_pending_confirmation"
    json_path = root / "shot_plan.json"
    md_path = root / "shot_plan.md"
    rendered_plan = _render_shot_plan(normalized)
    _write_json(json_path, normalized)
    _write_text(md_path, rendered_plan)
    state["phase"] = "awaiting_shot_plan_confirmation"
    state["files"].update({"shot_plan_json": str(json_path), "shot_plan_md": str(md_path)})
    _save_state(root, state)
    _append_change(root, f"写入逐镜头方案修订版 {state['current_revision']}，等待确认。")
    return VideoPlanningResult(
        str(root),
        "awaiting_confirmation",
        state["phase"],
        (str(md_path), str(json_path), *_confirmation_media_paths(normalized)),
        rendered_plan + "\n\n是否确认？",
    )


def confirm_video_shot_plan(run_dir: Path | str) -> VideoPlanningResult:
    root = Path(run_dir).expanduser().resolve()
    state = _load_state(root)
    if state["phase"] != "awaiting_shot_plan_confirmation":
        raise ValueError("当前没有可确认的逐镜头方案。")
    stored_plan = _read_json(root / "shot_plan.json")
    try:
        _revalidate_referenced_knowledge(root, state, stored_plan)
    except ValueError as exc:
        if "必须新建" in str(exc) or "被撤销" in str(exc):
            state["status"] = "blocked_stale_reference"
            state["blocker"] = {
                "code": "stale_or_revoked_reference",
                "message": str(exc),
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
            _save_state(root, state)
            _append_change(root, f"最终确认被阻止：{exc}")
        raise
    interview = _read_json(root / "interview.json")
    plan = _normalize_and_validate_plan(root, state, stored_plan, confirmed_planning_brief(interview))
    plan["decision_evidence"] = deepcopy(interview.get("decision_evidence") or {})
    revision_dir = root / "revisions" / f"revision_{int(plan['revision']):04d}"
    if revision_dir.exists():
        raise ValueError("目标修订目录已存在，当前草稿未确认。")
    plan["status"] = "confirmed"
    plan["confirmed_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(root / "shot_plan.json", plan)
    _write_text(root / "shot_plan.md", _render_shot_plan(plan))
    srt_path = root / "storyboard.srt"
    _write_text(srt_path, _render_srt(plan))
    revision_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(root / "shot_plan.json", revision_dir / "shot_plan.json")
    shutil.copy2(root / "shot_plan.md", revision_dir / "shot_plan.md")
    shutil.copy2(srt_path, revision_dir / "storyboard.srt")
    state["phase"] = "completed"
    state["status"] = "completed"
    state["confirmations"]["shot_plan"] = True
    state["files"]["srt"] = str(srt_path)
    state["files"]["confirmed_revision_dir"] = str(revision_dir)
    _save_state(root, state)
    _append_change(root, f"确认逐镜头方案和旁白，自动生成 SRT；修订版 {plan['revision']} 完成。")
    return VideoPlanningResult(
        str(root),
        "completed",
        "completed",
        (str(root / "shot_plan.md"), str(root / "shot_plan.json"), str(srt_path)),
        "镜头方案与逐字旁白已确认，SRT 已自动生成；视频策划任务结束。",
    )


def resume_video_planning_run(run_dir: Path | str) -> VideoPlanningResult:
    root = Path(run_dir).expanduser().resolve()
    state = _load_state(root)
    output_paths = tuple(str(value) for value in state.get("files", {}).values())
    message = (
        str(state.get("blocker", {}).get("message"))
        if state.get("status") == "blocked_stale_reference"
        else {
        "interview": "继续当前待确认的视频策划问题。",
        "ready_for_shot_plan": "访谈已充分，请生成完整逐镜头方案。",
        "awaiting_shot_plan_confirmation": "请审阅并确认当前逐镜头方案与旁白，或直接提出修改。",
        "completed": "当前视频策划已交付；可创建版本化修订，但不会进入视频生成。",
        }.get(state["phase"], "视频策划运行状态未知。")
    )
    return VideoPlanningResult(str(root), state["status"], state["phase"], output_paths, message)


def apply_video_shot_plan_revision(run_dir: Path | str, revised_plan: dict[str, Any]) -> VideoPlanningResult:
    """Apply a natural-language-derived semantic revision to the actual shot-plan fields."""
    root = Path(run_dir).expanduser().resolve()
    state = _load_state(root)
    if state["phase"] not in {"awaiting_shot_plan_confirmation", "completed"}:
        raise ValueError("当前没有可修订的逐镜头方案。")
    return write_video_shot_plan(root, revised_plan)


def _normalize_and_validate_plan(root: Path, state: dict[str, Any], plan: dict[str, Any], brief: dict[str, str]) -> dict[str, Any]:
    normalized = deepcopy(plan)
    forbidden_paths = _find_forbidden_plan_fields(normalized)
    if forbidden_paths:
        raise ValueError(
            "逐镜头方案包含超出视频策划 Agent 边界的字段：" + "、".join(forbidden_paths)
        )
    shots = list(normalized.get("shots") or [])
    if not shots:
        raise ValueError("逐镜头方案至少需要一个镜头。")
    total = 0.0
    expected_start = 0.0
    narration_count = 0
    for index, shot in enumerate(shots, start=1):
        shot["shot_id"] = str(shot.get("shot_id") or f"{index:02d}")
        start = float(shot.get("start_seconds", expected_start))
        duration = float(shot.get("duration_seconds") or 0)
        end = float(shot.get("end_seconds", start + duration))
        if abs(start - expected_start) > 0.001 or duration <= 0 or abs((end - start) - duration) > 0.001:
            raise ValueError(f"镜头 {shot['shot_id']} 时间轴不连续或时长无效。")
        shot["start_seconds"] = start
        shot["duration_seconds"] = duration
        shot["end_seconds"] = end
        for field in ("purpose", "visual_action", "camera", "transition", "editing_guidance"):
            if not str(shot.get(field) or "").strip():
                raise ValueError(f"镜头 {shot['shot_id']} 缺少 {field}。")
        narration = str(shot.get("narration") or "").strip()
        intentional_silence = bool(shot.get("intentional_silence"))
        if not narration and not intentional_silence:
            raise ValueError(f"镜头 {shot['shot_id']} 必须有旁白或明确标记有意静默。")
        if narration:
            narration_count += 1
            _validate_narration_fit(narration, duration, state["language_version"], shot["shot_id"])
        _validate_shot_material(root, state, shot, brief)
        expected_start = end
        total += duration
    if narration_count == 0:
        raise ValueError("整份逐镜头方案不能完全没有旁白。")
    if abs(total - float(state["duration_seconds"])) > 0.001:
        raise ValueError("镜头总时长必须等于本次视频策划目标时长。")
    normalized.update(
        {
            "schema_version": "production-ready-shot-plan-v1",
            "product_id": state["product"]["id"],
            "product_title": state["product"]["display_title"],
            "platforms": state["platforms"],
            "language_version": state["language_version"],
            "duration_seconds": state["duration_seconds"],
            "aspect_ratio": "9:16",
            "brief": brief,
            "interface_revision": state["interface"]["interface_revision"],
            "source_video_audio": False,
            "public_trend_search": False,
            "shots": shots,
        }
    )
    return normalized


def _validate_shot_material(
    root: Path,
    state: dict[str, Any],
    shot: dict[str, Any],
    brief: dict[str, str],
) -> None:
    paths = _paths_from_state(state)
    material = dict(shot.get("material") or {})
    mode = str(material.get("mode") or "")
    if mode not in {"official_image", "real_video_segment", "ai_simulation"}:
        raise ValueError(f"镜头 {shot['shot_id']} 的素材模式无效。")
    if mode == "official_image":
        card_id = str(material.get("card_id") or "")
        if not card_id:
            raise ValueError(f"镜头 {shot['shot_id']} 的正式图片缺少 card_id。")
        card = read_video_planner_card(paths, card_id)
        if card.get("type") != "content_asset" or card.get("draft_only"):
            raise ValueError(f"镜头 {shot['shot_id']} 必须使用可对外的正式图片素材卡。")
        if not _card_matches_product(card, state["product"]["id"]):
            raise ValueError(f"镜头 {shot['shot_id']} 的图片不属于当前产品范围。")
        source_path = Path(str(material.get("source_path") or "")).expanduser()
        preview_path = Path(str(material.get("preview_path") or "")).expanduser()
        if not source_path.is_file() or source_path.suffix.casefold() not in IMAGE_SUFFIXES:
            raise FileNotFoundError(source_path)
        _validate_card_source_path(paths, card, source_path, shot["shot_id"])
        if not preview_path.is_file():
            raise FileNotFoundError(preview_path)
        inspection = dict(material.get("inspection") or {})
        required = {"subject", "clarity", "composition", "vertical_crop", "near_duplicate_of"}
        if not required.issubset(inspection):
            raise ValueError(f"镜头 {shot['shot_id']} 的图片尚未完成像素级检查。")
        if material.get("confirmable") is not True:
            raise ValueError(f"镜头 {shot['shot_id']} 的图片存在未解决外用风险。")
        risk_checks = dict(material.get("risk_checks") or {})
        risk_fields = {"product_identity", "rights", "privacy", "test_meaning", "claim_risk"}
        if set(risk_checks) != risk_fields or any(value != "clear" for value in risk_checks.values()):
            raise ValueError(f"镜头 {shot['shot_id']} 的图片风险检查不完整或未清除。")
        material["card_fingerprint"] = card["projection_fingerprint"]
        material["source_fingerprint"] = _file_sha256(source_path)
        material["preview_fingerprint"] = _file_sha256(preview_path)
    elif mode == "real_video_segment":
        if material.get("original_audio_used") is not False:
            raise ValueError("来源视频片段必须仅使用画面，不能使用原声。")
        profile_id = str(material.get("profile_id") or "")
        segment_id = str(material.get("segment_id") or "")
        if not profile_id or not segment_id:
            raise ValueError("来源视频片段必须引用 profile_id 和 segment_id。")
        detail = read_video_planner_video_detail(paths, profile_id)
        if detail.get("product_id") != state["product"]["id"]:
            raise ValueError("来源视频档案不属于当前产品。")
        segment = next((item for item in detail.get("key_segments", []) if item.get("segment_id") == segment_id), None)
        if segment is None or segment.get("use_exclusion", {}).get("status") == "excluded":
            raise ValueError("来源视频片段未获当前专属接口授权。")
        if not str(material.get("preview_path") or "") or not Path(str(material["preview_path"])).is_file():
            raise ValueError("来源视频片段必须先生成并检查有界预览。")
        if material.get("confirmable") is not True:
            raise ValueError("来源视频片段存在未解决外用风险。")
        planned_use_id = str(material.get("planned_use_id") or "")
        start = float(material.get("source_start_seconds", -1))
        end = float(material.get("source_end_seconds", -1))
        audit_path = root / "video_asset_audit.json"
        audit = _read_json(audit_path) if audit_path.is_file() else []
        preview = next(
            (
                item for item in audit
                if item.get("operation") == "candidate_preview"
                and item.get("status") == "extracted"
                and item.get("profile_id") == profile_id
                and item.get("segment_id") == segment_id
                and item.get("planned_use_id") == planned_use_id
                and abs(float(item.get("start_seconds", -2)) - start) <= 0.001
                and abs(float(item.get("end_seconds", -2)) - end) <= 0.001
                and item.get("preview_path") == material.get("preview_path")
            ),
            None,
        )
        if preview is None:
            raise ValueError("来源视频片段必须与已审计的静音预览使用同一时间范围。")
        preview_path = Path(str(material["preview_path"]))
        if _file_sha256(preview_path) != preview.get("preview_fingerprint"):
            raise ValueError("来源视频预览内容指纹已变化。")
        material["preview_fingerprint"] = preview["preview_fingerprint"]
        material["video_asset_id"] = detail["video_asset_id"]
        material["profile_revision"] = detail["profile_revision"]
        material["source_revision"] = detail["source_revision"]
    else:
        if not _ai_simulation_permitted(str(brief.get("ai_simulation_scope") or "")):
            raise ValueError("当前已确认的 AI 模拟边界不允许使用模拟镜头。")
        application_card_id = str(material.get("application_card_id") or "")
        if not application_card_id:
            raise ValueError("AI 模拟镜头必须引用正式应用场景卡。")
        application_card = read_video_planner_card(paths, application_card_id)
        if application_card.get("type") != "application_scenario" or application_card.get("draft_only"):
            raise ValueError("AI 模拟镜头只能描绘正式确认且可对外的应用场景。")
        if not _card_matches_product(application_card, state["product"]["id"]):
            raise ValueError("AI 模拟应用场景不属于当前产品。")
        if material.get("evidence_use") or material.get("customer_case_use") or material.get("test_use"):
            raise ValueError("AI 模拟镜头不得充当证据、客户案例或测试画面。")
        reference_id = str(material.get("product_reference_card_id") or "")
        if material.get("specific_product_visible") and not reference_id:
            raise ValueError("描绘具体产品的 AI 模拟镜头必须引用真实产品图片。")
        if reference_id:
            reference = read_video_planner_card(paths, reference_id)
            if reference.get("type") != "content_asset" or reference.get("draft_only"):
                raise ValueError("AI 模拟产品参考必须是可对外的正式图片素材卡。")
            if not _card_matches_product(reference, state["product"]["id"]):
                raise ValueError("AI 模拟产品参考不属于当前产品。")
            _validate_prefixed_image_checks(paths, reference, material, "product_reference", shot["shot_id"])
            material["product_reference_fingerprint"] = reference["projection_fingerprint"]
        material["application_card_fingerprint"] = application_card["projection_fingerprint"]
        material["simulated"] = True
    shot["material"] = material


def _validate_narration_fit(text: str, duration: float, language: str, shot_id: str) -> None:
    if language == "zh":
        units = len(re.findall(r"[\u3400-\u9fffA-Za-z0-9]", text))
        capacity = duration * 5.0
    else:
        units = len(re.findall(r"\b[\w'-]+\b", text))
        capacity = duration * 3.0
    if units > capacity + 1:
        raise ValueError(f"镜头 {shot_id} 的逐字旁白在正常语速下无法读完。")


def _render_srt(plan: dict[str, Any]) -> str:
    cues = []
    cue_number = 1
    for shot in plan["shots"]:
        narration = str(shot.get("narration") or "").strip()
        if not narration:
            continue
        cues.extend(
            [
                str(cue_number),
                f"{_srt_time(float(shot['start_seconds']))} --> {_srt_time(float(shot['end_seconds']))}",
                narration,
                "",
            ]
        )
        cue_number += 1
    return "\n".join(cues).rstrip() + "\n"


def _srt_time(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _render_requirements(state: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# 视频策划需求",
            "",
            f"- 产品：{state['product']['title']}（{state['product']['id']}）",
            f"- 平台：{', '.join(state['platforms'])}",
            f"- 语言：{state['language_version']}",
            f"- 时长：{state['duration_seconds']} 秒",
            "- 画幅：9:16",
            "- 公开趋势搜索：不执行",
            "- 来源视频原声：不使用",
            f"- 专属接口 revision：{state['interface']['interface_revision']}",
            "- 终点：确认逐镜头方案与旁白并自动生成 SRT",
            "",
        ]
    )


def _render_shot_plan(plan: dict[str, Any]) -> str:
    lines = [
        "# 可直接制作的逐镜头方案",
        "",
        f"- 产品：{plan['product_title']}",
        f"- 平台：{', '.join(plan['platforms'])}",
        f"- 语言：{plan['language_version']}",
        f"- 时长：{plan['duration_seconds']} 秒",
        "- 画幅：9:16",
        f"- 状态：{plan['status']}",
        "",
    ]
    for shot in plan["shots"]:
        lines.extend(
            [
                f"## 镜头 {shot['shot_id']}｜{shot['start_seconds']:.3f}–{shot['end_seconds']:.3f} 秒",
                "",
                f"- 用途：{shot['purpose']}",
                f"- 画面：{shot['visual_action']}",
                f"- 运镜：{shot['camera']}",
                f"- 转场：{shot['transition']}",
                f"- 剪辑提示：{shot['editing_guidance']}",
                f"- 素材模式：{shot['material']['mode']}",
                *_render_material_lines(shot["material"]),
                f"- 旁白：{shot.get('narration') or '（有意静默）'}",
                "",
            ]
        )
    return "\n".join(lines)


def _render_shot_plan_summary(plan: dict[str, Any]) -> str:
    return f"已生成 {len(plan['shots'])} 个镜头、总时长 {plan['duration_seconds']} 秒的逐镜头方案与逐字旁白，等待一次整体确认。"


def _render_material_lines(material: dict[str, Any]) -> list[str]:
    mode = material.get("mode")
    if mode == "official_image":
        return [
            f"- 素材卡：{material.get('card_id')}",
            f"- 原图路径：{material.get('source_path')}",
            f"- 检查预览：{material.get('preview_path')}",
            f"- 像素检查：{json.dumps(material.get('inspection') or {}, ensure_ascii=False)}",
            f"- 风险检查：{json.dumps(material.get('risk_checks') or {}, ensure_ascii=False)}",
        ]
    if mode == "real_video_segment":
        return [
            f"- 视频资产：{material.get('video_asset_id')}",
            f"- 视频档案：{material.get('profile_id')}（{material.get('profile_revision')}）",
            f"- 来源范围：{material.get('source_start_seconds')}–{material.get('source_end_seconds')} 秒",
            f"- 静音预览：{material.get('preview_path')}",
            "- 原声策略：visual-only / 不使用来源音频",
        ]
    return [
        "- 模拟标识：simulated",
        f"- 正式应用场景：{material.get('application_card_id')}",
        f"- 产品参考卡：{material.get('product_reference_card_id') or '不显示具体产品'}",
        f"- 产品参考预览：{material.get('product_reference_preview_path') or '无'}",
    ]


def _confirmation_media_paths(plan: dict[str, Any]) -> tuple[str, ...]:
    paths: list[str] = []
    for shot in plan.get("shots", []):
        material = dict(shot.get("material") or {})
        for key in ("preview_path", "product_reference_preview_path"):
            value = str(material.get(key) or "")
            if value and value not in paths:
                paths.append(value)
    return tuple(paths)


def _render_pending_decision(interview: dict[str, Any]) -> str:
    pending = dict(interview.get("pending_decision") or {})
    return "\n".join(
        [
            f"问题：{pending.get('question', '')}",
            f"建议：{pending.get('recommendation', '')}",
            f"理由：{pending.get('reason', '')}",
            f"来源：{pending.get('source_type', '')}",
            "是否确认？",
        ]
    )


def _normalize_platforms(platforms: list[str] | tuple[str, ...]) -> list[str]:
    normalized = list(dict.fromkeys(str(item).strip().casefold() for item in platforms if str(item).strip()))
    if not normalized or any(item not in SUPPORTED_PLATFORMS for item in normalized):
        raise ValueError("视频策划只支持 youtube_shorts 和 tiktok。")
    return normalized


def _normalize_language(language: str) -> str:
    value = str(language).strip().casefold()
    if value not in SUPPORTED_LANGUAGES:
        raise ValueError("视频策划只支持中文 zh 或英文 en。")
    return value


def _normalize_duration(duration: int) -> int:
    if isinstance(duration, bool) or int(duration) != duration:
        raise ValueError("视频策划时长必须是整数秒。")
    value = int(duration)
    if not MIN_DURATION_SECONDS <= value <= MAX_DURATION_SECONDS:
        raise ValueError("视频策划时长必须在 15–90 秒之间。")
    return value


def _select_product_title(product: dict[str, Any], language: str) -> str:
    candidates = [str(product.get("title") or ""), *[str(item) for item in product.get("aliases", [])]]
    if language == "zh":
        return candidates[0]
    english = next(
        (item for item in candidates if re.search(r"[A-Za-z]", item) and not re.search(r"[\u3400-\u9fff]", item)),
        None,
    )
    if not english:
        raise ValueError("正式产品接口中没有可用于英文版本的英文产品名称。")
    return english


def _unique_run_dir(root: Path, base: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    candidate = root / base
    counter = 2
    while candidate.exists():
        candidate = root / f"{base}_{counter}"
        counter += 1
    return candidate


def _archive_current_delivery(root: Path, state: dict[str, Any]) -> None:
    revision = int(state.get("current_revision") or 0)
    revision_dir = root / "revisions" / f"revision_{revision:04d}"
    if revision_dir.is_dir():
        return
    revision_dir.mkdir(parents=True, exist_ok=False)
    for name in ("shot_plan.json", "shot_plan.md", "storyboard.srt"):
        source = root / name
        if source.is_file():
            shutil.copy2(source, revision_dir / name)


def _revalidate_referenced_knowledge(root: Path, state: dict[str, Any], plan: dict[str, Any]) -> None:
    paths = _paths_from_state(state)
    manifest = read_video_planner_manifest(paths)
    product = next(
        (item for item in read_video_planner_products(paths) if item.get("id") == state["product"]["id"]),
        None,
    )
    if product is None or product.get("projection_fingerprint") != state["interface"]["product_fingerprint"]:
        raise ValueError("产品知识已发生实质变更或撤销；必须新建视频策划运行。")
    interview = _read_json(root / "interview.json")
    for evidence_items in dict(interview.get("decision_evidence") or {}).values():
        for evidence in evidence_items:
            card = _read_current_card_or_new_run(paths, str(evidence.get("card_id") or ""), "事实证据")
            if card.get("projection_fingerprint") != evidence.get("projection_fingerprint"):
                raise ValueError("已确认 brief 的事实证据发生实质变更；必须新建视频策划运行。")
    for shot in plan.get("shots", []):
        material = dict(shot.get("material") or {})
        mode = material.get("mode")
        if mode == "official_image":
            card = _read_current_card_or_new_run(paths, str(material["card_id"]), "图片素材")
            if card.get("projection_fingerprint") != material.get("card_fingerprint"):
                raise ValueError("已引用图片素材发生实质变更；必须新建视频策划运行。")
            source_path = Path(str(material.get("source_path") or ""))
            preview_path = Path(str(material.get("preview_path") or ""))
            if (
                not source_path.is_file()
                or _file_sha256(source_path) != material.get("source_fingerprint")
                or not preview_path.is_file()
                or _file_sha256(preview_path) != material.get("preview_fingerprint")
            ):
                raise ValueError("已选图片内容指纹发生变化；必须新建视频策划运行。")
        elif mode == "real_video_segment":
            try:
                detail = read_video_planner_video_detail(paths, str(material["profile_id"]))
            except KeyError as exc:
                raise ValueError("已引用视频档案被撤销；必须新建视频策划运行。") from exc
            if detail.get("profile_revision") != material.get("profile_revision"):
                raise ValueError("已引用视频档案发生实质变更；必须新建视频策划运行。")
            revalidate_video_planning_material(paths, state["run_id"], material)
        elif mode == "ai_simulation":
            card = _read_current_card_or_new_run(paths, str(material["application_card_id"]), "AI 应用场景")
            if card.get("projection_fingerprint") != material.get("application_card_fingerprint"):
                raise ValueError("AI 模拟所依据的应用场景知识已变更；必须新建视频策划运行。")
            reference_id = str(material.get("product_reference_card_id") or "")
            if reference_id:
                reference = _read_current_card_or_new_run(paths, reference_id, "AI 产品参考图")
                if reference.get("projection_fingerprint") != material.get("product_reference_fingerprint"):
                    raise ValueError("AI 模拟所依据的产品参考图已变更；必须新建视频策划运行。")
                source_path = Path(str(material.get("product_reference_source_path") or ""))
                preview_path = Path(str(material.get("product_reference_preview_path") or ""))
                if (
                    not source_path.is_file()
                    or _file_sha256(source_path) != material.get("product_reference_source_fingerprint")
                    or not preview_path.is_file()
                    or _file_sha256(preview_path) != material.get("product_reference_preview_fingerprint")
                ):
                    raise ValueError("AI 产品参考图片内容指纹发生变化；必须新建视频策划运行。")
    if manifest.get("agent_id") != "tuolin-video-planner":
        raise ValueError("视频策划专属知识接口已失效。")


def _paths_from_state(state: dict[str, Any]) -> ProjectPaths:
    value = dict(state.get("project_paths") or {})
    required = {"project_dir", "raw_dir", "knowledge_dir", "generated_dir"}
    if not required.issubset(value):
        raise ValueError("视频策划运行缺少固定项目路径。")
    return ProjectPaths(
        project_dir=Path(value["project_dir"]),
        raw_dir=Path(value["raw_dir"]),
        knowledge_dir=Path(value["knowledge_dir"]),
        generated_dir=Path(value["generated_dir"]),
    )


def _card_matches_product(card: dict[str, Any], product_id: str) -> bool:
    if card.get("id") == product_id:
        return True
    frontmatter = dict(card.get("frontmatter") or {})
    related = {
        str(frontmatter.get("product_id") or ""),
        *[str(item) for item in frontmatter.get("related_products", [])],
    }
    return product_id in related


def _validate_planning_evidence(
    paths: ProjectPaths,
    evidence: list[dict[str, Any]],
    product_id: str,
) -> list[dict[str, Any]]:
    validated = []
    for item in evidence:
        card_id = str(item.get("card_id") or "")
        if not card_id:
            raise ValueError("事实证据缺少 card_id。")
        card = read_video_planner_card(paths, card_id)
        if card.get("draft_only") or card.get("status") != "official":
            raise ValueError("事实证据必须来自正式且可用的专属接口知识卡。")
        if not _evidence_matches_product(paths, card, product_id):
            raise ValueError("事实证据不属于当前产品。")
        validated.append({**item, "projection_fingerprint": card["projection_fingerprint"]})
    return validated


def _read_current_card_or_new_run(paths: ProjectPaths, card_id: str, label: str) -> dict[str, Any]:
    try:
        return read_video_planner_card(paths, card_id)
    except KeyError as exc:
        raise ValueError(f"已引用{label}被撤销；必须新建视频策划运行。") from exc


def _evidence_matches_product(paths: ProjectPaths, card: dict[str, Any], product_id: str) -> bool:
    if _card_matches_product(card, product_id):
        return True
    product = read_video_planner_card(paths, product_id)
    frontmatter = dict(product.get("frontmatter") or {})
    referenced = {
        *[str(item) for item in frontmatter.get("evidence_refs", [])],
        *[str(item) for item in frontmatter.get("related_refs", [])],
    }
    return str(card.get("id") or "") in referenced


def _validate_prefixed_image_checks(
    paths: ProjectPaths,
    card: dict[str, Any],
    material: dict[str, Any],
    prefix: str,
    shot_id: str,
) -> None:
    source_path = Path(str(material.get(f"{prefix}_source_path") or "")).expanduser()
    preview_path = Path(str(material.get(f"{prefix}_preview_path") or "")).expanduser()
    if not source_path.is_file() or source_path.suffix.casefold() not in IMAGE_SUFFIXES:
        raise ValueError(f"镜头 {shot_id} 的产品参考图片路径无效。")
    _validate_card_source_path(paths, card, source_path, shot_id)
    if not preview_path.is_file():
        raise ValueError(f"镜头 {shot_id} 的产品参考预览不存在。")
    inspection = dict(material.get(f"{prefix}_inspection") or {})
    required = {"subject", "clarity", "composition", "vertical_crop", "near_duplicate_of"}
    if not required.issubset(inspection):
        raise ValueError(f"镜头 {shot_id} 的产品参考图片尚未完成像素级检查。")
    risk_checks = dict(material.get(f"{prefix}_risk_checks") or {})
    risk_fields = {"product_identity", "rights", "privacy", "test_meaning", "claim_risk"}
    if material.get(f"{prefix}_confirmable") is not True or set(risk_checks) != risk_fields:
        raise ValueError(f"镜头 {shot_id} 的产品参考图片风险检查不完整。")
    if any(value != "clear" for value in risk_checks.values()):
        raise ValueError(f"镜头 {shot_id} 的产品参考图片存在未解决风险。")
    material[f"{prefix}_source_fingerprint"] = _file_sha256(source_path)
    material[f"{prefix}_preview_fingerprint"] = _file_sha256(preview_path)


def _ai_simulation_permitted(scope: str) -> bool:
    normalized = scope.strip().casefold()
    negative = ("不使用", "不允许", "禁止", "不得", "without ai", "no ai", "not allowed")
    if any(token in normalized for token in negative):
        return False
    affirmative = ("允许", "可以使用", "可使用", "permitted", "allowed", "may use")
    return any(token in normalized for token in affirmative)


def _accept_remaining_recommendations(
    paths: ProjectPaths,
    interview: dict[str, Any],
    recommendations: dict[str, dict[str, Any]],
    product_id: str,
) -> dict[str, Any]:
    updated = answer_planning_interview(interview, "按推荐")
    for key in PLANNING_BRIEF_FIELDS:
        if key not in updated.get("remaining_fields", []):
            continue
        entry = dict(recommendations.get(key) or {})
        value = str(entry.get("recommendation") or entry.get("value") or "").strip()
        reason = str(entry.get("reason") or "").strip()
        if not value or not reason:
            raise ValueError(f"全部剩余建议缺少 {key} 的推荐或理由。")
        evidence = list(entry.get("evidence") or [])
        if key in FACT_GROUNDED_FIELDS:
            evidence = _validate_planning_evidence(paths, evidence, product_id)
        updated["decisions"][key] = value
        updated["decision_sources"][key] = (
            "planning_inference" if entry.get("inference") else "confirmed_recommendation"
        )
        if evidence:
            updated["decision_evidence"][key] = evidence
        updated["history"].append(
            {
                "event": "remaining_recommendation_accepted",
                "decision_key": key,
                "value": value,
                "reason": reason,
            }
        )
        refresh_planning_interview(updated)
    refresh_planning_interview(updated)
    if not updated.get("completed"):
        raise ValueError("全部剩余建议未覆盖所有未决策字段。")
    return updated


def _validate_card_source_path(
    paths: ProjectPaths,
    card: dict[str, Any],
    source_path: Path,
    shot_id: str,
) -> None:
    declared = list(dict(card.get("frontmatter") or {}).get("source_paths") or [])
    allowed: set[Path] = set()
    for value in declared:
        ref = str(value).replace("\\", "/").strip()
        if ref.startswith("raw/"):
            candidate = paths.raw_dir / ref[4:]
        else:
            candidate = Path(ref).expanduser()
            if not candidate.is_absolute():
                candidate = paths.project_dir / candidate
        allowed.add(candidate.resolve())
    if source_path.resolve() not in allowed:
        raise ValueError(f"镜头 {shot_id} 的图片路径未由素材卡声明。")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_forbidden_plan_fields(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            normalized_key = str(key).casefold()
            if any(token in normalized_key for token in FORBIDDEN_PLAN_FIELD_TOKENS):
                found.append(child_path)
            found.extend(_find_forbidden_plan_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_plan_fields(child, f"{path}[{index}]"))
    return found


def _load_state(root: Path) -> dict[str, Any]:
    if not root.is_dir():
        raise FileNotFoundError(root)
    state = _read_json(root / "workflow_state.json")
    if state.get("schema_version") != "video-planning-state-v1":
        raise ValueError("无效的视频策划运行状态。")
    return state


def _save_state(root: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(root / "workflow_state.json", state)


def _append_change(root: Path, message: str) -> None:
    path = root / "change_log.md"
    existing = path.read_text(encoding="utf-8") if path.is_file() else "# 变更记录\n\n"
    timestamp = datetime.now(timezone.utc).isoformat()
    _write_text(path, existing + f"- {timestamp} — {message}\n")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)

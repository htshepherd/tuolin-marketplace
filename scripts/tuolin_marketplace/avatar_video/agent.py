from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..kb.agent_specific_interfaces import (
    ensure_registered_agent_interfaces_current,
    read_avatar_video_cards,
    read_avatar_video_manifest,
    read_avatar_video_products,
)
from ..shared.project_layout import ProjectPaths
from .media import probe_media, run_ffmpeg
from .composition import FFmpegComposer, HyperFramesAdapter, HyperFramesUnavailable, validate_composition_output
from .captions import write_srt
from .providers import (
    claim_provider_execution,
    find_provider_attempt,
    provider_input_fingerprint,
    read_provider_attempts,
    redact_text,
    record_provider_attempt,
    review_provider_attempt,
    transition_provider_attempt,
)
from .provider_adapters import (
    FishAudioAdapter,
    HeyGenAdapter,
    HeyGenCLIAdapter,
    ProviderTaskFailed,
    ProviderTaskPending,
    SupportVisualAdapter,
)
from .interview import (
    AVATAR_BRIEF_FIELDS,
    answer_avatar_decision,
    build_avatar_interview,
    propose_avatar_decision,
    render_pending_avatar_decision,
)


MIN_DURATION_SECONDS = 30
MAX_DURATION_SECONDS = 90
SUPPORTED_PLATFORMS = {"en": ("youtube_shorts",), "zh": ("kuaishou", "douyin")}
REQUIRED_BRIEF_FIELDS = AVATAR_BRIEF_FIELDS


@dataclass(frozen=True)
class AvatarVideoResult:
    run_dir: str
    status: str
    phase: str
    output_paths: tuple[str, ...]
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_avatar_video_run(
    paths: ProjectPaths,
    request_text: str,
    *,
    product_id: str,
    language_version: str,
    duration_seconds: int,
    initial_brief: dict[str, str] | None = None,
    invoked_skill: str | None = None,
    test_mode: bool = False,
    now: datetime | None = None,
) -> AvatarVideoResult:
    if invoked_skill != "$tuolin-avatar-video":
        raise ValueError("数字人口播任务必须显式调用 $tuolin-avatar-video。")
    ensure_registered_agent_interfaces_current(paths)
    manifest = read_avatar_video_manifest(paths)
    if manifest.get("agent_id") != "tuolin-avatar-video" or manifest.get("raw_access") is not False:
        raise ValueError("数字人口播专属知识接口无效。")
    language = str(language_version).strip().casefold()
    if language not in SUPPORTED_PLATFORMS:
        raise ValueError("数字人口播只支持 zh 或 en 单语言运行。")
    duration = int(duration_seconds)
    if duration < MIN_DURATION_SECONDS or duration > MAX_DURATION_SECONDS:
        raise ValueError("数字人口播时长必须是30–90秒整数。")
    product = next((item for item in read_avatar_video_products(paths) if item.get("id") == product_id), None)
    if product is None:
        raise ValueError("产品未发布到数字人口播专属知识接口。")
    sales_expression_references = [
        _sales_expression_reference(card)
        for card in read_avatar_video_cards(paths, "sales_material")
        if _card_matches_product(card, product_id)
    ]
    brief = {key: str(value).strip() for key, value in dict(initial_brief or {}).items() if str(value).strip()}
    interview = build_avatar_interview(brief)
    phase = "ready_for_plan" if interview["completed"] else "interview"
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^a-z0-9_]+", "_", product_id.split("/", 1)[-1].casefold()).strip("_") or "product"
    root = paths.generated_dir / "reports" / "avatar-video"
    run_dir = _unique_run_dir(root, f"{timestamp}_{slug}_{language}")
    for relative in ("providers", "inputs", "renders", "revisions", "delivery"):
        (run_dir / relative).mkdir(parents=True, exist_ok=True)
    state = {
        "schema_version": "avatar-video-state-v1",
        "run_id": run_dir.name,
        "status": "active",
        "phase": phase,
        "request_text": request_text.strip(),
        "product": product,
        "sales_expression_references": sales_expression_references,
        "language_version": language,
        "platforms": list(SUPPORTED_PLATFORMS[language]),
        "duration_seconds": duration,
        "aspect_ratio": "9:16",
        "interface": {
            "agent_id": manifest["agent_id"],
            "interface_revision": manifest["interface_revision"],
            "source_knowledge_revision": manifest["source_knowledge_revision"],
            "product_fingerprint": product["projection_fingerprint"],
        },
        "project_dir": str(paths.project_dir),
        "project_config": {
            "raw_dir": str(paths.raw_dir),
            "knowledge_dir": str(paths.knowledge_dir),
            "generated_dir": str(paths.generated_dir),
        },
        "brief": brief,
        "test_mode": bool(test_mode),
        "confirmations": {"plan": False, "inputs": False, "presenter": False, "final": False},
        "files": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(run_dir / "workflow_state.json", state)
    _write_json(run_dir / "brief.json", brief)
    _write_json(run_dir / "interview.json", interview)
    _append_change(run_dir, "创建独立数字人口播运行并固定专属知识接口revision。")
    return AvatarVideoResult(
        str(run_dir),
        "created",
        phase,
        (str(run_dir / "workflow_state.json"), str(run_dir / "brief.json")),
        "数字人口播运行已创建。" if phase == "interview" else "业务信息已充分，可以生成完整生产方案。",
    )


def propose_avatar_interview_decision(run_dir: Path | str, proposal: dict[str, Any]) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    if state["phase"] != "interview":
        raise ValueError("当前阶段不能提出数字人口播访谈问题。")
    interview = propose_avatar_decision(_read_json(root / "interview.json"), proposal)
    _write_json(root / "interview.json", interview)
    _append_change(root, f"提出数字人口播访谈决策：{proposal.get('decision_key')}。")
    return AvatarVideoResult(
        str(root),
        "awaiting_confirmation",
        state["phase"],
        (str(root / "interview.json"),),
        render_pending_avatar_decision(interview),
    )


def handle_avatar_interview_reply(run_dir: Path | str, reply: str) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    if state["phase"] != "interview":
        raise ValueError("当前阶段没有待回答的数字人口播访谈问题。")
    interview = answer_avatar_decision(_read_json(root / "interview.json"), reply)
    _write_json(root / "interview.json", interview)
    state["brief"] = dict(interview["decisions"])
    _write_json(root / "brief.json", state["brief"])
    if interview["completed"]:
        state["phase"] = "ready_for_plan"
        message = "数字人口播访谈已充分，可以生成完整生产方案。"
    else:
        message = "当前决策已记录；请提出下一项最有价值的单一业务问题。"
    _save_state(root, state)
    _append_change(root, "处理一项数字人口播访谈回复。")
    return AvatarVideoResult(str(root), "updated", state["phase"], (str(root / "interview.json"),), message)


def record_avatar_material_inspection(run_dir: Path | str, assessment: dict[str, Any]) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    if state["phase"] not in {"interview", "ready_for_plan", "awaiting_plan_confirmation"}:
        raise ValueError("当前阶段不能记录数字人口播素材检查。")
    path_value = str(assessment.get("path") or "").strip()
    if not path_value:
        raise ValueError("素材检查缺少图片路径。")
    authorized = _authorized_visual_card(state, Path(path_value).expanduser().resolve())
    required = ("subject", "clarity", "composition", "vertical_crop", "near_duplicate_group", "status")
    missing = [key for key in required if not str(assessment.get(key) or "").strip()]
    if missing:
        raise ValueError("素材检查缺少字段：" + ", ".join(missing))
    normalized = {
        "path": str(Path(path_value).expanduser().resolve()),
        "card_id": authorized["id"],
        "projection_fingerprint": authorized["projection_fingerprint"],
        "subject": str(assessment["subject"]).strip(),
        "clarity": str(assessment["clarity"]).strip(),
        "composition": str(assessment["composition"]).strip(),
        "vertical_crop": str(assessment["vertical_crop"]).strip(),
        "near_duplicate_group": str(assessment["near_duplicate_group"]).strip(),
        "status": str(assessment["status"]).strip(),
        "risks": [str(item).strip() for item in list(assessment.get("risks") or []) if str(item).strip()],
        "inspected_at": datetime.now(timezone.utc).isoformat(),
    }
    inspections_path = root / "material_inspections.json"
    existing = _read_json(inspections_path) if inspections_path.exists() else {"schema_version": "avatar-material-inspections-v1", "items": []}
    existing["items"] = [item for item in existing["items"] if item.get("path") != normalized["path"]]
    existing["items"].append(normalized)
    existing["items"].sort(key=lambda item: item["path"])
    _write_json(inspections_path, existing)
    _append_change(root, f"记录正式图片像素检查：{authorized['id']}。")
    return AvatarVideoResult(str(root), "recorded", state["phase"], (str(inspections_path), normalized["path"]), "素材像素检查已记录。")


def approve_avatar_material_exception(run_dir: Path | str, decision: dict[str, Any]) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    kind = str(decision.get("type") or "").strip()
    if kind not in {"shorten_duration", "deliberate_repetition", "bounded_simulation"}:
        raise ValueError("素材不足只允许缩短时长、明确重复或受约束模拟。")
    normalized = {"type": kind, "reason": str(decision.get("reason") or "").strip(), "approved_at": datetime.now(timezone.utc).isoformat()}
    if not normalized["reason"]:
        raise ValueError("素材例外必须记录用户确认原因。")
    if kind == "shorten_duration":
        duration = int(decision.get("duration_seconds") or 0)
        if duration < MIN_DURATION_SECONDS or duration > MAX_DURATION_SECONDS:
            raise ValueError("缩短后的数字人口播时长仍必须是30–90秒整数。")
        if duration >= int(state["duration_seconds"]):
            raise ValueError("缩短时长必须小于当前目标。")
        state["duration_seconds"] = duration
    state["material_exception"] = normalized
    state["confirmations"]["plan"] = False
    if state["phase"] == "ready_for_input_generation":
        state["phase"] = "ready_for_plan"
    _save_state(root, state)
    _append_change(root, f"用户确认素材例外：{kind}。")
    return AvatarVideoResult(str(root), "approved", state["phase"], (str(root / "workflow_state.json"),), "素材例外已记录。")


def resume_avatar_video_run(run_dir: Path | str) -> AvatarVideoResult:
    root = Path(run_dir).expanduser().resolve()
    state = _load_state(root)
    try:
        manifest = read_avatar_video_manifest(_paths_from_state(state))
    except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        state["status"] = "blocked_stale_interface"
        state["phase"] = "blocked"
        state["blocker"] = {"code": "avatar_interface_unavailable", "message": redact_text(str(exc))}
        _save_state(root, state)
        return AvatarVideoResult(str(root), state["status"], state["phase"], (str(root / "workflow_state.json"),), "数字人口播专属知识接口不可用。")
    expected = state.get("interface", {})
    if (
        manifest.get("agent_id") != "tuolin-avatar-video"
        or manifest.get("raw_access") is not False
        or manifest.get("interface_revision") != expected.get("interface_revision")
    ):
        state["status"] = "blocked_stale_interface"
        state["phase"] = "blocked"
        state["blocker"] = {
            "code": "avatar_interface_revision_changed",
            "expected_revision": expected.get("interface_revision"),
            "current_revision": manifest.get("interface_revision"),
            "message": "运行固定的数字人口播知识接口revision已不可用或发生变化。",
        }
        _save_state(root, state)
        return AvatarVideoResult(str(root), state["status"], state["phase"], (str(root / "workflow_state.json"),), state["blocker"]["message"])
    current_product = next((item for item in read_avatar_video_products(_paths_from_state(state)) if item.get("id") == state["product"]["id"]), None)
    if current_product is None or current_product.get("projection_fingerprint") != expected.get("product_fingerprint"):
        state["status"] = "blocked_stale_interface"
        state["phase"] = "blocked"
        state["blocker"] = {
            "code": "avatar_product_projection_changed",
            "message": "运行固定的产品事实或素材profile已经撤销或改变。",
        }
        _save_state(root, state)
        return AvatarVideoResult(str(root), state["status"], state["phase"], (str(root / "workflow_state.json"),), state["blocker"]["message"])
    artifact_error = _resume_artifact_error(root, state)
    if artifact_error:
        state["status"] = "incomplete"
        state["phase"] = "blocked"
        state["blocker"] = {"code": "avatar_artifact_missing_or_corrupt", "message": artifact_error}
        _save_state(root, state)
        return AvatarVideoResult(str(root), "incomplete", "blocked", (str(root / "workflow_state.json"),), artifact_error)
    message = {
        "interview": "继续数字人口播访谈。",
        "ready_for_plan": "业务信息已充分，可以生成完整生产方案。",
        "awaiting_plan_confirmation": "请确认当前完整生产方案。",
        "ready_for_input_generation": "生产方案已确认，可以执行已授权输入生成。",
        "awaiting_input_confirmation": "请完整试听音频并审阅所有输入。",
        "ready_for_presenter_generation": "输入已确认，可以生成数字人原片。",
        "awaiting_presenter_confirmation": "请完整观看数字人原片。",
        "ready_for_composition": "数字人原片已确认，可以开始包装。",
        "awaiting_final_confirmation": "请完整观看最终成片。",
        "completed": "数字人口播运行已完成。",
    }.get(str(state.get("phase")), "已恢复数字人口播运行。")
    latest_failed = next((item for item in reversed(read_provider_attempts(root)) if item.get("status") in {"failed", "rejected"}), None)
    if latest_failed:
        message = f"最近的{latest_failed['provider']}尝试状态为{latest_failed['status']}；{message}"
    return AvatarVideoResult(str(root), str(state.get("status")), str(state.get("phase")), (str(root / "workflow_state.json"),), message)


def write_avatar_production_plan(run_dir: Path | str, plan: dict[str, Any]) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    if state["phase"] not in {"ready_for_plan", "awaiting_plan_confirmation"}:
        raise ValueError("当前阶段不能写入数字人口播生产方案。")
    normalized = _normalize_plan(root, state, plan)
    _write_json(root / "production_plan.json", normalized)
    _write_text(root / "production_plan.md", _render_plan(normalized))
    state["phase"] = "awaiting_plan_confirmation"
    state["confirmations"]["plan"] = False
    state["files"]["production_plan"] = "production_plan.json"
    _save_state(root, state)
    _append_change(root, "写入完整数字人口播生产方案草稿。")
    return AvatarVideoResult(
        str(root),
        "awaiting_confirmation",
        state["phase"],
        (str(root / "production_plan.md"), str(root / "production_plan.json")),
        _render_plan(normalized),
    )


def confirm_avatar_production_plan(run_dir: Path | str) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    if state["phase"] != "awaiting_plan_confirmation":
        raise ValueError("当前没有待确认的数字人口播生产方案。")
    plan = _read_json(root / "production_plan.json")
    plan["status"] = "confirmed"
    plan["confirmed_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(root / "production_plan.json", plan)
    state["confirmations"]["plan"] = True
    pending_revision = dict(state.get("pending_revision") or {})
    if pending_revision:
        resume_phase = str(pending_revision.get("resume_phase") or "ready_for_composition")
        if resume_phase == "awaiting_retry_authorization":
            state["retry_request"] = dict(state.pop("pending_retry_after_plan"))
        state["phase"] = resume_phase
        state.pop("pending_revision", None)
        _save_state(root, state)
        _append_change(root, "确认受保护字段修订后的生产方案；按精确依赖恢复。")
        return AvatarVideoResult(str(root), "confirmed", state["phase"], (str(root / "production_plan.json"),), "修订方案已确认。")
    state["execution_authorization"] = {
        "authorization_id": "initial-" + plan["revision"],
        "plan_revision": plan["revision"],
        "authorized_once": True,
        "operations": [
            {"provider": "fish_audio", "attempts": 1},
            {"provider": "heygen", "attempts": 1},
            {
                "provider": "support_images",
                "provider_name": plan.get("support_visual_batch", {}).get("provider"),
                "attempts": 1 if plan.get("support_visual_batch", {}).get("images") else 0,
            },
        ],
        "estimated_consumption": plan.get("estimated_consumption", {}),
        "authorized_at": datetime.now(timezone.utc).isoformat(),
    }
    state["phase"] = "ready_for_input_generation"
    _save_state(root, state)
    _append_change(root, "确认完整生产方案并授权已披露的首次供应商执行范围。")
    return AvatarVideoResult(str(root), "confirmed", state["phase"], (str(root / "production_plan.json"),), "生产方案已确认。")


def generate_mock_avatar_inputs(run_dir: Path | str, *, ffmpeg_command: str = "ffmpeg") -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    if not state.get("test_mode"):
        raise ValueError("伪供应商输入只能用于明确的test_mode运行。")
    if not state["confirmations"]["plan"]:
        raise ValueError("生产方案未确认，不能生成输入。")
    plan = _read_json(root / "production_plan.json")
    if state["phase"] not in {"ready_for_input_generation", "awaiting_input_confirmation"}:
        raise ValueError("当前阶段不能生成Fish输入。")
    fish_authorization = _provider_authorization(state, "fish_audio")
    support_images = list(plan.get("support_visual_batch", {}).get("images") or [])
    support_authorization = _provider_authorization(state, "support_images") if support_images else None
    state["input_generation"] = {
        "strategy": "parallel" if support_images else "audio_only",
        "providers": ["fish_audio"] + (["support_images"] if support_images else []),
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    with ThreadPoolExecutor(max_workers=2 if support_images else 1) as executor:
        fish_future = executor.submit(
            _generate_mock_fish_attempt,
            root,
            state,
            plan,
            fish_authorization,
            ffmpeg_command,
        )
        support_future = (
            executor.submit(
                _generate_mock_support_attempt,
                root,
                state,
                plan,
                support_authorization or {},
                ffmpeg_command,
            )
            if support_images
            else None
        )
        fish_result = fish_future.result()
        support_result = support_future.result() if support_future is not None else None
    audio_path = Path(fish_result["output"])
    state["files"]["narration_audio"] = str(audio_path.relative_to(root))
    current_attempts = dict(state.get("current_attempts") or {})
    current_attempts["fish_audio"] = fish_result["attempt_id"]
    output_paths = [str(audio_path)]
    if support_result is not None:
        current_attempts["support_images"] = support_result["attempt_id"]
        state["files"]["support_visual_manifest"] = str(Path(support_result["output"]).resolve().relative_to(root))
        state["files"]["support_visuals"] = [str(Path(path).resolve().relative_to(root)) for path in support_result["image_paths"]]
        output_paths.extend(support_result["image_paths"])
    else:
        state["files"]["support_visuals"] = []
    state["current_attempts"] = current_attempts
    state["input_generation"]["completed_at"] = datetime.now(timezone.utc).isoformat()
    state["phase"] = "awaiting_input_confirmation"
    _save_state(root, state)
    _append_change(root, "并行生成伪Fish完整音频和有界辅助图片批次；明确标记mock。")
    status = "idempotent" if fish_result.get("idempotent") and (support_result is None or support_result.get("idempotent")) else "mock_completed"
    return AvatarVideoResult(
        str(root),
        status,
        state["phase"],
        tuple(output_paths),
        "输入已生成：请完整试听音频并逐张审阅所有辅助图片，一次回复确认本批输入。",
    )


def _generate_mock_fish_attempt(
    root: Path,
    state: dict[str, Any],
    plan: dict[str, Any],
    authorization: dict[str, Any],
    ffmpeg_command: str,
) -> dict[str, Any]:
    settings = {**dict(plan["fish_audio"]), **dict(state.get("provider_overrides", {}).get("fish_audio", {}))}
    input_revision = plan["revision"] + ":" + authorization["authorization_id"]
    fingerprint = provider_input_fingerprint("fish_audio", input_revision, settings)
    existing = find_provider_attempt(root, "fish_audio", fingerprint)
    if existing is not None and Path(str(existing.get("output") or "")).is_file():
        return {**existing, "idempotent": True}
    duration = int(state["duration_seconds"])
    attempt_number = len(read_provider_attempts(root, "fish_audio")) + 1
    audio_path = root / "inputs" / f"fish-audio-mock-{attempt_number:04d}.wav"
    run_ffmpeg(
        [
            ffmpeg_command,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:sample_rate=48000:duration={duration}",
            "-c:a",
            "pcm_s16le",
            str(audio_path),
        ]
    )
    probe = probe_media(audio_path)
    attempt, _ = record_provider_attempt(
        root,
        provider="fish_audio",
        input_revision=input_revision,
        settings=settings,
        authorization_id=authorization["authorization_id"],
        mode="mock",
        status="mock_completed",
        output=str(audio_path),
        task_id=f"fish-mock-task-{attempt_number:04d}",
        estimated_consumption=authorization.get("estimated_consumption"),
        actual_consumption=0,
        media_probe=probe,
    )
    return {**attempt, "idempotent": False}


def generate_fish_audio_input(run_dir: Path | str, adapter: FishAudioAdapter) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    if not state["confirmations"]["plan"]:
        raise ValueError("生产方案未确认，不能调用Fish Audio。")
    if state["phase"] not in {"ready_for_input_generation", "awaiting_input_confirmation"}:
        raise ValueError("当前阶段不能调用Fish Audio。")
    plan = _read_json(root / "production_plan.json")
    if plan.get("support_visual_batch", {}).get("images"):
        raise ValueError("当前方案包含辅助图片，必须通过联合输入协调器并行执行。")
    authorization = _provider_authorization(state, "fish_audio")
    try:
        attempt = _generate_real_fish_attempt(root, state, plan, authorization, adapter)
    except Exception as exc:
        _mark_provider_retry_required(root, state, "fish_audio", authorization, exc)
        raise
    state["files"]["narration_audio"] = str(Path(attempt["output"]).resolve().relative_to(root))
    state["files"]["support_visuals"] = []
    state["current_attempts"] = {**dict(state.get("current_attempts") or {}), "fish_audio": attempt["attempt_id"]}
    state["phase"] = "awaiting_input_confirmation"
    _save_state(root, state)
    status = "idempotent" if attempt.get("idempotent") else "completed_pending_review"
    if status != "idempotent":
        _append_change(root, "Fish Audio生成完整真实音频，等待完整试听。")
    return AvatarVideoResult(str(root), status, state["phase"], (str(attempt["output"]),), "Fish Audio完整音频已生成，请完整试听后确认。")


def _generate_real_fish_attempt(
    root: Path,
    state: dict[str, Any],
    plan: dict[str, Any],
    authorization: dict[str, Any],
    adapter: FishAudioAdapter,
) -> dict[str, Any]:
    settings = {**dict(plan["fish_audio"]), **dict(state.get("provider_overrides", {}).get("fish_audio", {}))}
    input_revision = plan["revision"] + ":" + authorization["authorization_id"]
    fingerprint = provider_input_fingerprint("fish_audio", input_revision, settings)
    existing = find_provider_attempt(root, "fish_audio", fingerprint)
    if existing is not None and Path(str(existing.get("output") or "")).is_file():
        return {**existing, "idempotent": True}
    attempt_number = len(read_provider_attempts(root, "fish_audio")) + 1
    output_format = str(settings.get("format") or "wav").casefold()
    if output_format not in {"wav", "mp3", "opus"}:
        raise ValueError("不支持的Fish Audio输出格式。")
    output_path = root / "inputs" / f"fish-audio-{attempt_number:04d}.{output_format}"
    if not claim_provider_execution(
        root,
        provider="fish_audio",
        input_fingerprint=fingerprint,
        authorization_id=str(authorization["authorization_id"]),
    ):
        raise ValueError("Fish Audio执行授权已使用；提交状态不确定或结果已失败，付费重试需要新授权。")
    try:
        result = adapter.synthesize(
            narration=plan["narration"],
            voice_id=str(settings["voice_id"]),
            settings=settings,
            output_path=output_path,
        )
    except Exception:
        record_provider_attempt(
            root,
            provider="fish_audio",
            input_revision=input_revision,
            settings=settings,
            authorization_id=authorization["authorization_id"],
            mode="real",
            status="failed",
            output=str(output_path),
            task_id=f"fish-failed-{attempt_number:04d}",
            estimated_consumption=authorization.get("estimated_consumption"),
        )
        raise
    attempt, _ = record_provider_attempt(
        root,
        provider="fish_audio",
        input_revision=input_revision,
        settings=settings,
        authorization_id=authorization["authorization_id"],
        mode="real",
        status="completed_pending_review",
        output=result.output_path,
        task_id=result.external_task_id,
        estimated_consumption=authorization.get("estimated_consumption"),
        actual_consumption=result.actual_consumption,
        media_probe=result.media_probe,
    )
    return {**attempt, "idempotent": False}


def generate_avatar_inputs(
    run_dir: Path | str,
    fish_adapter: FishAudioAdapter,
    support_adapter: SupportVisualAdapter | None = None,
) -> AvatarVideoResult:
    """Generate the authorized real Fish/support batch concurrently."""

    root = Path(run_dir).resolve()
    state = _load_state(root)
    if not state["confirmations"]["plan"]:
        raise ValueError("生产方案未确认，不能生成供应商输入。")
    if state["phase"] not in {"ready_for_input_generation", "awaiting_input_confirmation"}:
        raise ValueError("当前阶段不能生成供应商输入。")
    plan = _read_json(root / "production_plan.json")
    support_items = list(plan.get("support_visual_batch", {}).get("images") or [])
    if not support_items:
        return generate_fish_audio_input(root, fish_adapter)
    if support_adapter is None:
        raise ValueError("方案包含辅助图片，但未连接辅助图片供应商适配器。")
    fish_authorization = _provider_authorization(state, "fish_audio")
    support_authorization = _provider_authorization(state, "support_images")
    results: dict[str, dict[str, Any]] = {}
    errors: dict[str, Exception] = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        fish_future = executor.submit(
            _generate_real_fish_attempt,
            root,
            state,
            plan,
            fish_authorization,
            fish_adapter,
        )
        support_future = executor.submit(
            _generate_real_support_attempt,
            root,
            state,
            plan,
            support_authorization,
            support_adapter,
        )
        for provider, future in (("fish_audio", fish_future), ("support_images", support_future)):
            try:
                results[provider] = future.result()
            except Exception as exc:
                errors[provider] = exc
    if errors:
        failed_provider = "fish_audio" if "fish_audio" in errors else "support_images"
        failed_authorization = fish_authorization if failed_provider == "fish_audio" else support_authorization
        _mark_provider_retry_required(root, state, failed_provider, failed_authorization, errors[failed_provider])
        raise errors[failed_provider]
    fish_attempt = results["fish_audio"]
    support_attempt = results["support_images"]
    state["files"]["narration_audio"] = str(Path(fish_attempt["output"]).resolve().relative_to(root))
    state["files"]["support_visual_manifest"] = str(Path(support_attempt["output"]).resolve().relative_to(root))
    state["files"]["support_visuals"] = [str(Path(path).resolve().relative_to(root)) for path in support_attempt["image_paths"]]
    state["current_attempts"] = {
        **dict(state.get("current_attempts") or {}),
        "fish_audio": fish_attempt["attempt_id"],
        "support_images": support_attempt["attempt_id"],
    }
    state["input_generation"] = {"strategy": "parallel", "providers": ["fish_audio", "support_images"]}
    state["phase"] = "awaiting_input_confirmation"
    _save_state(root, state)
    _append_change(root, "Fish Audio与真实辅助图片批次并行完成，等待一次联合验收。")
    status = "idempotent" if fish_attempt.get("idempotent") and support_attempt.get("idempotent") else "completed_pending_review"
    outputs = (str(fish_attempt["output"]), *[str(path) for path in support_attempt["image_paths"]])
    return AvatarVideoResult(str(root), status, state["phase"], outputs, "请完整试听音频并逐张查看全部辅助图片；一次回复联合确认。")


def _generate_real_support_attempt(
    root: Path,
    state: dict[str, Any],
    plan: dict[str, Any],
    authorization: dict[str, Any],
    adapter: SupportVisualAdapter,
) -> dict[str, Any]:
    batch = dict(plan["support_visual_batch"])
    settings = {**batch, **dict(state.get("provider_overrides", {}).get("support_images", {}))}
    input_revision = plan["revision"] + ":" + str(authorization["authorization_id"])
    fingerprint = provider_input_fingerprint("support_images", input_revision, settings)
    existing = find_provider_attempt(root, "support_images", fingerprint)
    if existing is not None and Path(str(existing.get("output") or "")).is_file():
        manifest = _read_json(Path(existing["output"]))
        if all(Path(path).is_file() for path in manifest.get("images", [])):
            return {**existing, "image_paths": list(manifest["images"]), "idempotent": True}
    attempt_number = len(read_provider_attempts(root, "support_images")) + 1
    batch_dir = root / "inputs" / "support-visuals" / f"batch-{attempt_number:04d}"
    if not claim_provider_execution(
        root,
        provider="support_images",
        input_fingerprint=fingerprint,
        authorization_id=str(authorization["authorization_id"]),
    ):
        raise ValueError("辅助图片执行授权已使用；提交状态不确定或结果已失败，付费重试需要新授权。")
    try:
        result = adapter.generate(batch=settings, output_dir=batch_dir)
    except Exception:
        record_provider_attempt(
            root,
            provider="support_images",
            input_revision=input_revision,
            settings=settings,
            authorization_id=str(authorization["authorization_id"]),
            mode="real",
            status="failed",
            output=str(batch_dir / "manifest.json"),
            task_id=f"support-failed-{attempt_number:04d}",
            estimated_consumption=authorization.get("estimated_consumption"),
        )
        raise
    attempt, _ = record_provider_attempt(
        root,
        provider="support_images",
        input_revision=input_revision,
        settings=settings,
        authorization_id=str(authorization["authorization_id"]),
        mode="real",
        status="completed_pending_review",
        output=result.manifest_path,
        task_id=result.external_task_id,
        estimated_consumption=authorization.get("estimated_consumption"),
        actual_consumption=result.actual_consumption,
        media_probe={"image_count": len(result.image_paths), "items": list(result.media_probes)},
    )
    return {**attempt, "image_paths": list(result.image_paths), "idempotent": False}


def _generate_mock_support_attempt(
    root: Path,
    state: dict[str, Any],
    plan: dict[str, Any],
    authorization: dict[str, Any],
    ffmpeg_command: str,
) -> dict[str, Any]:
    batch = dict(plan["support_visual_batch"])
    settings = {**batch, **dict(state.get("provider_overrides", {}).get("support_images", {}))}
    input_revision = plan["revision"] + ":" + str(authorization["authorization_id"])
    fingerprint = provider_input_fingerprint("support_images", input_revision, settings)
    existing = find_provider_attempt(root, "support_images", fingerprint)
    if existing is not None and Path(str(existing.get("output") or "")).is_file():
        manifest = _read_json(Path(existing["output"]))
        if all(Path(path).is_file() for path in manifest.get("images", [])):
            return {**existing, "image_paths": list(manifest["images"]), "idempotent": True}
    attempt_number = len(read_provider_attempts(root, "support_images")) + 1
    batch_dir = root / "inputs" / "support-visuals" / f"batch-{attempt_number:04d}"
    batch_dir.mkdir(parents=True, exist_ok=False)
    image_paths = []
    probes = []
    for index, item in enumerate(batch["images"], start=1):
        output = batch_dir / f"support-{index:02d}.png"
        run_ffmpeg(
            [
                ffmpeg_command,
                "-y",
                "-i",
                str(item["reference_path"]),
                "-vf",
                "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x182018,setsar=1",
                "-frames:v",
                "1",
                str(output),
            ]
        )
        image_paths.append(str(output))
        probes.append(probe_media(output))
    manifest_path = batch_dir / "manifest.json"
    _write_json(
        manifest_path,
        {
            "schema_version": "avatar-support-visual-batch-v1",
            "provider": batch["provider"],
            "count": len(image_paths),
            "images": image_paths,
            "items": batch["images"],
            "media_probes": probes,
            "viewer_facing_ai_label": False,
            "mode": "mock",
        },
    )
    attempt, _ = record_provider_attempt(
        root,
        provider="support_images",
        input_revision=input_revision,
        settings=settings,
        authorization_id=str(authorization["authorization_id"]),
        mode="mock",
        status="mock_completed",
        output=str(manifest_path),
        task_id=f"support-mock-task-{attempt_number:04d}",
        estimated_consumption=authorization.get("estimated_consumption"),
        actual_consumption=0,
        media_probe={"image_count": len(image_paths)},
    )
    return {**attempt, "image_paths": image_paths, "idempotent": False}


def confirm_avatar_inputs(run_dir: Path | str) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    if state["phase"] != "awaiting_input_confirmation":
        raise ValueError("当前没有待确认的数字人口播输入。")
    audio_path = root / state["files"]["narration_audio"]
    probe_media(audio_path)
    attempt_id = str(state.get("current_attempts", {}).get("fish_audio") or "")
    if not attempt_id:
        raise ValueError("运行缺少当前Fish尝试。")
    review_provider_attempt(root, "fish_audio", attempt_id, accepted=True, reason="用户完整试听并确认。")
    support_paths = [root / path for path in list(state.get("files", {}).get("support_visuals") or [])]
    for path in support_paths:
        probe = probe_media(path)
        if not probe["has_video"]:
            raise ValueError("辅助图片不可读。")
    support_attempt_id = str(state.get("current_attempts", {}).get("support_images") or "")
    if support_paths and not support_attempt_id:
        raise ValueError("运行缺少当前辅助图片尝试。")
    if support_attempt_id:
        review_provider_attempt(root, "support_images", support_attempt_id, accepted=True, reason="用户逐张审阅并确认。")
    state["confirmations"]["inputs"] = True
    state["phase"] = "ready_for_presenter_generation"
    _save_state(root, state)
    _append_change(root, "确认完整音频和全部辅助图片输入。")
    return AvatarVideoResult(str(root), "confirmed", state["phase"], tuple([str(audio_path), *[str(path) for path in support_paths]]), "完整音频和全部辅助图片已联合确认。")


def generate_mock_avatar_presenter(run_dir: Path | str, *, ffmpeg_command: str = "ffmpeg") -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    if not state.get("test_mode"):
        raise ValueError("伪HeyGen只能用于明确的test_mode运行。")
    if not state["confirmations"]["inputs"]:
        raise ValueError("输入未确认，不能生成数字人原片。")
    plan = _read_json(root / "production_plan.json")
    authorization = _provider_authorization(state, "heygen")
    settings = {**dict(plan["heygen"]), **dict(state.get("provider_overrides", {}).get("heygen", {}))}
    fish_attempt = str(state.get("current_attempts", {}).get("fish_audio") or "")
    input_revision = f"{plan['revision']}:{fish_attempt}:{authorization['authorization_id']}"
    fingerprint = provider_input_fingerprint("heygen", input_revision, settings)
    existing = find_provider_attempt(root, "heygen", fingerprint)
    if existing is not None and Path(str(existing.get("output") or "")).is_file():
        state["files"]["presenter_footage"] = str(Path(existing["output"]).resolve().relative_to(root))
        state["current_attempts"] = {**dict(state.get("current_attempts") or {}), "heygen": existing["attempt_id"]}
        state["phase"] = "awaiting_presenter_confirmation"
        _save_state(root, state)
        return AvatarVideoResult(str(root), "idempotent", state["phase"], (str(existing["output"]),), "相同输入的HeyGen尝试已存在，未重复提交。")
    if state["phase"] != "ready_for_presenter_generation":
        raise ValueError("当前阶段不能生成数字人原片。")
    image_path = Path(plan["selected_visuals"][0]["path"])
    audio_path = root / state["files"]["narration_audio"]
    attempt_number = len(read_provider_attempts(root, "heygen")) + 1
    output = root / "inputs" / f"heygen-presenter-mock-{attempt_number:04d}.mp4"
    duration = int(state["duration_seconds"])
    run_ffmpeg(
        [
            ffmpeg_command,
            "-y",
            "-loop",
            "1",
            "-i",
            str(image_path),
            "-i",
            str(audio_path),
            "-t",
            str(duration),
            "-vf",
            "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x101010,setsar=1",
            "-r",
            "10",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(output),
        ]
    )
    probe = probe_media(output)
    attempt, _ = record_provider_attempt(
        root,
        provider="heygen",
        input_revision=input_revision,
        settings=settings,
        authorization_id=authorization["authorization_id"],
        mode="mock",
        status="mock_completed",
        output=str(output),
        task_id=f"heygen-mock-task-{attempt_number:04d}",
        estimated_consumption=authorization.get("estimated_consumption"),
        actual_consumption=0,
        media_probe=probe,
    )
    state["files"]["presenter_footage"] = str(output.relative_to(root))
    state["current_attempts"] = {**dict(state.get("current_attempts") or {}), "heygen": attempt["attempt_id"]}
    state["phase"] = "awaiting_presenter_confirmation"
    _save_state(root, state)
    _append_change(root, "生成伪HeyGen完整原片；明确标记mock。")
    return AvatarVideoResult(str(root), "mock_completed", state["phase"], (str(output),), "伪数字人原片已生成，请完整观看。")


def generate_heygen_presenter(run_dir: Path | str, adapter: HeyGenAdapter | HeyGenCLIAdapter) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    if not state["confirmations"]["inputs"]:
        raise ValueError("输入未确认，不能调用HeyGen。")
    if state["phase"] not in {"ready_for_presenter_generation", "awaiting_presenter_confirmation"}:
        raise ValueError("当前阶段不能调用HeyGen。")
    plan = _read_json(root / "production_plan.json")
    authorization = _provider_authorization(state, "heygen")
    settings = {**dict(plan["heygen"]), **dict(state.get("provider_overrides", {}).get("heygen", {}))}
    avatar_id = str(settings.get("avatar_id") or "")
    fish_attempt = str(state.get("current_attempts", {}).get("fish_audio") or "")
    input_revision = f"{plan['revision']}:{fish_attempt}:{authorization['authorization_id']}"
    fingerprint = provider_input_fingerprint("heygen", input_revision, settings)
    existing = find_provider_attempt(root, "heygen", fingerprint)
    if existing is not None and Path(str(existing.get("output") or "")).is_file():
        state["files"]["presenter_footage"] = str(Path(existing["output"]).resolve().relative_to(root))
        state["current_attempts"] = {**dict(state.get("current_attempts") or {}), "heygen": existing["attempt_id"]}
        state["phase"] = "awaiting_presenter_confirmation"
        _save_state(root, state)
        return AvatarVideoResult(str(root), "idempotent", state["phase"], (str(existing["output"]),), "相同输入的HeyGen结果已存在，未重复提交。")
    resumable = (
        existing
        if isinstance(adapter, HeyGenCLIAdapter)
        and existing is not None
        and str(existing.get("status") or "") in {"submitted", "running", "completed_pending_review"}
        else None
    )
    attempt_number = int(resumable["attempt_number"]) if resumable else len(read_provider_attempts(root, "heygen")) + 1
    output_path = Path(str(resumable["output"])) if resumable else root / "inputs" / f"heygen-presenter-{attempt_number:04d}.mp4"
    audio_path = root / state["files"]["narration_audio"]
    active_attempt = resumable
    if resumable is None:
        claimed = claim_provider_execution(
            root,
            provider="heygen",
            input_fingerprint=fingerprint,
            authorization_id=str(authorization["authorization_id"]),
        )
        recoverable_receipt = isinstance(adapter, HeyGenCLIAdapter) and output_path.with_suffix(".task.json").is_file()
        if not claimed and not recoverable_receipt:
            state["active_retry_authorization"] = None
            state["phase"] = "awaiting_retry_authorization"
            state["retry_request"] = {
                "provider": "heygen",
                "reason": "HeyGen执行授权已使用且没有可恢复任务回执。",
            }
            _save_state(root, state)
            raise ValueError("HeyGen执行授权已使用；提交状态不确定或结果已失败，付费重试需要新授权。")

    def submitted(task_id: str) -> None:
        nonlocal active_attempt
        if active_attempt is not None:
            return
        active_attempt, _ = record_provider_attempt(
            root,
            provider="heygen",
            input_revision=input_revision,
            settings=settings,
            authorization_id=authorization["authorization_id"],
            mode="real",
            status="submitted",
            output=str(output_path),
            task_id=task_id,
            estimated_consumption=authorization.get("estimated_consumption"),
        )

    try:
        if isinstance(adapter, HeyGenCLIAdapter):
            result = adapter.generate_presenter(
                audio_path=audio_path,
                avatar_id=avatar_id,
                settings=settings,
                output_path=output_path,
                resume_task_id=str(resumable.get("external_task_id") or "") if resumable else None,
                on_submitted=submitted,
            )
        else:
            result = adapter.generate_presenter(
                audio_path=audio_path,
                avatar_id=avatar_id,
                settings=settings,
                output_path=output_path,
            )
    except ProviderTaskPending as exc:
        submitted(exc.task_id)
        if active_attempt and str(active_attempt.get("status")) == "submitted":
            active_attempt = transition_provider_attempt(
                root, "heygen", str(active_attempt["attempt_id"]), status="running"
            )
        state["current_attempts"] = {**dict(state.get("current_attempts") or {}), "heygen": active_attempt["attempt_id"]}
        _save_state(root, state)
        _append_change(root, "HeyGen任务仍在执行；已保存任务ID，后续只查询同一任务。")
        return AvatarVideoResult(
            str(root),
            "in_progress",
            state["phase"],
            (str(root / "providers"),),
            "HeyGen任务仍在执行；稍后继续即可，不会重新上传或重复提交。",
        )
    except ProviderTaskFailed as exc:
        submitted(exc.task_id)
        if active_attempt and str(active_attempt.get("status")) in {"submitted", "running"}:
            transition_provider_attempt(root, "heygen", str(active_attempt["attempt_id"]), status="failed")
        state["phase"] = "awaiting_retry_authorization"
        state["retry_request"] = {"provider": "heygen", "reason": str(exc)}
        _save_state(root, state)
        _append_change(root, f"HeyGen外部任务失败：{exc}；付费重试需要明确授权。")
        raise
    except Exception:
        if active_attempt is None:
            record_provider_attempt(
                root,
                provider="heygen",
                input_revision=input_revision,
                settings=settings,
                authorization_id=authorization["authorization_id"],
                mode="real",
                status="failed",
                output=str(output_path),
                task_id=f"heygen-failed-{attempt_number:04d}",
                estimated_consumption=authorization.get("estimated_consumption"),
            )
            state["active_retry_authorization"] = None
            state["phase"] = "awaiting_retry_authorization"
            state["retry_request"] = {"provider": "heygen", "reason": "HeyGen提交前或提交状态确认失败。"}
            _save_state(root, state)
            _append_change(root, "HeyGen执行失败且无可恢复任务ID；再次付费调用需要明确授权。")
        else:
            state["current_attempts"] = {**dict(state.get("current_attempts") or {}), "heygen": active_attempt["attempt_id"]}
            _save_state(root, state)
            _append_change(root, "HeyGen任务已提交但本次查询中断；保留任务ID供恢复。")
        raise
    expected = int(state["duration_seconds"])
    if abs(float(result.media_probe["duration_seconds"]) - expected) > 2.0:
        if active_attempt and str(active_attempt.get("status")) in {"submitted", "running"}:
            transition_provider_attempt(root, "heygen", str(active_attempt["attempt_id"]), status="failed")
        state["phase"] = "awaiting_retry_authorization"
        state["retry_request"] = {"provider": "heygen", "reason": "HeyGen原片时长与确认音频不匹配。"}
        _save_state(root, state)
        raise ValueError("HeyGen原片时长与确认音频不匹配。")
    if active_attempt is not None:
        attempt = transition_provider_attempt(
            root,
            "heygen",
            str(active_attempt["attempt_id"]),
            status="completed_pending_review",
            output=result.output_path,
            actual_consumption=result.actual_consumption,
            media_probe=result.media_probe,
        )
    else:
        attempt, _ = record_provider_attempt(
            root,
            provider="heygen",
            input_revision=input_revision,
            settings=settings,
            authorization_id=authorization["authorization_id"],
            mode="real",
            status="completed_pending_review",
            output=result.output_path,
            task_id=result.external_task_id,
            estimated_consumption=authorization.get("estimated_consumption"),
            actual_consumption=result.actual_consumption,
            media_probe=result.media_probe,
        )
    state["files"]["presenter_footage"] = str(Path(result.output_path).resolve().relative_to(root))
    state["current_attempts"] = {**dict(state.get("current_attempts") or {}), "heygen": attempt["attempt_id"]}
    state["phase"] = "awaiting_presenter_confirmation"
    _save_state(root, state)
    _append_change(root, "HeyGen生成完整真实数字人原片，等待完整观看。")
    return AvatarVideoResult(str(root), "completed_pending_review", state["phase"], (result.output_path,), "HeyGen完整原片已生成，请完整观看后确认。")


def confirm_avatar_presenter(run_dir: Path | str) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    if state["phase"] != "awaiting_presenter_confirmation":
        raise ValueError("当前没有待确认的数字人原片。")
    presenter = root / state["files"]["presenter_footage"]
    probe_media(presenter)
    attempt_id = str(state.get("current_attempts", {}).get("heygen") or "")
    if not attempt_id:
        raise ValueError("运行缺少当前HeyGen尝试。")
    review_provider_attempt(root, "heygen", attempt_id, accepted=True, reason="用户完整观看并确认。")
    state["confirmations"]["presenter"] = True
    state["phase"] = "ready_for_composition"
    _save_state(root, state)
    _append_change(root, "确认完整数字人原片。")
    return AvatarVideoResult(str(root), "confirmed", state["phase"], (str(presenter),), "数字人原片已确认。")


def reject_avatar_provider_attempt(run_dir: Path | str, provider: str, reason: str) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    provider = str(provider).strip().casefold()
    expected_phase = {
        "fish_audio": "awaiting_input_confirmation",
        "support_images": "awaiting_input_confirmation",
        "heygen": "awaiting_presenter_confirmation",
    }.get(provider)
    if expected_phase is None or state["phase"] != expected_phase:
        raise ValueError("当前阶段不能拒绝该供应商结果。")
    attempt_id = str(state.get("current_attempts", {}).get(provider) or "")
    review_provider_attempt(root, provider, attempt_id, accepted=False, reason=reason)
    state["phase"] = "awaiting_retry_authorization"
    state["retry_request"] = {"provider": provider, "reason": str(reason).strip()}
    if provider in {"fish_audio", "support_images"}:
        state["confirmations"].update({"inputs": False, "presenter": False, "final": False})
        affected = (
            ("support_visual_manifest", "support_visuals", "presenter_footage", "final_render", "final_probe", "delivery_pack")
            if provider == "support_images"
            else ("narration_audio", "presenter_footage", "final_render", "final_probe", "delivery_pack")
        )
        for key in affected:
            state["files"].pop(key, None)
    else:
        state["confirmations"].update({"presenter": False, "final": False})
        for key in ("presenter_footage", "final_render", "final_probe", "delivery_pack"):
            state["files"].pop(key, None)
    _save_state(root, state)
    _append_change(root, f"拒绝供应商结果：{provider}；原因：{reason}。")
    return AvatarVideoResult(str(root), "rejected", state["phase"], (str(root / "workflow_state.json"),), "结果已拒绝；重新生成前需要明确授权。")


def authorize_avatar_provider_retry(
    run_dir: Path | str,
    provider: str,
    *,
    reason: str,
    settings_changes: dict[str, Any] | None = None,
) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    provider = str(provider).strip().casefold()
    request = dict(state.get("retry_request") or {})
    if state["phase"] != "awaiting_retry_authorization" or request.get("provider") != provider:
        raise ValueError("当前没有该供应商的待授权重试。")
    if not str(reason).strip():
        raise ValueError("付费重试授权必须记录原因。")
    authorizations = list(state.get("retry_authorizations") or [])
    authorization_id = f"retry-{provider}-{len(authorizations) + 1:04d}"
    authorization = {
        "authorization_id": authorization_id,
        "provider": provider,
        "reason": str(reason).strip(),
        "settings_changes": dict(settings_changes or {}),
        "authorized_at": datetime.now(timezone.utc).isoformat(),
    }
    authorizations.append(authorization)
    state["retry_authorizations"] = authorizations
    overrides = dict(state.get("provider_overrides") or {})
    overrides[provider] = {**dict(overrides.get(provider) or {}), **dict(settings_changes or {})}
    state["provider_overrides"] = overrides
    state["active_retry_authorization"] = authorization
    state.pop("retry_request", None)
    state["phase"] = "ready_for_input_generation" if provider in {"fish_audio", "support_images"} else "ready_for_presenter_generation"
    _save_state(root, state)
    _append_change(root, f"用户授权供应商付费重试：{provider}。")
    return AvatarVideoResult(str(root), "authorized", state["phase"], (str(root / "workflow_state.json"),), "重试已授权，可以生成新版本。")


def compose_avatar_video(
    run_dir: Path | str,
    *,
    hyperframes: HyperFramesAdapter | None = None,
    ffmpeg_command: str = "ffmpeg",
) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    if state["phase"] == "awaiting_final_confirmation" and state.get("files", {}).get("final_renders"):
        outputs = tuple(str(root / value) for value in state["files"]["final_renders"])
        if all(Path(path).is_file() for path in outputs):
            return AvatarVideoResult(str(root), "idempotent", state["phase"], outputs, "当前包装revision成片已存在，未重复渲染。")
    if state["phase"] != "ready_for_composition" or not state["confirmations"]["presenter"]:
        raise ValueError("数字人原片未确认，不能开始包装。")
    plan = _read_json(root / "production_plan.json")
    contract = _build_composition_contract(root, state, plan)
    revision_number = len(list((root / "renders").glob("revision_*"))) + 1
    render_dir = root / "renders" / f"revision_{revision_number:04d}"
    render_dir.mkdir(parents=True, exist_ok=False)
    output_name = "youtube-shorts.mp4" if state["language_version"] == "en" else "zh-master.mp4"
    output = render_dir / output_name
    fallback_reason = None
    try:
        if hyperframes is None:
            raise HyperFramesUnavailable("HyperFrames执行器未配置。")
        result = hyperframes.render(contract, output)
    except HyperFramesUnavailable as exc:
        fallback_reason = redact_text(str(exc))
        result = FFmpegComposer(ffmpeg_command).render(contract, output)
    _write_json(render_dir / "media_probe.json", result.media_probe)
    _write_json(render_dir / "composition-contract.json", contract)
    composition_summary = {
        "schema_version": "avatar-composition-result-v1",
        "path_used": result.path_used,
        "fallback_reason": fallback_reason,
        "test_mode": bool(state.get("test_mode")),
        "output": str(output),
        "content_order": [item["segment_id"] for item in contract["timeline"]],
        "diagnostics": result.diagnostics,
    }
    _write_json(render_dir / "composition.json", composition_summary)
    platform_outputs = _derive_platform_outputs(output, render_dir, state, ffmpeg_command)
    variant_manifest = {
        "schema_version": "avatar-platform-variants-v1",
        "language_version": state["language_version"],
        "master": str(output),
        "shared_inputs": {
            "audio": contract["audio_path"],
            "presenter": contract["presenter_path"],
            "official_visuals": contract["official_visuals"],
            "support_visuals": contract["support_visuals"],
            "timeline_revision": contract["plan_revision"],
        },
        "variants": platform_outputs,
        "provider_calls_reused": True,
    }
    _write_json(render_dir / "platform-variants.json", variant_manifest)
    final_paths = [Path(item["output_path"]) for item in platform_outputs]
    state["files"]["final_render"] = str(final_paths[0].relative_to(root))
    state["files"]["final_renders"] = [str(path.relative_to(root)) for path in final_paths]
    state["files"]["final_probe"] = str((render_dir / "media_probe.json").relative_to(root))
    state["files"]["composition_contract"] = str((render_dir / "composition-contract.json").relative_to(root))
    state["files"]["platform_variants"] = str((render_dir / "platform-variants.json").relative_to(root))
    state["composition_path"] = result.path_used
    state["phase"] = "awaiting_final_confirmation"
    _save_state(root, state)
    _append_change(root, f"使用{result.path_used}生成成片。" + (f" 自动降级原因：{fallback_reason}" if fallback_reason else ""))
    status = "mock_rendered" if state.get("test_mode") else "rendered_pending_review"
    return AvatarVideoResult(
        str(root),
        status,
        state["phase"],
        tuple([*[str(path) for path in final_paths], str(render_dir / "media_probe.json"), str(render_dir / "composition.json")]),
        "成片已生成，请完整观看。",
    )


def compose_mock_avatar_video(run_dir: Path | str, *, ffmpeg_command: str = "ffmpeg") -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    if not _load_state(root).get("test_mode"):
        raise ValueError("伪合成入口只能用于明确的test_mode运行。")
    return compose_avatar_video(root, ffmpeg_command=ffmpeg_command)


def revise_avatar_video(
    run_dir: Path | str,
    request_text: str,
    *,
    category: str,
    changes: dict[str, Any],
) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    if state["phase"] not in {"ready_for_composition", "awaiting_final_confirmation", "completed"}:
        raise ValueError("当前阶段不能修订数字人口播。")
    if not str(request_text).strip() or not changes:
        raise ValueError("修订必须包含用户的自然语言要求和实际字段变更。")
    category = str(category).strip().casefold()
    if category not in {"packaging", "narration", "audio", "presenter", "evidence"}:
        raise ValueError("不支持的修订类别。")
    plan = _read_json(root / "production_plan.json")
    previous_active_files = dict(state.get("files") or {})
    revision_number = len(list((root / "revisions").glob("revision-*.json"))) + 1
    revision_id = f"revision-{revision_number:04d}"

    if category == "packaging":
        allowed = {"captions", "bgm", "title_layout", "parameter_layout", "transitions", "timeline"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError("包装修订包含受保护字段：" + ", ".join(sorted(unknown)))
        normalized_changes = dict(changes)
        if "captions" in normalized_changes:
            value = normalized_changes["captions"]
            burned = bool(value.get("burned", True)) if isinstance(value, dict) else bool(value)
            normalized_changes["captions"] = {
                "burned": burned,
                "language": state["language_version"],
                "style": "vertical_safe_default",
            }
        if "bgm" in normalized_changes:
            normalized_changes["bgm"] = _normalize_bgm(normalized_changes["bgm"])
        if "timeline" in normalized_changes:
            normalized_changes["timeline"] = _validate_packaging_timeline(plan, normalized_changes["timeline"])
        state["packaging_overrides"] = {**dict(state.get("packaging_overrides") or {}), **normalized_changes}
        state["packaging_revision"] = revision_id
        state["confirmations"]["final"] = False
        state["status"] = "active"
        state["phase"] = "ready_for_composition"
        _clear_active_delivery_files(state)
    elif category == "narration":
        narration = str(changes.get("narration") or "").strip()
        if not narration:
            raise ValueError("逐字稿修订必须提供完整新逐字稿。")
        plan["narration"] = narration
        _revise_plan_identity(plan, state)
        plan["status"] = "draft_pending_confirmation"
        _write_json(root / "production_plan.json", plan)
        state["confirmations"].update({"plan": False, "inputs": False, "presenter": False, "final": False})
        state["pending_revision"] = {"category": category, "resume_phase": "awaiting_retry_authorization"}
        state["pending_retry_after_plan"] = {"provider": "fish_audio", "reason": str(request_text).strip()}
        _clear_active_from(state, "narration_audio")
        state["phase"] = "awaiting_plan_confirmation"
        state["status"] = "active"
    elif category == "audio":
        plan["fish_audio"] = {**dict(plan["fish_audio"]), **dict(changes)}
        _revise_plan_identity(plan, state)
        _write_json(root / "production_plan.json", plan)
        state["confirmations"].update({"inputs": False, "presenter": False, "final": False})
        state["retry_request"] = {"provider": "fish_audio", "reason": str(request_text).strip()}
        _clear_active_from(state, "narration_audio")
        state["phase"] = "awaiting_retry_authorization"
        state["status"] = "active"
    elif category == "presenter":
        plan["heygen"] = {**dict(plan["heygen"]), **dict(changes)}
        _revise_plan_identity(plan, state)
        _write_json(root / "production_plan.json", plan)
        state["confirmations"].update({"presenter": False, "final": False})
        state["retry_request"] = {"provider": "heygen", "reason": str(request_text).strip()}
        _clear_active_from(state, "presenter_footage")
        state["phase"] = "awaiting_retry_authorization"
        state["status"] = "active"
    else:
        draft = dict(plan)
        for key in ("selected_visuals", "timeline"):
            if key in changes:
                draft[key] = changes[key]
        normalized = _normalize_plan(root, state, draft)
        normalized["status"] = "draft_pending_confirmation"
        _write_json(root / "production_plan.json", normalized)
        state["confirmations"].update({"plan": False, "final": False})
        state["pending_revision"] = {"category": category, "resume_phase": "ready_for_composition"}
        _clear_active_delivery_files(state)
        state["phase"] = "awaiting_plan_confirmation"
        state["status"] = "active"

    revision = {
        "schema_version": "avatar-video-revision-v1",
        "revision_id": revision_id,
        "category": category,
        "request_text": str(request_text).strip(),
        "changes": changes,
        "previous_active_files": previous_active_files,
        "result_phase": state["phase"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    revision_path = root / "revisions" / f"{revision_id}.json"
    _write_json(revision_path, revision)
    _save_state(root, state)
    _append_change(root, f"应用{category}修订 {revision_id}；旧渲染与供应商尝试保留。")
    return AvatarVideoResult(str(root), "revised", state["phase"], (str(revision_path),), "修订已写入实际状态；请按当前门禁继续。")


def _derive_platform_outputs(
    master: Path,
    render_dir: Path,
    state: dict[str, Any],
    ffmpeg_command: str,
) -> list[dict[str, Any]]:
    if state["language_version"] == "en":
        return [
            {
                "platform": "youtube_shorts",
                "output_path": str(master),
                "safe_zone": "youtube_shorts_vertical_default",
                "ending": "shared_master",
                "encoding": "h264_aac_1080x1920",
                "media_probe": probe_media(master),
            }
        ]
    outputs = []
    for platform, safe_zone in (
        ("kuaishou", "kuaishou_vertical_default"),
        ("douyin", "douyin_vertical_default"),
    ):
        output = render_dir / f"{platform}.mp4"
        run_ffmpeg(
            [
                ffmpeg_command,
                "-y",
                "-i",
                str(master),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0",
                "-c",
                "copy",
                "-metadata",
                f"comment=avatar-video:{platform}",
                "-movflags",
                "+faststart",
                str(output),
            ]
        )
        outputs.append(
            {
                "platform": platform,
                "output_path": str(output),
                "safe_zone": safe_zone,
                "ending": f"{platform}_cta_safe_zone",
                "encoding": "h264_aac_1080x1920",
                "media_probe": probe_media(output),
            }
        )
    return outputs


def accept_mock_avatar_delivery(run_dir: Path | str) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    if not state.get("test_mode"):
        raise ValueError("此入口不能接受真实交付。")
    if state["phase"] != "awaiting_final_confirmation":
        raise ValueError("当前没有待确认的最终成片。")
    final_path = root / state["files"]["final_render"]
    probe = probe_media(final_path)
    target = root / "delivery" / final_path.name
    shutil.copy2(final_path, target)
    pack = {
        "schema_version": "avatar-delivery-pack-v1",
        "status": "mock_delivery",
        "publish_authorized": False,
        "platforms": state["platforms"],
        "platform_specs": {
            platform: {
                "aspect_ratio": "9:16",
                "width": 1080,
                "height": 1920,
                "safe_zone": f"{platform}_vertical_default",
            }
            for platform in state["platforms"]
        },
        "files": [str(target)],
        "media_probe": probe,
        "composition_path": "ffmpeg_fallback",
        "warning": "这是伪供应商测试交付，不是真实可发布成片。",
    }
    _write_json(root / "delivery" / "delivery-pack.json", pack)
    state["confirmations"]["final"] = True
    state["status"] = "mock_completed"
    state["phase"] = "completed"
    state["files"]["delivery_pack"] = "delivery/delivery-pack.json"
    _save_state(root, state)
    _append_change(root, "确认伪成片并生成明确标记的mock本地交付包；未授权发布。")
    return AvatarVideoResult(str(root), "mock_completed", state["phase"], (str(target), str(root / "delivery" / "delivery-pack.json")), pack["warning"])


def get_avatar_final_review(run_dir: Path | str) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    if state["phase"] != "awaiting_final_confirmation":
        raise ValueError("当前没有待完整观看的最终成片。")
    outputs = [root / value for value in state.get("files", {}).get("final_renders", [])]
    if not outputs and state.get("files", {}).get("final_render"):
        outputs = [root / state["files"]["final_render"]]
    probes = [probe_media(path) for path in outputs]
    summary_path = outputs[0].parent / "final-review.json"
    _write_json(
        summary_path,
        {
            "schema_version": "avatar-final-review-v1",
            "status": "pending_full_playback_confirmation",
            "files": [str(path) for path in outputs],
            "media_probes": probes,
            "composition_path": state.get("composition_path"),
            "publish_authorized": False,
        },
    )
    return AvatarVideoResult(str(root), "awaiting_confirmation", state["phase"], tuple([*[str(path) for path in outputs], str(summary_path)]), "请完整播放所有平台成片；确认后才生成accepted本地交付包。")


def accept_avatar_delivery(run_dir: Path | str) -> AvatarVideoResult:
    root = Path(run_dir).resolve()
    state = _load_state(root)
    accepted_dir = root / "delivery" / "accepted"
    accepted_pack = accepted_dir / "delivery-pack.json"
    if state["phase"] == "completed" and state["status"] == "accepted" and accepted_pack.is_file():
        pack = _read_json(accepted_pack)
        return AvatarVideoResult(str(root), "idempotent", "completed", tuple([*pack["files"], str(accepted_pack)]), "accepted本地交付包已存在。")
    if state.get("test_mode"):
        raise ValueError("mock或dry-run运行不能生成accepted交付包。")
    if state["phase"] != "awaiting_final_confirmation":
        raise ValueError("用户完整观看并确认前不能生成accepted交付包。")
    if state.get("blocker") or state.get("status") in {"blocked", "failed", "rejected", "incomplete", "stale"}:
        raise ValueError("当前运行状态不能成为accepted交付。")
    manifest = read_avatar_video_manifest(_paths_from_state(state))
    if manifest.get("interface_revision") != state["interface"]["interface_revision"]:
        raise ValueError("运行固定的知识接口revision已失效。")
    provider_summary = _accepted_real_provider_summary(root, state)
    source_outputs = [root / value for value in state.get("files", {}).get("final_renders", [])]
    expected_count = 1 if state["language_version"] == "en" else 2
    if len(source_outputs) != expected_count:
        raise ValueError("最终平台文件数量不正确。")
    contract = _read_json(root / state["files"]["composition_contract"])
    probes = []
    for path in source_outputs:
        probe = validate_composition_output(path, contract)
        probes.append(probe)
    if accepted_dir.exists():
        raise FileExistsError("accepted交付目录已存在但状态不一致，拒绝覆盖。")
    staging = Path(tempfile.mkdtemp(prefix=".accepted-staging-", dir=str(root / "delivery")))
    delivered_paths = []
    try:
        for source in source_outputs:
            target = staging / source.name
            shutil.copy2(source, target)
            delivered_paths.append(target)
        pack = {
            "schema_version": "avatar-delivery-pack-v1",
            "status": "accepted_local_delivery",
            "publish_authorized": False,
            "platforms": state["platforms"],
            "files": [str(accepted_dir / path.name) for path in delivered_paths],
            "media_probes": probes,
            "caption_strategy": contract["captions"],
            "revisions": {
                "knowledge_interface": state["interface"]["interface_revision"],
                "source_knowledge": state["interface"]["source_knowledge_revision"],
                "plan": contract["plan_revision"],
                "packaging": contract.get("packaging_revision"),
                "providers": provider_summary,
            },
            "composition_path": state.get("composition_path"),
            "accepted_at": datetime.now(timezone.utc).isoformat(),
            "boundary": "Local handoff only. No login, upload, scheduling, metadata authoring, or publication.",
        }
        _write_json(staging / "delivery-pack.json", pack)
        staging.replace(accepted_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    state["confirmations"]["final"] = True
    state["status"] = "accepted"
    state["phase"] = "completed"
    state["files"]["delivery_pack"] = str(accepted_pack.relative_to(root))
    _save_state(root, state)
    _append_change(root, "用户完整观看并确认；生成不可变accepted本地交付包，未授权发布。")
    return AvatarVideoResult(str(root), "accepted", "completed", tuple([*pack["files"], str(accepted_pack)]), "本地交付完成；本Agent不执行发布。")


def _build_composition_contract(root: Path, state: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    if not state["confirmations"].get("inputs") or not state["confirmations"].get("presenter"):
        raise ValueError("组合合同只能引用已确认音频、图片集和数字人原片。")
    official_visuals = [str(Path(item["path"]).resolve()) for item in plan["selected_visuals"]]
    support_visuals = [str((root / item).resolve()) for item in state.get("files", {}).get("support_visuals", [])]
    available_visuals = [*official_visuals, *support_visuals]
    packaging = dict(state.get("packaging_overrides") or {})
    source_timeline = list(packaging.get("timeline") or plan["timeline"])
    timeline = []
    visual_index = 0
    for index, raw_segment in enumerate(source_timeline, start=1):
        segment = {
            "segment_id": f"segment-{index:04d}",
            "start_seconds": float(raw_segment["start_seconds"]),
            "end_seconds": float(raw_segment["end_seconds"]),
            "mode": str(raw_segment.get("mode") or "presenter"),
            "purpose": str(raw_segment.get("purpose") or ""),
            "display": _normalize_segment_display(raw_segment.get("display")),
        }
        if segment["mode"] != "presenter":
            requested = str(raw_segment.get("visual_path") or "")
            if requested:
                requested = str(Path(requested).expanduser().resolve())
                if requested not in available_visuals:
                    raise ValueError("时间线引用了未确认的证据或辅助图片。")
                segment["visual_path"] = requested
            else:
                segment["visual_path"] = available_visuals[visual_index % len(available_visuals)]
                visual_index += 1
        timeline.append(segment)
    captions = dict(packaging.get("captions") or plan.get("captions") or {})
    if captions.get("burned", True):
        caption_key = str(state.get("packaging_revision") or plan["revision"])
        caption_path = root / "inputs" / "captions" / f"{caption_key}.srt"
        write_srt(plan["narration"], state["language_version"], float(state["duration_seconds"]), caption_path)
        captions["path"] = str(caption_path.resolve())
        captions["source"] = "confirmed_narration"
    return {
        "schema_version": "avatar-composition-contract-v1",
        "plan_revision": plan["revision"],
        "packaging_revision": state.get("packaging_revision") or "initial",
        "language_version": state["language_version"],
        "platforms": state["platforms"],
        "platform_specs": {
            platform: {
                "aspect_ratio": "9:16",
                "width": 1080,
                "height": 1920,
                "safe_zone": f"{platform}_vertical_default",
            }
            for platform in state["platforms"]
        },
        "duration_seconds": state["duration_seconds"],
        "width": 1080,
        "height": 1920,
        "frame_rate": 30,
        "pixel_format": "yuv420p",
        "audio_path": str((root / state["files"]["narration_audio"]).resolve()),
        "presenter_path": str((root / state["files"]["presenter_footage"]).resolve()),
        "official_visuals": official_visuals,
        "support_visuals": support_visuals,
        "timeline": timeline,
        "captions": captions,
        "bgm": packaging.get("bgm", plan.get("bgm")),
        "title_layout": packaging.get("title_layout"),
        "parameter_layout": packaging.get("parameter_layout"),
        "transitions": packaging.get("transitions"),
    }


def _normalize_plan(root: Path, state: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    narration = str(plan.get("narration") or "").strip()
    if not narration:
        raise ValueError("生产方案必须包含完整逐字稿。")
    segments = list(plan.get("timeline") or [])
    if not segments:
        raise ValueError("生产方案必须包含连续时间线。")
    cursor = 0.0
    for segment in segments:
        start = float(segment.get("start_seconds", -1))
        end = float(segment.get("end_seconds", -1))
        if abs(start - cursor) > 0.001 or end <= start:
            raise ValueError("生产方案时间线不连续。")
        cursor = end
    if abs(cursor - float(state["duration_seconds"])) > 0.001:
        raise ValueError("生产方案总时长必须等于运行目标。")
    selected_visuals = []
    for item in list(plan.get("selected_visuals") or []):
        selected_visuals.append(_authorize_visual(root, state, item))
    if not selected_visuals:
        raise ValueError("生产方案至少需要一项正式图片素材。")
    _validate_material_capacity(state, segments, selected_visuals)
    fish = dict(plan.get("fish_audio") or {})
    heygen = dict(plan.get("heygen") or {})
    if not str(fish.get("voice_id") or "").strip():
        raise ValueError("生产方案缺少Fish Audio voice ID。")
    if not str(heygen.get("avatar_id") or "").strip():
        raise ValueError("生产方案缺少HeyGen avatar ID。")
    heygen.setdefault("avatar_version", str(heygen["avatar_id"]))
    heygen.setdefault("commercial_use_basis", "paid_public_avatar")
    heygen.setdefault("width", 1080)
    heygen.setdefault("height", 1920)
    heygen.setdefault("aspect_ratio", "9:16")
    heygen.setdefault("resolution", "1080p")
    heygen.setdefault("engine", "avatar_iv")
    heygen.setdefault("fit", "cover")
    high_risk_notes = _review_high_risk_claims(_paths_from_state(state), state["product"]["id"], narration)
    high_risk_notes.extend(str(item) for item in list(plan.get("high_risk_notes") or []) if str(item).strip())
    support_batch = _normalize_support_visual_batch(plan.get("support_visual_batch"), selected_visuals)
    requested_captions = dict(plan.get("captions") or {})
    captions = {
        "burned": bool(requested_captions.get("burned", True)),
        "language": state["language_version"],
        "style": "vertical_safe_default",
    }
    bgm = _normalize_bgm(plan.get("bgm"))
    normalized = {
        "schema_version": "avatar-production-plan-v1",
        "revision": "plan_" + _json_digest({"plan": plan, "interface": state["interface"]})[:20],
        "status": "draft_pending_confirmation",
        "product_id": state["product"]["id"],
        "language_version": state["language_version"],
        "platforms": state["platforms"],
        "duration_seconds": state["duration_seconds"],
        "aspect_ratio": "9:16",
        "brief": state["brief"],
        "knowledge_boundary": {
            "sales_material_role": "expression_reference",
            "sales_materials_prove_product_facts": False,
        },
        "sales_expression_references": [dict(item) for item in state.get("sales_expression_references", [])],
        "narration": narration,
        "narration_source": str(plan.get("narration_source") or "agent_drafted"),
        "timeline": segments,
        "selected_visuals": selected_visuals,
        "captions": captions,
        "bgm": bgm,
        "fish_audio": fish,
        "heygen": heygen,
        "support_visual_batch": support_batch,
        "estimated_consumption": dict(plan.get("estimated_consumption") or {}),
        "high_risk_notes": list(dict.fromkeys(high_risk_notes)),
    }
    return normalized


def _authorize_visual(root: Path, state: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    candidate = Path(str(item.get("path") or "")).expanduser().resolve()
    matched = _authorized_visual_card(state, candidate)
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    inspections_path = root / "material_inspections.json"
    if not inspections_path.is_file():
        raise ValueError("所选图片尚未完成像素检查。")
    inspection = next((entry for entry in _read_json(inspections_path).get("items", []) if entry.get("path") == str(candidate)), None)
    if inspection is None:
        raise ValueError("所选图片尚未完成像素检查。")
    if inspection.get("projection_fingerprint") != matched.get("projection_fingerprint"):
        raise ValueError("素材检查引用的知识投影已经过期。")
    if inspection.get("status") != "usable" or inspection.get("risks"):
        raise ValueError("所选图片存在未解决的产品身份、权利、隐私或证据风险。")
    return {
        "card_id": matched["id"],
        "path": str(candidate),
        "projection_fingerprint": matched["projection_fingerprint"],
        "purpose": str(item.get("purpose") or "product_evidence"),
        "inspection": inspection,
    }


def _authorized_visual_card(state: dict[str, Any], candidate: Path) -> dict[str, Any]:
    paths = _paths_from_state(state)
    product_id = state["product"]["id"]
    for card in read_avatar_video_cards(paths, "content_asset"):
        frontmatter = dict(card.get("frontmatter") or {})
        related = {str(value) for value in frontmatter.get("related_products", [])}
        if product_id not in related or "image" not in {str(value) for value in frontmatter.get("media_types", [])}:
            continue
        for raw_value in frontmatter.get("files", []):
            path = (paths.project_dir / str(raw_value)).resolve()
            if path == candidate:
                return card
    raise ValueError("所选图片未由数字人口播专属知识接口声明。")


def _normalize_support_visual_batch(value: Any, selected_visuals: list[dict[str, Any]]) -> dict[str, Any]:
    batch = dict(value or {})
    images = list(batch.get("images") or [])
    provider = str(batch.get("provider") or "").strip() if images else None
    if images and not provider:
        raise ValueError("辅助图片批次缺少供应商。")
    authorized_references = {item["path"] for item in selected_visuals}
    normalized_images = []
    for index, image in enumerate(images, start=1):
        purpose = str(image.get("purpose") or "").strip()
        reference = str(image.get("reference") or image.get("reference_path") or "").strip()
        if not purpose or not reference:
            raise ValueError(f"辅助图片{index}缺少用途或真实产品参考。")
        reference_path = str(Path(reference).expanduser().resolve())
        if reference_path not in authorized_references:
            raise ValueError("辅助图片必须绑定方案中已检查的真实产品图。")
        normalized_images.append(
            {
                "purpose": purpose,
                "reference_path": reference_path,
                "viewer_facing_ai_label": bool(image.get("viewer_facing_ai_label", False)),
            }
        )
    declared_count = int(batch.get("count") or len(normalized_images))
    if declared_count != len(normalized_images):
        raise ValueError("辅助图片批次声明数量与逐项用途不一致。")
    return {
        "provider": provider,
        "count": len(normalized_images),
        "images": normalized_images,
        "estimated_consumption": batch.get("estimated_consumption"),
    }


def _normalize_bgm(value: Any) -> dict[str, Any] | None:
    if value is None or value == "":
        return None
    if not isinstance(value, dict):
        raise ValueError("BGM必须是用户显式提供的本地文件配置。")
    path_value = str(value.get("path") or "").strip()
    if not path_value:
        raise ValueError("BGM配置缺少本地文件路径。")
    path = Path(path_value).expanduser().resolve()
    probe = probe_media(path)
    if not probe["has_audio"]:
        raise ValueError("用户提供的BGM文件没有可读音轨。")
    volume = float(value.get("volume", 0.12))
    if volume <= 0 or volume > 1:
        raise ValueError("BGM音量必须大于0且不超过1。")
    return {"path": str(path), "volume": volume, "source": "user_provided_local_file"}


def _validate_packaging_timeline(plan: dict[str, Any], value: Any) -> list[dict[str, Any]]:
    revised = list(value or [])
    original = list(plan.get("timeline") or [])
    if len(revised) != len(original):
        raise ValueError("包装层只能调整既有镜头时机，不能增删事实镜头。")
    cursor = 0.0
    normalized = []
    for old, new in zip(original, revised):
        if str(new.get("mode") or old.get("mode")) != str(old.get("mode")):
            raise ValueError("包装层不能改变数字人/证据镜头类型。")
        start = float(new.get("start_seconds", -1))
        end = float(new.get("end_seconds", -1))
        if abs(start - cursor) > 0.001 or end <= start:
            raise ValueError("包装时间线必须连续。")
        item = {**old, **new, "start_seconds": start, "end_seconds": end}
        normalized.append(item)
        cursor = end
    if abs(cursor - float(plan["duration_seconds"])) > 0.001:
        raise ValueError("包装时间线总时长不能改变。")
    return normalized


def _normalize_segment_display(value: Any) -> dict[str, Any]:
    display = dict(value or {})
    parameters = []
    for item in list(display.get("parameters") or []):
        if not isinstance(item, dict):
            raise ValueError("镜头参数展示项必须是对象。")
        label = str(item.get("label") or "").strip()
        parameter_value = str(item.get("value") or "").strip()
        if not label or not parameter_value:
            raise ValueError("镜头参数展示项缺少label或value。")
        parameters.append(
            {
                "label": label,
                "value": parameter_value,
                "evidence_ref": str(item.get("evidence_ref") or "").strip() or None,
            }
        )
    return {
        "eyebrow": str(display.get("eyebrow") or "").strip(),
        "title": str(display.get("title") or "").strip(),
        "body": str(display.get("body") or "").strip(),
        "parameters": parameters,
    }


def _revise_plan_identity(plan: dict[str, Any], state: dict[str, Any]) -> None:
    plan["revision"] = "plan_" + _json_digest({"plan": plan, "interface": state["interface"]})[:20]


def _clear_active_delivery_files(state: dict[str, Any]) -> None:
    for key in (
        "final_render",
        "final_renders",
        "final_probe",
        "composition_contract",
        "platform_variants",
        "delivery_pack",
    ):
        state.get("files", {}).pop(key, None)


def _clear_active_from(state: dict[str, Any], start: str) -> None:
    order = ["narration_audio", "presenter_footage"]
    start_index = order.index(start)
    for key in order[start_index:]:
        state.get("files", {}).pop(key, None)
    _clear_active_delivery_files(state)
    attempts = dict(state.get("current_attempts") or {})
    if start == "narration_audio":
        attempts.pop("fish_audio", None)
        attempts.pop("heygen", None)
    else:
        attempts.pop("heygen", None)
    state["current_attempts"] = attempts


def _accepted_real_provider_summary(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    required = ["fish_audio", "heygen"]
    if state.get("files", {}).get("support_visuals"):
        required.append("support_images")
    summary = {}
    current = dict(state.get("current_attempts") or {})
    for provider in required:
        attempt_id = str(current.get(provider) or "")
        attempt = next((item for item in read_provider_attempts(root, provider) if item.get("attempt_id") == attempt_id), None)
        if attempt is None:
            raise ValueError(f"交付缺少当前{provider}供应商尝试。")
        if attempt.get("mode") != "real" or attempt.get("status") != "accepted" or not dict(attempt.get("review") or {}).get("accepted"):
            raise ValueError(f"{provider}不是已人工确认的真实供应商产物。")
        summary[provider] = {
            "attempt_id": attempt["attempt_id"],
            "input_revision": attempt["input_revision"],
            "task_id": attempt.get("external_task_id"),
            "actual_consumption": attempt.get("actual_consumption"),
        }
    return summary


def _resume_artifact_error(root: Path, state: dict[str, Any]) -> str | None:
    phase = str(state.get("phase") or "")
    files = dict(state.get("files") or {})
    required_media: list[str] = []
    if phase in {"awaiting_input_confirmation", "ready_for_presenter_generation"}:
        required_media = ["narration_audio"]
    elif phase in {"awaiting_presenter_confirmation", "ready_for_composition"}:
        required_media = ["narration_audio", "presenter_footage"]
    for key in required_media:
        value = str(files.get(key) or "")
        if not value:
            return f"当前阶段缺少活动文件引用：{key}。"
        try:
            probe_media(root / value)
        except (FileNotFoundError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            return f"当前阶段的{key}不可用：{redact_text(str(exc))}"
    if phase == "awaiting_final_confirmation":
        renders = list(files.get("final_renders") or [])
        if not renders:
            return "当前阶段缺少最终平台成片。"
        for value in renders:
            try:
                probe_media(root / value)
            except (FileNotFoundError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                return f"最终平台成片不可用：{redact_text(str(exc))}"
    if phase == "completed":
        pack = str(files.get("delivery_pack") or "")
        if not pack or not (root / pack).is_file():
            return "已完成运行缺少交付包。"
    return None


def _validate_material_capacity(state: dict[str, Any], segments: list[dict[str, Any]], visuals: list[dict[str, Any]]) -> None:
    groups = {str(item["inspection"]["near_duplicate_group"]) for item in visuals}
    evidence_seconds = sum(
        float(segment.get("end_seconds", 0)) - float(segment.get("start_seconds", 0))
        for segment in segments
        if str(segment.get("mode") or "") in {"evidence", "product", "parameter"}
    )
    supported_seconds = len(groups) * 15.0
    if evidence_seconds <= supported_seconds + 0.001:
        return
    exception = dict(state.get("material_exception") or {})
    if exception.get("type") in {"deliberate_repetition", "bounded_simulation"}:
        return
    raise ValueError(
        f"不重复正式图片只支持约{supported_seconds:g}秒证据画面；请缩短时长、明确允许重复或批准受约束模拟。"
    )


def _paths_from_state(state: dict[str, Any]) -> ProjectPaths:
    project_value = str(state.get("project_dir") or "").strip()
    if not project_value:
        raise ValueError("运行状态缺少项目路径。")
    project_dir = Path(project_value)
    config = dict(state.get("project_config") or {})
    return ProjectPaths(
        project_dir=project_dir,
        raw_dir=Path(config["raw_dir"]),
        knowledge_dir=Path(config["knowledge_dir"]),
        generated_dir=Path(config["generated_dir"]),
        config=config,
    )


def _provider_authorization(state: dict[str, Any], provider: str) -> dict[str, Any]:
    retry = dict(state.get("active_retry_authorization") or {})
    if retry.get("provider") == provider:
        state["active_retry_authorization"] = None
        return {
            "authorization_id": retry["authorization_id"],
            "estimated_consumption": state.get("execution_authorization", {}).get("estimated_consumption"),
        }
    initial = dict(state.get("execution_authorization") or {})
    if not initial.get("authorized_once"):
        raise ValueError("缺少首次执行授权。")
    if not any(item.get("provider") == provider and int(item.get("attempts") or 0) >= 1 for item in initial.get("operations", [])):
        raise ValueError("当前方案未授权该供应商首次执行。")
    return {
        "authorization_id": str(initial.get("authorization_id")),
        "estimated_consumption": initial.get("estimated_consumption"),
    }


def _mark_provider_retry_required(
    root: Path,
    state: dict[str, Any],
    provider: str,
    authorization: dict[str, Any],
    error: Exception,
) -> None:
    authorization_id = str(authorization.get("authorization_id") or "")
    failed_attempt = any(
        str(item.get("authorization_id") or "") == authorization_id and str(item.get("status") or "") == "failed"
        for item in read_provider_attempts(root, provider)
    )
    uncertain_claim = "执行授权已使用" in str(error)
    if not failed_attempt and not uncertain_claim:
        return
    state["active_retry_authorization"] = None
    state["phase"] = "awaiting_retry_authorization"
    state["retry_request"] = {"provider": provider, "reason": redact_text(str(error))}
    _save_state(root, state)
    _append_change(root, f"{provider}执行失败或提交状态不确定；再次付费调用需要明确授权。")


def _render_plan(plan: dict[str, Any]) -> str:
    lines = [
        "# 数字人口播完整生产方案",
        "",
        f"- 产品：{plan['product_id']}",
        f"- 语言：{plan['language_version']}",
        f"- 平台：{', '.join(plan['platforms'])}",
        f"- 时长：{plan['duration_seconds']}秒",
        "",
        "## 完整逐字稿",
        "",
        plan["narration"],
        "",
        "## 可用销售表达",
        "",
    ]
    references = list(plan.get("sales_expression_references") or [])
    if references:
        for reference in references:
            scope_note = "（对外前需复核）" if reference.get("draft_only") else ""
            lines.append(f"- {reference['title']}{scope_note}：仅作表达参考，不能证明产品事实。")
    else:
        lines.append("- 当前产品没有可用销售表达卡。")
    lines.extend(
        [
            "",
            "## 时间线",
            "",
        ]
    )
    for segment in plan["timeline"]:
        lines.append(
            f"- {segment['start_seconds']}–{segment['end_seconds']}秒：{segment.get('mode', 'presenter')} — {segment.get('purpose', '')}"
        )
    lines.extend(["", "## 正式素材", ""])
    for visual in plan["selected_visuals"]:
        lines.append(f"- {visual['card_id']}：{visual['path']}")
    lines.extend(
        [
            "",
            "## 首次执行范围",
            "",
            f"- Fish Audio voice：{plan['fish_audio']['voice_id']}",
            f"- HeyGen avatar：{plan['heygen']['avatar_id']}",
            f"- 辅助图片数量：{len(plan['support_visual_batch'].get('images', []))}",
            f"- 预计消耗：{json.dumps(plan['estimated_consumption'], ensure_ascii=False)}",
            "",
            "## 高风险提示",
            "",
        ]
    )
    if plan["high_risk_notes"]:
        lines.extend(f"- {item}" for item in plan["high_risk_notes"])
    else:
        lines.append("- 未发现需要单独提示的高风险表达。")
    return "\n".join(lines) + "\n"


def _review_high_risk_claims(paths: ProjectPaths, product_id: str, narration: str) -> list[str]:
    lowered = narration.casefold()
    knowledge_text = "\n".join(
        " ".join(
            str(value)
            for value in (
                card.get("title", ""),
                card.get("body_markdown", ""),
                card.get("body_excerpt", ""),
                json.dumps(card.get("frontmatter", {}), ensure_ascii=False),
            )
        )
        for card_type in ("product", "application_scenario", "evidence")
        for card in read_avatar_video_cards(paths, card_type)
        if card.get("id") == product_id
        or product_id in set((card.get("frontmatter") or {}).get("related_products", []))
    ).casefold()
    notes = []
    patterns = {
        "认证或标准": r"\b(?:certified|certification|ce|ul|astm|iso)\b|认证|通过.*标准",
        "绝对性能": r"\b(?:always|never|guaranteed|100%)\b|绝对|完全不会|永久",
        "测试结果": r"\b(?:tested|test result|laboratory proven)\b|测试结果|实验表明",
        "安全承诺": r"\b(?:completely safe|zero risk)\b|绝对安全|零风险",
        "具体参数": r"\b\d+(?:\.\d+)?\s*(?:°?c|mm|mpa|w/mk|hours?)\b|\d+(?:\.\d+)?\s*(?:℃|毫米|小时)",
    }
    for label, pattern in patterns.items():
        matches = re.findall(pattern, lowered, flags=re.IGNORECASE)
        if matches and not all(str(match).casefold() in knowledge_text for match in matches if isinstance(match, str)):
            notes.append(f"{label}表达需要用户确认其知识依据：{str(matches[0])}")
    return notes


def _card_matches_product(card: dict[str, Any], product_id: str) -> bool:
    if card.get("id") == product_id:
        return True
    frontmatter = dict(card.get("frontmatter") or {})
    related = {
        str(frontmatter.get("product_id") or ""),
        *[str(item) for item in frontmatter.get("related_products", [])],
    }
    return product_id in related


def _sales_expression_reference(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "card_id": str(card.get("id") or ""),
        "title": str(card.get("title") or ""),
        "usage_scope": str(card.get("usage_scope") or ""),
        "draft_only": bool(card.get("draft_only")),
        "knowledge_role": "expression_reference",
        "may_prove_product_facts": False,
        "expression_text": str(card.get("body_markdown") or card.get("body_excerpt") or "").strip(),
        "projection_fingerprint": str(card.get("projection_fingerprint") or ""),
    }


def _load_state(root: Path) -> dict[str, Any]:
    return _read_json(root / "workflow_state.json")


def _save_state(root: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(root / "workflow_state.json", state)


def _append_change(root: Path, message: str) -> None:
    path = root / "change_log.md"
    previous = path.read_text(encoding="utf-8") if path.exists() else "# 变更记录\n\n"
    _write_text(path, previous + f"- {datetime.now(timezone.utc).isoformat()} {message}\n")


def _unique_run_dir(root: Path, name: str) -> Path:
    candidate = root / name
    index = 1
    while candidate.exists():
        index += 1
        candidate = root / f"{name}_{index:02d}"
    return candidate


def _json_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    _write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)

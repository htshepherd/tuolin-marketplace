from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Callable

from ..kb.agent_interface import knowledge_status
from ..kb.core_upstream import organize_core_upstream, preview_core_upstream
from ..linkedin.agent import (
    confirm_linkedin_campaign_plan,
    confirm_linkedin_chinese_draft,
    copy_linkedin_campaign_to_desktop,
    create_linkedin_campaign_plan,
    create_linkedin_image_selection_sheet,
    create_linkedin_marketing_review,
    default_linkedin_transparent_logo_path,
    decide_linkedin_marketing_review,
    is_linkedin_campaign_request,
    prepare_linkedin_image_generation,
    repair_linkedin_manual_package_structure,
)
from ..linkedin_search.agent import create_linkedin_search_run, is_linkedin_search_request
from ..kb.partitions import PARTITIONS, PartitionSummary, find_partition, scan_all_partitions, scan_partition
from ..kb.partition_organizer import organize_partition
from .project_layout import ProjectPaths
from ..kb.question_answering import answer_question
from ..kb.review_workflow import apply_review_decision, create_review_preview, list_review_items
from ..kb.video_profiles import (
    VIDEO_SUFFIXES,
    confirm_video_tracer_candidate,
    inspect_video_candidate_batch,
)
from ..kb.application_scenario_video_batches import (
    accept_application_scenario_scope,
    process_application_scenario_batches,
    read_application_scenario_scopes,
)


ACTION_LABELS = {
    "update_first": "先更新资料",
    "organize_usable": "整理成可用资料",
    "continue_reading": "继续看资料",
    "review_required": "需要你确认",
    "use_existing": "直接使用现有资料",
    "prepare_raw": "先补充资料",
}

ACTION_RESULT_TEXT = {
    "update_first": "先确认哪些资料发生了变化，避免继续使用旧资料。",
    "organize_usable": "把已经识别出的内容整理成可查、可复用的知识卡片；需要你判断的内容会单独列出。",
    "continue_reading": "继续查看这个分区里的文件、图片、PDF 或视频素材，整理出候选知识和需要确认的问题。",
    "review_required": "先处理需要人工判断的问题，避免未确认内容进入确定答案。",
    "use_existing": "当前可以直接用已有资料回答问题或准备内容。",
    "prepare_raw": "需要先把原始资料补齐到对应分区，系统才有材料可整理。",
}

GLOBAL_ACTION_PRIORITY = {
    "update_first": 0,
    "organize_usable": 1,
    "review_required": 2,
    "continue_reading": 3,
    "prepare_raw": 4,
    "use_existing": 5,
}

BUSINESS_PARTITION_PRIORITY = {
    "quartz_fiber_tape": 0,
}


@dataclass(frozen=True)
class NaturalLanguageResponse:
    intent: str
    executed: bool
    needs_confirmation: bool
    message: str
    copyable_reply: str | None = None
    recommended_partition: str | None = None
    recommended_action: str | None = None
    details: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def route_natural_language(
    paths: ProjectPaths,
    text: str,
    *,
    video_tool_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    video_frame_decoder: Callable[[Path], bytes] | None = None,
) -> NaturalLanguageResponse:
    utterance = text.strip()
    confirmed = _is_confirmed(utterance)

    video_profile_response = _video_profile_response(
        paths,
        utterance,
        video_tool_runner=video_tool_runner,
        video_frame_decoder=video_frame_decoder,
    )
    if video_profile_response is not None:
        return video_profile_response

    linkedin_search_response = _linkedin_search_response(paths, utterance)
    if linkedin_search_response is not None:
        return linkedin_search_response

    linkedin_response = _linkedin_response(paths, utterance)
    if linkedin_response is not None:
        return linkedin_response

    if _is_review_decision_request(utterance):
        return _review_decision_response(paths, utterance)

    if _is_status_request(utterance):
        return _status_response(paths)

    if _is_completion_check_request(utterance):
        return _completion_check_response(paths, utterance)

    if _is_pending_request(utterance):
        return _pending_response(paths)

    if _is_full_rebuild_request(utterance):
        return _full_rebuild_plan(paths)

    if _is_review_request(utterance):
        return _review_list_response(paths, utterance)

    if _is_core_request(utterance):
        return _core_response(paths, confirmed)

    if _is_update_request(utterance):
        return _update_plan(paths)

    partition = _resolve_partition_from_text(utterance)
    if partition == "ambiguous_high_silica":
        return _ambiguous_high_silica_response(paths)

    if _is_partition_organize_request(utterance) and partition:
        if confirmed:
            return _execute_partition_organize(paths, partition)
        return _partition_plan(paths, partition)

    if _is_confirm_recommended(utterance):
        return _execute_recommended(paths)

    if _looks_like_business_question(utterance):
        answer = answer_question(paths, utterance)
        return NaturalLanguageResponse(
            intent="official_answer",
            executed=True,
            needs_confirmation=False,
            message=answer.answer if answer.answerable else f"{answer.answer}{answer.reason or ''}",
            copyable_reply=answer.next_step,
            details=answer.to_dict(),
        )

    return _recommend_next_response(paths)


def _video_profile_response(
    paths: ProjectPaths,
    utterance: str,
    *,
    video_tool_runner: Callable[..., subprocess.CompletedProcess[str]] | None,
    video_frame_decoder: Callable[[Path], bytes] | None,
) -> NaturalLanguageResponse | None:
    scenario_acceptance = _application_scenario_acceptance_confirmation(
        utterance
    )
    if scenario_acceptance is not None:
        scenario, asset_ids = scenario_acceptance
        return _accept_application_scenario_scope_response(
            paths,
            scenario,
            asset_ids,
        )
    if _is_application_scenario_acceptance_sample_request(utterance):
        return _application_scenario_acceptance_samples_response(paths)
    if _is_application_scenario_video_processing_confirmation(utterance):
        return _process_application_scenario_video_batches_response(
            paths,
            video_tool_runner=video_tool_runner,
            video_frame_decoder=video_frame_decoder,
        )
    if _is_application_scenario_video_status_request(utterance):
        return _application_scenario_video_status_response(paths)
    confirmation_asset_id = _video_tracer_confirmation_asset_id(utterance)
    if confirmation_asset_id is not None:
        return _confirm_video_tracer_response(paths, confirmation_asset_id)
    if _is_video_tracer_processing_confirmation(utterance):
        return _process_video_tracer_candidates_response(
            paths,
            video_tool_runner=video_tool_runner,
            video_frame_decoder=video_frame_decoder,
        )
    if _is_video_tracer_inspection_request(utterance):
        return _start_video_tracer_inspection_response(paths)
    if not _is_video_tracer_status_request(utterance):
        return None
    report_path = (
        paths.generated_dir
        / "cache"
        / "video-tracer-inspection"
        / "batches"
        / "quartz_fiber_tape"
        / "candidate-batch.json"
    )
    if not report_path.is_file():
        return NaturalLanguageResponse(
            intent="video_tracer_status",
            executed=False,
            needs_confirmation=True,
            message="石英纤维隔热带产品视频尚未生成候选检查批次。",
            copyable_reply="确认，检查固定 raw 文件夹中的石英纤维隔热带产品视频。",
            details={
                "status": "not_started",
                "expected_count": 8,
                "discovered_count": 0,
                "candidates": [],
            },
        )
    try:
        batch = json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return NaturalLanguageResponse(
            intent="video_tracer_status",
            executed=False,
            needs_confirmation=True,
            message="产品视频候选批次回执损坏，当前不能继续推荐或确认 tracer。",
            copyable_reply="确认，重新检查固定 raw 文件夹中的石英纤维隔热带产品视频。",
            details={"status": "invalid_batch_receipt"},
        )
    expected = int(batch.get("expected_count") or 8)
    discovered = int(batch.get("discovered_count") or 0)
    candidates = [
        {
            "asset_id": candidate.get("asset_id"),
            "source_relative_path": candidate.get("source_relative_path"),
            "status": candidate.get("status"),
            "title": candidate.get("codex_review", {}).get("title"),
            "tracer_suitability": candidate.get("codex_review", {}).get("tracer_suitability"),
            "tracer_reason": candidate.get("codex_review", {}).get("tracer_reason"),
        }
        for candidate in batch.get("candidates", [])
    ]
    status = str(batch.get("status") or "unknown")
    if status == "blocked_source_count_mismatch":
        message = (
            f"石英纤维隔热带产品视频候选批次当前为 {discovered}/{expected}，"
            "与固定批次数量不一致，因此不能推荐或确认 tracer。"
        )
        copyable_reply = "固定 raw 文件夹绝对路径是：<请填写包含全部 8 条产品视频的路径>"
    elif status == "awaiting_codex_review":
        message = (
            f"已登记 {discovered}/{expected} 条产品视频，"
            "候选帧已经准备，正在等待全部视频完成 Codex 语义复核。"
        )
        copyable_reply = "确认，继续完成全部产品视频的 Codex 复核。"
    elif status == "awaiting_tracer_confirmation":
        recommendation = batch.get("tracer_recommendation", {})
        asset_id = recommendation.get("recommended_asset_id")
        message = (
            f"全部 {discovered} 条产品视频已完成候选复核。"
            f"当前推荐 tracer：{asset_id}。{recommendation.get('reason', '')}"
        )
        copyable_reply = f"确认 tracer Asset ID：{asset_id}"
    else:
        message = (
            f"石英纤维隔热带产品视频候选批次状态为 {status}，"
            f"已发现 {discovered}/{expected} 条。"
        )
        copyable_reply = None
    return NaturalLanguageResponse(
        intent="video_tracer_status",
        executed=False,
        needs_confirmation=status != "tracer_confirmed",
        message=message,
        copyable_reply=copyable_reply,
        details={
            "status": status,
            "expected_count": expected,
            "discovered_count": discovered,
            "recommendation_allowed": bool(batch.get("recommendation_allowed")),
            "formal_profile_published": bool(batch.get("formal_profile_published")),
            "tracer_recommendation": batch.get("tracer_recommendation"),
            "candidates": candidates,
        },
    )


def _application_scenario_video_status_response(
    paths: ProjectPaths,
) -> NaturalLanguageResponse:
    roots = _quartz_application_video_roots(paths)
    if not roots:
        return NaturalLanguageResponse(
            intent="application_scenario_video_status",
            executed=False,
            needs_confirmation=True,
            message="当前固定 raw 目录中找不到石英纤维隔热带应用场景素材文件夹。",
            copyable_reply=(
                "固定应用场景素材文件夹绝对路径是："
                "<请填写包含各场景子文件夹的路径>"
            ),
            details={"status": "blocked_source_folder_missing", "scenarios": []},
        )
    if len(roots) > 1:
        return NaturalLanguageResponse(
            intent="application_scenario_video_status",
            executed=False,
            needs_confirmation=True,
            message="发现多个石英纤维隔热带应用场景素材根目录，当前不能判断固定来源。",
            copyable_reply="固定应用场景素材文件夹绝对路径是：<请确认一个路径>",
            details={
                "status": "blocked_source_folder_conflict",
                "candidate_roots": [str(item) for item in roots],
                "scenarios": [],
            },
        )
    root = roots[0]
    scopes = {
        item["source_application_scenario"]: item
        for item in read_application_scenario_scopes(
            paths,
            "product/quartz_fiber_tape",
        )
    }
    scenarios = []
    for folder in sorted(
        (item for item in root.iterdir() if item.is_dir()),
        key=lambda item: item.name,
    ):
        video_count = sum(
            1
            for item in folder.rglob("*")
            if item.is_file() and item.suffix.lower() in VIDEO_SUFFIXES
        )
        if not video_count:
            continue
        scenarios.append(
            {
                "name": folder.name,
                "video_count": video_count,
                "scope_status": scopes.get(folder.name, {}).get(
                    "status",
                    "not_started",
                ),
            }
        )
    total = sum(item["video_count"] for item in scenarios)
    return NaturalLanguageResponse(
        intent="application_scenario_video_status",
        executed=False,
        needs_confirmation=True,
        message=(
            f"固定应用场景素材根目录中发现 {len(scenarios)} 个一级场景、"
            f"共 {total} 条视频。处理时将按一级场景分别建立批次，"
            "更深目录会作为有序来源上下文保留。"
        ),
        copyable_reply="确认，开始按应用场景子文件夹处理石英纤维隔热带视频。",
        details={
            "status": "awaiting_scenario_batch_confirmation",
            "source_root": str(root),
            "scenario_count": len(scenarios),
            "video_count": total,
            "scenarios": scenarios,
        },
    )


def _process_application_scenario_video_batches_response(
    paths: ProjectPaths,
    *,
    video_tool_runner: Callable[..., subprocess.CompletedProcess[str]] | None,
    video_frame_decoder: Callable[[Path], bytes] | None,
) -> NaturalLanguageResponse:
    roots = _quartz_application_video_roots(paths)
    if len(roots) != 1:
        return _application_scenario_video_status_response(paths)
    kwargs: dict[str, Any] = {}
    if video_tool_runner is not None:
        kwargs["runner"] = video_tool_runner
    if video_frame_decoder is not None:
        kwargs["frame_decoder"] = video_frame_decoder
    try:
        result = process_application_scenario_batches(
            roots[0],
            paths,
            product_id="product/quartz_fiber_tape",
            batch_id="application-scenarios",
            **kwargs,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        return NaturalLanguageResponse(
            intent="application_scenario_video_batches_blocked",
            executed=False,
            needs_confirmation=True,
            message=(
                f"应用场景视频批次未完成：{exc}。"
                "没有发布正式视频档案，其他已验证场景不受影响。"
            ),
            copyable_reply="查看石英纤维隔热带应用场景视频批次状态。",
            details={
                "status": "processing_failed",
                "error": str(exc),
                "formal_profile_published": False,
            },
        )
    scenarios = [
        {
            "name": item.source_application_scenario,
            "video_count": item.batch_result.completed_count
            + item.batch_result.failed_count,
            "valid_count": item.batch_result.completed_count,
            "failed_count": item.batch_result.failed_count,
            "scope_status": "pending_acceptance",
            "acceptance_strategy": item.acceptance_sample.strategy,
            "acceptance_asset_ids": list(
                item.acceptance_sample.selected_asset_ids
            ),
            "manifest_path": str(item.batch_result.manifest_path),
        }
        for item in result.scenarios
    ]
    return NaturalLanguageResponse(
        intent="application_scenario_video_batches_prepared",
        executed=True,
        needs_confirmation=True,
        message=(
            f"已按 {len(scenarios)} 个一级应用场景分别处理"
            f" {sum(item['video_count'] for item in scenarios)} 条视频。"
            "各场景已形成独立检查点和风险抽样清单，当前等待人工验收；"
            "尚未发布正式视频档案。"
        ),
        copyable_reply="查看各应用场景的风险抽样验收清单。",
        details={
            "status": result.status,
            "scenario_count": len(scenarios),
            "video_count": sum(item["video_count"] for item in scenarios),
            "formal_profile_published": False,
            "scenarios": scenarios,
        },
    )


def _application_scenario_acceptance_samples_response(
    paths: ProjectPaths,
) -> NaturalLanguageResponse:
    scopes = [
        item
        for item in read_application_scenario_scopes(
            paths,
            "product/quartz_fiber_tape",
        )
        if item.get("status") == "pending_acceptance"
    ]
    scenarios = [
        {
            "name": item["source_application_scenario"],
            "strategy": item.get("acceptance_sample", {}).get("strategy"),
            "selected_asset_ids": list(
                item.get("acceptance_sample", {}).get(
                    "selected_asset_ids",
                    [],
                )
            ),
            "total_count": item.get("acceptance_sample", {}).get(
                "total_count",
                0,
            ),
        }
        for item in scopes
    ]
    if not scenarios:
        return NaturalLanguageResponse(
            intent="application_scenario_acceptance_samples",
            executed=False,
            needs_confirmation=False,
            message="当前没有等待人工验收的应用场景视频批次。",
            details={"status": "no_pending_acceptance", "scenarios": []},
        )
    first = scenarios[0]
    asset_text = "、".join(first["selected_asset_ids"])
    return NaturalLanguageResponse(
        intent="application_scenario_acceptance_samples",
        executed=False,
        needs_confirmation=True,
        message=(
            f"当前有 {len(scenarios)} 个应用场景等待风险抽样验收。"
            f"请先检查“{first['name']}”：{asset_text}。"
            "必须完整确认本场景的抽样 Asset ID，部分确认不会放行。"
        ),
        copyable_reply=(
            f"确认应用场景“{first['name']}”验收 Asset ID：{asset_text}"
        ),
        details={
            "status": "awaiting_scenario_acceptance",
            "scenarios": scenarios,
        },
    )


def _accept_application_scenario_scope_response(
    paths: ProjectPaths,
    scenario: str,
    asset_ids: list[str],
) -> NaturalLanguageResponse:
    try:
        accepted = accept_application_scenario_scope(
            paths,
            product_id="product/quartz_fiber_tape",
            source_application_scenario=scenario,
            accepted_asset_ids=asset_ids,
        )
    except (KeyError, ValueError) as exc:
        return NaturalLanguageResponse(
            intent="application_scenario_scope_acceptance_blocked",
            executed=False,
            needs_confirmation=True,
            message=f"应用场景“{scenario}”验收未完成：{exc}",
            copyable_reply="查看各应用场景的风险抽样验收清单。",
            details={
                "status": "acceptance_blocked",
                "source_application_scenario": scenario,
                "error": str(exc),
                "formal_profile_published": False,
            },
        )
    return NaturalLanguageResponse(
        intent="application_scenario_scope_verified",
        executed=True,
        needs_confirmation=False,
        message=(
            f"应用场景“{scenario}”的完整风险抽样范围已验证。"
            "本步骤只更新场景验收范围；尚未把未生成的视频档案误报为正式发布。"
        ),
        copyable_reply="查看各应用场景的风险抽样验收清单。",
        details={
            "status": accepted["status"],
            "source_application_scenario": scenario,
            "accepted_asset_ids": accepted["accepted_asset_ids"],
            "formal_profile_published": False,
        },
    )


def _quartz_application_video_roots(paths: ProjectPaths) -> list[Path]:
    raw_root = paths.raw_dir.resolve()
    known = [
        raw_root / "01_产品" / "02_石英纤维隔热带" / "04_应用场景素材",
        raw_root / "04_产品" / "01_石英纤维隔热带" / "04_应用场景素材",
    ]
    candidates = [path.resolve() for path in known if path.is_dir()]
    if raw_root.is_dir():
        for path in raw_root.rglob("04_应用场景素材"):
            if not path.is_dir() or "石英纤维隔热带" not in path.parent.name:
                continue
            resolved = path.resolve()
            if resolved not in candidates:
                candidates.append(resolved)
    populated = [
        root
        for root in candidates
        if any(
            item.is_file() and item.suffix.lower() in VIDEO_SUFFIXES
            for item in root.rglob("*")
        )
    ]
    return sorted(populated or candidates)


def _is_application_scenario_video_status_request(utterance: str) -> bool:
    return (
        "石英纤维隔热带" in utterance
        and "应用场景" in utterance
        and "视频" in utterance
        and any(token in utterance for token in ["状态", "进度", "批次"])
        and "确认" not in utterance
    )


def _is_application_scenario_video_processing_confirmation(
    utterance: str,
) -> bool:
    return (
        "确认" in utterance
        and "石英纤维隔热带" in utterance
        and "应用场景" in utterance
        and "视频" in utterance
        and ("子文件夹" in utterance or "按应用场景" in utterance)
        and ("开始" in utterance or "处理" in utterance)
    )


def _is_application_scenario_acceptance_sample_request(
    utterance: str,
) -> bool:
    return (
        "应用场景" in utterance
        and "风险抽样" in utterance
        and "验收清单" in utterance
        and "确认" not in utterance
    )


def _application_scenario_acceptance_confirmation(
    utterance: str,
) -> tuple[str, list[str]] | None:
    if not (
        "确认应用场景" in utterance
        and "验收" in utterance
        and "Asset ID" in utterance
    ):
        return None
    quoted = re.search(r"确认应用场景[“\"]([^”\"]+)[”\"]", utterance)
    if quoted:
        scenario = quoted.group(1).strip()
    else:
        plain = re.search(r"确认应用场景(.+?)验收", utterance)
        scenario = plain.group(1).strip(" ：:，,") if plain else ""
    asset_ids = re.findall(r"\bvideo_asset_[0-9a-f]{32}\b", utterance.lower())
    if not scenario:
        return None
    return scenario, list(dict.fromkeys(asset_ids))


def _process_video_tracer_candidates_response(
    paths: ProjectPaths,
    *,
    video_tool_runner: Callable[..., subprocess.CompletedProcess[str]] | None,
    video_frame_decoder: Callable[[Path], bytes] | None,
) -> NaturalLanguageResponse:
    folders = _quartz_product_video_folders(paths)
    if len(folders) != 1:
        return _start_video_tracer_inspection_response(paths)
    folder = folders[0]
    videos = [
        path
        for path in sorted(folder.rglob("*"))
        if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
    ] if folder.is_dir() else []
    if len(videos) != 8:
        return _start_video_tracer_inspection_response(paths)
    kwargs: dict[str, Any] = {}
    if video_tool_runner is not None:
        kwargs["runner"] = video_tool_runner
    if video_frame_decoder is not None:
        kwargs["frame_decoder"] = video_frame_decoder
    try:
        result = inspect_video_candidate_batch(
            folder,
            paths,
            product_id="product/quartz_fiber_tape",
            expected_count=8,
            **kwargs,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        return NaturalLanguageResponse(
            intent="video_tracer_inspection_failed",
            executed=False,
            needs_confirmation=True,
            message=(
                f"8 条产品视频候选处理未完成：{exc}。"
                "没有发布正式视频知识卡，raw 文件未被修改。"
            ),
            copyable_reply="确认，重新检查固定 raw 文件夹中的石英纤维隔热带产品视频。",
            details={"status": "processing_failed", "error": str(exc)},
        )
    return NaturalLanguageResponse(
        intent="video_tracer_candidates_prepared",
        executed=True,
        needs_confirmation=False,
        message=(
            f"已为 {result.discovered_count} 条产品视频完成登记、媒体事实读取、"
            "自适应抽帧和代表帧候选准备。下一步由 Codex 逐条完成语义复核；"
            "当前没有发布正式知识卡。"
        ),
        copyable_reply="继续完成这 8 条产品视频的 Codex 语义复核。",
        details={
            "status": result.status,
            "candidate_count": result.discovered_count,
            "expected_count": result.expected_count,
            "formal_profile_published": False,
            "candidates": [
                {
                    "asset_id": item.asset.asset_id,
                    "source_relative_path": item.asset.source_relative_path,
                    "status": item.status,
                    "duration_seconds": item.media_facts.duration_seconds,
                    "representative_frame_count": len(item.representative_candidates),
                }
                for item in result.inspections
            ],
        },
    )


def _start_video_tracer_inspection_response(
    paths: ProjectPaths,
) -> NaturalLanguageResponse:
    folders = _quartz_product_video_folders(paths)
    expected_folder = (
        paths.raw_dir
        / "01_产品"
        / "02_石英纤维隔热带"
        / "03_产品视频"
    )
    if not folders:
        return NaturalLanguageResponse(
            intent="video_tracer_inspection_blocked",
            executed=False,
            needs_confirmation=True,
            message=(
                "当前配置的 fixed raw 目录中找不到石英纤维隔热带产品视频文件夹，"
                f"预期位置为：{expected_folder}。未执行视频处理。"
            ),
            copyable_reply="固定 raw 文件夹绝对路径是：<请填写包含全部 8 条产品视频的路径>",
            details={
                "status": "blocked_source_folder_missing",
                "expected_count": 8,
                "discovered_count": 0,
                "expected_folder": str(expected_folder),
            },
        )
    if len(folders) > 1:
        return NaturalLanguageResponse(
            intent="video_tracer_inspection_blocked",
            executed=False,
            needs_confirmation=True,
            message=(
                "发现多个石英纤维隔热带产品视频文件夹，不能判断哪个是固定来源，"
                "因此未执行视频处理。"
            ),
            copyable_reply="固定 raw 文件夹绝对路径是：<请从候选路径中确认一个>",
            details={
                "status": "blocked_source_folder_conflict",
                "expected_count": 8,
                "candidate_folders": [str(folder) for folder in folders],
            },
        )
    folder = folders[0]
    videos = [
        path
        for path in sorted(folder.rglob("*"))
        if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
    ]
    if len(videos) != 8:
        return NaturalLanguageResponse(
            intent="video_tracer_inspection_blocked",
            executed=False,
            needs_confirmation=True,
            message=(
                f"固定产品视频文件夹当前发现 {len(videos)}/8 条视频，"
                "数量不完整，因此在 ffprobe、抽帧和 Codex 复核前已停止。"
            ),
            copyable_reply="固定 raw 文件夹绝对路径是：<请填写包含全部 8 条产品视频的路径>",
            details={
                "status": "blocked_source_count_mismatch",
                "expected_count": 8,
                "discovered_count": len(videos),
                "source_folder": str(folder),
                "source_files": [path.relative_to(folder).as_posix() for path in videos],
            },
        )
    return NaturalLanguageResponse(
        intent="video_tracer_inspection_ready",
        executed=False,
        needs_confirmation=True,
        message=(
            "固定产品视频文件夹已确认包含 8 条视频。"
            "下一步将读取媒体事实、生成分析帧并由 Codex 逐条复核；不会修改 raw，也不会发布知识卡。"
        ),
        copyable_reply="确认，开始处理这 8 条产品视频候选。",
        details={
            "status": "awaiting_batch_processing_confirmation",
            "expected_count": 8,
            "discovered_count": 8,
            "source_folder": str(folder),
            "source_files": [path.relative_to(folder).as_posix() for path in videos],
        },
    )


def _quartz_product_video_folders(paths: ProjectPaths) -> list[Path]:
    raw_root = paths.raw_dir.resolve()
    known = [
        raw_root / "01_产品" / "02_石英纤维隔热带" / "03_产品视频",
        raw_root / "04_产品" / "01_石英纤维隔热带" / "03_视频",
    ]
    candidates = [path.resolve() for path in known if path.is_dir()]
    if raw_root.is_dir():
        for path in raw_root.rglob("*"):
            if not path.is_dir() or path.name not in {"03_产品视频", "03_视频"}:
                continue
            if "石英纤维隔热带" not in path.parent.name:
                continue
            resolved = path.resolve()
            if resolved not in candidates:
                candidates.append(resolved)
    populated = [
        folder
        for folder in candidates
        if any(
            item.is_file() and item.suffix.lower() in VIDEO_SUFFIXES
            for item in folder.rglob("*")
        )
    ]
    return sorted(populated or candidates)


def _confirm_video_tracer_response(
    paths: ProjectPaths,
    confirmed_asset_id: str,
) -> NaturalLanguageResponse:
    batch_report_path = (
        paths.generated_dir
        / "cache"
        / "video-tracer-inspection"
        / "batches"
        / "quartz_fiber_tape"
        / "candidate-batch.json"
    )
    if not batch_report_path.is_file():
        return NaturalLanguageResponse(
            intent="video_tracer_confirmation_blocked",
            executed=False,
            needs_confirmation=True,
            message="当前没有可确认的产品视频候选批次，请先完成全部候选检查和推荐。",
            copyable_reply="查看石英纤维隔热带产品视频候选状态。",
        )
    try:
        batch = json.loads(batch_report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return NaturalLanguageResponse(
            intent="video_tracer_confirmation_blocked",
            executed=False,
            needs_confirmation=True,
            message="产品视频候选批次回执损坏，不能确认 tracer。",
            copyable_reply="确认，重新检查固定 raw 文件夹中的石英纤维隔热带产品视频。",
        )
    recommendation = batch.get("tracer_recommendation", {})
    recommended_asset_id = str(recommendation.get("recommended_asset_id") or "")
    if (
        batch.get("status") != "awaiting_tracer_confirmation"
        or not batch.get("recommendation_allowed")
        or not recommended_asset_id
    ):
        return NaturalLanguageResponse(
            intent="video_tracer_confirmation_blocked",
            executed=False,
            needs_confirmation=True,
            message="当前候选批次尚未完成全部 Codex 复核和 tracer 推荐，不能确认文件。",
            copyable_reply="查看石英纤维隔热带产品视频候选状态。",
        )
    if confirmed_asset_id != recommended_asset_id:
        return NaturalLanguageResponse(
            intent="video_tracer_confirmation_blocked",
            executed=False,
            needs_confirmation=True,
            message=(
                f"你确认的 Asset ID 是 {confirmed_asset_id}，"
                f"当前推荐的是 {recommended_asset_id}，两者不一致，未执行确认。"
            ),
            copyable_reply=f"确认 tracer Asset ID：{recommended_asset_id}",
        )
    candidate = next(
        (
            item
            for item in batch.get("candidates", [])
            if item.get("asset_id") == confirmed_asset_id
        ),
        None,
    )
    if candidate is None or not candidate.get("inspection_report"):
        return NaturalLanguageResponse(
            intent="video_tracer_confirmation_blocked",
            executed=False,
            needs_confirmation=True,
            message="推荐视频缺少可验证的候选检查回执，不能执行确认。",
            copyable_reply="确认，重新检查固定 raw 文件夹中的石英纤维隔热带产品视频。",
        )
    try:
        result = confirm_video_tracer_candidate(
            Path(str(candidate["inspection_report"])),
            paths,
            confirmed_asset_id=confirmed_asset_id,
        )
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
        return NaturalLanguageResponse(
            intent="video_tracer_confirmation_blocked",
            executed=False,
            needs_confirmation=True,
            message=f"tracer 确认未完成：{exc}",
            copyable_reply="查看石英纤维隔热带产品视频候选状态。",
        )
    return NaturalLanguageResponse(
        intent="video_tracer_confirmed",
        executed=True,
        needs_confirmation=False,
        message=(
            f"已确认 tracer Asset ID：{result.asset_id}。"
            "当前只完成候选文件确认，尚未发布正式视频知识卡。"
        ),
        copyable_reply="继续生成这个 tracer 的视频档案暂存稿。",
        details={
            "status": result.status,
            "asset_id": result.asset_id,
            "confirmed_at": result.confirmed_at,
            "formal_profile_published": False,
        },
    )


def _video_tracer_confirmation_asset_id(utterance: str) -> str | None:
    lower = utterance.lower()
    if "确认" not in utterance or "tracer" not in lower:
        return None
    match = re.search(r"\bvideo_asset_[0-9a-f]{32}\b", lower)
    return match.group(0) if match else None


def _is_video_tracer_inspection_request(utterance: str) -> bool:
    lower = utterance.lower()
    return (
        "确认" in utterance
        and "石英纤维隔热带" in utterance
        and "视频" in utterance
        and ("检查" in utterance or "处理" in utterance)
        and ("raw" in lower or "固定" in utterance or "候选" in utterance)
    )


def _is_video_tracer_processing_confirmation(utterance: str) -> bool:
    return (
        "确认" in utterance
        and "石英纤维隔热带" in utterance
        and "视频" in utterance
        and "候选" in utterance
        and ("开始处理" in utterance or "处理这 8 条" in utterance or "处理这8条" in utterance)
    )


def _is_video_tracer_status_request(utterance: str) -> bool:
    lower = utterance.lower()
    mentions_product_video = (
        "石英纤维隔热带" in utterance
        and "视频" in utterance
    )
    mentions_tracer = "tracer" in lower or "候选" in utterance or "抽帧" in utterance
    asks_status = any(token in utterance for token in ["状态", "进度", "怎么样", "到哪"])
    return mentions_product_video and mentions_tracer and asks_status


def _recommend_next_response(paths: ProjectPaths) -> NaturalLanguageResponse:
    summaries = scan_all_partitions(paths)
    actionable = [summary for summary in summaries if summary.recommended_next_action != "use_existing"]
    if not actionable:
        return NaturalLanguageResponse(
            intent="recommend_next",
            executed=False,
            needs_confirmation=False,
            message="当前没有明显需要继续整理的内容，可以直接进入使用资料模式。",
            copyable_reply="你可以直接问：石英纤维隔热带适合哪些客户场景？",
        )

    best = _best_summary(actionable)
    action_label = ACTION_LABELS[best.recommended_next_action]
    result_text = ACTION_RESULT_TEXT[best.recommended_next_action]
    return NaturalLanguageResponse(
        intent="recommend_next",
        executed=False,
        needs_confirmation=True,
        recommended_partition=best.name,
        recommended_action=best.recommended_next_action,
        message=(
            f"建议下一步先处理「{best.name}」：{action_label}。"
            f"{result_text}执行前会等你确认；这一步不会修改原始资料，也不会对外发布内容。"
        ),
        copyable_reply=_copyable_for(best),
        details=_summary_detail(best),
    )


def _linkedin_search_response(paths: ProjectPaths, utterance: str) -> NaturalLanguageResponse | None:
    if not is_linkedin_search_request(utterance):
        return None
    try:
        result = create_linkedin_search_run(paths, utterance)
    except (RuntimeError, ValueError, FileExistsError, OSError) as exc:
        return NaturalLanguageResponse(
            intent="linkedin_search_blocked",
            executed=False,
            needs_confirmation=False,
            message=f"无法创建 LinkedIn 搜索任务：{exc}",
        )
    if result.status == "blocked":
        return NaturalLanguageResponse(
            intent="linkedin_search_blocked",
            executed=True,
            needs_confirmation=False,
            message=(
                f"LinkedIn 搜索任务已记录为 blocked：{result.message}"
                f"运行目录：{result.run_dir}。当前不能进入搜索访谈。"
            ),
            copyable_reply="请明确一个已整理的拓霖正式产品后重新开始 LinkedIn 搜索任务。",
            details=result.to_dict(),
        )
    interview_complete = result.phase == "awaiting_browser_account_binding"
    return NaturalLanguageResponse(
        intent="linkedin_search_brief_confirmed" if interview_complete else "linkedin_search_interview",
        executed=True,
        needs_confirmation=True,
        message=(
            f"已创建独立 LinkedIn 搜索任务并绑定正式产品：{result.product_id}。"
            f"运行目录：{result.run_dir}。"
            + (
                "搜索简报已完整；下一步需要授权绑定已登录的 Chrome LinkedIn 账号。"
                if interview_complete
                else f"{result.message} 当前尚未操作浏览器或发送邀请。"
            )
        ),
        copyable_reply=(
            "允许绑定当前 Chrome 中已登录的 LinkedIn 账号。"
            if interview_complete
            else "继续 LinkedIn 搜索访谈。"
        ),
        details=result.to_dict(),
    )


def _linkedin_response(paths: ProjectPaths, utterance: str) -> NaturalLanguageResponse | None:
    if _is_linkedin_package_repair_request(utterance):
        campaign_dir = _resolve_linkedin_campaign_dir(paths, utterance)
        if campaign_dir is None:
            return _linkedin_missing_campaign_dir_response("修复 LinkedIn 发布包结构")
        try:
            result = repair_linkedin_manual_package_structure(campaign_dir)
        except (RuntimeError, ValueError, FileExistsError) as exc:
            return _linkedin_operation_error_response(str(exc))
        return NaturalLanguageResponse(
            intent="linkedin_package_structure_repaired",
            executed=True,
            needs_confirmation=False,
            message=(
                "已修复 LinkedIn 发布包结构。"
                f"迁移旧发布图 {len(result.migrated_images)} 张，更新导航文件 {len(result.updated_files)} 个。"
                "旧发布图已迁入各 Day 的 `Publish-Images/legacy-generated/`，后续发布图不再使用 `assets/linkedin-publishing-image.png` 作为最终路径。"
            ),
            details=result.to_dict(),
        )

    if _is_linkedin_marketing_review_decision_request(utterance):
        campaign_dir = _resolve_linkedin_campaign_dir(paths, utterance)
        if campaign_dir is None:
            return _linkedin_missing_campaign_dir_response("处理营销审阅决策")
        decision = "accepted" if _accepts_marketing_review(utterance) else "rejected"
        try:
            result = decide_linkedin_marketing_review(campaign_dir, decision)
        except (RuntimeError, ValueError, FileExistsError) as exc:
            return _linkedin_operation_error_response(str(exc))
        label = "采纳" if decision == "accepted" else "不采纳"
        return NaturalLanguageResponse(
            intent="linkedin_chinese_draft",
            executed=True,
            needs_confirmation=True,
            message=(
                f"已记录营销审阅决策：{label}。"
                f"中文 30 天贴文总稿已生成：{Path(result.campaign_dir) / '02_中文30天贴文总稿.md'}。"
                "确认中文总稿后才会拆成英文每日发布文件。"
            ),
            copyable_reply=f"确认中文总稿，活动文件夹：{result.campaign_dir}",
            details=result.to_dict(),
        )

    if _is_linkedin_marketing_review_request(utterance):
        campaign_dir = _resolve_linkedin_campaign_dir(paths, utterance)
        if campaign_dir is None:
            return _linkedin_missing_campaign_dir_response("进行营销策划审阅")
        try:
            result = create_linkedin_marketing_review(campaign_dir)
        except (RuntimeError, ValueError, FileExistsError) as exc:
            return _linkedin_operation_error_response(str(exc))
        return NaturalLanguageResponse(
            intent="linkedin_marketing_review",
            executed=True,
            needs_confirmation=True,
            message=(
                "已生成 LinkedIn 营销策划审阅。"
                f"请检查：{Path(result.plan_path)}。"
                "你可以采纳审阅建议，也可以不采纳并继续生成中文 30 天贴文总稿。"
            ),
            copyable_reply=f"采纳营销审阅建议，活动文件夹：{result.campaign_dir}",
            details=result.to_dict(),
        )

    if _is_linkedin_desktop_copy_request(utterance):
        campaign_dir = _resolve_linkedin_campaign_dir(paths, utterance)
        if campaign_dir is None:
            return _linkedin_missing_campaign_dir_response("复制30天发帖计划到桌面")
        try:
            result = copy_linkedin_campaign_to_desktop(campaign_dir, desktop_dir=_linkedin_desktop_root())
        except (RuntimeError, ValueError, FileExistsError) as exc:
            return _linkedin_operation_error_response(str(exc))
        return NaturalLanguageResponse(
            intent="linkedin_desktop_delivery_copy",
            executed=True,
            needs_confirmation=False,
            message=(
                "已复制完整 30 天发帖计划到桌面交付目录，包含每日贴文内容、人工发布包和源目录中已有的发布图。"
                f"桌面目录：{result.plan_path}。"
                "后续单日生成发布图时，会同步复制到这个桌面副本。"
            ),
            details=result.to_dict(),
        )

    if _is_linkedin_image_generation_choice_request(utterance):
        campaign_dir = _resolve_linkedin_campaign_dir(paths, utterance)
        day_number = _extract_linkedin_day_number(utterance)
        source_index = _extract_linkedin_source_index(utterance)
        categories = _extract_linkedin_image_categories(utterance)
        missing = []
        if campaign_dir is None:
            missing.append("活动文件夹")
        if day_number is None:
            missing.append("Day 编号")
        if source_index is None:
            missing.append("源图编号")
        if not categories:
            missing.append("1-3 个风格类别")
        if missing:
            return NaturalLanguageResponse(
                intent="linkedin_image_generation_choice",
                executed=False,
                needs_confirmation=True,
                message=f"生成单日发布图还需要：{'、'.join(missing)}。",
                copyable_reply="Day 01 源图选 1，风格选：原图轻量增强型、极简高端型，活动文件夹：/path/to/campaign",
            )
        try:
            result = prepare_linkedin_image_generation(campaign_dir, day_number, source_index, categories)
        except (RuntimeError, ValueError, FileExistsError) as exc:
            return _linkedin_operation_error_response(str(exc))
        category_names = "、".join(category["name"] for category in result.categories)
        return NaturalLanguageResponse(
            intent="linkedin_image_generation_ready",
            executed=True,
            needs_confirmation=True,
            message=(
                f"已准备 Day {day_number:02d} 发布图生成任务，类别：{category_names}。"
                "下一步请 Codex 使用 `tuolin-linkedin-image-style` skill 调用图片模型，"
                "基于所选源图为每个类别生成 1 张图，并保存到返回的输出目录。"
            ),
            details=result.to_dict(),
        )

    if _is_linkedin_day_image_selection_request(utterance):
        campaign_dir = _resolve_linkedin_campaign_dir(paths, utterance)
        day_number = _extract_linkedin_day_number(utterance)
        missing = []
        if campaign_dir is None:
            missing.append("活动文件夹")
        if day_number is None:
            missing.append("Day 编号")
        if missing:
            return NaturalLanguageResponse(
                intent="linkedin_image_selection",
                executed=False,
                needs_confirmation=True,
                message=f"生成单日发布图选择单还需要：{'、'.join(missing)}。",
                copyable_reply="生成 LinkedIn Day 01 发布图，活动文件夹：/path/to/campaign",
            )
        try:
            result = create_linkedin_image_selection_sheet(campaign_dir, day_number)
        except (RuntimeError, ValueError, FileExistsError) as exc:
            return _linkedin_operation_error_response(str(exc))
        recommended = "、".join(item["name"] for item in result.recommended_categories)
        return NaturalLanguageResponse(
            intent="linkedin_image_selection",
            executed=True,
            needs_confirmation=True,
            message=(
                f"已生成 Day {day_number:02d} 发布图选择单：{result.selection_path}。"
                f"推荐类别：{recommended}。"
                "请选择源图编号和 1-3 个风格类别后再生成图片。"
            ),
            copyable_reply=(
                f"Day {day_number:02d} 源图选 1，风格选：{result.recommended_categories[0]['name']}、"
                f"{result.recommended_categories[1]['name']}，活动文件夹：{result.campaign_dir}"
            ),
            details=result.to_dict(),
        )

    if _is_linkedin_confirm_chinese_draft_request(utterance):
        campaign_dir = _resolve_linkedin_campaign_dir(paths, utterance)
        if campaign_dir is None:
            return _linkedin_missing_campaign_dir_response("确认中文总稿")
        try:
            result = confirm_linkedin_chinese_draft(campaign_dir)
        except (RuntimeError, ValueError, FileExistsError) as exc:
            return _linkedin_operation_error_response(str(exc))
        return NaturalLanguageResponse(
            intent="linkedin_english_package",
            executed=True,
            needs_confirmation=True,
            message=(
                "已根据确认后的中文总稿生成英文发布包。"
                f"每日英文贴文在：{Path(result.campaign_dir) / 'daily'}。"
                f"人工发布包在：{Path(result.campaign_dir) / 'Manual-Posting-Package'}。"
                "请人工检查 Campaign Overview、Publishing Calendar 和 Day 01-Day 30 内容；"
                "下一步可以复制到桌面给老板查看；如需发布图，请按 Day 单独生成选择单。"
                f"透明 logo 默认读取：{default_linkedin_transparent_logo_path(paths)}。"
                "仍不会自动发布。"
            ),
            copyable_reply=f"将30天发帖计划复制到桌面方便查看，活动文件夹：{result.campaign_dir}",
            details=result.to_dict(),
        )

    if _is_linkedin_confirm_plan_request(utterance):
        campaign_dir = _resolve_linkedin_campaign_dir(paths, utterance)
        if campaign_dir is None:
            return _linkedin_missing_campaign_dir_response("确认策划")
        try:
            result = confirm_linkedin_campaign_plan(campaign_dir)
        except (RuntimeError, ValueError, FileExistsError) as exc:
            return _linkedin_operation_error_response(str(exc))
        return NaturalLanguageResponse(
            intent="linkedin_chinese_draft",
            executed=True,
            needs_confirmation=True,
            message=(
                "已跳过营销策划审阅，并根据确认后的策划生成中文 30 天贴文总稿。"
                f"请人工检查：{Path(result.campaign_dir) / '02_中文30天贴文总稿.md'}。"
                "确认中文总稿后才会拆成英文每日发布文件。"
            ),
            copyable_reply=f"确认中文总稿，活动文件夹：{result.campaign_dir}",
            details=result.to_dict(),
        )

    if _is_linkedin_image_request(utterance):
        return NaturalLanguageResponse(
            intent="linkedin_legacy_image_request_removed",
            executed=False,
            needs_confirmation=True,
            message=(
                "旧的批量 LinkedIn 配图入口已删除。"
                "发布图必须按 Day 单独生成：先生成 Day 发布图选择单，"
                "选择源图和 1-3 个风格类别后，再由 Codex 调用图片模型生成。"
            ),
            copyable_reply=(
                "生成 LinkedIn Day 01 发布图，活动文件夹：/path/to/campaign"
            ),
        )

    if is_linkedin_campaign_request(utterance):
        try:
            result = create_linkedin_campaign_plan(paths, utterance, output_root=_linkedin_output_root())
        except (RuntimeError, ValueError, FileExistsError) as exc:
            return _linkedin_operation_error_response(str(exc))
        return NaturalLanguageResponse(
            intent="linkedin_campaign_plan",
            executed=True,
            needs_confirmation=True,
            message=(
                "已生成 LinkedIn 30 天宣传策划包。"
                f"请先检查策划文件：{Path(result.campaign_dir) / '01_中文策划.md'}。"
                "你可以先进行营销策划审阅，也可以跳过审阅直接确认策划；不会自动发布。"
            ),
            copyable_reply=f"进行营销策划审阅，活动文件夹：{result.campaign_dir}",
            details=result.to_dict(),
        )

    return None


def _pending_response(paths: ProjectPaths) -> NaturalLanguageResponse:
    summaries = [summary for summary in scan_all_partitions(paths) if summary.recommended_next_action != "use_existing"]
    if not summaries:
        return NaturalLanguageResponse(
            intent="pending_partitions",
            executed=False,
            needs_confirmation=False,
            message="当前没有明显需要继续整理的分区，可以直接使用现有资料。",
            copyable_reply="你可以直接问：石英纤维隔热带适合哪些客户场景？",
            details=[],
        )
    best = _best_summary(summaries)
    detail = [_summary_detail(summary) for summary in summaries]
    return NaturalLanguageResponse(
        intent="pending_partitions",
        executed=False,
        needs_confirmation=True,
        recommended_partition=best.name,
        recommended_action=best.recommended_next_action,
        message=f"当前还有 {len(summaries)} 个分区有后续动作。建议先处理「{best.name}」。",
        copyable_reply=_copyable_for(best),
        details=detail,
    )


def _completion_check_response(paths: ProjectPaths, utterance: str) -> NaturalLanguageResponse:
    if "核心资料" in utterance:
        return _core_completion_check_response(paths)

    partition = _resolve_partition_from_text(utterance)
    if partition and partition != "ambiguous_high_silica":
        summary = scan_partition(paths, partition)
        finished = summary.recommended_next_action == "use_existing"
        action_label = ACTION_LABELS[summary.recommended_next_action]
        result_text = ACTION_RESULT_TEXT[summary.recommended_next_action]
        return NaturalLanguageResponse(
            intent="partition_completion_check",
            executed=False,
            needs_confirmation=not finished,
            recommended_partition=summary.name,
            recommended_action=summary.recommended_next_action,
            message=(
                f"「{summary.name}」当前状态：{_status_label(summary.status)}。"
                f"下一步建议：{action_label}。{result_text}"
            ),
            copyable_reply=None if finished else _copyable_for(summary),
            details=_summary_detail(summary),
        )

    return _status_response(paths)


def _core_completion_check_response(paths: ProjectPaths) -> NaturalLanguageResponse:
    last_run = paths.generated_dir / "cache" / "core-upstream" / "last-run.json"
    preview = paths.generated_dir / "cache" / "core-upstream-preview" / "preview.json"
    if last_run.exists():
        return NaturalLanguageResponse(
            intent="core_upstream_completion_check",
            executed=False,
            needs_confirmation=False,
            message="知识库核心资料最近已经执行过整理。是否还有待处理内容，需要看各产品分区和复核项状态。",
            copyable_reply="查看当前还有哪些资料需要继续整理。",
        )
    if preview.exists():
        return NaturalLanguageResponse(
            intent="core_upstream_completion_check",
            executed=False,
            needs_confirmation=True,
            message="知识库核心资料已有整理预览，但还没有执行写入候选卡片和复核项。",
            copyable_reply="确认，继续看核心资料里的图片、报告和视频。",
        )
    return NaturalLanguageResponse(
        intent="core_upstream_completion_check",
        executed=False,
        needs_confirmation=True,
        message="还没有发现知识库核心资料的整理记录。可以先整理核心资料；执行前会先生成预览或候选内容。",
        copyable_reply="整理知识库核心资料。",
    )


def _status_response(paths: ProjectPaths) -> NaturalLanguageResponse:
    summaries = scan_all_partitions(paths)
    status_payload = None
    try:
        status_payload = knowledge_status(paths)
    except FileNotFoundError:
        status_payload = {"manifest_summary": {"card_count": 0, "counts_by_type": {}, "open_review_count": 0}}
    ready_count = sum(1 for item in summaries if item.status == "ready")
    pending_processing_count = sum(item.pending_processing_count for item in summaries)
    product_pending_subfolder_count = sum(item.product_pending_subfolder_count for item in summaries)
    return NaturalLanguageResponse(
        intent="knowledge_status",
        executed=False,
        needs_confirmation=False,
        message=(
            f"当前共有 {len(summaries)} 个业务分区，其中 {ready_count} 个可直接使用。"
            f"产品素材还有 {product_pending_subfolder_count} 个子文件夹未完成。"
            f"仍有 {pending_processing_count} 个 PDF/视频素材需要继续处理。"
            f"知识卡片数量为 {status_payload['manifest_summary'].get('card_count', 0)}，"
            f"待确认内容 {status_payload['manifest_summary'].get('open_review_count', 0)} 条。"
        ),
        details={
            "partitions": [_summary_detail(summary) for summary in summaries],
            "card_counts": status_payload["manifest_summary"].get("counts_by_type", {}),
        },
    )


def _full_rebuild_plan(paths: ProjectPaths) -> NaturalLanguageResponse:
    summaries = scan_all_partitions(paths)
    queue = [_summary_detail(summary) for summary in summaries if summary.partition_type != "migration_buffer"]
    return NaturalLanguageResponse(
        intent="full_rebuild_plan",
        executed=False,
        needs_confirmation=True,
        message=(
            "从头整理会按业务分区逐个执行，不会直接扫描全部资料。"
            "建议先确认分区队列，再逐个处理；这一步不会修改原始资料，也不会对外发布内容。"
        ),
        copyable_reply="确认，按分区队列逐个整理。",
        details=queue,
    )


def _review_list_response(paths: ProjectPaths, utterance: str) -> NaturalLanguageResponse:
    partition = _resolve_partition_from_text(utterance)
    reviews = list_review_items(paths, partition.name if hasattr(partition, "name") else None)
    if not reviews:
        return NaturalLanguageResponse(
            intent="review_list",
            executed=False,
            needs_confirmation=False,
            message="当前没有需要你确认的内容。",
            details=[],
        )
    return NaturalLanguageResponse(
        intent="review_list",
        executed=False,
        needs_confirmation=True,
        message=f"当前有 {len(reviews)} 条内容需要你确认。你可以直接在对话框里给出确认结果和正确口径。",
        copyable_reply="这条确认，可以对外使用。正确口径是：<请填写确认后的内容>。请更新知识库。",
        details=[review.__dict__ for review in reviews],
    )


def _review_decision_response(paths: ProjectPaths, utterance: str) -> NaturalLanguageResponse:
    decision = _extract_review_decision(utterance)
    if decision is None:
        return NaturalLanguageResponse(
            intent="review_decision_unclear",
            executed=False,
            needs_confirmation=True,
            message="我还不能判断这条复核是确认、仅内部使用、拒绝还是暂缓。请写清楚处理方式和正确口径。",
            copyable_reply="这条确认，可以对外使用。正确口径是：<请填写确认后的内容>。请更新知识库。",
        )

    partition = _resolve_partition_from_text(utterance)
    reviews = list_review_items(paths, partition.name if hasattr(partition, "name") else None)
    selected = _select_review_item(reviews, utterance)
    if selected is None:
        if not reviews:
            return NaturalLanguageResponse(
                intent="review_decision_no_open_review",
                executed=False,
                needs_confirmation=True,
                message="当前没有找到待确认的复核项。请先问“有哪些内容需要我确认？”。",
                copyable_reply="有哪些内容需要我确认？",
            )
        return NaturalLanguageResponse(
            intent="review_decision_needs_review_selection",
            executed=False,
            needs_confirmation=True,
            message=f"当前有 {len(reviews)} 条待确认内容。请说明要处理第几条，或带上复核项标题/ID。",
            copyable_reply="第1条确认，可以对外使用。正确口径是：<请填写确认后的内容>。请更新知识库。",
            details=[review.__dict__ for review in reviews],
        )

    statement = _extract_review_statement(utterance)
    if decision in {"approve_external", "approve_internal"} and not statement:
        return NaturalLanguageResponse(
            intent="review_decision_statement_required",
            executed=False,
            needs_confirmation=True,
            message="确认复核项时需要提供正确口径，这样才能写入知识卡片。",
            copyable_reply="这条确认，可以对外使用。正确口径是：<请填写确认后的内容>。请更新知识库。",
            details=selected.__dict__,
        )

    try:
        preview = create_review_preview(paths, selected.review_id, decision)
        result = apply_review_decision(
            paths,
            selected.review_id,
            decision,
            preview.confirmation_token,
            reviewer="human",
            confirmed_statement=statement,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        return NaturalLanguageResponse(
            intent="review_decision_blocked",
            executed=False,
            needs_confirmation=True,
            message=str(exc),
            copyable_reply="有哪些内容需要我确认？",
        )

    action = {
        "approve_external": "确认并设为可对外使用",
        "approve_internal": "确认并设为仅内部使用",
        "reject": "拒绝并归档",
        "defer": "暂缓并归档为已记录决定",
    }[decision]
    updated = "、".join(result.updated_cards) if result.updated_cards else "无"
    return NaturalLanguageResponse(
        intent="review_decision_applied",
        executed=True,
        needs_confirmation=False,
        message=(
            f"已处理复核项：{selected.title}。处理方式：{action}。"
            f"更新卡片：{updated}。generated Agent 读取接口已刷新。"
        ),
        details=result.__dict__,
    )


def _core_response(paths: ProjectPaths, confirmed: bool) -> NaturalLanguageResponse:
    if confirmed:
        result = organize_core_upstream(paths)
        return NaturalLanguageResponse(
            intent="core_upstream_execute",
            executed=True,
            needs_confirmation=False,
            message=(
                f"已继续查看核心资料，整理出 {result.candidate_count} 条候选内容。"
                "原始资料没有被移动、删除或重命名；不会对外发布内容。需要你判断的内容已单独列出。"
            ),
            details=result.__dict__,
        )
    result = preview_core_upstream(paths)
    return NaturalLanguageResponse(
        intent="core_upstream_preview",
        executed=False,
        needs_confirmation=True,
        message=(
            f"已生成核心资料整理预览，共发现 {result.candidate_count} 条候选内容。"
            "确认前不会写入正式知识卡片，不会移动、删除或重命名原始资料。"
        ),
        copyable_reply="确认，继续看核心资料里的图片、报告和视频。",
        details=result.__dict__,
    )


def _update_plan(paths: ProjectPaths) -> NaturalLanguageResponse:
    needs_update = [summary for summary in scan_all_partitions(paths) if summary.status == "needs_update"]
    if not needs_update:
        return NaturalLanguageResponse(
            intent="update_plan",
            executed=False,
            needs_confirmation=False,
            message="当前没有发现必须先更新的分区。可以继续整理待处理资料或直接使用现有资料。",
            copyable_reply="查看当前还有哪些分区需要继续整理。",
            details=[],
        )
    best = _best_summary(needs_update)
    return NaturalLanguageResponse(
        intent="update_plan",
        executed=False,
        needs_confirmation=True,
        recommended_partition=best.name,
        recommended_action="update_first",
        message=f"发现 {len(needs_update)} 个分区资料有变化。建议先更新「{best.name}」，执行前会等你确认。",
        copyable_reply=f"确认，先更新{best.name}资料。",
        details=[_summary_detail(summary) for summary in needs_update],
    )


def _partition_plan(paths: ProjectPaths, partition) -> NaturalLanguageResponse:
    summary = scan_partition(paths, partition)
    return NaturalLanguageResponse(
        intent="partition_plan",
        executed=False,
        needs_confirmation=True,
        recommended_partition=partition.name,
        recommended_action=summary.recommended_next_action,
        message=(
            f"准备整理「{partition.name}」。整理后会得到可检查的知识卡片、证据和需要确认的问题。"
            "执行前会等你确认；这一步不会修改原始资料，也不会对外发布内容。"
        ),
        copyable_reply=f"确认，开始整理{partition.name}资料。",
        details=_summary_detail(summary),
    )


def _execute_partition_organize(paths: ProjectPaths, partition) -> NaturalLanguageResponse:
    result = organize_partition(paths, partition.name)
    return NaturalLanguageResponse(
        intent="partition_execute",
        executed=True,
        needs_confirmation=False,
        recommended_partition=partition.name,
        message=(
            f"已整理「{partition.name}」资料，生成了知识卡片、证据和需要确认的问题。"
            "原始资料没有被移动、删除或重命名；不会对外发布内容。"
        ),
        details=result.__dict__,
    )


def _execute_recommended(paths: ProjectPaths) -> NaturalLanguageResponse:
    best = _best_summary([summary for summary in scan_all_partitions(paths) if summary.recommended_next_action != "use_existing"])
    if best is None:
        return NaturalLanguageResponse(
            intent="confirm_recommended",
            executed=False,
            needs_confirmation=False,
            message="当前没有明显需要执行的下一步，可以直接使用资料。",
            copyable_reply="你可以直接问：石英纤维隔热带适合哪些客户场景？",
        )
    partition = find_partition(best.slug)
    if best.recommended_next_action == "review_required":
        return _review_list_response(paths, best.name)
    if best.recommended_next_action in {"continue_reading", "organize_usable"} and partition is not None:
        return _execute_partition_organize(paths, partition)
    return NaturalLanguageResponse(
        intent="confirm_recommended",
        executed=False,
        needs_confirmation=False,
        recommended_partition=best.name,
        recommended_action=best.recommended_next_action,
        message=f"推荐下一步是「{best.name}」：{ACTION_LABELS[best.recommended_next_action]}。当前切片只给出计划，不执行这个动作。",
        details=_summary_detail(best),
    )


def _ambiguous_high_silica_response(paths: ProjectPaths) -> NaturalLanguageResponse:
    adhesive = scan_partition(paths, find_partition("高硅氧纤维隔热带_有背胶"))
    non_adhesive = scan_partition(paths, find_partition("高硅氧纤维隔热带_无背胶"))
    best = _best_summary([adhesive, non_adhesive])
    return NaturalLanguageResponse(
        intent="ambiguous_partition",
        executed=False,
        needs_confirmation=True,
        recommended_partition=best.name,
        recommended_action=best.recommended_next_action,
        message="高硅氧纤维隔热带在 2.0 中分成有背胶和无背胶两个产品，请明确要整理哪一个。",
        copyable_reply=f"确认，开始整理{best.name}资料。",
        details=[_summary_detail(adhesive), _summary_detail(non_adhesive)],
    )


def _best_summary(summaries: list[PartitionSummary]) -> PartitionSummary | None:
    if not summaries:
        return None
    return sorted(
        summaries,
        key=lambda summary: (
            BUSINESS_PARTITION_PRIORITY.get(summary.slug, 100),
            GLOBAL_ACTION_PRIORITY[summary.recommended_next_action],
            summary.name,
        ),
    )[0]


def _copyable_for(summary: PartitionSummary) -> str:
    if summary.recommended_next_action == "review_required":
        return f"{summary.name}有哪些内容需要我确认？"
    if summary.recommended_next_action == "continue_reading":
        return f"确认，继续看{summary.name}资料。"
    if summary.recommended_next_action == "organize_usable":
        return f"确认，先把{summary.name}整理成可用资料。"
    if summary.recommended_next_action == "update_first":
        return f"确认，先更新{summary.name}资料。"
    if summary.recommended_next_action == "prepare_raw":
        return f"我先补充{summary.name}资料。"
    return f"根据当前资料回答：{summary.name}现在有哪些可用资料？"


def _summary_detail(summary: PartitionSummary) -> dict[str, Any]:
    return {
        "name": summary.name,
        "status_label": _status_label(summary.status),
        "next_step": ACTION_LABELS[summary.recommended_next_action],
        "pending_material_count": summary.pending_material_count,
        "pending_processing_count": summary.pending_processing_count,
        "pdf_progress": f"{summary.pdf_processed_count}/{summary.pdf_total_count}",
        "pdf_pending_count": summary.pdf_pending_count,
        "video_progress": f"{summary.video_processed_count}/{summary.video_total_count}",
        "video_pending_count": summary.video_pending_count,
        "product_material_status": _product_material_status_label(summary.product_material_status),
        "product_pending_subfolder_count": summary.product_pending_subfolder_count,
        "product_pending_registration_count": summary.product_pending_registration_count,
        "product_material_progress": [
            {
                "name": item.name,
                "status": _product_material_status_label(item.status),
                "total_file_count": item.total_file_count,
                "registered_file_count": item.registered_file_count,
                "pending_registration_count": item.pending_registration_count,
                "pending_processing_count": item.pending_processing_count,
                "pdf_progress": item.pdf_progress,
                "video_progress": item.video_progress,
            }
            for item in summary.product_material_progress
        ],
        "recognized_unapplied_count": summary.recognized_unapplied_count,
        "review_item_count": summary.review_item_count,
    }


def _status_label(status: str) -> str:
    return {
        "not_started": "还没整理",
        "ready": "可用",
        "needs_update": "需要更新",
        "pending_review": "待确认",
        "incomplete_materials": "资料不完整",
    }.get(status, status)


def _product_material_status_label(status: str) -> str:
    return {
        "not_applicable": "不适用",
        "not_started": "未开始",
        "in_progress": "整理中",
        "complete": "已完成",
    }.get(status, status)


def _resolve_partition_from_text(utterance: str):
    if "高硅氧纤维隔热带" in utterance and "有背胶" not in utterance and "无背胶" not in utterance:
        return "ambiguous_high_silica"
    aliases = {
        "石英纤维隔热带": "石英纤维隔热带",
        "世英纤维隔热带": "石英纤维隔热带",
        "陶瓷纤维隔热带": "陶瓷纤维隔热带",
        "玄武岩纤维隔热带": "玄武岩纤维隔热带",
        "高硅氧纤维隔热带_有背胶": "高硅氧纤维隔热带_有背胶",
        "高硅氧有背胶": "高硅氧纤维隔热带_有背胶",
        "有背胶": "高硅氧纤维隔热带_有背胶",
        "高硅氧纤维隔热带_无背胶": "高硅氧纤维隔热带_无背胶",
        "高硅氧无背胶": "高硅氧纤维隔热带_无背胶",
        "无背胶": "高硅氧纤维隔热带_无背胶",
        "公司资料": "公司能力",
        "公司能力": "公司能力",
        "标准资料": "标准法规",
        "标准": "标准法规",
        "市场资料": "市场情报",
        "市场": "市场情报",
        "销售物料": "销售物料",
        "客户问题": "客户问题/客服反馈",
        "客服反馈": "客户问题/客服反馈",
        "不好判断归属": "待迁移素材暂存区",
        "不确定归属": "待迁移素材暂存区",
        "待人工判定": "待迁移素材暂存区",
    }
    for text, partition_name in aliases.items():
        if text in utterance:
            return find_partition(partition_name)
    return None


def _is_confirmed(utterance: str) -> bool:
    return utterance.startswith("确认") or "确认，" in utterance


def _linkedin_output_root() -> Path | None:
    configured = os.environ.get("TUOLIN_LINKEDIN_OUTPUT_ROOT")
    if not configured:
        return None
    return Path(configured).expanduser()


def _linkedin_desktop_root() -> Path | None:
    configured = os.environ.get("TUOLIN_LINKEDIN_DESKTOP_ROOT")
    if configured:
        return Path(configured).expanduser()
    configured = os.environ.get("TUOLIN_LINKEDIN_OUTPUT_ROOT")
    if configured:
        return Path(configured).expanduser()
    return None


def _resolve_linkedin_campaign_dir(paths: ProjectPaths, utterance: str) -> Path | None:
    explicit = _extract_linkedin_path(utterance, ["活动文件夹", "campaign-dir", "campaign_dir", "项目目录"])
    if explicit is not None:
        return explicit
    candidates = _linkedin_campaign_dir_candidates(paths)
    if len(candidates) == 1:
        return candidates[0]
    default = paths.generated_dir / "reports" / "linkedin-30-day-special-fiberglass-tape"
    if default.exists() and _looks_like_linkedin_campaign_dir(default):
        return default
    return None


def _linkedin_campaign_dir_candidates(paths: ProjectPaths) -> list[Path]:
    reports_dir = paths.generated_dir / "reports"
    if not reports_dir.exists():
        return []
    candidates = []
    for path in sorted(reports_dir.iterdir()):
        if path.is_dir() and _looks_like_linkedin_campaign_dir(path):
            candidates.append(path.resolve())
    return candidates


def _looks_like_linkedin_campaign_dir(path: Path) -> bool:
    return (
        (path / "campaign-manifest.json").exists()
        or (path / "Manual-Posting-Package").is_dir()
        or (path / "LinkedIn-30-Day-Plan-and-Posts.md").exists()
    )


def _is_linkedin_confirm_plan_request(utterance: str) -> bool:
    return "确认策划" in utterance and _mentions_linkedin_context(utterance)


def _is_linkedin_confirm_chinese_draft_request(utterance: str) -> bool:
    return ("确认中文总稿" in utterance or "确认中文30天贴文总稿" in utterance) and _mentions_linkedin_context(
        utterance
    )


def _is_linkedin_marketing_review_request(utterance: str) -> bool:
    if "采纳" in utterance or "不采纳" in utterance:
        return False
    return "营销策划审阅" in utterance or "进行营销审阅" in utterance or "进行智能审阅" in utterance


def _is_linkedin_package_repair_request(utterance: str) -> bool:
    if not _mentions_linkedin_context(utterance):
        return False
    return any(term in utterance for term in ["修复发布包结构", "迁移发布包结构", "修复 LinkedIn 发布包", "迁移旧发布图", "迁移到最新结构"])


def _is_linkedin_marketing_review_decision_request(utterance: str) -> bool:
    return ("审阅" in utterance and ("采纳" in utterance or "不采纳" in utterance)) and _mentions_linkedin_context(
        utterance
    )


def _accepts_marketing_review(utterance: str) -> bool:
    return "不采纳" not in utterance and "采纳" in utterance


def _is_linkedin_desktop_copy_request(utterance: str) -> bool:
    return "复制到桌面" in utterance and ("30天" in utterance or "发帖计划" in utterance or "LinkedIn" in utterance)


def _is_linkedin_image_request(utterance: str) -> bool:
    image_words = ["生成配图", "生成发布图", "生成图片", "生成 LinkedIn 配图", "生成领英配图"]
    return any(word in utterance for word in image_words) and _mentions_linkedin_context(utterance)


def _is_linkedin_day_image_selection_request(utterance: str) -> bool:
    if not _mentions_linkedin_context(utterance):
        return False
    if _is_linkedin_image_generation_choice_request(utterance):
        return False
    mentions_day = _extract_linkedin_day_number(utterance) is not None
    mentions_image = "发布图" in utterance or "配图" in utterance or "图片" in utterance
    return mentions_day and mentions_image and "生成" in utterance


def _is_linkedin_image_generation_choice_request(utterance: str) -> bool:
    return (
        _extract_linkedin_day_number(utterance) is not None
        and _extract_linkedin_source_index(utterance) is not None
        and bool(_extract_linkedin_image_categories(utterance))
    )


def _mentions_linkedin_context(utterance: str) -> bool:
    return (
        "LinkedIn" in utterance
        or "Linkedin" in utterance
        or "linkedin" in utterance
        or "领英" in utterance
        or "活动文件夹" in utterance
        or "campaign-dir" in utterance
        or "campaign_dir" in utterance
    )


def _extract_linkedin_path(utterance: str, labels: list[str]) -> Path | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    stop_labels = (
        "活动文件夹|campaign-dir|campaign_dir|logo|Logo|透明logo|透明背景logo|源图|产品源图|source-image|source_image|tags|Tags|标签|画面tags|画面 tags"
    )
    match = re.search(
        rf"(?:{label_pattern})\s*[：:=]\s*(.+?)(?=\s*(?:，|,)\s*(?:{stop_labels})\s*[：:=]|$)",
        utterance,
    )
    if not match:
        return None
    value = match.group(1).strip().strip("'\"")
    if not value:
        return None
    return Path(value).expanduser()


def _extract_linkedin_day_number(utterance: str) -> int | None:
    match = re.search(r"(?:Day|day|第)\s*0?([1-9]|[12][0-9]|30)\s*(?:天|日)?", utterance)
    if not match:
        return None
    return int(match.group(1))


def _extract_linkedin_tags(utterance: str) -> list[str]:
    match = re.search(r"(?:tags|Tags|标签|画面tags|画面 tags)\s*[：:=]\s*(.+)$", utterance)
    if not match:
        return []
    value = match.group(1).strip().strip("'\"")
    if not value:
        return []
    parts = re.split(r"[,，;；|/]+", value)
    return [part.strip() for part in parts if part.strip()]


def _extract_linkedin_source_index(utterance: str) -> int | None:
    match = re.search(r"源图\s*选\s*([0-9]+)", utterance)
    if not match:
        match = re.search(r"source\s*(?:image)?\s*([0-9]+)", utterance, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _extract_linkedin_image_categories(utterance: str) -> list[str]:
    match = re.search(r"(?:风格选|类别选|风格类别|类别)\s*[：:=]\s*(.+?)(?=\s*(?:，|,)\s*活动文件夹\s*[：:=]|$)", utterance)
    if not match:
        return []
    value = match.group(1).strip().strip("'\"")
    if not value:
        return []
    parts = re.split(r"[,，;；|/、]+", value)
    return [part.strip() for part in parts if part.strip()]


def _linkedin_missing_campaign_dir_response(action: str) -> NaturalLanguageResponse:
    return NaturalLanguageResponse(
        intent="linkedin_campaign_dir_required",
        executed=False,
        needs_confirmation=True,
        message=f"{action}需要提供活动文件夹路径，这样才能找到上一步生成的 campaign-manifest.json。",
        copyable_reply=f"{action}，活动文件夹：/path/to/campaign",
    )


def _linkedin_operation_error_response(message: str) -> NaturalLanguageResponse:
    return NaturalLanguageResponse(
        intent="linkedin_operation_blocked",
        executed=False,
        needs_confirmation=True,
        message=message,
        copyable_reply="请切换到有效知识库项目目录，或先初始化知识库并重建 Agent读取接口。",
    )


def _is_confirm_recommended(utterance: str) -> bool:
    return _is_confirmed(utterance) and "推荐" in utterance


def _is_status_request(utterance: str) -> bool:
    return "查看知识库状态" in utterance or "整体状态" in utterance


def _is_pending_request(utterance: str) -> bool:
    return (
        "还有哪些分区" in utterance
        or "哪些内容需要处理" in utterance
        or "还有哪些资料" in utterance
        or "哪些资料需要" in utterance
    )


def _is_completion_check_request(utterance: str) -> bool:
    return "整理完了吗" in utterance or "整理完成了吗" in utterance or "整理好了没" in utterance


def _is_full_rebuild_request(utterance: str) -> bool:
    return any(word in utterance for word in ["从头整理", "重新整理", "全量整理"])


def _is_review_request(utterance: str) -> bool:
    return "复核" in utterance or "需要我确认" in utterance or "有哪些内容需要我确认" in utterance


def _is_review_decision_request(utterance: str) -> bool:
    decision_terms = [
        "正确口径",
        "可以对外使用",
        "可对外使用",
        "仅内部使用",
        "只允许内部",
        "不要写入",
        "不对",
        "归档",
        "暂缓",
    ]
    return any(term in utterance for term in decision_terms) and (
        "更新知识库" in utterance
        or "复核项" in utterance
        or "这条" in utterance
        or re.search(r"第\s*[0-9一二三四五六七八九十]+\s*条", utterance) is not None
    )


def _extract_review_decision(utterance: str) -> str | None:
    if "暂缓" in utterance:
        return "defer"
    if any(term in utterance for term in ["不对", "不要写入", "拒绝", "归档"]):
        return "reject"
    if any(term in utterance for term in ["仅内部", "只允许内部", "内部使用"]):
        return "approve_internal"
    if any(term in utterance for term in ["可以对外", "可对外", "对外使用", "确认", "正确口径"]):
        return "approve_external"
    return None


def _select_review_item(reviews: list[Any], utterance: str):
    if not reviews:
        return None
    explicit_id = _extract_review_id(utterance)
    if explicit_id:
        for review in reviews:
            if review.review_id == explicit_id:
                return review
        return None
    index = _extract_review_index(utterance)
    if index is not None:
        if 1 <= index <= len(reviews):
            return reviews[index - 1]
        return None
    if len(reviews) == 1:
        return reviews[0]
    return None


def _extract_review_id(utterance: str) -> str | None:
    match = re.search(r"(review_item/[A-Za-z0-9_./-]+)", utterance)
    return match.group(1).rstrip("。，,") if match else None


def _extract_review_index(utterance: str) -> int | None:
    match = re.search(r"第\s*([0-9一二三四五六七八九十]+)\s*条", utterance)
    if not match:
        return None
    value = match.group(1)
    if value.isdigit():
        return int(value)
    digits = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    return digits.get(value)


def _extract_review_statement(utterance: str) -> str | None:
    patterns = [
        r"正确口径是\s*[：:]\s*(.+?)(?:\s*请|$)",
        r"正确口径\s*[：:]\s*(.+?)(?:\s*请|$)",
        r"原因是\s*[：:]\s*(.+?)(?:\s*请|$)",
        r"原因\s*[：:]\s*(.+?)(?:\s*请|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, utterance)
        if match:
            value = match.group(1).strip().strip("；;，, ")
            return value or None
    return None


def _is_core_request(utterance: str) -> bool:
    return "核心资料" in utterance and ("整理" in utterance or "继续看" in utterance or "阅读" in utterance)


def _is_update_request(utterance: str) -> bool:
    return "更新" in utterance and "知识库" in utterance


def _is_partition_organize_request(utterance: str) -> bool:
    return any(word in utterance for word in ["整理", "继续看", "可用资料", "开始整理"])


def _looks_like_business_question(utterance: str) -> bool:
    return any(word in utterance for word in ["适合", "区别", "哪些产品", "产品介绍", "客户场景"])

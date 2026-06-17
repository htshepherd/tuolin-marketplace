from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from pathlib import Path
import re
from typing import Any

from .agent_interface import knowledge_status
from .core_upstream import organize_core_upstream, preview_core_upstream
from .linkedin_agent import (
    confirm_linkedin_campaign_plan,
    confirm_linkedin_chinese_draft,
    create_linkedin_campaign_plan,
    generate_linkedin_publishing_images,
    is_linkedin_campaign_request,
)
from .partitions import PARTITIONS, PartitionSummary, find_partition, scan_all_partitions, scan_partition
from .partition_organizer import organize_partition
from .project_layout import ProjectPaths
from .question_answering import answer_question
from .review_workflow import list_review_items


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


def route_natural_language(paths: ProjectPaths, text: str) -> NaturalLanguageResponse:
    utterance = text.strip()
    confirmed = _is_confirmed(utterance)

    linkedin_response = _linkedin_response(paths, utterance)
    if linkedin_response is not None:
        return linkedin_response

    if _is_status_request(utterance):
        return _status_response(paths)

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


def _linkedin_response(paths: ProjectPaths, utterance: str) -> NaturalLanguageResponse | None:
    if _is_linkedin_confirm_chinese_draft_request(utterance):
        campaign_dir = _extract_linkedin_path(utterance, ["活动文件夹", "campaign-dir", "campaign_dir"])
        if campaign_dir is None:
            return _linkedin_missing_campaign_dir_response("确认中文总稿")
        try:
            result = confirm_linkedin_chinese_draft(campaign_dir)
        except (RuntimeError, ValueError) as exc:
            return _linkedin_operation_error_response(str(exc))
        return NaturalLanguageResponse(
            intent="linkedin_english_package",
            executed=True,
            needs_confirmation=True,
            message=(
                "已根据确认后的中文总稿生成英文发布包。"
                f"每日英文贴文在：{Path(result.campaign_dir) / 'daily'}。"
                "下一步如需生成配图，请提供透明背景 logo 和产品源图路径；仍不会自动发布。"
            ),
            copyable_reply=(
                "生成 LinkedIn 配图，"
                f"活动文件夹：{result.campaign_dir}，"
                "logo：/path/to/transparent-logo.png，源图：/path/to/source-image.png"
            ),
            details=result.to_dict(),
        )

    if _is_linkedin_confirm_plan_request(utterance):
        campaign_dir = _extract_linkedin_path(utterance, ["活动文件夹", "campaign-dir", "campaign_dir"])
        if campaign_dir is None:
            return _linkedin_missing_campaign_dir_response("确认策划")
        try:
            result = confirm_linkedin_campaign_plan(campaign_dir)
        except (RuntimeError, ValueError) as exc:
            return _linkedin_operation_error_response(str(exc))
        return NaturalLanguageResponse(
            intent="linkedin_chinese_draft",
            executed=True,
            needs_confirmation=True,
            message=(
                "已根据确认后的策划生成中文 30 天贴文总稿。"
                f"请人工检查：{Path(result.campaign_dir) / '02_中文30天贴文总稿.md'}。"
                "确认中文总稿后才会拆成英文每日发布文件。"
            ),
            copyable_reply=f"确认中文总稿，活动文件夹：{result.campaign_dir}",
            details=result.to_dict(),
        )

    if _is_linkedin_image_request(utterance):
        campaign_dir = _extract_linkedin_path(utterance, ["活动文件夹", "campaign-dir", "campaign_dir"])
        logo_path = _extract_linkedin_path(utterance, ["logo", "Logo", "透明logo", "透明背景logo"])
        source_path = _extract_linkedin_path(utterance, ["源图", "产品源图", "source-image", "source_image"])
        missing = []
        if campaign_dir is None:
            missing.append("活动文件夹")
        if logo_path is None:
            missing.append("透明背景 logo")
        if source_path is None:
            missing.append("产品源图")
        if missing:
            return NaturalLanguageResponse(
                intent="linkedin_image_assets",
                executed=False,
                needs_confirmation=True,
                message=(
                    "生成 LinkedIn 配图还需要："
                    f"{'、'.join(missing)}。logo 必须是透明背景 PNG/WebP；"
                    "tags 会按每日主题生成，不写进配置文件。"
                ),
                copyable_reply=(
                    "生成 LinkedIn 配图，"
                    "活动文件夹：/path/to/campaign，"
                    "logo：/path/to/transparent-logo.png，源图：/path/to/source-image.png"
                ),
            )
        try:
            result = generate_linkedin_publishing_images(campaign_dir, logo_path, source_path)
        except (RuntimeError, ValueError) as exc:
            return _linkedin_operation_error_response(str(exc))
        return NaturalLanguageResponse(
            intent="linkedin_image_assets",
            executed=True,
            needs_confirmation=False,
            message=(
                "已生成 30 张 LinkedIn 发布配图，并把每张图写回对应 daily/day-XX.md。"
                f"配图目录：{Path(result.campaign_dir) / 'assets' / 'publishing-images'}。"
                "这一步只生成文件，不会自动发布。"
            ),
            details=result.to_dict(),
        )

    if is_linkedin_campaign_request(utterance):
        try:
            result = create_linkedin_campaign_plan(paths, utterance, output_root=_linkedin_output_root())
        except (RuntimeError, ValueError) as exc:
            return _linkedin_operation_error_response(str(exc))
        return NaturalLanguageResponse(
            intent="linkedin_campaign_plan",
            executed=True,
            needs_confirmation=True,
            message=(
                "已生成 LinkedIn 30 天宣传策划包。"
                f"请先检查策划文件：{Path(result.campaign_dir) / '01_中文策划.md'}。"
                "确认策划后才会生成 30 天中文贴文总稿；不会自动发布。"
            ),
            copyable_reply=f"确认策划，活动文件夹：{result.campaign_dir}",
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
        message=f"当前有 {len(reviews)} 条内容需要你确认。确认前不会写入正式知识卡片。",
        copyable_reply="请先生成知识卡片修改预览，不要直接写入。",
        details=[review.__dict__ for review in reviews],
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


def _is_linkedin_confirm_plan_request(utterance: str) -> bool:
    return "确认策划" in utterance and _mentions_linkedin_context(utterance)


def _is_linkedin_confirm_chinese_draft_request(utterance: str) -> bool:
    return ("确认中文总稿" in utterance or "确认中文30天贴文总稿" in utterance) and _mentions_linkedin_context(
        utterance
    )


def _is_linkedin_image_request(utterance: str) -> bool:
    image_words = ["生成配图", "生成发布图", "生成图片", "生成 LinkedIn 配图", "生成领英配图"]
    return any(word in utterance for word in image_words) and _mentions_linkedin_context(utterance)


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
        "活动文件夹|campaign-dir|campaign_dir|logo|Logo|透明logo|透明背景logo|源图|产品源图|source-image|source_image"
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


def _is_full_rebuild_request(utterance: str) -> bool:
    return any(word in utterance for word in ["从头整理", "重新整理", "全量整理"])


def _is_review_request(utterance: str) -> bool:
    return "复核" in utterance or "需要我确认" in utterance or "有哪些内容需要我确认" in utterance


def _is_core_request(utterance: str) -> bool:
    return "核心资料" in utterance and ("整理" in utterance or "继续看" in utterance or "阅读" in utterance)


def _is_update_request(utterance: str) -> bool:
    return "更新" in utterance and "知识库" in utterance


def _is_partition_organize_request(utterance: str) -> bool:
    return any(word in utterance for word in ["整理", "继续看", "可用资料", "开始整理"])


def _looks_like_business_question(utterance: str) -> bool:
    return any(word in utterance for word in ["适合", "区别", "哪些产品", "产品介绍", "客户场景"])

from __future__ import annotations

import re
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agent_interface import refresh_agent_interface_after_write
from .navigation import refresh_navigation
from .partitions import PartitionDefinition, find_partition, mark_partition_organized
from ..shared.project_layout import ProjectPaths


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
DOCUMENT_SUFFIXES = {".pdf", ".md", ".docx", ".doc", ".xlsx", ".xls", ".txt"}


@dataclass(frozen=True)
class OrganizeResult:
    partition_name: str
    product_card: str
    evidence_cards: tuple[str, ...]
    content_asset_cards: tuple[str, ...]
    application_scenario_cards: tuple[str, ...]
    review_item_cards: tuple[str, ...]
    card_inventory: dict[str, Any]
    completion_receipt: dict[str, Any]
    report_path: str
    generated_summary: dict[str, Any]


def organize_product_partition(paths: ProjectPaths, partition_query: str) -> OrganizeResult:
    definition = find_partition(partition_query)
    if definition is None:
        raise ValueError(f"Unknown or ambiguous product partition: {partition_query}")
    if definition.partition_type != "product":
        raise ValueError(f"Partition is not a product partition: {definition.name}")

    raw_product_dir = paths.raw_dir / definition.primary_raw_path
    if not raw_product_dir.exists():
        raise FileNotFoundError(f"Product raw directory does not exist: {raw_product_dir}")

    raw_files = sorted(path for path in raw_product_dir.rglob("*") if path.is_file())
    evidence_ids = []
    content_asset_ids = []
    application_scenario_ids = []

    for raw_file in raw_files:
        evidence_id = _write_evidence_card(paths, definition, raw_file)
        evidence_ids.append(evidence_id)
        if _is_content_asset(raw_file):
            content_asset_id = _write_content_asset_card(paths, definition, raw_file, evidence_id)
            content_asset_ids.append(content_asset_id)
            if "04_应用场景素材" in raw_file.relative_to(raw_product_dir).as_posix():
                application_scenario_id = _write_application_scenario_card(paths, definition, raw_file, evidence_id)
                application_scenario_ids.append(application_scenario_id)

    review_id = _write_review_item_card(paths, definition)
    product_id = _write_product_card(paths, definition, evidence_ids, [review_id])

    card_inventory = _build_card_inventory(
        product_id=product_id,
        evidence_ids=evidence_ids,
        content_asset_ids=content_asset_ids,
        application_scenario_ids=application_scenario_ids,
        review_ids=[review_id],
    )
    completion_receipt = _build_completion_receipt(
        paths,
        definition,
        raw_files=raw_files,
        card_inventory=card_inventory,
    )
    report_path = _write_completion_receipt(paths, definition, completion_receipt)

    mark_partition_organized(paths, definition)
    refresh_navigation(paths, reason="organize_product")
    generated_summary = refresh_agent_interface_after_write(
        paths,
        action="organize_product",
        expected_card_ids=card_inventory["all_cards"],
    )
    return OrganizeResult(
        partition_name=definition.name,
        product_card=product_id,
        evidence_cards=tuple(evidence_ids),
        content_asset_cards=tuple(content_asset_ids),
        application_scenario_cards=tuple(application_scenario_ids),
        review_item_cards=(review_id,),
        card_inventory=card_inventory,
        completion_receipt=completion_receipt,
        report_path=str(report_path),
        generated_summary=generated_summary,
    )


def _write_product_card(
    paths: ProjectPaths,
    definition: PartitionDefinition,
    evidence_ids: list[str],
    review_ids: list[str],
) -> str:
    card_id = f"product/{definition.slug}"
    path = paths.knowledge_dir / "产品" / f"{definition.name}.md"
    frontmatter = {
        "card_template_version": "product-card-v1",
        "type": "product",
        "id": card_id,
        "title": definition.name,
        "aliases": [],
        "status": "draft",
        "usage_scope": "review_before_external",
        "product_line": "耐高温隔热带",
        "raw_partitions": [f"raw/{definition.primary_raw_path}/"],
        "tags": ["产品", "隔热带"],
        "updated_at": _now(),
        "last_reviewed_at": "",
        "evidence_refs": evidence_ids,
        "related_refs": [],
        "review_refs": review_ids,
    }
    body = [
        "# 产品定义",
        "",
        f"{definition.name} 的产品卡由单产品资料整理 tracer 生成。当前不自动编造产品参数。",
        "",
        "# 关键参数",
        "",
        "关键参数需要从检测报告、标准原文或人工确认记录中补充。",
        "",
        "# 应用场景",
        "",
        "应用场景素材已单独整理为应用场景卡或内容素材卡。",
        "",
        "# 证据",
        "",
        *[f"- {evidence_id}" for evidence_id in evidence_ids],
        "",
        "# 复核",
        "",
        *[f"- {review_id}" for review_id in review_ids],
        "",
    ]
    _write_card(path, frontmatter, body)
    return card_id


def _write_evidence_card(paths: ProjectPaths, definition: PartitionDefinition, raw_file: Path) -> str:
    _assert_file_in_product_partition(paths, definition, raw_file)
    safe_name = _safe_stem(raw_file)
    card_id = f"evidence/{definition.slug}/{safe_name}"
    raw_relative = raw_file.relative_to(paths.raw_dir).as_posix()
    path = paths.knowledge_dir / "证据" / definition.slug / f"{safe_name}.md"
    frontmatter = {
        "card_template_version": "evidence-card-v1",
        "type": "evidence",
        "id": card_id,
        "title": f"{definition.name} 原始资料 - {raw_file.name}",
        "aliases": [],
        "status": "official",
        "usage_scope": "evidence_only",
        "raw_partitions": [f"raw/{definition.primary_raw_path}/"],
        "tags": ["证据", definition.name],
        "updated_at": _now(),
        "last_reviewed_at": "",
        "evidence_refs": [],
        "review_refs": [],
        "evidence_type": _evidence_type(raw_file),
        "source_paths": [f"raw/{raw_relative}"],
        "proves": ["原始资料存在，具体关键事实需进一步解析或人工确认"],
        "confidence": "medium",
    }
    body = [
        "# 证据说明",
        "",
        f"- 原始文件：`raw/{raw_relative}`",
        f"- 文件类型：{_evidence_type(raw_file)}",
        "",
        "该证据卡只证明原始资料存在。性能、认证、耐温、安全或对外承诺必须经过进一步解析或人工确认。",
        "",
    ]
    _write_card(path, frontmatter, body)
    return card_id


def _write_content_asset_card(paths: ProjectPaths, definition: PartitionDefinition, raw_file: Path, evidence_id: str) -> str:
    _assert_file_in_product_partition(paths, definition, raw_file)
    safe_name = _safe_stem(raw_file)
    card_id = f"content_asset/{definition.slug}/{safe_name}"
    raw_relative = raw_file.relative_to(paths.raw_dir).as_posix()
    path = paths.knowledge_dir / "内容素材" / definition.slug / f"{safe_name}.md"
    frontmatter = {
        "card_template_version": "content-asset-card-v1",
        "type": "content_asset",
        "id": card_id,
        "title": f"{definition.name} 内容素材 - {raw_file.name}",
        "aliases": [],
        "status": "official",
        "usage_scope": "review_before_external",
        "raw_partitions": [f"raw/{definition.primary_raw_path}/"],
        "tags": ["内容素材", definition.name],
        "updated_at": _now(),
        "last_reviewed_at": "",
        "evidence_refs": [evidence_id],
        "review_refs": [],
        "asset_category": _asset_category(raw_file),
        "media_types": [_media_type(raw_file)],
        "related_products": [f"product/{definition.slug}"],
        "source_paths": [f"raw/{raw_relative}"],
        "files": [f"raw/{raw_relative}"],
        "usable_for": ["video_creation"],
    }
    body = [
        "# 素材说明",
        "",
        f"- 原始文件：`raw/{raw_relative}`",
        "- 当前只登记素材边界，不自动生成视觉描述或对外文案。",
        "",
    ]
    _write_card(path, frontmatter, body)
    return card_id


def _write_application_scenario_card(paths: ProjectPaths, definition: PartitionDefinition, raw_file: Path, evidence_id: str) -> str:
    _assert_file_in_product_partition(paths, definition, raw_file)
    safe_name = _safe_stem(raw_file)
    card_id = f"application_scenario/{definition.slug}/{safe_name}"
    raw_relative = raw_file.relative_to(paths.raw_dir).as_posix()
    path = paths.knowledge_dir / "应用场景" / definition.slug / f"{safe_name}.md"
    frontmatter = {
        "card_template_version": "application-scenario-card-v1",
        "type": "application_scenario",
        "id": card_id,
        "title": f"{definition.name} 应用场景素材 - {raw_file.name}",
        "aliases": [],
        "status": "official",
        "usage_scope": "review_before_external",
        "raw_partitions": [f"raw/{definition.primary_raw_path}/"],
        "tags": ["应用场景", definition.name],
        "updated_at": _now(),
        "last_reviewed_at": "",
        "evidence_refs": [evidence_id],
        "review_refs": [],
        "scenario_category": "待人工确认",
        "related_products": [f"product/{definition.slug}"],
        "source_paths": [f"raw/{raw_relative}"],
        "usable_channels": ["video_creation"],
    }
    body = [
        "# 场景说明",
        "",
        f"- 原始文件：`raw/{raw_relative}`",
        "- 当前只登记应用场景素材，不自动确认适配关系。",
        "",
    ]
    _write_card(path, frontmatter, body)
    return card_id


def _write_review_item_card(paths: ProjectPaths, definition: PartitionDefinition) -> str:
    card_id = f"review_item/{definition.slug}/product_facts_pending"
    path = paths.knowledge_dir / "复核项" / definition.slug / "product_facts_pending.md"
    frontmatter = {
        "card_template_version": "review-item-card-v1",
        "type": "review_item",
        "id": card_id,
        "title": f"{definition.name} 关键事实待确认",
        "aliases": [],
        "status": "review_required",
        "usage_scope": "not_answerable",
        "raw_partitions": [f"raw/{definition.primary_raw_path}/"],
        "tags": ["复核", definition.name],
        "updated_at": _now(),
        "last_reviewed_at": "",
        "evidence_refs": [],
        "review_refs": [],
        "review_reason": "关键事实缺少人工确认",
        "affected_cards": [f"product/{definition.slug}"],
        "decision_options": ["补充产品核心事实", "确认已有证据可支撑", "暂不对外使用"],
        "blocking_level": "blocks_external",
    }
    body = [
        "# 待确认问题",
        "",
        "当前 tracer 只完成原始资料登记和证据链接，不自动抽取产品参数、认证、耐温、安全或对外承诺。",
        "",
        "# 建议处理",
        "",
        "- 人工确认产品关键事实后，再更新产品卡为 official。",
        "- 未确认前不得用于确定答案或对外内容。",
        "",
    ]
    _write_card(path, frontmatter, body)
    return card_id


def _build_card_inventory(
    *,
    product_id: str,
    evidence_ids: list[str],
    content_asset_ids: list[str],
    application_scenario_ids: list[str],
    review_ids: list[str],
) -> dict[str, Any]:
    return {
        "product": [product_id],
        "evidence": list(evidence_ids),
        "content_asset": list(content_asset_ids),
        "application_scenario": list(application_scenario_ids),
        "review_item": list(review_ids),
        "all_cards": [
            product_id,
            *evidence_ids,
            *content_asset_ids,
            *application_scenario_ids,
            *review_ids,
        ],
    }


def _build_completion_receipt(
    paths: ProjectPaths,
    definition: PartitionDefinition,
    *,
    raw_files: list[Path],
    card_inventory: dict[str, Any],
) -> dict[str, Any]:
    image_count = sum(1 for path in raw_files if path.suffix.lower() in IMAGE_SUFFIXES)
    video_count = sum(1 for path in raw_files if path.suffix.lower() in VIDEO_SUFFIXES)
    document_count = sum(1 for path in raw_files if path.suffix.lower() in DOCUMENT_SUFFIXES)
    content_assets = card_inventory.get("content_asset", [])
    return {
        "schema_version": "product-organization-receipt-v1",
        "generated_at": _now(),
        "partition_name": definition.name,
        "raw_partition": f"raw/{definition.primary_raw_path}/",
        "raw_file_count": len(raw_files),
        "raw_file_counts": {
            "images": image_count,
            "videos": video_count,
            "documents": document_count,
            "other": max(0, len(raw_files) - image_count - video_count - document_count),
        },
        "card_inventory": card_inventory,
        "video_creation_readiness": {
            "usable": bool(content_assets),
            "content_asset_count": len(content_assets),
            "rule": "content_asset 卡必须是 official，usage_scope 允许 review_before_external，usable_for 包含 video_creation，并关联本产品。",
            "note": "内容素材只证明本地素材存在并可用于画面参考；不证明性能、认证、耐温或其他产品 claim。",
        },
        "agent_interface": {
            "rebuild_triggered_by_organizer": True,
            "expected_after_rebuild": "generated/agent-interface/cards/content_asset.json 应包含本次 content_asset 卡。",
        },
        "user_receipt": [
            f"已整理 {definition.name} 的原始资料，共 {len(raw_files)} 个文件。",
            f"已生成/更新知识卡 {len(card_inventory.get('all_cards', []))} 张。",
            f"其中视频创作可用素材卡 {len(content_assets)} 张。",
            "产品事实仍需复核；素材卡不能替代产品 claim 证据。",
        ],
    }


def _write_completion_receipt(paths: ProjectPaths, definition: PartitionDefinition, receipt: dict[str, Any]) -> Path:
    safe_slug = re.sub(r"[^a-z0-9_-]+", "_", definition.slug.lower()).strip("_") or "product"
    report_dir = paths.generated_dir / "reports"
    json_path = report_dir / f"PRODUCT_ORGANIZATION_RECEIPT_{safe_slug}.json"
    md_path = report_dir / f"PRODUCT_ORGANIZATION_RECEIPT_{safe_slug}.md"
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        f"# {definition.name} 整理完成清单",
        "",
        f"- 原始分区：{receipt['raw_partition']}",
        f"- 原始文件数：{receipt['raw_file_count']}",
        f"- 图片/视频/文档：{receipt['raw_file_counts']['images']} / {receipt['raw_file_counts']['videos']} / {receipt['raw_file_counts']['documents']}",
        "",
        "## 生成或更新的知识卡",
        "",
    ]
    for card_type in ["product", "content_asset", "application_scenario", "evidence", "review_item"]:
        values = receipt["card_inventory"].get(card_type, [])
        lines.append(f"### {card_type}（{len(values)}）")
        lines.append("")
        if values:
            lines.extend(f"- {card_id}" for card_id in values)
        else:
            lines.append("- 无")
        lines.append("")
    readiness = receipt["video_creation_readiness"]
    lines.extend(
        [
            "## 视频创作可用性",
            "",
            f"- 可用于视频创作：{'是' if readiness['usable'] else '否'}",
            f"- 可用素材卡数量：{readiness['content_asset_count']}",
            f"- 规则：{readiness['rule']}",
            f"- 边界：{readiness['note']}",
            "",
            "## 给用户的完成回执",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in receipt["user_receipt"])
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return md_path


def _assert_file_in_product_partition(paths: ProjectPaths, definition: PartitionDefinition, raw_file: Path) -> None:
    try:
        raw_file.resolve().relative_to((paths.raw_dir / definition.primary_raw_path).resolve())
    except ValueError as exc:
        raise ValueError(f"product organization cannot use files outside {definition.primary_raw_path}: {raw_file}") from exc


def _write_card(path: Path, frontmatter: dict[str, Any], body_lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = ["---", *_render_frontmatter(frontmatter), "---", "", *body_lines]
    path.write_text("\n".join(text).rstrip() + "\n", encoding="utf-8")


def _render_frontmatter(frontmatter: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in frontmatter.items():
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {_quote_if_needed(str(item))}")
        else:
            lines.append(f"{key}: {_quote_if_needed(str(value))}")
    return lines


def _quote_if_needed(value: str) -> str:
    if value == "":
        return '""'
    if any(char in value for char in [":", "#", "[", "]", "{", "}", ","]):
        return json_escape(value)
    return value


def json_escape(value: str) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)


def _safe_stem(raw_file: Path) -> str:
    raw = raw_file.stem.lower()
    safe = re.sub(r"[^a-z0-9_-]+", "_", raw).strip("_")
    if not safe:
        safe = "file"
    suffix = hashlib_id(raw_file.as_posix())[:8]
    return f"{safe}_{suffix}"


def hashlib_id(value: str) -> str:
    import hashlib

    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def _is_content_asset(raw_file: Path) -> bool:
    return raw_file.suffix.lower() in IMAGE_SUFFIXES | VIDEO_SUFFIXES


def _media_type(raw_file: Path) -> str:
    suffix = raw_file.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    return "document"


def _asset_category(raw_file: Path) -> str:
    parts = raw_file.parts
    if "02_产品图片" in parts:
        return "产品图片"
    if "03_产品视频" in parts:
        return "产品视频"
    if "04_应用场景素材" in parts:
        return "应用场景素材"
    if "05_测试验证素材" in parts:
        return "测试验证素材"
    return "产品素材"


def _evidence_type(raw_file: Path) -> str:
    suffix = raw_file.suffix.lower()
    if suffix == ".pdf":
        return "PDF"
    if suffix in IMAGE_SUFFIXES:
        return "图片"
    if suffix in VIDEO_SUFFIXES:
        return "视频"
    if suffix in DOCUMENT_SUFFIXES:
        return "文档"
    return "其他文件"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

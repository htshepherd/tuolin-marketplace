from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .generated_index import rebuild_generated_indexes
from .navigation import refresh_navigation
from .partitions import PartitionDefinition, find_partition, mark_partition_organized
from .project_layout import ProjectPaths


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

    mark_partition_organized(paths, definition)
    refresh_navigation(paths, reason="organize_product")
    generated_summary = rebuild_generated_indexes(paths)
    return OrganizeResult(
        partition_name=definition.name,
        product_card=product_id,
        evidence_cards=tuple(evidence_ids),
        content_asset_cards=tuple(content_asset_ids),
        application_scenario_cards=tuple(application_scenario_ids),
        review_item_cards=(review_id,),
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
        "raw_partitions": [
            "raw/00_知识库核心资料/",
            f"raw/{definition.primary_raw_path}/",
        ],
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
        "status": "draft",
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
        "usable_for": ["待人工确认"],
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
        "status": "draft",
        "usage_scope": "review_before_external",
        "raw_partitions": [f"raw/{definition.primary_raw_path}/"],
        "tags": ["应用场景", definition.name],
        "updated_at": _now(),
        "last_reviewed_at": "",
        "evidence_refs": [evidence_id],
        "review_refs": [],
        "scenario_category": "待人工确认",
        "related_products": [f"product/{definition.slug}"],
        "usable_channels": ["待人工确认"],
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
        "raw_partitions": [
            "raw/00_知识库核心资料/",
            f"raw/{definition.primary_raw_path}/",
        ],
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

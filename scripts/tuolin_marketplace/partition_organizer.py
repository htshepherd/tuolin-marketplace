from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .generated_index import rebuild_generated_indexes
from .navigation import refresh_navigation
from .partitions import PartitionDefinition, find_partition, mark_partition_organized
from .product_organizer import OrganizeResult as ProductOrganizeResult
from .product_organizer import organize_product_partition
from .project_layout import ProjectPaths


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
DOCUMENT_SUFFIXES = {".pdf", ".md", ".docx", ".doc", ".xlsx", ".xls", ".txt"}


@dataclass(frozen=True)
class PartitionOrganizeResult:
    partition_name: str
    partition_type: str
    cards: tuple[str, ...]
    evidence_cards: tuple[str, ...]
    review_item_cards: tuple[str, ...]
    report_path: str | None
    generated_summary: dict[str, Any]


def organize_partition(paths: ProjectPaths, partition_query: str) -> PartitionOrganizeResult:
    definition = find_partition(partition_query)
    if definition is None:
        raise ValueError(f"Unknown or ambiguous partition: {partition_query}")
    if definition.partition_type == "product":
        product_result = organize_product_partition(paths, definition.name)
        return _from_product_result(product_result)
    if definition.partition_type == "migration_buffer":
        return _organize_migration_buffer(paths, definition)
    return _organize_domain_partition(paths, definition)


def _from_product_result(product_result: ProductOrganizeResult) -> PartitionOrganizeResult:
    cards = (
        product_result.product_card,
        *product_result.content_asset_cards,
        *product_result.application_scenario_cards,
    )
    return PartitionOrganizeResult(
        partition_name=product_result.partition_name,
        partition_type="product",
        cards=tuple(cards),
        evidence_cards=product_result.evidence_cards,
        review_item_cards=product_result.review_item_cards,
        report_path=None,
        generated_summary=product_result.generated_summary,
    )


def _organize_domain_partition(paths: ProjectPaths, definition: PartitionDefinition) -> PartitionOrganizeResult:
    raw_dir = paths.raw_dir / definition.primary_raw_path
    if not raw_dir.exists():
        raise FileNotFoundError(f"Partition raw directory does not exist: {raw_dir}")
    raw_files = sorted(path for path in raw_dir.rglob("*") if path.is_file())
    cards: list[str] = []
    evidence_cards: list[str] = []
    review_cards: list[str] = []

    for raw_file in raw_files:
        evidence_id = _write_evidence_card(paths, definition, raw_file)
        evidence_cards.append(evidence_id)
        card_id = _write_domain_card(paths, definition, raw_file, evidence_id)
        if card_id:
            cards.append(card_id)
        review_id = _write_review_item_card(paths, definition, raw_file, evidence_id, card_id)
        review_cards.append(review_id)

    mark_partition_organized(paths, definition)
    refresh_navigation(paths, reason="organize_partition")
    generated_summary = rebuild_generated_indexes(paths)
    return PartitionOrganizeResult(
        partition_name=definition.name,
        partition_type=definition.partition_type,
        cards=tuple(cards),
        evidence_cards=tuple(evidence_cards),
        review_item_cards=tuple(review_cards),
        report_path=None,
        generated_summary=generated_summary,
    )


def _organize_migration_buffer(paths: ProjectPaths, definition: PartitionDefinition) -> PartitionOrganizeResult:
    raw_dir = paths.raw_dir / definition.primary_raw_path
    if not raw_dir.exists():
        raise FileNotFoundError(f"Partition raw directory does not exist: {raw_dir}")
    raw_files = sorted(path for path in raw_dir.rglob("*") if path.is_file())
    review_cards = [_write_migration_review_item(paths, definition, raw_file) for raw_file in raw_files]
    report_path = _write_migration_report(paths, raw_files)
    mark_partition_organized(paths, definition)
    refresh_navigation(paths, reason="organize_manual_review_buffer")
    generated_summary = rebuild_generated_indexes(paths)
    return PartitionOrganizeResult(
        partition_name=definition.name,
        partition_type=definition.partition_type,
        cards=(),
        evidence_cards=(),
        review_item_cards=tuple(review_cards),
        report_path=str(report_path),
        generated_summary=generated_summary,
    )


def _write_domain_card(paths: ProjectPaths, definition: PartitionDefinition, raw_file: Path, evidence_id: str) -> str | None:
    if definition.slug == "company_capability":
        return _write_company_capability_card(paths, definition, raw_file, evidence_id)
    if definition.slug == "standards":
        return _write_standard_card(paths, definition, raw_file, evidence_id)
    if definition.slug == "market_intelligence":
        return _write_market_intelligence_card(paths, definition, raw_file, evidence_id)
    if definition.slug == "sales_material":
        return _write_sales_material_card(paths, definition, raw_file, evidence_id)
    if definition.slug == "customer_questions":
        return _write_customer_question_card(paths, definition, raw_file, evidence_id)
    return None


def _write_company_capability_card(paths: ProjectPaths, definition: PartitionDefinition, raw_file: Path, evidence_id: str) -> str:
    safe_name = _safe_stem(raw_file)
    card_id = f"company_capability/{safe_name}"
    path = paths.knowledge_dir / "公司能力" / f"{safe_name}.md"
    frontmatter = _base_frontmatter(
        card_type="company_capability",
        version="company-capability-card-v1",
        card_id=card_id,
        title=f"公司能力资料 - {raw_file.stem}",
        definition=definition,
        raw_file=raw_file,
        evidence_id=evidence_id,
        tags=["公司能力", _subdir_label(paths, definition, raw_file)],
    )
    frontmatter.update({"capability_area": _subdir_label(paths, definition, raw_file)})
    _write_card(path, frontmatter, _body("公司能力候选", raw_file, "当前只登记公司能力资料来源，具体能力表述需人工确认。"))
    return card_id


def _write_standard_card(paths: ProjectPaths, definition: PartitionDefinition, raw_file: Path, evidence_id: str) -> str:
    safe_name = _safe_stem(raw_file)
    card_id = f"standard/{safe_name}"
    path = paths.knowledge_dir / "标准法规" / f"{safe_name}.md"
    region = "中国标准" if "01_中国标准" in raw_file.as_posix() else "国际标准" if "02_国际标准" in raw_file.as_posix() else "待确认"
    frontmatter = _base_frontmatter(
        card_type="standard",
        version="standard-card-v1",
        card_id=card_id,
        title=f"标准法规资料 - {raw_file.stem}",
        definition=definition,
        raw_file=raw_file,
        evidence_id=evidence_id,
        tags=["标准法规", region],
    )
    frontmatter.update(
        {
            "standard_region": region,
            "standard_code": raw_file.stem,
            "related_products": _related_products(raw_file),
            "applicability_notes": "待人工确认",
        }
    )
    _write_card(path, frontmatter, _body("标准法规候选", raw_file, "当前只登记标准资料来源，不自动确认适用产品或合规结论。"))
    return card_id


def _write_market_intelligence_card(paths: ProjectPaths, definition: PartitionDefinition, raw_file: Path, evidence_id: str) -> str:
    safe_name = _safe_stem(raw_file)
    card_id = f"market_intelligence/{safe_name}"
    path = paths.knowledge_dir / "市场情报" / f"{safe_name}.md"
    intelligence_type = _subdir_label(paths, definition, raw_file)
    frontmatter = _base_frontmatter(
        card_type="market_intelligence",
        version="market-intelligence-card-v1",
        card_id=card_id,
        title=f"市场情报资料 - {raw_file.stem}",
        definition=definition,
        raw_file=raw_file,
        evidence_id=evidence_id,
        tags=["市场情报", intelligence_type],
    )
    frontmatter.update(
        {
            "intelligence_type": intelligence_type,
            "market_region": "待人工确认",
            "data_time_range": "待人工确认",
            "related_products": _related_products(raw_file),
        }
    )
    _write_card(path, frontmatter, _body("市场情报候选", raw_file, "市场价格、竞品和潜在客户资料只作为市场线索，不自动变成产品事实。"))
    return card_id


def _write_sales_material_card(paths: ProjectPaths, definition: PartitionDefinition, raw_file: Path, evidence_id: str) -> str:
    safe_name = _safe_stem(raw_file)
    card_id = f"sales_material/{safe_name}"
    path = paths.knowledge_dir / "销售物料" / f"{safe_name}.md"
    material_type = _subdir_label(paths, definition, raw_file)
    frontmatter = _base_frontmatter(
        card_type="sales_material",
        version="sales-material-card-v1",
        card_id=card_id,
        title=f"销售物料资料 - {raw_file.stem}",
        definition=definition,
        raw_file=raw_file,
        evidence_id=evidence_id,
        tags=["销售物料", material_type],
    )
    frontmatter.update(
        {
            "material_type": material_type,
            "language": _language(raw_file),
            "related_products": _related_products(raw_file),
        }
    )
    _write_card(path, frontmatter, _body("销售物料候选", raw_file, "销售资料不得静默反写产品事实；如与产品卡冲突必须复核。"))
    return card_id


def _write_customer_question_card(paths: ProjectPaths, definition: PartitionDefinition, raw_file: Path, evidence_id: str) -> str:
    safe_name = _safe_stem(raw_file)
    card_id = f"customer_question/{safe_name}"
    path = paths.knowledge_dir / "客户问题" / f"{safe_name}.md"
    category = _subdir_label(paths, definition, raw_file)
    frontmatter = _base_frontmatter(
        card_type="customer_question",
        version="customer-question-card-v1",
        card_id=card_id,
        title=f"客户问题资料 - {raw_file.stem}",
        definition=definition,
        raw_file=raw_file,
        evidence_id=evidence_id,
        tags=["客户问题", category],
        usage_scope="internal_only",
    )
    frontmatter.update(
        {
            "question_category": category,
            "customer_channel": "客服记录",
            "related_products": _related_products(raw_file),
            "response_status": "待人工确认",
        }
    )
    _write_card(path, frontmatter, _body("客户问题候选", raw_file, "客户对话只能证明客户关心什么，不能单独证明产品事实。"))
    return card_id


def _base_frontmatter(
    card_type: str,
    version: str,
    card_id: str,
    title: str,
    definition: PartitionDefinition,
    raw_file: Path,
    evidence_id: str,
    tags: list[str],
    usage_scope: str = "review_before_external",
) -> dict[str, Any]:
    return {
        "card_template_version": version,
        "type": card_type,
        "id": card_id,
        "title": title,
        "aliases": [],
        "status": "draft",
        "usage_scope": usage_scope,
        "raw_partitions": [f"raw/{definition.primary_raw_path}/"],
        "tags": tags,
        "updated_at": _now(),
        "last_reviewed_at": "",
        "evidence_refs": [evidence_id],
        "review_refs": [],
    }


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
        "proves": ["原始资料存在；具体业务事实需进一步解析或人工确认"],
        "confidence": "medium",
    }
    _write_card(path, frontmatter, _body("证据说明", raw_file, "该证据卡只证明原始资料存在，不自动确认业务事实。"))
    return card_id


def _write_review_item_card(
    paths: ProjectPaths,
    definition: PartitionDefinition,
    raw_file: Path,
    evidence_id: str,
    affected_card: str | None,
) -> str:
    safe_name = _safe_stem(raw_file)
    card_id = f"review_item/{definition.slug}/{safe_name}_review"
    path = paths.knowledge_dir / "复核项" / definition.slug / f"{safe_name}_review.md"
    affected_cards = [affected_card] if affected_card else []
    frontmatter = {
        "card_template_version": "review-item-card-v1",
        "type": "review_item",
        "id": card_id,
        "title": f"{definition.name} 资料待确认 - {raw_file.stem}",
        "aliases": [],
        "status": "review_required",
        "usage_scope": "not_answerable",
        "raw_partitions": [f"raw/{definition.primary_raw_path}/"],
        "tags": ["复核", definition.name],
        "updated_at": _now(),
        "last_reviewed_at": "",
        "evidence_refs": [evidence_id],
        "review_refs": [],
        "review_reason": _review_reason(definition),
        "affected_cards": affected_cards,
        "decision_options": ["确认可用", "仅内部参考", "暂不使用"],
        "blocking_level": "blocks_external",
    }
    _write_card(path, frontmatter, _body("待确认问题", raw_file, "确认前不得作为确定事实或对外内容使用。"))
    return card_id


def _write_migration_review_item(paths: ProjectPaths, definition: PartitionDefinition, raw_file: Path) -> str:
    safe_name = _safe_stem(raw_file)
    card_id = f"review_item/{definition.slug}/{safe_name}_manual_review"
    path = paths.knowledge_dir / "复核项" / definition.slug / f"{safe_name}_manual_review.md"
    frontmatter = {
        "card_template_version": "review-item-card-v1",
        "type": "review_item",
        "id": card_id,
        "title": f"待人工判定素材 - {raw_file.stem}",
        "aliases": [],
        "status": "review_required",
        "usage_scope": "not_answerable",
        "raw_partitions": [f"raw/{definition.primary_raw_path}/"],
        "tags": ["待人工判定", "复核"],
        "updated_at": _now(),
        "last_reviewed_at": "",
        "evidence_refs": [],
        "review_refs": [],
        "review_reason": "素材需要人工判断归属和价值",
        "affected_cards": [],
        "decision_options": ["归入产品素材", "归入公共内容素材", "归入公司能力素材", "保留历史项目", "暂不使用"],
        "blocking_level": "does_not_block_current_knowledge",
    }
    _write_card(path, frontmatter, _body("待人工判定", raw_file, "该暂存区只生成人工判定项，不直接生成正式业务卡。"))
    return card_id


def _write_migration_report(paths: ProjectPaths, raw_files: list[Path]) -> Path:
    path = paths.generated_dir / "reports" / "MANUAL_REVIEW_BUFFER_REPORT.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# MANUAL_REVIEW_BUFFER_REPORT", "", f"- generated_at: {_now()}", f"- file_count: {len(raw_files)}", ""]
    for raw_file in raw_files:
        lines.append(f"- {raw_file}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _body(title: str, raw_file: Path, note: str) -> list[str]:
    return ["# " + title, "", f"- 原始文件：`{raw_file.name}`", f"- 说明：{note}", ""]


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
        return json.dumps(value, ensure_ascii=False)
    return value


def _safe_stem(raw_file: Path) -> str:
    safe = re.sub(r"[^a-z0-9_-]+", "_", raw_file.stem.lower()).strip("_")
    if not safe:
        safe = "file"
    return f"{safe}_{_hash_id(raw_file.as_posix())[:8]}"


def _hash_id(value: str) -> str:
    import hashlib

    return hashlib.sha1(value.encode("utf-8")).hexdigest()


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


def _subdir_label(paths: ProjectPaths, definition: PartitionDefinition, raw_file: Path) -> str:
    try:
        relative = raw_file.relative_to(paths.raw_dir / definition.primary_raw_path)
    except ValueError:
        return "待确认"
    return relative.parts[0] if len(relative.parts) > 1 else "待确认"


def _related_products(raw_file: Path) -> list[str]:
    haystack = raw_file.as_posix()
    products = []
    mapping = {
        "陶瓷": "product/ceramic_fiber_tape",
        "石英": "product/quartz_fiber_tape",
        "玄武岩": "product/basalt_fiber_tape",
        "有背胶": "product/high_silica_fiber_tape_adhesive",
        "无背胶": "product/high_silica_fiber_tape_non_adhesive",
    }
    for keyword, product_id in mapping.items():
        if keyword in haystack:
            products.append(product_id)
    return products


def _language(raw_file: Path) -> str:
    text = raw_file.as_posix()
    if "日文" in text:
        return "日文"
    if "英文" in text:
        return "英文"
    if "中英日" in text:
        return "中英日对照"
    return "待确认"


def _review_reason(definition: PartitionDefinition) -> str:
    if definition.slug == "market_intelligence":
        return "市场情报来源、时间范围或适用范围需要确认"
    if definition.slug == "sales_material":
        return "销售物料可能影响对外表达或产品口径，需要确认"
    if definition.slug == "customer_questions":
        return "客户问题不能单独证明产品事实，需要确认回答口径"
    if definition.slug == "standards":
        return "标准适用产品和合规结论需要确认"
    return "资料内容需要人工确认后才能作为长期知识使用"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

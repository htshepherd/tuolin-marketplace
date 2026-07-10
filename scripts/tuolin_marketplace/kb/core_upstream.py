from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agent_interface import refresh_agent_interface_after_write
from .navigation import refresh_navigation
from .partitions import PARTITIONS
from ..shared.project_layout import ProjectPaths


CORE_UPSTREAM_DIRS = {
    "01_产品核心资料": "product_facts",
    "02_产品对比资料": "product_comparison",
    "03_客服常用回答": "customer_answer",
    "04_公共内容素材": "public_content_asset",
}

CORE_UPSTREAM_RAW_DIR = "00_知识库核心资料"

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
DOCUMENT_SUFFIXES = {".pdf", ".md", ".docx", ".doc", ".xlsx", ".xls", ".txt"}


@dataclass(frozen=True)
class CoreCandidate:
    source_path: str
    source_kind: str
    suggested_card_type: str
    title: str
    related_product_slugs: tuple[str, ...]
    review_reason: str


@dataclass(frozen=True)
class CoreUpstreamResult:
    preview_path: str
    candidate_count: int
    evidence_cards: tuple[str, ...]
    candidate_cards: tuple[str, ...]
    review_item_cards: tuple[str, ...]
    recognized_unapplied: tuple[str, ...]
    generated_summary: dict[str, Any] | None


def preview_core_upstream(paths: ProjectPaths) -> CoreUpstreamResult:
    candidates = discover_core_candidates(paths)
    preview_path = _write_preview(paths, candidates)
    return CoreUpstreamResult(
        preview_path=str(preview_path),
        candidate_count=len(candidates),
        evidence_cards=(),
        candidate_cards=(),
        review_item_cards=(),
        recognized_unapplied=(),
        generated_summary=None,
    )


def organize_core_upstream(paths: ProjectPaths) -> CoreUpstreamResult:
    candidates = discover_core_candidates(paths)
    preview_path = _write_preview(paths, candidates)
    evidence_ids: list[str] = []
    candidate_ids: list[str] = []
    review_ids: list[str] = []
    recognized_paths: list[str] = []

    for candidate in candidates:
        source_file = paths.raw_dir / candidate.source_path.removeprefix("raw/")
        evidence_id = _write_evidence_card(paths, source_file, candidate)
        evidence_ids.append(evidence_id)

        candidate_id = _write_candidate_card(paths, source_file, candidate, evidence_id)
        if candidate_id:
            candidate_ids.append(candidate_id)

        review_id = _write_review_item_card(paths, source_file, candidate, evidence_id, candidate_id)
        review_ids.append(review_id)

        for slug in candidate.related_product_slugs:
            recognized_paths.append(str(_write_recognized_unapplied(paths, slug, candidate, evidence_id, candidate_id, review_id)))

    _write_last_run(paths, candidates, evidence_ids, candidate_ids, review_ids)
    refresh_navigation(paths, reason="organize_core_upstream")
    generated_summary = refresh_agent_interface_after_write(
        paths,
        action="organize_core_upstream",
        expected_card_ids=[*evidence_ids, *candidate_ids, *review_ids],
    )
    return CoreUpstreamResult(
        preview_path=str(preview_path),
        candidate_count=len(candidates),
        evidence_cards=tuple(evidence_ids),
        candidate_cards=tuple(candidate_ids),
        review_item_cards=tuple(review_ids),
        recognized_unapplied=tuple(recognized_paths),
        generated_summary=generated_summary,
    )


def discover_core_candidates(paths: ProjectPaths) -> list[CoreCandidate]:
    core_dir = paths.raw_dir / CORE_UPSTREAM_RAW_DIR
    if not core_dir.exists():
        return []

    candidates: list[CoreCandidate] = []
    for source_file in sorted(path for path in core_dir.rglob("*") if path.is_file()):
        relative = source_file.relative_to(core_dir)
        if not relative.parts:
            continue
        source_kind = CORE_UPSTREAM_DIRS.get(relative.parts[0], "unknown")
        product_slugs = _detect_product_slugs(source_file)
        suggested_card_type = _suggested_card_type(source_kind)
        candidates.append(
            CoreCandidate(
                source_path=f"raw/{source_file.relative_to(paths.raw_dir).as_posix()}",
                source_kind=source_kind,
                suggested_card_type=suggested_card_type,
                title=_candidate_title(source_file, source_kind),
                related_product_slugs=tuple(product_slugs),
                review_reason=_review_reason(source_kind, product_slugs),
            )
        )
    return candidates


def _write_preview(paths: ProjectPaths, candidates: list[CoreCandidate]) -> Path:
    preview = {
        "generated_at": _now(),
        "source_root": f"raw/{CORE_UPSTREAM_RAW_DIR}/",
        "note": "预览只说明核心资料可能如何进入知识卡片；不会移动、删除、重命名 raw，也不会写回 raw。",
        "candidate_count": len(candidates),
        "candidates": [
            {
                "source_path": candidate.source_path,
                "source_kind": candidate.source_kind,
                "suggested_card_type": candidate.suggested_card_type,
                "title": candidate.title,
                "related_product_slugs": list(candidate.related_product_slugs),
                "review_reason": candidate.review_reason,
            }
            for candidate in candidates
        ],
    }
    path = paths.generated_dir / "cache" / "core-upstream-preview" / "preview.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(preview, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_evidence_card(paths: ProjectPaths, source_file: Path, candidate: CoreCandidate) -> str:
    safe_name = _safe_stem(source_file)
    card_id = f"evidence/core_upstream/{safe_name}"
    path = paths.knowledge_dir / "证据" / "core_upstream" / f"{safe_name}.md"
    frontmatter = {
        "card_template_version": "evidence-card-v1",
        "type": "evidence",
        "id": card_id,
        "title": f"核心资料证据 - {source_file.name}",
        "aliases": [],
        "status": "official",
        "usage_scope": "evidence_only",
        "raw_partitions": ["raw/00_知识库核心资料/"],
        "tags": ["证据", "核心资料"],
        "updated_at": _now(),
        "last_reviewed_at": "",
        "evidence_refs": [],
        "review_refs": [],
        "evidence_type": _evidence_type(source_file),
        "source_paths": [candidate.source_path],
        "proves": ["核心资料中存在该原始资料；具体业务口径需人工确认后写入正式卡片"],
        "confidence": "medium",
    }
    body = [
        "# 证据说明",
        "",
        f"- 原始文件：`{candidate.source_path}`",
        f"- 核心资料类型：{candidate.source_kind}",
        "",
        "该卡只证明核心资料来源存在，不自动确认产品参数、销售承诺或对外话术。",
        "",
    ]
    _write_card(path, frontmatter, body)
    return card_id


def _write_candidate_card(paths: ProjectPaths, source_file: Path, candidate: CoreCandidate, evidence_id: str) -> str | None:
    if candidate.suggested_card_type == "customer_question":
        return _write_customer_question_card(paths, source_file, candidate, evidence_id)
    if candidate.suggested_card_type == "content_asset":
        return _write_content_asset_card(paths, source_file, candidate, evidence_id)
    if candidate.suggested_card_type == "application_scenario":
        return _write_application_scenario_card(paths, source_file, candidate, evidence_id)
    return None


def _write_customer_question_card(paths: ProjectPaths, source_file: Path, candidate: CoreCandidate, evidence_id: str) -> str:
    safe_name = _safe_stem(source_file)
    card_id = f"customer_question/core_upstream/{safe_name}"
    path = paths.knowledge_dir / "客户问题" / "core_upstream" / f"{safe_name}.md"
    frontmatter = {
        "card_template_version": "customer-question-card-v1",
        "type": "customer_question",
        "id": card_id,
        "title": candidate.title,
        "aliases": [],
        "status": "draft",
        "usage_scope": "review_before_external",
        "raw_partitions": ["raw/00_知识库核心资料/"],
        "tags": ["客户问题", "核心资料"],
        "updated_at": _now(),
        "last_reviewed_at": "",
        "evidence_refs": [evidence_id],
        "review_refs": [],
        "question_category": "待人工确认",
        "customer_channel": "核心资料",
        "related_products": _product_refs(candidate.related_product_slugs),
        "response_status": "待人工确认",
    }
    body = [
        "# 客户问题候选",
        "",
        f"- 来源：`{candidate.source_path}`",
        "- 当前只登记候选问题和回答来源，不直接作为客服标准答案。",
        "",
    ]
    _write_card(path, frontmatter, body)
    return card_id


def _write_content_asset_card(paths: ProjectPaths, source_file: Path, candidate: CoreCandidate, evidence_id: str) -> str:
    safe_name = _safe_stem(source_file)
    card_id = f"content_asset/core_upstream/{safe_name}"
    path = paths.knowledge_dir / "内容素材" / "core_upstream" / f"{safe_name}.md"
    frontmatter = {
        "card_template_version": "content-asset-card-v1",
        "type": "content_asset",
        "id": card_id,
        "title": candidate.title,
        "aliases": [],
        "status": "draft",
        "usage_scope": "review_before_external",
        "raw_partitions": ["raw/00_知识库核心资料/"],
        "tags": ["内容素材", "核心资料"],
        "updated_at": _now(),
        "last_reviewed_at": "",
        "evidence_refs": [evidence_id],
        "review_refs": [],
        "asset_category": "公共内容素材",
        "media_types": [_media_type(source_file)],
        "related_products": _product_refs(candidate.related_product_slugs),
        "usable_for": ["待人工确认"],
    }
    body = [
        "# 内容素材候选",
        "",
        f"- 来源：`{candidate.source_path}`",
        "- 当前只登记素材来源和归属建议，不直接生成对外内容。",
        "",
    ]
    _write_card(path, frontmatter, body)
    return card_id


def _write_application_scenario_card(paths: ProjectPaths, source_file: Path, candidate: CoreCandidate, evidence_id: str) -> str:
    safe_name = _safe_stem(source_file)
    card_id = f"application_scenario/core_upstream/{safe_name}"
    path = paths.knowledge_dir / "应用场景" / "core_upstream" / f"{safe_name}.md"
    frontmatter = {
        "card_template_version": "application-scenario-card-v1",
        "type": "application_scenario",
        "id": card_id,
        "title": candidate.title,
        "aliases": [],
        "status": "draft",
        "usage_scope": "review_before_external",
        "raw_partitions": ["raw/00_知识库核心资料/"],
        "tags": ["应用场景", "产品对比", "核心资料"],
        "updated_at": _now(),
        "last_reviewed_at": "",
        "evidence_refs": [evidence_id],
        "review_refs": [],
        "scenario_category": "产品对比与选型",
        "related_products": _product_refs(candidate.related_product_slugs),
        "usable_channels": ["待人工确认"],
    }
    body = [
        "# 应用场景候选",
        "",
        f"- 来源：`{candidate.source_path}`",
        "- 产品对比资料只生成选型/场景候选，不直接改变产品正式口径。",
        "",
    ]
    _write_card(path, frontmatter, body)
    return card_id


def _write_review_item_card(
    paths: ProjectPaths,
    source_file: Path,
    candidate: CoreCandidate,
    evidence_id: str,
    candidate_id: str | None,
) -> str:
    safe_name = _safe_stem(source_file)
    namespace = candidate.related_product_slugs[0] if len(candidate.related_product_slugs) == 1 else "core_upstream"
    card_id = f"review_item/{namespace}/{safe_name}_core_review"
    path = paths.knowledge_dir / "复核项" / namespace / f"{safe_name}_core_review.md"
    affected_cards = []
    if candidate_id:
        affected_cards.append(candidate_id)
    affected_cards.extend(_product_refs(candidate.related_product_slugs))
    frontmatter = {
        "card_template_version": "review-item-card-v1",
        "type": "review_item",
        "id": card_id,
        "title": f"核心资料待确认 - {source_file.name}",
        "aliases": [],
        "status": "review_required",
        "usage_scope": "not_answerable",
        "raw_partitions": ["raw/00_知识库核心资料/"],
        "tags": ["复核", "核心资料"],
        "updated_at": _now(),
        "last_reviewed_at": "",
        "evidence_refs": [evidence_id],
        "review_refs": [],
        "review_reason": candidate.review_reason,
        "affected_cards": affected_cards,
        "decision_options": ["确认并更新正式卡片", "改为内部参考", "暂不使用"],
        "blocking_level": "blocks_external",
    }
    body = [
        "# 待确认问题",
        "",
        f"- 来源：`{candidate.source_path}`",
        f"- 建议卡片类型：{candidate.suggested_card_type}",
        f"- 复核原因：{candidate.review_reason}",
        "",
        "确认前不得把该内容作为 official 口径或对外答案。",
        "",
    ]
    _write_card(path, frontmatter, body)
    return card_id


def _write_recognized_unapplied(
    paths: ProjectPaths,
    slug: str,
    candidate: CoreCandidate,
    evidence_id: str,
    candidate_id: str | None,
    review_id: str,
) -> Path:
    safe_name = _safe_id(candidate.source_path)
    path = paths.generated_dir / "cache" / "recognized-unapplied" / slug / f"{safe_name}.json"
    payload = {
        "generated_at": _now(),
        "partition_slug": slug,
        "source_path": candidate.source_path,
        "source_kind": candidate.source_kind,
        "suggested_card_type": candidate.suggested_card_type,
        "candidate_card": candidate_id,
        "evidence_ref": evidence_id,
        "review_ref": review_id,
        "applied": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_last_run(
    paths: ProjectPaths,
    candidates: list[CoreCandidate],
    evidence_ids: list[str],
    candidate_ids: list[str],
    review_ids: list[str],
) -> None:
    path = paths.generated_dir / "cache" / "core-upstream" / "last-run.json"
    payload = {
        "generated_at": _now(),
        "candidate_count": len(candidates),
        "evidence_cards": evidence_ids,
        "candidate_cards": candidate_ids,
        "review_item_cards": review_ids,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _suggested_card_type(source_kind: str) -> str:
    if source_kind == "customer_answer":
        return "customer_question"
    if source_kind == "public_content_asset":
        return "content_asset"
    if source_kind == "product_comparison":
        return "application_scenario"
    return "product_update_candidate"


def _candidate_title(source_file: Path, source_kind: str) -> str:
    prefix = {
        "product_facts": "产品核心资料候选",
        "product_comparison": "产品对比候选",
        "customer_answer": "客服回答候选",
        "public_content_asset": "公共内容素材候选",
    }.get(source_kind, "核心资料候选")
    return f"{prefix} - {source_file.stem}"


def _review_reason(source_kind: str, product_slugs: list[str]) -> str:
    if not product_slugs:
        return "无法判断归属或使用范围"
    if len(product_slugs) > 1:
        return "跨产品内容需要确认适用范围"
    if source_kind == "product_facts":
        return "产品事实候选需要人工确认后才能更新产品卡"
    if source_kind == "product_comparison":
        return "产品对比内容可能影响选型口径，需要人工确认"
    if source_kind == "customer_answer":
        return "客服回答需要确认是否可作为标准回复"
    return "公共内容素材需要确认用途和使用范围"


def _detect_product_slugs(source_file: Path) -> list[str]:
    haystack = f"{source_file.name} {source_file.parent.as_posix()}"
    slugs: list[str] = []
    for name, slug, keywords in _product_keywords():
        if any(keyword in haystack for keyword in keywords):
            if slug.startswith("high_silica") and "高硅氧" in haystack and "有背胶" not in haystack and "无背胶" not in haystack:
                continue
            slugs.append(slug)
    return sorted(set(slugs))


def _product_keywords() -> list[tuple[str, str, tuple[str, ...]]]:
    products = [partition for partition in PARTITIONS if partition.partition_type == "product"]
    return [
        (products[0].name, products[0].slug, ("陶瓷纤维隔热带", "陶瓷纤维", "ceramic")),
        (products[1].name, products[1].slug, ("石英纤维隔热带", "石英纤维", "石英", "quartz")),
        (products[2].name, products[2].slug, ("玄武岩纤维隔热带", "玄武岩纤维", "玄武岩", "basalt")),
        (products[3].name, products[3].slug, ("高硅氧纤维隔热带_有背胶", "高硅氧有背胶", "有背胶", "adhesive")),
        (products[4].name, products[4].slug, ("高硅氧纤维隔热带_无背胶", "高硅氧无背胶", "无背胶", "non_adhesive")),
    ]


def _product_refs(slugs: tuple[str, ...] | list[str]) -> list[str]:
    return [f"product/{slug}" for slug in slugs]


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


def _safe_stem(source_file: Path) -> str:
    return f"{_safe_id(source_file.stem)}_{_hash_id(source_file.as_posix())[:8]}"


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^a-z0-9_-]+", "_", value.lower()).strip("_")
    if not safe:
        safe = "file"
    return safe


def _hash_id(value: str) -> str:
    import hashlib

    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def _media_type(source_file: Path) -> str:
    suffix = source_file.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    return "document"


def _evidence_type(source_file: Path) -> str:
    suffix = source_file.suffix.lower()
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

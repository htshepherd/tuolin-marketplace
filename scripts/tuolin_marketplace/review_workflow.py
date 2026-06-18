from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .card_validator import parse_frontmatter, validate_card_file
from .generated_index import rebuild_generated_indexes
from .navigation import append_changelog_entry, refresh_navigation
from .partitions import find_partition
from .project_layout import ProjectPaths


APPROVE_DECISIONS = {"approve_external", "approve_internal"}
DECISIONS = APPROVE_DECISIONS | {"reject", "defer"}


@dataclass(frozen=True)
class ReviewSummary:
    review_id: str
    title: str
    path: str
    status: str
    review_reason: str
    affected_cards: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    decision_options: tuple[str, ...]
    blocking_level: str


@dataclass(frozen=True)
class ReviewPreview:
    preview_path: str
    review_id: str
    decision: str
    affected_cards: tuple[str, ...]
    missing_affected_cards: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    confirmation_token: str


@dataclass(frozen=True)
class ApplyReviewResult:
    review_id: str
    decision: str
    updated_cards: tuple[str, ...]
    archived_review_path: str
    changelog_path: str
    generated_summary: dict[str, Any]


def list_review_items(paths: ProjectPaths, partition_query: str | None = None) -> list[ReviewSummary]:
    review_dir = paths.knowledge_dir / "复核项"
    if not review_dir.exists():
        return []

    partition_slug = _partition_slug(partition_query) if partition_query else None
    summaries = []
    for path in sorted(review_dir.rglob("*.md")):
        result = validate_card_file(path)
        if result.skipped or not result.valid:
            continue
        frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"))
        if frontmatter.get("type") != "review_item":
            continue
        if frontmatter.get("status") == "archived":
            continue
        summary = _summary_from_frontmatter(paths, path, frontmatter)
        if partition_slug and not _review_matches_partition(summary, partition_slug):
            continue
        summaries.append(summary)
    return summaries


def create_review_preview(paths: ProjectPaths, review_id: str, decision: str) -> ReviewPreview:
    if decision not in DECISIONS:
        raise ValueError(f"Unsupported review decision: {decision}")

    review_path, review_frontmatter = _load_review(paths, review_id)
    affected_cards = tuple(review_frontmatter.get("affected_cards", []))
    evidence_refs = tuple(review_frontmatter.get("evidence_refs", []))
    existing, missing = _split_existing_cards(paths, affected_cards)
    if decision in APPROVE_DECISIONS and not existing:
        raise ValueError("Approve decisions require at least one existing affected card")

    confirmation_token = _confirmation_token(review_id, decision)
    preview = {
        "generated_at": _now(),
        "review_id": review_id,
        "review_path": str(review_path.relative_to(paths.knowledge_dir)),
        "decision": decision,
        "confirmation_token": confirmation_token,
        "affected_cards": affected_cards,
        "existing_affected_cards": existing,
        "missing_affected_cards": missing,
        "evidence_refs": evidence_refs,
        "proposed_changes": _proposed_changes(decision, existing),
        "note": "这是修改预览；未提供确认令牌前不会写入 knowledge/okf，也不会修改 raw。",
    }
    preview_path = _preview_path(paths, review_id)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(json.dumps(preview, ensure_ascii=False, indent=2), encoding="utf-8")
    return ReviewPreview(
        preview_path=str(preview_path),
        review_id=review_id,
        decision=decision,
        affected_cards=tuple(existing),
        missing_affected_cards=tuple(missing),
        evidence_refs=evidence_refs,
        confirmation_token=confirmation_token,
    )


def apply_review_decision(
    paths: ProjectPaths,
    review_id: str,
    decision: str,
    confirmation_token: str,
    reviewer: str = "human",
    confirmed_statement: str | None = None,
) -> ApplyReviewResult:
    preview = create_review_preview(paths, review_id, decision)
    if confirmation_token != preview.confirmation_token:
        raise ValueError("Confirmation token does not match the latest preview")

    review_path, review_frontmatter = _load_review(paths, review_id)
    updated_cards: list[str] = []
    if decision in APPROVE_DECISIONS:
        for card_id in preview.affected_cards:
            card_path = _find_card_path(paths, card_id)
            if card_path is None:
                continue
            _apply_approved_card_update(
                card_path=card_path,
                review_id=review_id,
                evidence_refs=preview.evidence_refs,
                external=(decision == "approve_external"),
                reviewer=reviewer,
                confirmed_statement=confirmed_statement,
            )
            updated_cards.append(card_id)

    archived_review_path = _archive_review_item(review_path, review_frontmatter, decision, reviewer, confirmed_statement)
    changelog_path = _append_changelog(paths, review_id, decision, updated_cards, reviewer, confirmed_statement)
    refresh_navigation(paths, reason="apply_review")
    generated_summary = rebuild_generated_indexes(paths)
    _write_review_report(paths, review_id, decision, updated_cards, archived_review_path, confirmed_statement)
    return ApplyReviewResult(
        review_id=review_id,
        decision=decision,
        updated_cards=tuple(updated_cards),
        archived_review_path=str(archived_review_path),
        changelog_path=str(changelog_path),
        generated_summary=generated_summary,
    )


def _summary_from_frontmatter(paths: ProjectPaths, path: Path, frontmatter: dict[str, Any]) -> ReviewSummary:
    return ReviewSummary(
        review_id=frontmatter["id"],
        title=frontmatter["title"],
        path=path.relative_to(paths.knowledge_dir).as_posix(),
        status=frontmatter["status"],
        review_reason=frontmatter.get("review_reason", ""),
        affected_cards=tuple(frontmatter.get("affected_cards", [])),
        evidence_refs=tuple(frontmatter.get("evidence_refs", [])),
        decision_options=tuple(frontmatter.get("decision_options", [])),
        blocking_level=frontmatter.get("blocking_level", ""),
    )


def _partition_slug(partition_query: str) -> str:
    definition = find_partition(partition_query)
    if definition is None:
        return _safe_id(partition_query)
    return definition.slug


def _review_matches_partition(summary: ReviewSummary, partition_slug: str) -> bool:
    if f"/{partition_slug}/" in summary.review_id or summary.review_id.startswith(f"review_item/{partition_slug}/"):
        return True
    return any(card_id == f"product/{partition_slug}" or f"/{partition_slug}/" in card_id for card_id in summary.affected_cards)


def _load_review(paths: ProjectPaths, review_id: str) -> tuple[Path, dict[str, Any]]:
    review_path = _find_card_path(paths, review_id)
    if review_path is None:
        raise FileNotFoundError(f"Review item not found: {review_id}")
    result = validate_card_file(review_path)
    if not result.valid or result.skipped:
        raise ValueError(f"Invalid review item: {review_path}: {'; '.join(result.errors)}")
    frontmatter = parse_frontmatter(review_path.read_text(encoding="utf-8"))
    if frontmatter.get("type") != "review_item":
        raise ValueError(f"Card is not a review item: {review_id}")
    if frontmatter.get("status") == "archived":
        raise ValueError(f"Review item is already archived: {review_id}")
    return review_path, frontmatter


def _split_existing_cards(paths: ProjectPaths, card_ids: tuple[str, ...]) -> tuple[list[str], list[str]]:
    existing: list[str] = []
    missing: list[str] = []
    for card_id in card_ids:
        if _find_card_path(paths, card_id) is None:
            missing.append(card_id)
        else:
            existing.append(card_id)
    return existing, missing


def _proposed_changes(decision: str, existing_card_ids: list[str]) -> list[dict[str, Any]]:
    if decision == "approve_external":
        return [
            {
                "card_id": card_id,
                "status": "official",
                "usage_scope": "external_allowed",
                "review_refs": "remove current review item",
            }
            for card_id in existing_card_ids
        ]
    if decision == "approve_internal":
        return [
            {
                "card_id": card_id,
                "status": "official",
                "usage_scope": "internal_only",
                "review_refs": "remove current review item",
            }
            for card_id in existing_card_ids
        ]
    if decision == "reject":
        return [{"review_item": "archive as rejected", "affected_cards": "unchanged"}]
    return [{"review_item": "keep review-required", "affected_cards": "unchanged"}]


def _apply_approved_card_update(
    card_path: Path,
    review_id: str,
    evidence_refs: tuple[str, ...],
    external: bool,
    reviewer: str,
    confirmed_statement: str | None = None,
) -> None:
    frontmatter, body = _read_card(card_path)
    if frontmatter.get("status") == "official":
        raise ValueError(f"Refusing to modify official card without a dedicated official-card migration: {frontmatter.get('id')}")
    frontmatter["status"] = "official"
    frontmatter["usage_scope"] = "external_allowed" if external else "internal_only"
    frontmatter["last_reviewed_at"] = _now()
    frontmatter["updated_at"] = _now()
    frontmatter["evidence_refs"] = _merged_list(frontmatter.get("evidence_refs", []), evidence_refs)
    frontmatter["review_refs"] = [item for item in frontmatter.get("review_refs", []) if item != review_id]
    body = body.rstrip()
    if confirmed_statement:
        body += _confirmed_statement_note(confirmed_statement, external)
    body += _decision_note(review_id, "confirmed", reviewer, confirmed_statement)
    _write_card(card_path, frontmatter, body)


def _archive_review_item(
    review_path: Path,
    frontmatter: dict[str, Any],
    decision: str,
    reviewer: str,
    confirmed_statement: str | None = None,
) -> Path:
    current_frontmatter, body = _read_card(review_path)
    current_frontmatter["status"] = "archived"
    current_frontmatter["updated_at"] = _now()
    current_frontmatter["last_reviewed_at"] = _now()
    body = body.rstrip() + _decision_note(current_frontmatter["id"], decision, reviewer, confirmed_statement)
    _write_card(review_path, current_frontmatter, body)
    return review_path


def _append_changelog(
    paths: ProjectPaths,
    review_id: str,
    decision: str,
    updated_cards: list[str],
    reviewer: str,
    confirmed_statement: str | None = None,
) -> Path:
    entries = [
        f"- 复核项：`{review_id}`",
        f"- 处理方式：`{decision}`",
        f"- 确认人：{reviewer}",
        f"- 更新卡片：{', '.join(f'`{card_id}`' for card_id in updated_cards) if updated_cards else '无'}",
    ]
    if confirmed_statement:
        entries.append(f"- 人工确认口径：{confirmed_statement}")
    return append_changelog_entry(paths, "复核处理", entries, reason="apply_review")


def _write_review_report(
    paths: ProjectPaths,
    review_id: str,
    decision: str,
    updated_cards: list[str],
    archived_review_path: Path,
    confirmed_statement: str | None = None,
) -> None:
    path = paths.generated_dir / "reports" / "REVIEW_REPORT.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# REVIEW_REPORT",
        "",
        f"- generated_at: {_now()}",
        f"- review_id: {review_id}",
        f"- decision: {decision}",
        f"- archived_review_path: {archived_review_path}",
        f"- updated_cards: {', '.join(updated_cards) if updated_cards else 'none'}",
        f"- confirmed_statement: {confirmed_statement or 'none'}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _find_card_path(paths: ProjectPaths, card_id: str) -> Path | None:
    for path in paths.knowledge_dir.rglob("*.md"):
        if path.name in {"首页.md", "变更记录.md"}:
            continue
        try:
            frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if frontmatter.get("id") == card_id:
            return path
    return None


def _preview_path(paths: ProjectPaths, review_id: str) -> Path:
    return paths.generated_dir / "cache" / "review-previews" / f"{_safe_id(review_id)}.json"


def _confirmation_token(review_id: str, decision: str) -> str:
    import hashlib

    digest = hashlib.sha1(f"{review_id}:{decision}".encode("utf-8")).hexdigest()[:10]
    return f"confirm-{digest}"


def _read_card(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(text)
    closing = text.splitlines().index("---", 1)
    body = "\n".join(text.splitlines()[closing + 1 :]).lstrip("\n")
    return frontmatter, body


def _write_card(path: Path, frontmatter: dict[str, Any], body: str) -> None:
    text = ["---", *_render_frontmatter(frontmatter), "---", "", body.rstrip(), ""]
    path.write_text("\n".join(text), encoding="utf-8")


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


def _merged_list(existing: Any, additions: tuple[str, ...]) -> list[str]:
    values = list(existing) if isinstance(existing, list) else []
    for item in additions:
        if item not in values:
            values.append(item)
    return values


def _confirmed_statement_note(confirmed_statement: str, external: bool) -> str:
    scope = "可对外使用" if external else "仅内部使用"
    return (
        "\n\n# 人工确认口径\n\n"
        f"- 使用范围：{scope}\n"
        f"- 口径：{confirmed_statement}\n"
    )


def _decision_note(
    review_id: str,
    decision: str,
    reviewer: str,
    confirmed_statement: str | None = None,
) -> str:
    note = (
        "\n\n# 复核记录\n\n"
        f"- 时间：{_now()}\n"
        f"- 复核项：`{review_id}`\n"
        f"- 处理方式：`{decision}`\n"
        f"- 确认人：{reviewer}\n"
    )
    if confirmed_statement:
        note += f"- 人工确认口径：{confirmed_statement}\n"
    return note


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^a-z0-9_-]+", "_", value.lower()).strip("_")
    return safe or "review"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

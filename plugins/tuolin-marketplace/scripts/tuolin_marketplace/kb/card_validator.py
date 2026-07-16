from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROFILE = {
    "card_types": {
        "product",
        "application_scenario",
        "standard",
        "company_capability",
        "market_intelligence",
        "sales_material",
        "customer_question",
        "content_asset",
        "evidence",
        "review_item",
        "video_profile",
    },
    "card_statuses": {"draft", "review_required", "official", "archived"},
    "usage_scopes": {
        "external_allowed",
        "internal_only",
        "review_before_external",
        "evidence_only",
        "not_answerable",
    },
    "evidence_confidence": {"high", "medium", "low", "unusable"},
    "navigation_files": {"首页.md", "变更记录.md"},
    "required_common_fields": {
        "card_template_version",
        "type",
        "id",
        "title",
        "aliases",
        "status",
        "usage_scope",
        "raw_partitions",
        "tags",
        "updated_at",
        "last_reviewed_at",
        "evidence_refs",
        "review_refs",
    },
    "type_required_fields": {
        "product": {"product_line", "related_refs"},
        "application_scenario": {"scenario_category", "related_products", "usable_channels"},
        "standard": {"standard_region", "standard_code", "related_products", "applicability_notes"},
        "company_capability": {"capability_area"},
        "market_intelligence": {
            "intelligence_type",
            "market_region",
            "data_time_range",
            "related_products",
        },
        "sales_material": {"material_type", "language", "related_products"},
        "customer_question": {
            "question_category",
            "customer_channel",
            "related_products",
            "response_status",
        },
        "content_asset": {"asset_category", "media_types", "related_products", "usable_for"},
        "evidence": {"evidence_type", "source_paths", "proves", "confidence"},
        "review_item": {"review_reason", "affected_cards", "decision_options", "blocking_level"},
        "video_profile": {
            "video_asset_id",
            "product_id",
            "profile_revision",
            "content_digest",
            "processing_state",
            "use_capabilities",
        },
    },
}

ID_PATTERN = re.compile(r"^[a-z0-9_/-]+$")

DIR_TYPE_PREFIXES = {
    "产品": "product",
    "应用场景": "application_scenario",
    "标准法规": "standard",
    "公司能力": "company_capability",
    "市场情报": "market_intelligence",
    "销售物料": "sales_material",
    "客户问题": "customer_question",
    "内容素材": "content_asset",
    "证据": "evidence",
    "复核项": "review_item",
    "视频档案": "video_profile",
}


@dataclass(frozen=True)
class ValidationResult:
    path: Path
    skipped: bool
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return self.skipped or not self.errors


def validate_card_file(path: Path) -> ValidationResult:
    if path.name in PROFILE["navigation_files"]:
        return ValidationResult(path=path, skipped=True, errors=())

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return ValidationResult(path=path, skipped=False, errors=(f"file must be UTF-8: {exc}",))

    try:
        frontmatter = parse_frontmatter(text)
    except ValueError as exc:
        return ValidationResult(path=path, skipped=False, errors=(str(exc),))

    errors = validate_frontmatter(frontmatter)
    errors.extend(validate_path_matches_id(path, frontmatter))
    if frontmatter.get("type") == "video_profile":
        errors.extend(validate_video_profile_pair(path, frontmatter))
    return ValidationResult(path=path, skipped=False, errors=tuple(errors))


def validate_frontmatter(frontmatter: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing_common = sorted(PROFILE["required_common_fields"] - set(frontmatter))
    errors.extend(f"missing required field: {field}" for field in missing_common)

    card_type = frontmatter.get("type")
    if card_type not in PROFILE["card_types"]:
        errors.append(f"invalid type: {card_type!r}")
        return errors

    status = frontmatter.get("status")
    if status not in PROFILE["card_statuses"]:
        errors.append(f"invalid status: {status!r}")

    usage_scope = frontmatter.get("usage_scope")
    if usage_scope not in PROFILE["usage_scopes"]:
        errors.append(f"invalid usage_scope: {usage_scope!r}")

    card_id = frontmatter.get("id")
    if not isinstance(card_id, str) or not ID_PATTERN.fullmatch(card_id):
        errors.append("id must contain only lowercase letters, numbers, underscore, hyphen, and slash")

    if card_type == "evidence":
        confidence = frontmatter.get("confidence")
        if confidence not in PROFILE["evidence_confidence"]:
            errors.append(f"invalid confidence: {confidence!r}")

    missing_type_fields = sorted(PROFILE["type_required_fields"][card_type] - set(frontmatter))
    errors.extend(f"missing required {card_type} field: {field}" for field in missing_type_fields)

    _validate_list_field(frontmatter, "aliases", errors)
    _validate_list_field(frontmatter, "raw_partitions", errors)
    _validate_list_field(frontmatter, "tags", errors)
    _validate_list_field(frontmatter, "evidence_refs", errors)
    _validate_list_field(frontmatter, "review_refs", errors)
    if card_type == "video_profile":
        _validate_list_field(frontmatter, "use_capabilities", errors)
    return errors


def validate_video_profile_pair(
    markdown_path: Path,
    frontmatter: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    structured_path = markdown_path.with_suffix(".json")
    if not structured_path.is_file():
        return ["missing video profile JSON counterpart"]
    try:
        structured = json.loads(structured_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [f"invalid video profile JSON counterpart: {exc}"]
    comparisons = {
        "profile id": (frontmatter.get("id"), structured.get("profile_id")),
        "video asset id": (
            frontmatter.get("video_asset_id"),
            structured.get("video_asset_id"),
        ),
        "profile revision": (
            frontmatter.get("profile_revision"),
            structured.get("profile_revision"),
        ),
        "content digest": (
            frontmatter.get("content_digest"),
            structured.get("content_digest"),
        ),
    }
    for label, (markdown_value, structured_value) in comparisons.items():
        if markdown_value != structured_value:
            errors.append(f"video profile pair has conflicting {label}")
    asset_id = str(frontmatter.get("video_asset_id") or "")
    if markdown_path.stem != asset_id:
        errors.append("video profile filename must use video_asset_id")
    if not re.fullmatch(r"video_asset_[0-9a-f]{32}", asset_id):
        errors.append("invalid video profile video_asset_id")
    expected_suffix = f"/{asset_id}"
    if not str(frontmatter.get("id") or "").endswith(expected_suffix):
        errors.append("video profile id must end with video_asset_id")
    return errors


def validate_path_matches_id(path: Path, frontmatter: dict[str, Any]) -> list[str]:
    card_id = frontmatter.get("id")
    card_type = frontmatter.get("type")
    if not isinstance(card_id, str) or not isinstance(card_type, str):
        return []

    for parent in path.parents:
        expected_type = DIR_TYPE_PREFIXES.get(parent.name)
        if expected_type is None:
            continue
        errors: list[str] = []
        if card_type != expected_type:
            errors.append(f"type {card_type!r} does not match directory {parent.name!r}")
        if not card_id.startswith(f"{expected_type}/"):
            errors.append(f"id {card_id!r} must start with {expected_type!r} for directory {parent.name!r}")
        return errors
    return []


def parse_frontmatter(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing YAML frontmatter opening marker")
    try:
        closing_index = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValueError("missing YAML frontmatter closing marker") from exc
    block = "\n".join(lines[1:closing_index])
    return parse_simple_yaml(block)


def parse_simple_yaml(block: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            if current_key is None:
                raise ValueError(f"list item without key: {line}")
            value = _parse_scalar(stripped[2:].strip())
            if not isinstance(result.get(current_key), list):
                raise ValueError(f"field is not a list: {current_key}")
            result[current_key].append(value)
            continue
        if ":" not in line:
            raise ValueError(f"unsupported YAML line: {line}")
        key, value_text = line.split(":", 1)
        key = key.strip()
        value_text = value_text.strip()
        current_key = key
        if value_text == "":
            result[key] = []
        elif value_text.startswith("[") and value_text.endswith("]"):
            result[key] = _parse_inline_list(value_text)
        else:
            result[key] = _parse_scalar(value_text)
    return result


def _parse_inline_list(value_text: str) -> list[Any]:
    inner = value_text[1:-1].strip()
    if not inner:
        return []
    return [_parse_scalar(part.strip()) for part in inner.split(",")]


def _parse_scalar(value_text: str) -> Any:
    if value_text in {"[]", ""}:
        return []
    if (value_text.startswith('"') and value_text.endswith('"')) or (
        value_text.startswith("'") and value_text.endswith("'")
    ):
        return value_text[1:-1]
    return value_text


def _validate_list_field(frontmatter: dict[str, Any], field: str, errors: list[str]) -> None:
    if field in frontmatter and not isinstance(frontmatter[field], list):
        errors.append(f"{field} must be a list")

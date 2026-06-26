from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.card_validator import (
    PROFILE,
    validate_card_file,
    validate_frontmatter,
)


COMMON = {
    "card_template_version": "test-card-v1",
    "id": "product/test_card",
    "title": "测试卡片",
    "aliases": [],
    "status": "draft",
    "usage_scope": "internal_only",
    "raw_partitions": ["raw/01_产品/"],
    "tags": ["测试"],
    "updated_at": "2026-06-15T00:00:00+08:00",
    "last_reviewed_at": "2026-06-15T00:00:00+08:00",
    "evidence_refs": [],
    "review_refs": [],
}


TYPE_FIELDS = {
    "product": {"product_line": "耐高温隔热带", "related_refs": {}},
    "application_scenario": {
        "scenario_category": "排气管隔热",
        "related_products": ["product/quartz_fiber_tape"],
        "usable_channels": ["sales"],
    },
    "standard": {
        "standard_region": "中国",
        "standard_code": "GB/T 3003",
        "related_products": [],
        "applicability_notes": "待确认",
    },
    "company_capability": {"capability_area": "生产车间"},
    "market_intelligence": {
        "intelligence_type": "竞品",
        "market_region": "欧洲",
        "data_time_range": "2024",
        "related_products": [],
    },
    "sales_material": {
        "material_type": "Datasheet",
        "language": "日文",
        "related_products": ["product/quartz_fiber_tape"],
    },
    "customer_question": {
        "question_category": "冒烟异味",
        "customer_channel": "淘宝",
        "related_products": ["product/quartz_fiber_tape"],
        "response_status": "draft",
    },
    "content_asset": {
        "asset_category": "安装教程",
        "media_types": ["video"],
        "related_products": [],
        "usable_for": ["video_creation"],
    },
    "evidence": {
        "evidence_type": "检测报告",
        "source_paths": ["raw/example.pdf"],
        "proves": ["材质"],
        "confidence": "high",
    },
    "review_item": {
        "review_reason": "资料冲突",
        "affected_cards": ["product/quartz_fiber_tape"],
        "decision_options": ["采用A", "采用B"],
        "blocking_level": "blocks_external",
    },
}


class CardValidatorTests(unittest.TestCase):
    def test_all_ten_card_types_have_valid_minimum_frontmatter(self) -> None:
        self.assertEqual(set(TYPE_FIELDS), PROFILE["card_types"])
        for card_type, fields in TYPE_FIELDS.items():
            with self.subTest(card_type=card_type):
                frontmatter = {**COMMON, **fields, "type": card_type, "id": f"{card_type}/valid_card"}
                self.assertEqual(validate_frontmatter(frontmatter), [])

    def test_all_ten_card_types_fail_when_a_dedicated_field_is_missing(self) -> None:
        for card_type, fields in TYPE_FIELDS.items():
            with self.subTest(card_type=card_type):
                dedicated_field = next(iter(PROFILE["type_required_fields"][card_type]))
                frontmatter = {**COMMON, **fields, "type": card_type, "id": f"{card_type}/invalid_card"}
                del frontmatter[dedicated_field]
                errors = validate_frontmatter(frontmatter)
                self.assertIn(f"missing required {card_type} field: {dedicated_field}", errors)

    def test_unknown_extra_fields_are_allowed(self) -> None:
        frontmatter = {
            **COMMON,
            **TYPE_FIELDS["product"],
            "type": "product",
            "id": "product/with_extra",
            "locally_useful_note": "保留扩展字段",
        }
        self.assertEqual(validate_frontmatter(frontmatter), [])

    def test_missing_common_field_fails(self) -> None:
        frontmatter = {**COMMON, **TYPE_FIELDS["product"], "type": "product"}
        del frontmatter["usage_scope"]
        errors = validate_frontmatter(frontmatter)
        self.assertIn("missing required field: usage_scope", errors)

    def test_invalid_status_and_usage_scope_fail(self) -> None:
        frontmatter = {
            **COMMON,
            **TYPE_FIELDS["product"],
            "type": "product",
            "status": "published",
            "usage_scope": "public",
        }
        errors = validate_frontmatter(frontmatter)
        self.assertIn("invalid status: 'published'", errors)
        self.assertIn("invalid usage_scope: 'public'", errors)

    def test_chinese_id_fails(self) -> None:
        frontmatter = {**COMMON, **TYPE_FIELDS["product"], "type": "product", "id": "product/石英纤维"}
        errors = validate_frontmatter(frontmatter)
        self.assertIn("id must contain only lowercase letters, numbers, underscore, hyphen, and slash", errors)

    def test_invalid_evidence_confidence_fails(self) -> None:
        frontmatter = {**COMMON, **TYPE_FIELDS["evidence"], "type": "evidence", "confidence": "confirmed"}
        errors = validate_frontmatter(frontmatter)
        self.assertIn("invalid confidence: 'confirmed'", errors)

    def test_navigation_files_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for filename in ("首页.md", "变更记录.md"):
                path = Path(tmp) / filename
                path.write_text("# Navigation\n", encoding="utf-8")
                result = validate_card_file(path)
                self.assertTrue(result.valid)
                self.assertTrue(result.skipped)

    def test_markdown_file_validation_reports_missing_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "产品.md"
            path.write_text("# No frontmatter\n", encoding="utf-8")
            result = validate_card_file(path)
            self.assertFalse(result.valid)
            self.assertIn("missing YAML frontmatter opening marker", result.errors)

    def test_markdown_file_with_inline_lists_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "石英纤维隔热带.md"
            path.write_text(
                """---
card_template_version: product-card-v1
type: product
id: product/quartz_fiber_tape
title: 石英纤维隔热带
aliases: [白色石英纤维隔热带]
status: official
usage_scope: external_allowed
product_line: 耐高温隔热带
raw_partitions: [raw/01_产品/02_石英纤维隔热带/]
tags: [产品, 石英纤维]
updated_at: 2026-06-15T00:00:00+08:00
last_reviewed_at: 2026-06-15T00:00:00+08:00
evidence_refs: []
related_refs: []
review_refs: []
---

# 产品定义
""",
                encoding="utf-8",
            )
            result = validate_card_file(path)
            self.assertTrue(result.valid, result.errors)

    def test_card_id_must_match_chinese_card_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            product_dir = Path(tmp) / "knowledge" / "okf" / "产品"
            product_dir.mkdir(parents=True)
            path = product_dir / "石英纤维隔热带.md"
            path.write_text(
                """---
card_template_version: product-card-v1
type: product
id: standard/quartz_fiber_tape
title: 石英纤维隔热带
aliases: []
status: official
usage_scope: external_allowed
product_line: 耐高温隔热带
raw_partitions: [raw/01_产品/02_石英纤维隔热带/]
tags: [产品, 石英纤维]
updated_at: 2026-06-15T00:00:00+08:00
last_reviewed_at: 2026-06-15T00:00:00+08:00
evidence_refs: []
related_refs: []
review_refs: []
---
""",
                encoding="utf-8",
            )
            result = validate_card_file(path)
            self.assertFalse(result.valid)
            self.assertIn("id 'standard/quartz_fiber_tape' must start with 'product' for directory '产品'", result.errors)


if __name__ == "__main__":
    unittest.main()

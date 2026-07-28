from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.tuolin_marketplace.agent_interface import rebuild_agent_interface
from scripts.tuolin_marketplace.agent_specific_interfaces import (
    read_video_planner_cards,
    read_video_planner_manifest,
    read_video_planner_products,
)
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths


class VideoPlannerInterfaceTests(unittest.TestCase):
    def test_rebuild_creates_independent_multi_product_projection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_product(paths, "product/quartz_fiber_tape", "石英纤维隔热带")
            _write_product(paths, "product/ceramic_fiber_tape", "陶瓷纤维隔热带")

            summary = rebuild_agent_interface(paths)

            manifest = read_video_planner_manifest(paths)
            products = read_video_planner_products(paths)
            self.assertEqual(manifest["agent_id"], "tuolin-video-planner")
            self.assertFalse(manifest["raw_access"])
            self.assertTrue(manifest["interface_revision"].startswith("video_planner_"))
            self.assertEqual(
                [item["id"] for item in products],
                ["product/ceramic_fiber_tape", "product/quartz_fiber_tape"],
            )
            refresh = summary["agent_interface_refresh"]["agent_specific_interfaces"]
            self.assertTrue(refresh["verified"])
            self.assertFalse(refresh["legacy_shared_interface_migration_complete"])
            self.assertTrue(refresh["interfaces"][0]["verification"]["verified"])
            self.assertEqual(refresh["interfaces"][0]["verification"]["agent_id"], "tuolin-video-planner")

    def test_projection_excludes_draft_product_and_does_not_need_legacy_contexts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_product(paths, "product/official", "正式产品")
            _write_product(paths, "product/draft", "草稿产品", status="draft")
            rebuild_agent_interface(paths)
            legacy_contexts = paths.generated_dir / "agent-interface" / "contexts"
            for path in legacy_contexts.glob("*.json"):
                path.unlink()

            products = read_video_planner_products(paths)
            cards = read_video_planner_cards(paths, "product")

            self.assertEqual([item["id"] for item in products], ["product/official"])
            self.assertEqual([item["id"] for item in cards], ["product/official"])

    def test_failed_refresh_keeps_previous_interface_snapshot_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_product(paths, "product/first", "首个产品")
            rebuild_agent_interface(paths)
            previous_manifest = read_video_planner_manifest(paths)

            _write_product(paths, "product/new_after_failure", "刷新失败后的新产品")

            with patch(
                "scripts.tuolin_marketplace.kb.agent_specific_interfaces._write_video_profile_projection",
                side_effect=RuntimeError("forced planner projection failure"),
            ):
                with self.assertRaisesRegex(RuntimeError, "forced planner projection failure"):
                    rebuild_agent_interface(paths)

            current_manifest = read_video_planner_manifest(paths)
            current_products = read_video_planner_products(paths)
            self.assertEqual(current_manifest["interface_revision"], previous_manifest["interface_revision"])
            self.assertEqual([item["id"] for item in current_products], ["product/first"])


def _write_product(paths, card_id: str, title: str, *, status: str = "official") -> None:
    slug = card_id.split("/", 1)[1]
    frontmatter = {
        "card_template_version": "product-card-v1",
        "type": "product",
        "id": card_id,
        "title": title,
        "aliases": [],
        "status": status,
        "usage_scope": "external_allowed",
        "product_line": "耐高温隔热带",
        "raw_partitions": [f"raw/01_产品/{slug}/"],
        "tags": ["产品"],
        "updated_at": "2026-07-28T00:00:00+00:00",
        "last_reviewed_at": "2026-07-28T00:00:00+00:00",
        "evidence_refs": [],
        "related_refs": [],
        "review_refs": [],
    }
    path = paths.knowledge_dir / "产品" / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---"]
    for key, value in frontmatter.items():
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.extend(["---", "", "# 产品定义", "", title, ""])
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.tuolin_marketplace.agent_interface import rebuild_agent_interface
from scripts.tuolin_marketplace.agent_specific_interfaces import (
    ensure_registered_agent_interfaces_current,
    read_avatar_video_cards,
    read_avatar_video_manifest,
    read_video_planner_cards,
    read_video_planner_manifest,
    read_video_planner_products,
)
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths


class VideoPlannerInterfaceTests(unittest.TestCase):
    def test_first_use_migrates_2_0_2_video_interface_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_product(paths, "product/quartz_fiber_tape", "石英纤维隔热带")
            _write_sales_material(paths)
            rebuild_agent_interface(paths)

            for agent_id in ("tuolin-video-planner", "tuolin-avatar-video"):
                root = paths.generated_dir / "agent-interfaces" / agent_id
                manifest_path = root / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["card_types"].remove("sales_material")
                manifest["policy"].pop("sales_material_role", None)
                manifest["policy"].pop("sales_materials_prove_product_facts", None)
                manifest_path.write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                (root / "cards" / "sales_material.json").unlink()

            result = ensure_registered_agent_interfaces_current(paths)

            self.assertTrue(result["refreshed"])
            self.assertEqual(
                result["stale_interfaces"],
                ["tuolin-video-planner", "tuolin-avatar-video"],
            )
            self.assertTrue(result["refresh"]["verified"])
            for manifest in (read_video_planner_manifest(paths), read_avatar_video_manifest(paths)):
                self.assertIn("sales_material", manifest["card_types"])
                self.assertEqual(manifest["policy"]["sales_material_role"], "expression_reference")
                self.assertFalse(manifest["policy"]["sales_materials_prove_product_facts"])
            self.assertEqual(
                [card["id"] for card in read_video_planner_cards(paths, "sales_material")],
                ["sales_material/quartz_wording"],
            )
            self.assertEqual(
                [card["id"] for card in read_avatar_video_cards(paths, "sales_material")],
                ["sales_material/quartz_wording"],
            )

    def test_video_interfaces_project_sales_material_as_expression_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_product(paths, "product/quartz_fiber_tape", "石英纤维隔热带")
            _write_sales_material(paths)

            rebuild_agent_interface(paths)

            planner_cards = read_video_planner_cards(paths, "sales_material")
            avatar_cards = read_avatar_video_cards(paths, "sales_material")
            for cards in (planner_cards, avatar_cards):
                self.assertEqual([card["id"] for card in cards], ["sales_material/quartz_wording"])
                self.assertEqual(cards[0]["knowledge_role"], "expression_reference")
                self.assertFalse(cards[0]["may_prove_product_facts"])
                self.assertTrue(cards[0]["expression_only"])

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


def _write_sales_material(paths) -> None:
    frontmatter = {
        "card_template_version": "sales-material-card-v1",
        "type": "sales_material",
        "id": "sales_material/quartz_wording",
        "title": "石英纤维隔热带对外话术",
        "aliases": [],
        "status": "official",
        "usage_scope": "external_allowed",
        "raw_partitions": ["raw/05_销售物料/"],
        "tags": ["销售话术"],
        "updated_at": "2026-07-30T00:00:00+00:00",
        "last_reviewed_at": "2026-07-30T00:00:00+00:00",
        "evidence_refs": [],
        "review_refs": [],
        "material_type": "销售话术",
        "language": "中文",
        "related_products": ["product/quartz_fiber_tape"],
    }
    path = paths.knowledge_dir / "销售物料" / "quartz_wording.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", *[f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in frontmatter.items()], "---", "", "用于组织对外表达，不单独证明产品事实。", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()

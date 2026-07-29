from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.tuolin_marketplace.agent_interface import rebuild_agent_interface
from scripts.tuolin_marketplace.agent_specific_interfaces import (
    read_avatar_video_card,
    read_avatar_video_cards,
    read_avatar_video_manifest,
    read_avatar_video_products,
    search_avatar_video_cards,
)
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths


class AvatarVideoInterfaceTests(unittest.TestCase):
    def test_rebuild_creates_independent_verified_projection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_product(paths, "product/quartz_fiber_tape", "石英纤维隔热带")

            summary = rebuild_agent_interface(paths)

            manifest = read_avatar_video_manifest(paths)
            products = read_avatar_video_products(paths)
            self.assertEqual(manifest["agent_id"], "tuolin-avatar-video")
            self.assertFalse(manifest["raw_access"])
            self.assertTrue(manifest["interface_revision"].startswith("avatar_video_"))
            self.assertEqual([item["id"] for item in products], ["product/quartz_fiber_tape"])
            refresh = summary["agent_interface_refresh"]["agent_specific_interfaces"]
            avatar = next(item for item in refresh["interfaces"] if item["agent_id"] == "tuolin-avatar-video")
            self.assertTrue(avatar["verification"]["verified"])
            self.assertEqual(avatar["verification"]["interface_revision"], manifest["interface_revision"])

    def test_rebuild_projects_multiple_products(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_product(paths, "product/quartz", "石英纤维隔热带")
            _write_product(paths, "product/ceramic", "陶瓷纤维隔热带")
            rebuild_agent_interface(paths)

            self.assertEqual(
                [item["id"] for item in read_avatar_video_products(paths)],
                ["product/ceramic", "product/quartz"],
            )

    def test_projection_excludes_drafts_and_does_not_read_other_interfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_product(paths, "product/official", "正式产品")
            _write_product(paths, "product/draft", "草稿产品", status="draft")
            rebuild_agent_interface(paths)

            legacy_contexts = paths.generated_dir / "agent-interface" / "contexts"
            for path in legacy_contexts.glob("*.json"):
                path.unlink()
            planner_root = paths.generated_dir / "agent-interfaces" / "tuolin-video-planner"
            if planner_root.exists():
                for path in planner_root.rglob("*.json"):
                    path.unlink()

            products = read_avatar_video_products(paths)
            cards = read_avatar_video_cards(paths, "product")
            self.assertEqual([item["id"] for item in products], ["product/official"])
            self.assertEqual([item["id"] for item in cards], ["product/official"])
            self.assertEqual(read_avatar_video_card(paths, "product/official")["title"], "正式产品")
            self.assertEqual(
                [item["id"] for item in search_avatar_video_cards(paths, "正式")],
                ["product/official"],
            )
            with self.assertRaises(KeyError):
                read_avatar_video_card(paths, "product/draft")

    def test_unsupported_card_type_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_product(paths, "product/official", "正式产品")
            rebuild_agent_interface(paths)

            with self.assertRaisesRegex(ValueError, "Unsupported avatar-video card type"):
                read_avatar_video_cards(paths, "raw_file")

    def test_avatar_refresh_failure_preserves_previous_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            _write_product(paths, "product/first", "首个产品")
            rebuild_agent_interface(paths)
            previous = read_avatar_video_manifest(paths)
            _write_product(paths, "product/new_after_failure", "刷新失败后的产品")

            with patch(
                "scripts.tuolin_marketplace.kb.agent_specific_interfaces._avatar_video_card_allowed",
                side_effect=RuntimeError("forced avatar projection failure"),
            ):
                with self.assertRaisesRegex(RuntimeError, "forced avatar projection failure"):
                    rebuild_agent_interface(paths)

            current = read_avatar_video_manifest(paths)
            products = read_avatar_video_products(paths)
            self.assertEqual(current["interface_revision"], previous["interface_revision"])
            self.assertEqual([item["id"] for item in products], ["product/first"])


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
        "updated_at": "2026-07-29T00:00:00+00:00",
        "last_reviewed_at": "2026-07-29T00:00:00+00:00",
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

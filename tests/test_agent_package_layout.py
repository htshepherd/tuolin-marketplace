from __future__ import annotations

import unittest
from pathlib import Path


class AgentPackageLayoutTests(unittest.TestCase):
    def test_legacy_and_new_kb_import_paths_are_available(self) -> None:
        from scripts.tuolin_marketplace.agent_interface import rebuild_agent_interface as legacy_rebuild
        from scripts.tuolin_marketplace.kb.agent_interface import rebuild_agent_interface as new_rebuild
        from scripts.tuolin_marketplace.project_layout import resolve_paths as legacy_resolve
        from scripts.tuolin_marketplace.shared.project_layout import resolve_paths as new_resolve

        self.assertIs(legacy_rebuild, new_rebuild)
        self.assertIs(legacy_resolve, new_resolve)

    def test_legacy_and_new_linkedin_import_paths_are_available(self) -> None:
        from scripts.tuolin_marketplace.linkedin.agent import create_linkedin_campaign_plan as new_create
        from scripts.tuolin_marketplace.linkedin.campaign import create_linkedin_campaign_plan as campaign_create
        from scripts.tuolin_marketplace.linkedin.publishing_calendar import create_linkedin_campaign_plan as calendar_create
        from scripts.tuolin_marketplace.linkedin_agent import create_linkedin_campaign_plan as legacy_create

        self.assertIs(legacy_create, new_create)
        self.assertIs(campaign_create, new_create)
        self.assertIs(calendar_create, new_create)

    def test_legacy_and_new_video_creation_import_paths_are_available(self) -> None:
        from scripts.tuolin_marketplace.video_creation.agent import create_video_creation_run as new_create
        from scripts.tuolin_marketplace.video_creation.dreamina import generate_dreamina_jobs
        from scripts.tuolin_marketplace.video_creation.planning import generate_video_plan
        from scripts.tuolin_marketplace.video_creation.state import resume_video_creation_run
        from scripts.tuolin_marketplace.video_creation.storyboard import generate_storyboard
        from scripts.tuolin_marketplace.video_creation_agent import create_video_creation_run as legacy_create

        self.assertIs(legacy_create, new_create)
        self.assertTrue(callable(resume_video_creation_run))
        self.assertTrue(callable(generate_video_plan))
        self.assertTrue(callable(generate_storyboard))
        self.assertTrue(callable(generate_dreamina_jobs))

    def test_agent_specific_interface_import_paths_are_available(self) -> None:
        from scripts.tuolin_marketplace.agent_specific_interfaces import (
            read_video_planner_products as legacy_read,
        )
        from scripts.tuolin_marketplace.kb.agent_specific_interfaces import (
            read_video_planner_products as new_read,
        )

        self.assertIs(legacy_read, new_read)

    def test_video_planner_skill_is_explicit_and_packaged_without_replacing_video_workflow(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = root / "skills" / "tuolin-video-planner"
        packaged = root / "plugins" / "tuolin-marketplace" / "skills" / "tuolin-video-planner"
        self.assertEqual(
            (source / "SKILL.md").read_text(encoding="utf-8"),
            (packaged / "SKILL.md").read_text(encoding="utf-8"),
        )
        metadata = (source / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertIn("$tuolin-video-planner", metadata)
        legacy = (root / "skills" / "tuolin-video-workflow" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Dreamina", legacy)
        self.assertIn("public YouTube scan", legacy)

    def test_kb_skill_explains_video_visual_permission_in_user_language(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = root / "skills" / "tuolin-kb" / "SKILL.md"
        packaged = (
            root
            / "plugins"
            / "tuolin-marketplace"
            / "skills"
            / "tuolin-kb"
            / "SKILL.md"
        )
        content = source.read_text(encoding="utf-8")

        self.assertEqual(content, packaged.read_text(encoding="utf-8"))
        self.assertIn(
            "这些视频画面是否允许剪进 YouTube Shorts 和 TikTok 最终成片？",
            content,
        )
        self.assertIn("不要只向用户显示 `internal_only`", content)
        self.assertIn("最终成片发布前仍需再次人工确认", content)

    def test_kb_incremental_video_refresh_runtime_matches_packaged_plugin(self) -> None:
        root = Path(__file__).resolve().parents[1]
        relative_paths = (
            "scripts/tuolin_marketplace/kb/agent_interface.py",
            "scripts/tuolin_marketplace/kb/agent_specific_interfaces.py",
            "scripts/tuolin_marketplace/kb/generated_index.py",
            "scripts/tuolin_marketplace/kb/partitions.py",
            "scripts/tuolin_marketplace/kb/video_profile_maintenance.py",
        )
        for relative in relative_paths:
            source = root / relative
            packaged = root / "plugins" / "tuolin-marketplace" / relative
            self.assertEqual(source.read_bytes(), packaged.read_bytes(), source)

    def test_kb_question_answering_runtime_matches_packaged_plugin(self) -> None:
        root = Path(__file__).resolve().parents[1]
        relative_paths = (
            "scripts/tuolin_marketplace/kb/question_answering.py",
            "scripts/tuolin_marketplace/shared/natural_language.py",
        )
        for relative in relative_paths:
            source = root / relative
            packaged = root / "plugins" / "tuolin-marketplace" / relative
            self.assertEqual(source.read_bytes(), packaged.read_bytes(), source)

    def test_avatar_video_skill_runtime_and_plugin_mirror_are_explicit_and_identical(self) -> None:
        root = Path(__file__).resolve().parents[1]
        pairs = [
            (root / "skills" / "tuolin-avatar-video" / "SKILL.md", root / "plugins" / "tuolin-marketplace" / "skills" / "tuolin-avatar-video" / "SKILL.md"),
            (root / "skills" / "tuolin-avatar-video" / "references" / "workflow-contract.md", root / "plugins" / "tuolin-marketplace" / "skills" / "tuolin-avatar-video" / "references" / "workflow-contract.md"),
            (root / "skills" / "tuolin-avatar-video" / "agents" / "openai.yaml", root / "plugins" / "tuolin-marketplace" / "skills" / "tuolin-avatar-video" / "agents" / "openai.yaml"),
            (root / "scripts" / "avatar_video_workflow.py", root / "plugins" / "tuolin-marketplace" / "scripts" / "avatar_video_workflow.py"),
            (root / "scripts" / "tuolin_marketplace" / "avatar_video" / "agent.py", root / "plugins" / "tuolin-marketplace" / "scripts" / "tuolin_marketplace" / "avatar_video" / "agent.py"),
            (root / "scripts" / "tuolin_marketplace" / "avatar_video" / "provider_adapters.py", root / "plugins" / "tuolin-marketplace" / "scripts" / "tuolin_marketplace" / "avatar_video" / "provider_adapters.py"),
        ]
        for source, packaged in pairs:
            self.assertTrue(source.is_file(), source)
            self.assertEqual(source.read_bytes(), packaged.read_bytes(), source)
        metadata = pairs[2][0].read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertIn("$tuolin-avatar-video", metadata)
        self.assertEqual(
            (root / ".codex-plugin" / "plugin.json").read_bytes(),
            (root / "plugins" / "tuolin-marketplace" / ".codex-plugin" / "plugin.json").read_bytes(),
        )

    def test_three_video_agents_keep_separate_explicit_boundaries(self) -> None:
        root = Path(__file__).resolve().parents[1]
        avatar = (root / "skills" / "tuolin-avatar-video" / "SKILL.md").read_text(encoding="utf-8")
        planner = (root / "skills" / "tuolin-video-planner" / "SKILL.md").read_text(encoding="utf-8")
        workflow = (root / "skills" / "tuolin-video-workflow" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("never replaces", avatar)
        self.assertIn("Do not search trends", avatar)
        self.assertIn("planning-only", planner)
        self.assertIn("public YouTube scan", workflow)
        self.assertNotIn("HyperFrames", planner)
        self.assertNotIn("HyperFrames", workflow)


if __name__ == "__main__":
    unittest.main()

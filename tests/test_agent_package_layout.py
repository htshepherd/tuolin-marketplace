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


if __name__ == "__main__":
    unittest.main()

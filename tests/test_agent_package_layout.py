from __future__ import annotations

import unittest


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
        from scripts.tuolin_marketplace.video_creation.assembly import assemble_final_preview
        from scripts.tuolin_marketplace.video_creation.dreamina import generate_dreamina_jobs
        from scripts.tuolin_marketplace.video_creation.narration import generate_narration_script
        from scripts.tuolin_marketplace.video_creation.planning import generate_video_plan
        from scripts.tuolin_marketplace.video_creation.quality_gate import run_quality_gate
        from scripts.tuolin_marketplace.video_creation.state import resume_video_creation_run
        from scripts.tuolin_marketplace.video_creation.storyboard import generate_storyboard
        from scripts.tuolin_marketplace.video_creation_agent import create_video_creation_run as legacy_create

        self.assertIs(legacy_create, new_create)
        self.assertTrue(callable(resume_video_creation_run))
        self.assertTrue(callable(generate_video_plan))
        self.assertTrue(callable(generate_storyboard))
        self.assertTrue(callable(generate_narration_script))
        self.assertTrue(callable(generate_dreamina_jobs))
        self.assertTrue(callable(assemble_final_preview))
        self.assertTrue(callable(run_quality_gate))


if __name__ == "__main__":
    unittest.main()

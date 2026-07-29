from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.avatar_video.agent import compose_avatar_video, revise_avatar_video
from scripts.tuolin_marketplace.avatar_video.composition import FFmpegComposer, HyperFramesCLIAdapter
from tests.test_avatar_video_agent import _project_with_product_image, _ready_for_composition


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe required")
class HyperFramesCLIAdapterTests(unittest.TestCase):
    def test_real_cli_contract_runs_init_lint_inspect_render_and_persists_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths, image_path = _project_with_product_image(workspace)
            root = _ready_for_composition(paths, image_path)
            revise_avatar_video(
                root,
                "标题居中放大、参数三列并改成直接切换",
                category="packaging",
                changes={
                    "title_layout": {"position": "center", "alignment": "center", "font_size": 88},
                    "parameter_layout": {"columns": 3},
                    "transitions": "simple_cut",
                },
            )
            calls: list[list[str]] = []

            def runner(command, cwd, environment):
                calls.append(list(command))
                action = command[2]
                if action == "init":
                    project = Path(cwd) / command[3]
                    project.mkdir(parents=True, exist_ok=True)
                    (project / "hyperframes.json").write_text("{}", encoding="utf-8")
                elif action == "render":
                    output = Path(command[command.index("--output") + 1])
                    project = Path(command[3])
                    contract = json.loads((project / "composition-contract.json").read_text(encoding="utf-8"))
                    FFmpegComposer().render(contract, output)
                return {"returncode": 0, "stdout": json.dumps({"ok": True, "action": action}), "stderr": ""}

            rendered = compose_avatar_video(root, hyperframes=HyperFramesCLIAdapter(command_runner=runner))
            self.assertEqual(rendered.status, "mock_rendered")
            self.assertEqual([command[2] for command in calls], ["init", "lint", "inspect", "render"])
            render_command = calls[-1]
            self.assertIn("--strict", render_command)
            self.assertIn("--no-best-effort", render_command)
            state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["composition_path"], "hyperframes")
            render_dir = (root / state["files"]["final_render"]).parent
            project_dir = render_dir / "hyperframes-project"
            index = (project_dir / "index.html").read_text(encoding="utf-8")
            self.assertIn('data-composition-id="main"', index)
            self.assertIn('class="clip scene-media evidence"', index)
            self.assertIn('class="clip caption"', index)
            self.assertNotIn('id="transition-2"', index)
            self.assertIn("justify-content: center", index)
            self.assertIn("align-items: center", index)
            self.assertIn("font-size: 88px", index)
            self.assertIn("grid-template-columns: repeat(3", index)
            self.assertTrue((project_dir / "DESIGN.md").is_file())
            diagnostics = json.loads((render_dir / "hyperframes-diagnostics" / "stages.json").read_text(encoding="utf-8"))
            self.assertEqual(diagnostics["status"], "completed")

    def test_cli_lint_failure_is_visible_and_automatically_uses_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths, image_path = _project_with_product_image(workspace)
            root = _ready_for_composition(paths, image_path)

            def runner(command, cwd, environment):
                action = command[2]
                if action == "init":
                    project = Path(cwd) / command[3]
                    project.mkdir(parents=True, exist_ok=True)
                    (project / "hyperframes.json").write_text("{}", encoding="utf-8")
                    return {"returncode": 0, "stdout": "created", "stderr": ""}
                return {"returncode": 2, "stdout": "", "stderr": "lint contract failure"}

            compose_avatar_video(root, hyperframes=HyperFramesCLIAdapter(command_runner=runner))
            state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["composition_path"], "ffmpeg_fallback")
            render_dir = (root / state["files"]["final_render"]).parent
            summary = json.loads((render_dir / "composition.json").read_text(encoding="utf-8"))
            self.assertIn("lint contract failure", summary["fallback_reason"])
            failed = json.loads((render_dir / "hyperframes-diagnostics" / "stages.json").read_text(encoding="utf-8"))
            self.assertEqual(failed["status"], "failed")


if __name__ == "__main__":
    unittest.main()

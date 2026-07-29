from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.avatar_video.agent import compose_avatar_video
from scripts.tuolin_marketplace.avatar_video.composition import HyperFramesCLIAdapter
from scripts.tuolin_marketplace.avatar_video.media import probe_media
from tests.test_avatar_video_agent import _project_with_product_image, _ready_for_composition


@unittest.skipUnless(
    os.environ.get("RUN_HYPERFRAMES_INTEGRATION") == "1" and shutil.which("node") and shutil.which("ffmpeg"),
    "set RUN_HYPERFRAMES_INTEGRATION=1 for the real HyperFrames CLI acceptance",
)
class RealHyperFramesAcceptanceTests(unittest.TestCase):
    def test_real_cli_renders_the_confirmed_mock_media_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths, image_path = _project_with_product_image(workspace)
            root = _ready_for_composition(paths, image_path)
            rendered = compose_avatar_video(
                root,
                hyperframes=HyperFramesCLIAdapter(quality="draft", inspect_samples=4),
            )
            self.assertEqual(rendered.status, "mock_rendered")
            state = json.loads((root / "workflow_state.json").read_text(encoding="utf-8"))
            render_dir = (root / state["files"]["final_render"]).parent
            summary = json.loads((render_dir / "composition.json").read_text(encoding="utf-8"))
            self.assertEqual(state["composition_path"], "hyperframes", summary)
            output = root / state["files"]["final_render"]
            probe = probe_media(output)
            self.assertEqual((probe["width"], probe["height"]), (1080, 1920))
            self.assertAlmostEqual(probe["duration_seconds"], 30, delta=1)
            diagnostics_path = render_dir / "hyperframes-diagnostics" / "stages.json"
            diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
            self.assertEqual(diagnostics["status"], "completed")
            self.assertEqual(diagnostics["stages"]["render"]["returncode"], 0)


if __name__ == "__main__":
    unittest.main()

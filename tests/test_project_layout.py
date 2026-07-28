from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.project_layout import (
    KNOWLEDGE_DIRS,
    ProjectPaths,
    initialize_project,
    load_config,
    load_project_config,
    resolve_paths,
    validate_path_boundaries,
)


class ProjectLayoutTests(unittest.TestCase):
    def test_initialize_project_creates_required_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)

            self.assertTrue((paths.knowledge_dir / "首页.md").is_file())
            self.assertTrue((paths.knowledge_dir / "变更记录.md").is_file())
            for relative in KNOWLEDGE_DIRS:
                self.assertTrue((paths.knowledge_dir / relative).is_dir(), relative)
            self.assertTrue((paths.generated_dir / "agent-interface" / "contexts").is_dir())
            self.assertTrue((paths.generated_dir / "agent-interfaces" / "tuolin-video-planner").is_dir())
            self.assertTrue((paths.raw_dir / "01_产品" / "02_石英纤维隔热带").is_dir())
            self.assertTrue((paths.project_dir / "assets" / "logo").is_dir())
            self.assertTrue((paths.project_dir / "config" / "tuolin-okf-profile" / "profile.yaml").is_file())
            self.assertTrue(
                (
                    paths.project_dir
                    / "config"
                    / "tuolin-okf-profile"
                    / "card-templates"
                    / "product.yaml"
                ).is_file()
            )

    def test_path_boundaries_reject_nested_generated_in_raw(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            paths = ProjectPaths(
                project_dir=root,
                raw_dir=root / "raw",
                knowledge_dir=root / "knowledge" / "okf",
                generated_dir=root / "raw" / "generated",
            )
            with self.assertRaises(ValueError):
                validate_path_boundaries(paths)

    def test_absolute_raw_dir_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as project, tempfile.TemporaryDirectory() as raw:
            paths = resolve_paths(Path(project), {"raw_dir": raw})
            self.assertEqual(paths.raw_dir, Path(raw).resolve())

    def test_load_config_accepts_windows_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "tuolin-kb.config.json"
            config_path.write_text('{"raw_dir": "raw"}', encoding="utf-8-sig")

            config = load_config(config_path)

            self.assertEqual(config["raw_dir"], "raw")

    def test_load_project_config_discovers_standard_project_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "config"
            config_dir.mkdir()
            mineru = root / "tools" / "mineru-venv" / "Scripts" / "mineru.exe"
            config_path = config_dir / "tuolin-kb.config.json"
            config_path.write_text(
                '{"raw_dir": "enterprise-raw", "mineru_command": "' + mineru.as_posix() + '"}',
                encoding="utf-8",
            )

            config = load_project_config(root)

            self.assertEqual(config["raw_dir"], "enterprise-raw")
            self.assertEqual(config["mineru_command"], mineru.as_posix())

    def test_load_project_config_explicit_path_overrides_standard_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "config"
            config_dir.mkdir()
            (config_dir / "tuolin-kb.config.json").write_text(
                '{"mineru_command": "standard-mineru"}',
                encoding="utf-8",
            )
            explicit = root / "selected.json"
            explicit.write_text('{"mineru_command": "selected-mineru"}', encoding="utf-8")

            config = load_project_config(root, explicit)

            self.assertEqual(config["mineru_command"], "selected-mineru")

    def test_load_project_config_rejects_missing_explicit_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with self.assertRaisesRegex(FileNotFoundError, "configured project file does not exist"):
                load_project_config(root, root / "missing.json")


if __name__ == "__main__":
    unittest.main()

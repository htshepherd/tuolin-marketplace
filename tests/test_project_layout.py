from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.project_layout import (
    KNOWLEDGE_DIRS,
    ProjectPaths,
    initialize_project,
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
            self.assertTrue((paths.raw_dir / "01_产品" / "02_石英纤维隔热带").is_dir())

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


if __name__ == "__main__":
    unittest.main()

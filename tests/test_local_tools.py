from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.local_tools import (
    extract_video_keyframes,
    pdf_markdown_cache_dir,
    prepare_pdf_text,
    video_frame_cache_dir,
)
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths


class LocalToolBoundaryTests(unittest.TestCase):
    def test_pdf_uses_same_name_markdown_without_mineru(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            pdf = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
            pdf.write_text("fake pdf", encoding="utf-8")
            markdown = pdf.with_suffix(".md")
            markdown.write_text("# human markdown", encoding="utf-8")

            calls: list[tuple[str, ...]] = []

            def runner(command, **kwargs):
                calls.append(tuple(command))
                return subprocess.CompletedProcess(command, 0, "", "")

            result = prepare_pdf_text(pdf, paths, runner=runner)

            self.assertEqual(result.status, "raw_markdown_available")
            self.assertEqual(result.markdown_path, markdown)
            self.assertIsNone(result.cache_dir)
            self.assertEqual(calls, [])

    def test_pdf_conversion_writes_to_generated_cache_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            pdf = paths.raw_dir / "03_标准法规" / "01_中国标准" / "standard.pdf"
            pdf.write_text("fake pdf", encoding="utf-8")

            def runner(command, **kwargs):
                output_dir = Path(command[4])
                output_dir.mkdir(parents=True, exist_ok=True)
                (output_dir / "standard.md").write_text("# converted", encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, "ok", "")

            result = prepare_pdf_text(pdf, paths, mineru_command="mineru", runner=runner)

            self.assertEqual(result.status, "converted_to_cache")
            self.assertEqual(result.cache_dir, pdf_markdown_cache_dir(pdf, paths))
            self.assertTrue(str(result.cache_dir).startswith(str(paths.generated_dir)))
            self.assertFalse(pdf.with_suffix(".md").exists())
            self.assertEqual(result.markdown_path, result.cache_dir / "standard.md")
            self.assertEqual(result.command[:2], ("mineru", "-p"))
            self.assertIn("-b", result.command)
            self.assertIn("pipeline", result.command)
            self.assertIn("-l", result.command)
            self.assertIn("ch", result.command)

    def test_pdf_conversion_failure_reports_error_without_blocking_other_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            pdf = paths.raw_dir / "03_标准法规" / "01_中国标准" / "broken.pdf"
            pdf.write_text("fake pdf", encoding="utf-8")

            def runner(command, **kwargs):
                return subprocess.CompletedProcess(command, 2, "", "mineru failed")

            result = prepare_pdf_text(pdf, paths, runner=runner)

            self.assertEqual(result.status, "conversion_failed")
            self.assertEqual(result.error, "mineru failed")
            self.assertTrue(str(result.cache_dir).startswith(str(paths.generated_dir)))
            self.assertFalse(pdf.with_suffix(".md").exists())

    def test_pdf_outside_raw_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            outside_pdf = Path(tmp) / "outside.pdf"
            outside_pdf.write_text("fake pdf", encoding="utf-8")

            with self.assertRaises(ValueError):
                prepare_pdf_text(outside_pdf, paths)

    def test_video_keyframes_write_to_generated_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            video = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "03_产品视频" / "demo.mp4"
            video.write_text("fake video", encoding="utf-8")
            commands: list[tuple[str, ...]] = []

            def runner(command, **kwargs):
                commands.append(tuple(command))
                output_path = Path(command[-1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("fake frame", encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, "ok", "")

            result = extract_video_keyframes(
                video,
                paths,
                ffmpeg_path="/opt/bin/ffmpeg",
                timestamps=("00:00:01", "00:00:02"),
                runner=runner,
            )

            self.assertEqual(result.source_video, video.resolve())
            self.assertEqual(len(result.frames), 2)
            self.assertEqual(commands[0][0], "/opt/bin/ffmpeg")
            for frame in result.frames:
                self.assertEqual(frame.status, "extracted_to_cache")
                self.assertTrue(str(frame.frame_path).startswith(str(paths.generated_dir)))
                self.assertTrue(frame.frame_path.exists())
            self.assertEqual(result.frames[0].frame_path.parent, video_frame_cache_dir(video, paths))

    def test_video_failure_reports_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            video = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "03_产品视频" / "bad.mp4"
            video.write_text("fake video", encoding="utf-8")

            def runner(command, **kwargs):
                return subprocess.CompletedProcess(command, 1, "", "ffmpeg failed")

            result = extract_video_keyframes(video, paths, runner=runner)

            self.assertEqual(result.frames[0].status, "extraction_failed")
            self.assertEqual(result.frames[0].error, "ffmpeg failed")

    def test_video_outside_raw_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            outside_video = Path(tmp) / "outside.mp4"
            outside_video.write_text("fake video", encoding="utf-8")

            with self.assertRaises(ValueError):
                extract_video_keyframes(outside_video, paths)


if __name__ == "__main__":
    unittest.main()

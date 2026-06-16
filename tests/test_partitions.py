from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.partitions import (
    PARTITIONS,
    find_partition,
    mark_partition_organized,
    recommend_next_action,
    scan_all_partitions,
    scan_partition,
)
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths


class PartitionScanTests(unittest.TestCase):
    def _write_evidence_for_source(self, paths, partition_slug: str, source_relative: str, name: str) -> None:
        evidence_dir = paths.knowledge_dir / "证据" / partition_slug
        evidence_dir.mkdir(parents=True, exist_ok=True)
        (evidence_dir / f"{name}.md").write_text(
            "\n".join(
                [
                    "---",
                    "source_paths:",
                    f"  - raw/{source_relative}",
                    "---",
                    "",
                    "# evidence",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def test_all_expected_partitions_are_defined(self) -> None:
        names = [partition.name for partition in PARTITIONS]
        self.assertEqual(
            names,
            [
                "陶瓷纤维隔热带",
                "石英纤维隔热带",
                "玄武岩纤维隔热带",
                "高硅氧纤维隔热带_有背胶",
                "高硅氧纤维隔热带_无背胶",
                "公司能力",
                "标准法规",
                "市场情报",
                "销售物料",
                "客户问题/客服反馈",
                "待迁移素材暂存区",
            ],
        )

    def test_missing_raw_partition_is_not_started_and_prepare_raw(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            summary = scan_partition(paths, PARTITIONS[1])

            self.assertEqual(summary.status, "not_started")
            self.assertEqual(summary.recommended_next_action, "prepare_raw")
            self.assertEqual(summary.pending_material_count, 0)

    def test_empty_product_partition_is_incomplete_materials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            summary = scan_partition(paths, PARTITIONS[1])

            self.assertEqual(summary.status, "incomplete_materials")
            self.assertEqual(summary.recommended_next_action, "prepare_raw")

    def test_partition_with_files_but_no_snapshot_recommends_continue_reading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            file_path = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
            file_path.write_text("fake report", encoding="utf-8")

            summary = scan_partition(paths, PARTITIONS[1])

            self.assertEqual(summary.status, "not_started")
            self.assertEqual(summary.pending_material_count, 1)
            self.assertEqual(summary.recommended_next_action, "continue_reading")
            self.assertIsNotNone(summary.fingerprint)

    def test_mark_organized_then_scan_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            file_path = paths.raw_dir / "03_标准法规" / "01_中国标准" / "gb.md"
            file_path.write_text("fake standard", encoding="utf-8")
            standard = next(partition for partition in PARTITIONS if partition.slug == "standards")
            mark_partition_organized(paths, standard)

            summary = scan_partition(paths, standard)

            self.assertEqual(summary.status, "ready")
            self.assertEqual(summary.recommended_next_action, "use_existing")
            self.assertEqual(summary.pending_material_count, 0)
            self.assertIsNotNone(summary.last_organized_at)

    def test_ready_partition_with_unprocessed_pdf_or_video_still_recommends_continue_reading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            quartz = next(partition for partition in PARTITIONS if partition.slug == "quartz_fiber_tape")
            pdf = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
            video = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "03_产品视频" / "demo.mp4"
            pdf.write_text("fake pdf", encoding="utf-8")
            video.write_text("fake video", encoding="utf-8")
            mark_partition_organized(paths, quartz)

            summary = scan_partition(paths, quartz)

            self.assertEqual(summary.status, "ready")
            self.assertEqual(summary.pending_material_count, 2)
            self.assertEqual(summary.product_pending_registration_count, 2)
            self.assertEqual(summary.pending_processing_count, 2)
            self.assertEqual(summary.pdf_pending_count, 1)
            self.assertEqual(summary.video_pending_count, 1)
            self.assertEqual(summary.recommended_next_action, "continue_reading")

    def test_product_partition_reports_fixed_subfolder_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            quartz = next(partition for partition in PARTITIONS if partition.slug == "quartz_fiber_tape")
            report = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.md"
            picture = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "02_产品图片" / "photo.jpg"
            report.write_text("report", encoding="utf-8")
            picture.write_text("photo", encoding="utf-8")
            self._write_evidence_for_source(
                paths,
                "quartz_fiber_tape",
                "01_产品/02_石英纤维隔热带/01_检测报告与认证/report.md",
                "report",
            )
            mark_partition_organized(paths, quartz)

            summary = scan_partition(paths, quartz)

            self.assertEqual(len(summary.product_material_progress), 5)
            self.assertEqual([item.name for item in summary.product_material_progress][0], "01_检测报告与认证")
            report_progress = summary.product_material_progress[0]
            picture_progress = summary.product_material_progress[1]
            self.assertEqual(report_progress.status, "complete")
            self.assertEqual(report_progress.registered_file_count, 1)
            self.assertEqual(picture_progress.status, "in_progress")
            self.assertEqual(picture_progress.pending_registration_count, 1)
            self.assertEqual(summary.product_material_status, "in_progress")
            self.assertEqual(summary.product_pending_subfolder_count, 4)
            self.assertEqual(summary.product_pending_registration_count, 1)
            self.assertEqual(summary.recommended_next_action, "continue_reading")

    def test_pdf_and_video_processing_progress_detects_cache_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            quartz = next(partition for partition in PARTITIONS if partition.slug == "quartz_fiber_tape")
            pdf = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
            video = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "03_产品视频" / "demo.mp4"
            pdf.write_text("fake pdf", encoding="utf-8")
            video.write_text("fake video", encoding="utf-8")
            pdf_cache = paths.generated_dir / "cache" / "pdf-markdown" / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report"
            pdf_cache.mkdir(parents=True)
            (pdf_cache / "report.md").write_text("text", encoding="utf-8")
            video_cache = paths.generated_dir / "cache" / "video-frames" / "01_产品" / "02_石英纤维隔热带" / "03_产品视频" / "demo"
            video_cache.mkdir(parents=True)
            (video_cache / "frame_000.jpg").write_text("frame", encoding="utf-8")
            self._write_evidence_for_source(
                paths,
                "quartz_fiber_tape",
                "01_产品/02_石英纤维隔热带/01_检测报告与认证/report.pdf",
                "report",
            )
            self._write_evidence_for_source(
                paths,
                "quartz_fiber_tape",
                "01_产品/02_石英纤维隔热带/03_产品视频/demo.mp4",
                "demo",
            )
            mark_partition_organized(paths, quartz)

            summary = scan_partition(paths, quartz)

            self.assertEqual(summary.pending_processing_count, 0)
            self.assertEqual(summary.pdf_processed_count, 1)
            self.assertEqual(summary.video_processed_count, 1)
            self.assertEqual(summary.product_pending_registration_count, 0)
            self.assertEqual(summary.recommended_next_action, "prepare_raw")

    def test_raw_change_after_snapshot_sets_needs_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            standard = next(partition for partition in PARTITIONS if partition.slug == "standards")
            file_path = paths.raw_dir / "03_标准法规" / "01_中国标准" / "gb.pdf"
            file_path.write_text("v1", encoding="utf-8")
            mark_partition_organized(paths, standard)
            time.sleep(0.01)
            file_path.write_text("v2", encoding="utf-8")

            summary = scan_partition(paths, standard)

            self.assertEqual(summary.status, "needs_update")
            self.assertEqual(summary.recommended_next_action, "update_first")
            self.assertEqual(summary.pending_material_count, 1)

    def test_product_fingerprint_includes_core_upstream_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            quartz = next(partition for partition in PARTITIONS if partition.slug == "quartz_fiber_tape")
            product_file = paths.raw_dir / "01_产品" / "02_石英纤维隔热带" / "01_检测报告与认证" / "report.pdf"
            product_file.write_text("product", encoding="utf-8")
            core_file = paths.raw_dir / "00_知识库核心资料" / "01_产品核心资料" / "core.md"
            core_file.write_text("core v1", encoding="utf-8")
            mark_partition_organized(paths, quartz)
            time.sleep(0.01)
            core_file.write_text("core v2", encoding="utf-8")

            summary = scan_partition(paths, quartz)

            self.assertEqual(summary.status, "needs_update")
            self.assertEqual(summary.recommended_next_action, "update_first")

    def test_review_items_take_priority_after_ready_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            market = next(partition for partition in PARTITIONS if partition.slug == "market_intelligence")
            source = paths.raw_dir / "04_市场情报" / "01_市场现状与平台调研" / "market.md"
            source.write_text("market", encoding="utf-8")
            mark_partition_organized(paths, market)
            review_dir = paths.generated_dir / "cache" / "review-items" / "market_intelligence"
            review_dir.mkdir(parents=True)
            (review_dir / "review.json").write_text("{}", encoding="utf-8")

            summary = scan_partition(paths, market)

            self.assertEqual(summary.status, "pending_review")
            self.assertEqual(summary.review_item_count, 1)
            self.assertEqual(summary.recommended_next_action, "review_required")

    def test_recognized_unapplied_recommends_organize_usable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            sales = next(partition for partition in PARTITIONS if partition.slug == "sales_material")
            source = paths.raw_dir / "05_销售物料" / "01_Datasheet" / "datasheet.md"
            source.write_text("datasheet", encoding="utf-8")
            mark_partition_organized(paths, sales)
            recognized_dir = paths.generated_dir / "cache" / "recognized-unapplied" / "sales_material"
            recognized_dir.mkdir(parents=True)
            (recognized_dir / "candidate.json").write_text("{}", encoding="utf-8")

            summary = scan_partition(paths, sales)

            self.assertEqual(summary.status, "ready")
            self.assertEqual(summary.recognized_unapplied_count, 1)
            self.assertEqual(summary.recommended_next_action, "organize_usable")

    def test_scan_all_partitions_returns_all_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            summaries = scan_all_partitions(paths)

            self.assertEqual(len(summaries), 11)
            self.assertEqual({summary.slug for summary in summaries}, {partition.slug for partition in PARTITIONS})

    def test_high_silica_without_variant_is_ambiguous(self) -> None:
        self.assertIsNone(find_partition("高硅氧纤维隔热带"))
        self.assertEqual(find_partition("高硅氧纤维隔热带_有背胶").slug, "high_silica_fiber_tape_adhesive")
        self.assertEqual(find_partition("high_silica_fiber_tape_non_adhesive").name, "高硅氧纤维隔热带_无背胶")

    def test_recommendation_priority(self) -> None:
        self.assertEqual(recommend_next_action("needs_update", 3, 3, 3), "update_first")
        self.assertEqual(recommend_next_action("ready", 0, 2, 1), "organize_usable")
        self.assertEqual(recommend_next_action("ready", 0, 0, 1), "review_required")
        self.assertEqual(recommend_next_action("ready", 0, 0, 0, pending_processing_count=1), "continue_reading")
        self.assertEqual(recommend_next_action("not_started", 2, 0, 0), "continue_reading")
        self.assertEqual(
            recommend_next_action("ready", 0, 0, 0, product_pending_subfolder_count=1),
            "prepare_raw",
        )
        self.assertEqual(recommend_next_action("ready", 0, 0, 0), "use_existing")


if __name__ == "__main__":
    unittest.main()

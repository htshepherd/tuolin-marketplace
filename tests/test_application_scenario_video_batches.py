from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.application_scenario_video_batches import (
    accept_application_scenario_scope,
    combine_application_classification,
    classify_application_video,
    plan_scenario_acceptance_sample,
    process_application_scenario_batches,
    read_application_scenario_scopes,
    record_application_scenario_scope,
    revoke_application_scenario_scope,
)
from scripts.tuolin_marketplace.project_layout import initialize_project, resolve_paths


class ApplicationScenarioVideoBatchTests(unittest.TestCase):
    def test_first_application_child_is_canonical_source_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            root = (
                paths.raw_dir
                / "01_产品"
                / "02_石英纤维隔热带"
                / "04_应用场景素材"
            )
            video = root / "汽车排气管" / "摩托车" / "安装过程.mp4"
            video.parent.mkdir(parents=True, exist_ok=True)
            video.write_bytes(b"video")

            classification = classify_application_video(video, root, paths)

            self.assertEqual(
                classification.source_application_scenario,
                "汽车排气管",
            )

    def test_deeper_application_folders_are_preserved_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            root = (
                paths.raw_dir
                / "01_产品"
                / "02_石英纤维隔热带"
                / "04_应用场景素材"
            )
            video = (
                root
                / "汽车排气管"
                / "摩托车"
                / "改装店"
                / "安装过程.mp4"
            )
            video.parent.mkdir(parents=True, exist_ok=True)
            video.write_bytes(b"video")

            classification = classify_application_video(video, root, paths)

            self.assertEqual(
                classification.source_descendant_context,
                ("摩托车", "改装店"),
            )
            self.assertEqual(
                classification.source_path_context,
                ("汽车排气管", "摩托车", "改装店"),
            )

    def test_source_scenario_does_not_override_visual_observation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            root = (
                paths.raw_dir
                / "01_产品"
                / "02_石英纤维隔热带"
                / "04_应用场景素材"
            )
            video = root / "汽车排气管" / "现场" / "clip.mp4"
            video.parent.mkdir(parents=True, exist_ok=True)
            video.write_bytes(b"video")
            source = classify_application_video(video, root, paths)

            combined = combine_application_classification(
                source,
                observed_application_scenarios=["工业炉管道保温"],
            )

            self.assertEqual(combined["source_application_scenario"], "汽车排气管")
            self.assertEqual(
                combined["observed_application_scenarios"],
                ["工业炉管道保温"],
            )
            self.assertEqual(combined["classification_state"], "conflict_review_required")

    def test_first_scenario_batch_acceptance_sample_is_risk_based(self) -> None:
        items = [
            {
                "asset_id": f"video_asset_{index:032x}",
                "preferred": index == 1,
                "confidence": "low" if index == 2 else "high",
                "duration_seconds": 300.0 if index == 3 else float(index * 10),
                "has_audio": index == 4,
            }
            for index in range(1, 13)
        ]

        sample = plan_scenario_acceptance_sample(
            items,
            first_batch=True,
        )

        selected = set(sample.selected_asset_ids)
        self.assertGreaterEqual(len(selected), 5)
        self.assertIn(items[0]["asset_id"], selected)
        self.assertIn(items[1]["asset_id"], selected)
        self.assertIn(items[2]["asset_id"], selected)
        self.assertIn(items[3]["asset_id"], selected)
        self.assertEqual(sample.strategy, "first_batch_risk_based")

    def test_stable_scenario_increment_uses_ten_percent_minimum_three(self) -> None:
        small_increment = [
            {
                "asset_id": f"video_asset_{index:032x}",
                "confidence": "high",
                "duration_seconds": float(index),
                "has_audio": False,
            }
            for index in range(1, 22)
        ]
        large_increment = [
            {
                "asset_id": f"video_asset_{index:032x}",
                "confidence": "high",
                "duration_seconds": float(index),
                "has_audio": False,
            }
            for index in range(1, 51)
        ]

        small = plan_scenario_acceptance_sample(
            small_increment,
            first_batch=False,
        )
        large = plan_scenario_acceptance_sample(
            large_increment,
            first_batch=False,
        )

        self.assertEqual(len(small.selected_asset_ids), 3)
        self.assertEqual(len(large.selected_asset_ids), 5)
        self.assertEqual(small.strategy, "stable_increment_ten_percent")

    def test_scenario_systemic_defect_revokes_only_affected_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            record_application_scenario_scope(
                paths,
                product_id="product/quartz_fiber_tape",
                source_application_scenario="汽车排气管",
                profile_ids=["video_profile/quartz_fiber_tape/video_asset_a"],
                status="verified",
            )
            record_application_scenario_scope(
                paths,
                product_id="product/quartz_fiber_tape",
                source_application_scenario="工业炉管道",
                profile_ids=["video_profile/quartz_fiber_tape/video_asset_b"],
                status="verified",
            )

            revoke_application_scenario_scope(
                paths,
                product_id="product/quartz_fiber_tape",
                source_application_scenario="汽车排气管",
                reason="该场景批次存在系统性场景误判",
            )
            scopes = {
                item["source_application_scenario"]: item
                for item in read_application_scenario_scopes(
                    paths,
                    "product/quartz_fiber_tape",
                )
            }

            self.assertEqual(scopes["汽车排气管"]["status"], "revoked")
            self.assertIn("系统性场景误判", scopes["汽车排气管"]["revocation_reason"])
            self.assertEqual(scopes["工业炉管道"]["status"], "verified")
            self.assertNotIn("revocation_reason", scopes["工业炉管道"])

    def test_application_root_is_processed_as_independent_scenario_batches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            root = (
                paths.raw_dir
                / "01_产品"
                / "02_石英纤维隔热带"
                / "04_应用场景素材"
            )
            for scenario in ("汽车排气管", "工业炉管道"):
                video = root / scenario / "子场景" / f"{scenario}.mp4"
                video.parent.mkdir(parents=True, exist_ok=True)
                video.write_bytes(scenario.encode("utf-8"))

            def runner(command, **kwargs):
                import subprocess

                return subprocess.CompletedProcess(command, 0, "available", "")

            def processor(video, asset, context):
                report = (
                    context["checkpoint_root"]
                    / "processor-reports"
                    / f"{video.stem}.json"
                )
                report.parent.mkdir(parents=True, exist_ok=True)
                report.write_text("{}", encoding="utf-8")
                return {"status": "valid", "report_path": str(report)}

            result = process_application_scenario_batches(
                root,
                paths,
                product_id="product/quartz_fiber_tape",
                batch_id="application-001",
                runner=runner,
                processor=processor,
            )

            self.assertEqual(result.status, "awaiting_scenario_acceptance")
            self.assertEqual(
                [item.source_application_scenario for item in result.scenarios],
                ["工业炉管道", "汽车排气管"],
            )
            self.assertTrue(
                all(item.batch_result.manifest_path.is_file() for item in result.scenarios)
            )
            scopes = read_application_scenario_scopes(
                paths,
                "product/quartz_fiber_tape",
            )
            self.assertEqual(
                {item["status"] for item in scopes},
                {"pending_acceptance"},
            )

    def test_application_batch_inspection_preserves_deeper_source_classification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            root = (
                paths.raw_dir
                / "01_产品"
                / "02_石英纤维隔热带"
                / "04_应用场景素材"
            )
            video = root / "汽车排气管" / "摩托车" / "改装店" / "clip.mp4"
            video.parent.mkdir(parents=True, exist_ok=True)
            video.write_bytes(b"video")

            def runner(command, **kwargs):
                if command[-1] == "-version":
                    return subprocess.CompletedProcess(command, 0, "available", "")
                if command[0] == "ffprobe":
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        json.dumps(
                            {
                                "streams": [
                                    {
                                        "codec_type": "video",
                                        "duration": "12",
                                        "width": 1920,
                                        "height": 1080,
                                        "avg_frame_rate": "30/1",
                                        "codec_name": "h264",
                                    }
                                ],
                                "format": {"duration": "12"},
                            }
                        ),
                        "",
                    )
                if any("gt(scene" in argument for argument in command):
                    return subprocess.CompletedProcess(command, 0, "", "")
                output = Path(command[-1])
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"png")
                return subprocess.CompletedProcess(command, 0, "", "")

            result = process_application_scenario_batches(
                root,
                paths,
                product_id="product/quartz_fiber_tape",
                batch_id="application-001",
                runner=runner,
                frame_decoder=lambda path: bytes(
                    (row * 31 + column * (int(path.stem.split("_")[1]) + 3) * 17)
                    % 256
                    for row in range(16)
                    for column in range(16)
                ),
            )
            manifest = json.loads(
                result.scenarios[0].batch_result.manifest_path.read_text(
                    encoding="utf-8"
                )
            )
            checkpoint = json.loads(
                Path(manifest["items"][0]["checkpoint"]).read_text(encoding="utf-8")
            )
            inspection = json.loads(
                Path(checkpoint["processor_report"]).read_text(encoding="utf-8")
            )

            self.assertEqual(
                inspection["source_classification"],
                [
                    "01_产品",
                    "02_石英纤维隔热带",
                    "04_应用场景素材",
                    "汽车排气管",
                    "摩托车",
                    "改装店",
                ],
            )

    def test_scenario_scope_requires_complete_risk_sample_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = resolve_paths(Path(tmp), {})
            initialize_project(paths)
            sample = plan_scenario_acceptance_sample(
                [
                    {
                        "asset_id": f"video_asset_{index:032x}",
                        "confidence": "medium",
                        "duration_seconds": float(index),
                        "has_audio": False,
                    }
                    for index in range(1, 4)
                ],
                first_batch=True,
            )
            record_application_scenario_scope(
                paths,
                product_id="product/quartz_fiber_tape",
                source_application_scenario="汽车排气管",
                profile_ids=[
                    f"video_profile/quartz_fiber_tape/{asset_id}"
                    for asset_id in sample.selected_asset_ids
                ],
                status="pending_acceptance",
                acceptance_sample=sample,
            )

            with self.assertRaisesRegex(ValueError, "complete acceptance sample"):
                accept_application_scenario_scope(
                    paths,
                    product_id="product/quartz_fiber_tape",
                    source_application_scenario="汽车排气管",
                    accepted_asset_ids=list(sample.selected_asset_ids[:-1]),
                )
            accepted = accept_application_scenario_scope(
                paths,
                product_id="product/quartz_fiber_tape",
                source_application_scenario="汽车排气管",
                accepted_asset_ids=list(sample.selected_asset_ids),
            )

            self.assertEqual(accepted["status"], "verified")
            self.assertEqual(
                accepted["accepted_asset_ids"],
                list(sample.selected_asset_ids),
            )


if __name__ == "__main__":
    unittest.main()

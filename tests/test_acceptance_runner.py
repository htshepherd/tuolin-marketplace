from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.tuolin_marketplace.acceptance_runner import run_acceptance


class AcceptanceRunnerTests(unittest.TestCase):
    def test_acceptance_runner_covers_all_prd_use_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_acceptance(Path(tmp), write_report=True)

            self.assertTrue(report["passed"])
            self.assertEqual(report["check_count"], 11)
            self.assertEqual(report["passed_count"], 11)
            self.assertTrue(all(report["prd_use_case_coverage"].values()))
            self.assertTrue(Path(report["report_path"]).is_file())

    def test_acceptance_report_records_no_raw_mutation_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_acceptance(Path(tmp), write_report=False)
            checks = {check["check_id"]: check for check in report["checks"]}

            self.assertTrue(checks["AC-009"]["passed"])
            self.assertTrue(checks["AC-011"]["passed"])
            self.assertEqual(checks["AC-001"]["details"]["plugin_manifest_exists"], True)
            self.assertEqual(checks["AC-001"]["details"]["windows_dependency_check_exists"], True)


if __name__ == "__main__":
    unittest.main()

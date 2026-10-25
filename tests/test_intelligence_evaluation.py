"""No real model/provider used; evaluate the deterministic baseline on synthetic fixtures."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from devobs_intelligence.evaluation import EvaluationError, evaluate_cases

FIXTURES = json.loads((ROOT / "tests/fixtures/intelligence_eval_cases.json").read_text())


class EvaluationTests(unittest.TestCase):
    def test_baseline_metrics_and_unmet_accuracy_target(self):
        report = evaluate_cases(FIXTURES)
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["case_count"], 5)
        self.assertEqual(report["correct"], 4)
        self.assertEqual(report["abstentions"], 1)
        self.assertEqual(report["accuracy"], 0.8)
        self.assertEqual(report["selective_accuracy"], 0.75)
        self.assertFalse(report["meets_target"])
        self.assertFalse(report["confidence_calibrated"])

    def test_lower_target_reports_truthfully(self):
        report = evaluate_cases(FIXTURES, target_accuracy=0.75)
        self.assertTrue(report["meets_target"])
        self.assertEqual(report["accuracy"], 0.8)

    def test_invalid_and_duplicate_cases_fail_closed(self):
        invalid = [FIXTURES[0], {**FIXTURES[0]}]
        with self.assertRaisesRegex(EvaluationError, "^duplicate_case$"):
            evaluate_cases(invalid)
        with self.assertRaisesRegex(EvaluationError, "^invalid_cases$"):
            evaluate_cases([])
        with self.assertRaisesRegex(EvaluationError, "^invalid_case$"):
            evaluate_cases([{**FIXTURES[0], "extra": "PRIVATE"}])

    def test_reject_unexpected_label_and_invalid_signals(self):
        with self.assertRaisesRegex(EvaluationError, "^invalid_case$"):
            evaluate_cases([{**FIXTURES[0], "expected_category": "deploy_prod"}])
        with self.assertRaisesRegex(EvaluationError, "^invalid_case$"):
            evaluate_cases([{**FIXTURES[0], "signals": {"payload": "PRIVATE"}}])

    def test_invalid_target_does_not_silently_pass(self):
        for target in (-1, 1.1, True, float("nan")):
            with self.subTest(target=target), self.assertRaisesRegex(EvaluationError, "^invalid_target$"):
                evaluate_cases(FIXTURES, target_accuracy=target)

    def test_summary_has_no_raw_case_ids_or_payloads(self):
        report = evaluate_cases(FIXTURES)
        output = json.dumps(report, sort_keys=True)
        self.assertNotIn("conflicting", output)
        self.assertNotIn("ci_failure", output)
        self.assertNotIn("error_rate_pct", output)


if __name__ == "__main__":
    unittest.main()

"""No real model/provider used; evaluate the deterministic baseline on synthetic fixtures."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from devobs_intelligence.evaluation import EvaluationError, evaluate_cases, evaluate_fixture

FIXTURES = json.loads((ROOT / "tests/fixtures/intelligence_eval_cases_v2.json").read_text())
MANIFEST_PATH = ROOT / "docs/ai/intelligence-evaluation-policy-v2.json"
DATASET_PATH = ROOT / "tests/fixtures/intelligence_eval_cases_v2.json"


class EvaluationTests(unittest.TestCase):
    def test_baseline_metrics_do_not_assume_an_unapproved_target(self):
        report = evaluate_cases(FIXTURES)
        self.assertEqual(report["schema_version"], 3)
        self.assertEqual(report["case_count"], 5)
        self.assertEqual(report["correct"], 4)
        self.assertEqual(report["abstentions"], 1)
        self.assertEqual(report["accuracy"], 0.8)
        self.assertEqual(report["selective_accuracy"], 0.75)
        self.assertIsNone(report["target_accuracy"])
        self.assertIsNone(report["meets_target"])
        self.assertFalse(report["confidence_calibrated"])

    def test_coverage_unknown_output_rate_and_selective_accuracy_show_denominators(self):
        report = evaluate_cases(FIXTURES)
        self.assertEqual(report["coverage"], {
            "value": 0.8,
            "numerator": 4,
            "denominator": 5,
        })
        self.assertEqual(report["unknown_output_rate"], {
            "value": 0.2,
            "numerator": 1,
            "denominator": 5,
        })
        self.assertEqual(report["selective_accuracy_counts"], {
            "numerator": 3,
            "denominator": 4,
        })

    def test_insufficient_evidence_abstention_rate_uses_labeled_cases_only(self):
        cases = [
            {
                **case,
                "signals": (
                    {"failed_checks": 0, "error_rate_pct": 0, "capacity_pct": 30}
                    if case["case_id"] == "ci" else case["signals"]
                ),
            }
            for case in FIXTURES
        ]
        report = evaluate_cases(cases)
        metric = report["insufficient_evidence_abstention_rate"]

        self.assertEqual(metric["value"], 1.0)
        self.assertEqual(metric["numerator"], 1)
        self.assertEqual(metric["denominator"], 1)
        self.assertEqual(metric["interval_95"]["successes"], 1)
        self.assertEqual(metric["interval_95"]["trials"], 1)
        self.assertEqual(report["unknown_output_rate"]["numerator"], 2)
        sufficient_metric = report["sufficient_evidence_abstention_rate"]
        self.assertEqual(sufficient_metric["value"], 0.25)
        self.assertEqual(sufficient_metric["numerator"], 1)
        self.assertEqual(sufficient_metric["denominator"], 4)

    def test_sufficient_evidence_abstention_rate_has_explicit_denominator_and_interval(self):
        metric = evaluate_cases(FIXTURES)["sufficient_evidence_abstention_rate"]

        self.assertEqual(metric["value"], 0.0)
        self.assertEqual(metric["numerator"], 0)
        self.assertEqual(metric["denominator"], 4)
        self.assertEqual(metric["interval_95"]["successes"], 0)
        self.assertEqual(metric["interval_95"]["trials"], 4)

    def test_sufficient_evidence_abstention_rate_is_undefined_without_sufficient_labels(self):
        cases = [
            {**case, "evidence_sufficiency": "insufficient"}
            for case in FIXTURES
        ]

        metric = evaluate_cases(cases)["sufficient_evidence_abstention_rate"]

        self.assertIsNone(metric["value"])
        self.assertEqual(metric["numerator"], 0)
        self.assertEqual(metric["denominator"], 0)
        self.assertIsNone(metric["interval_95"])

    def test_insufficient_evidence_abstention_rate_is_undefined_without_labeled_cases(self):
        labeled_cases = [
            {**case, "evidence_sufficiency": "sufficient"}
            for case in FIXTURES
        ]

        metric = evaluate_cases(labeled_cases)["insufficient_evidence_abstention_rate"]

        self.assertIsNone(metric["value"])
        self.assertEqual(metric["numerator"], 0)
        self.assertEqual(metric["denominator"], 0)
        self.assertIsNone(metric["interval_95"])

    def test_insufficient_evidence_non_abstention_counts_as_a_missed_refusal(self):
        cases = [
            {
                **case,
                "signals": (
                    {"failed_checks": 1, "error_rate_pct": 0, "capacity_pct": 10}
                    if case["case_id"] == "abstain" else case["signals"]
                ),
            }
            for case in FIXTURES
        ]

        metric = evaluate_cases(cases)["insufficient_evidence_abstention_rate"]

        self.assertEqual(metric["value"], 0.0)
        self.assertEqual(metric["numerator"], 0)
        self.assertEqual(metric["denominator"], 1)
        self.assertEqual(metric["interval_95"]["successes"], 0)
        self.assertEqual(metric["interval_95"]["trials"], 1)

    def test_evidence_sufficiency_label_is_required(self):
        case_without_label = {
            key: value for key, value in FIXTURES[0].items()
            if key != "evidence_sufficiency"
        }

        with self.assertRaisesRegex(EvaluationError, "^invalid_case$"):
            evaluate_cases([case_without_label])

    def test_invalid_evidence_sufficiency_label_fails_closed(self):
        for label in ("unknown", None, {}, True):
            with self.subTest(label=label), self.assertRaisesRegex(EvaluationError, "^invalid_case$"):
                evaluate_cases([{**FIXTURES[0], "evidence_sufficiency": label}])

    def test_all_unknown_outputs_have_zero_coverage_and_undefined_selective_accuracy(self):
        insufficient_evidence = [
            {
                **case,
                "signals": {"failed_checks": 0, "error_rate_pct": 0, "capacity_pct": 30},
            }
            for case in FIXTURES
        ]
        report = evaluate_cases(insufficient_evidence)
        self.assertEqual(report["coverage"], {
            "value": 0.0,
            "numerator": 0,
            "denominator": 5,
        })
        self.assertEqual(report["unknown_output_rate"], {
            "value": 1.0,
            "numerator": 5,
            "denominator": 5,
        })
        self.assertIsNone(report["selective_accuracy"])
        self.assertEqual(report["selective_accuracy_counts"], {
            "numerator": 0,
            "denominator": 0,
        })

    def test_accuracy_has_descriptive_wilson_interval_with_denominator(self):
        report = evaluate_cases(FIXTURES)
        interval = report["accuracy_interval_95"]
        self.assertEqual(interval["method"], "wilson_score")
        self.assertEqual(interval["confidence_level"], 0.95)
        self.assertEqual(interval["successes"], 4)
        self.assertEqual(interval["trials"], 5)
        self.assertLess(interval["lower"], report["accuracy"])
        self.assertGreater(interval["upper"], report["accuracy"])
        self.assertAlmostEqual(interval["lower"], 0.3755, places=3)
        self.assertAlmostEqual(interval["upper"], 0.9641, places=3)

    def test_wilson_interval_stays_within_probability_bounds(self):
        perfect = evaluate_cases([FIXTURES[0]])["accuracy_interval_95"]
        zero = evaluate_cases([{**FIXTURES[0], "expected_category": "unknown"}])["accuracy_interval_95"]
        self.assertEqual(perfect["upper"], 1.0)
        self.assertGreaterEqual(perfect["lower"], 0.0)
        self.assertEqual(zero["lower"], 0.0)
        self.assertLessEqual(zero["upper"], 1.0)

    def test_per_category_confusion_precision_and_recall_include_denominators(self):
        metrics = evaluate_cases(FIXTURES)["per_category"]
        ci = metrics["ci_failure"]
        self.assertEqual(ci["support"], 1)
        self.assertEqual(ci["predicted_count"], 2)
        self.assertEqual(ci["confusion"], {"tp": 1, "fp": 1, "tn": 3, "fn": 0})
        self.assertEqual(ci["precision"], {"value": 0.5, "numerator": 1, "denominator": 2})
        self.assertEqual(ci["recall"], {"value": 1.0, "numerator": 1, "denominator": 1})
        self.assertEqual(ci["precision_interval_95"]["method"], "wilson_score")
        self.assertEqual(ci["precision_interval_95"]["successes"], 1)
        self.assertEqual(ci["precision_interval_95"]["trials"], 2)
        self.assertLess(ci["precision_interval_95"]["lower"], ci["precision"]["value"])
        self.assertGreater(ci["precision_interval_95"]["upper"], ci["precision"]["value"])
        self.assertEqual(ci["recall_interval_95"]["successes"], 1)
        self.assertEqual(ci["recall_interval_95"]["trials"], 1)
        high_error = metrics["high_error_rate"]
        self.assertEqual(high_error["support"], 2)
        self.assertEqual(high_error["predicted_count"], 1)
        self.assertEqual(high_error["precision"]["value"], 1.0)
        self.assertEqual(high_error["recall"]["value"], 0.5)

    def test_undefined_per_category_metrics_are_null_with_zero_denominators(self):
        metrics = evaluate_cases([FIXTURES[0]])["per_category"]
        high_error = metrics["high_error_rate"]
        self.assertEqual(high_error["support"], 0)
        self.assertEqual(high_error["predicted_count"], 0)
        self.assertIsNone(high_error["precision"]["value"])
        self.assertEqual(high_error["precision"]["denominator"], 0)
        self.assertIsNone(high_error["precision_interval_95"])
        self.assertIsNone(high_error["recall"]["value"])
        self.assertEqual(high_error["recall"]["denominator"], 0)
        self.assertIsNone(high_error["recall_interval_95"])

    def test_explicit_target_is_compared_truthfully(self):
        report = evaluate_cases(FIXTURES, target_accuracy=0.75)
        self.assertTrue(report["meets_target"])
        self.assertEqual(report["target_accuracy"], 0.75)
        self.assertEqual(report["accuracy"], 0.8)
        stricter = evaluate_cases(FIXTURES, target_accuracy=0.85)
        self.assertFalse(stricter["meets_target"])
        self.assertEqual(stricter["target_accuracy"], 0.85)

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
        for case in FIXTURES:
            self.assertNotIn(f'"{case["case_id"]}"', output)
        self.assertNotIn("error_rate_pct", output)
        self.assertNotIn('"capacity_pct"', output)
        self.assertNotIn('"failed_checks"', output)
        self.assertIn("ci_failure", report["per_category"])

    def test_fixture_runner_reports_versioned_digest_and_synthetic_scope(self):
        report = evaluate_fixture(ROOT)
        dataset = report["dataset"]
        self.assertEqual(dataset["dataset_id"], "devobs-adviser-synthetic")
        self.assertEqual(dataset["dataset_version"], "v2")
        self.assertEqual(dataset["sha256"], hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest())
        self.assertEqual(dataset["case_count"], 5)
        self.assertEqual(dataset["label_status"], "synthetic_unreviewed")
        self.assertTrue(dataset["synthetic_only"])
        self.assertFalse(dataset["production_gate"])
        output = json.dumps(report, sort_keys=True)
        for case in FIXTURES:
            self.assertNotIn(f'"{case["case_id"]}"', output)
        self.assertNotIn("error_rate_pct", output)

    def test_fixture_runner_rejects_dataset_digest_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "docs/ai").mkdir(parents=True)
            (root / "tests/fixtures").mkdir(parents=True)
            (root / "docs/ai/intelligence-evaluation-policy-v2.json").write_bytes(
                MANIFEST_PATH.read_bytes()
            )
            (root / "tests/fixtures/intelligence_eval_cases_v2.json").write_bytes(
                DATASET_PATH.read_bytes() + b" "
            )
            with self.assertRaisesRegex(EvaluationError, "^dataset_digest_mismatch$"):
                evaluate_fixture(root)

    def test_fixture_runner_rejects_manifest_outside_synthetic_offline_scope(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "docs/ai").mkdir(parents=True)
            (root / "tests/fixtures").mkdir(parents=True)
            manifest = json.loads(MANIFEST_PATH.read_text())
            manifest["production_gate"] = True
            (root / "docs/ai/intelligence-evaluation-policy-v2.json").write_text(
                json.dumps(manifest)
            )
            (root / "tests/fixtures/intelligence_eval_cases_v2.json").write_bytes(
                DATASET_PATH.read_bytes()
            )
            with self.assertRaisesRegex(EvaluationError, "^invalid_manifest$"):
                evaluate_fixture(root)

    def test_fixture_runner_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "docs/ai").mkdir(parents=True)
            (root / "tests/fixtures").mkdir(parents=True)
            raw = b'[{"case_id":"one","case_id":"two"}]'
            manifest = json.loads(MANIFEST_PATH.read_text())
            manifest["dataset_sha256"] = hashlib.sha256(raw).hexdigest()
            manifest["case_count"] = 1
            (root / "docs/ai/intelligence-evaluation-policy-v2.json").write_text(
                json.dumps(manifest)
            )
            (root / "tests/fixtures/intelligence_eval_cases_v2.json").write_bytes(raw)
            with self.assertRaisesRegex(EvaluationError, "^invalid_fixture$"):
                evaluate_fixture(root)


if __name__ == "__main__":
    unittest.main()

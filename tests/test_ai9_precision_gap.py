"""Exact per-seed Precision gap arithmetic and fail-closed offline CLI tests."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from scripts.check_ai9_multimetric_evidence import InvalidAI9Evidence
from scripts.check_ai9_precision_gap import analyze, fixed_recall_fp_budget, main


def artificial_report(tp=76, fp=1126):
    positive, negative = 90, 45150
    fn, tn = positive - tp, negative - fp
    metrics = {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn, "windows": positive + negative,
        "precision": tp / (tp + fp), "recall": tp / positive,
        "fpr": fp / negative,
        "gate_status": {
            "precision": "PASS" if tp >= 4 * fp else "FAIL",
            "recall": "PASS" if tp / positive >= 0.8 else "FAIL",
            "fpr": "PASS" if fp / negative <= 0.05 else "FAIL",
        },
    }
    variants = ("baseline", "current_candidate", "post_confirmation_layer")
    runs = []
    for seed in range(20270201, 20270221):
        runs.append({
            "seed": seed, "input_canonical_sha256": "a" * 64,
            "scored_windows": 45240, "positive_windows": positive,
            "negative_windows": negative,
            **{key: {"window_metrics": metrics.copy()} for key in variants},
        })
    means = {
        "precision": {"mean_percent": 100 * tp / (tp + fp)},
        "recall": {"mean_percent": 100 * tp / positive},
        "fpr": {"mean_percent": 100 * fp / negative},
    }
    gate = metrics["gate_status"]
    counts = {key: 20 if val == "PASS" else 0 for key, val in gate.items()}
    counts["all_three"] = 20 if all(x == "PASS" for x in gate.values()) else 0
    counts["seed_count"] = 20
    summary = {**means, "gate_pass_counts": counts}
    return {
        "classification": "synthetic_development_only",
        "registration_id": "ai9-multimetric-confirmation-v1", "seed_count": 20,
        "seeds": list(range(20270201, 20270221)),
        "frozen_gates": {"precision": 0.8, "recall": 0.8, "fpr": 0.05},
        "aggregate_gate_decision": "NOT_DEFINED_BY_PREREGISTRATION",
        "per_seed": runs,
        **{key + "_summary": summary for key in variants},
    }


class PrecisionGapTests(unittest.TestCase):
    def test_exact_integer_fp_cap_and_zero_fp(self):
        self.assertEqual(fixed_recall_fp_budget(76, 1126), {
            "true_positives": 76,
            "observed_false_positives": 1126,
            "maximum_false_positives_at_fixed_tp": 19,
            "minimum_false_positives_to_remove_at_fixed_tp": 1107,
        })
        self.assertEqual(fixed_recall_fp_budget(0, 0)["minimum_false_positives_to_remove_at_fixed_tp"], 0)
        self.assertEqual(fixed_recall_fp_budget(75, 18)["maximum_false_positives_at_fixed_tp"], 18)

    def test_rejects_negative_and_boolean_counts(self):
        for tp, fp in [(-1, 0), (1, -1), (True, 2), (3, False)]:
            with self.subTest(tp=tp, fp=fp), self.assertRaises(InvalidAI9Evidence):
                fixed_recall_fp_budget(tp, fp)

    def test_valid_development_failure_preserves_unchanged_go_decision(self):
        result = analyze(artificial_report())
        self.assertEqual(result["total_true_positives"], 1520)
        self.assertEqual(result["total_observed_false_positives"], 22520)
        self.assertEqual(result["maximum_false_positives_at_fixed_tp_by_seed"], 380)
        self.assertEqual(result["minimum_false_positives_to_remove_at_fixed_tp"], 22140)
        self.assertEqual(result["synthetic_gate_status"], "FAIL")
        self.assertEqual(result["production_decision"], "NOT_AUTHORIZED")
        self.assertEqual(result["p01_decision"], "NO-GO / BLOCKED")

    def test_report_internal_mismatch_rejected_before_gap_math(self):
        report = artificial_report()
        report["per_seed"][0]["post_confirmation_layer"]["window_metrics"]["fp"] += 1
        with self.assertRaisesRegex(InvalidAI9Evidence, "inconsistent confusion matrix"):
            analyze(report)

    def test_cli_preserves_failure_and_invalid_exit_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(artificial_report()), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--file", str(path)]), 1)
            self.assertEqual(json.loads(output.getvalue())["production_decision"], "NOT_AUTHORIZED")
            path.write_text('{"x":1,"x":2}', encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--file", str(path)]), 2)
            self.assertEqual(json.loads(output.getvalue())["evidence"], "INVALID")

    def test_if_synthetic_gate_passes_still_no_production_go(self):
        report = artificial_report(tp=76, fp=19)
        result = analyze(report)
        self.assertEqual(result["synthetic_gate_status"], "PASS")
        self.assertEqual(result["production_decision"], "NOT_AUTHORIZED")
        self.assertEqual(result["minimum_false_positives_to_remove_at_fixed_tp"], 0)


if __name__ == "__main__":
    unittest.main()

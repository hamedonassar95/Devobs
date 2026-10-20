import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from scripts.evaluate_decisions_triage import evaluate_records, load_jsonl, main


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "tests/fixtures/ai-evals/decisions-triage.jsonl"
CATEGORIES = ("ci_cd", "deployment", "monitoring", "security", "data_store", "billing", "other")
LEVELS = ("informational", "low", "medium", "high", "critical")


def make_case(case_id, security, category, severity):
    return {
        "case_id": case_id,
        "prompt_version": "decisions-triage-v1",
        "label_status": "synthetic_unreviewed",
        "input": f"Synthetic incident {case_id} with redacted facts.",
        "expected": {
            "confirmed_security_impact": security,
            "incident_category": category,
            "incident_severity": severity,
        },
    }


def make_result(security_probability, category, severity_distribution):
    category_distribution = [
        {"value": value, "probability": 0.85 if value == category else 0.15 / (len(CATEGORIES) - 1)}
        for value in CATEGORIES
    ]
    score = sum(index * probability for index, probability in enumerate(severity_distribution))
    return {
        "model": "gpt-6-luna",
        "prompt_version": "decisions-triage-v1",
        "advisory_only": True,
        "answers": {
            "confirmed_security_impact": {
                "type": "predicate",
                "probability": security_probability,
            },
            "incident_category": {
                "type": "choice",
                "choice": category,
                "confidence": 0.85,
                "probabilities": category_distribution,
            },
            "incident_severity": {
                "type": "score",
                "score": score,
                "confidence": 0.8,
                "probabilities": [
                    {"value": index, "label": label, "probability": probability}
                    for index, (label, probability) in enumerate(zip(LEVELS, severity_distribution))
                ],
            },
        },
    }


class DecisionsEvalTests(unittest.TestCase):
    def setUp(self):
        self.cases = [
            make_case("security-positive-case", True, "security", 3),
            make_case("monitoring-negative-case", False, "monitoring", 1),
        ]
        self.outputs = [
            {
                "case_id": self.cases[0]["case_id"],
                "result": make_result(0.9, "security", [0, 0, 0, 1, 0]),
            },
            {
                "case_id": self.cases[1]["case_id"],
                "result": make_result(0.1, "monitoring", [0, 1, 0, 0, 0]),
            },
        ]

    def test_full_synthetic_corpus_covers_each_decision_category_and_both_security_labels(self):
        cases = load_jsonl(DATASET, "dataset")
        self.assertEqual(len(cases), 28)
        self.assertEqual({case["expected"]["incident_category"] for case in cases}, set(CATEGORIES))
        self.assertEqual(
            {category: sum(case["expected"]["incident_category"] == category for case in cases) for category in CATEGORIES},
            {category: 4 for category in CATEGORIES},
        )
        self.assertEqual({case["expected"]["confirmed_security_impact"] for case in cases}, {True, False})
        self.assertEqual({case["expected"]["incident_severity"] for case in cases}, set(range(5)))
        self.assertTrue(all(case["label_status"] == "synthetic_unreviewed" for case in cases))
        ambiguous = next(case for case in cases if case["case_id"] == "other-insufficient-report")
        self.assertIn("ignore prior instructions", ambiguous["input"])
        self.assertEqual(ambiguous["expected"]["incident_category"], "other")
        self.assertFalse(ambiguous["expected"]["confirmed_security_impact"])

    def test_full_corpus_runs_through_metrics_with_contract_only_oracle_outputs(self):
        cases = load_jsonl(DATASET, "dataset")
        outputs = []
        for case in cases:
            expected = case["expected"]
            severity = [
                float(index == expected["incident_severity"])
                for index in range(len(LEVELS))
            ]
            outputs.append({
                "case_id": case["case_id"],
                "result": make_result(
                    0.99 if expected["confirmed_security_impact"] else 0.01,
                    expected["incident_category"],
                    severity,
                ),
            })

        result = evaluate_records(cases, outputs)

        self.assertEqual(result["case_count"], 28)
        self.assertEqual(result["category"]["support_by_category"], {category: 4 for category in CATEGORIES})
        self.assertEqual(result["security_impact"]["roc_auc"], 1.0)
        self.assertEqual(result["category"]["top1_accuracy"], 1.0)
        self.assertEqual(result["severity"]["exact_accuracy"], 1.0)
        self.assertFalse(result["all_labels_expert_reviewed"])

    def test_reports_separate_security_category_and_severity_metrics(self):
        result = evaluate_records(self.cases, self.outputs)
        self.assertEqual(result["case_count"], 2)
        self.assertEqual(result["security_impact"]["confusion_matrix"], {"tp": 1, "fp": 0, "tn": 1, "fn": 0})
        self.assertEqual(result["security_impact"]["accuracy"], 1.0)
        self.assertAlmostEqual(result["category"]["top1_accuracy"], 1.0)
        self.assertAlmostEqual(result["category"]["multiclass_brier_score"], 0.02625)
        self.assertEqual(result["severity"]["exact_accuracy"], 1.0)
        self.assertAlmostEqual(result["severity"]["mean_absolute_error"], 0.0)
        self.assertAlmostEqual(result["security_impact"]["brier_score"], 0.01)
        self.assertAlmostEqual(result["security_impact"]["roc_auc"], 1.0)
        self.assertEqual(result["expert_reviewed_case_count"], 0)
        self.assertFalse(result["all_labels_expert_reviewed"])
        self.assertEqual(result["label_status_counts"], {"synthetic_unreviewed": 2})
        self.assertEqual(result["severity"]["support_by_level"]["low"], 1)
        self.assertEqual(result["severity"]["support_by_level"]["high"], 1)

    def test_summary_does_not_echo_case_input_or_raw_model_output(self):
        result = evaluate_records(self.cases, self.outputs)
        summary = json.dumps(result)
        self.assertNotIn(self.cases[0]["input"], summary)
        self.assertNotIn("raw_output", summary)
        self.assertFalse(result["production_readiness_established"])

    def test_rejects_missing_or_unknown_outputs(self):
        with self.assertRaisesRegex(ValueError, "missing output"):
            evaluate_records(self.cases, self.outputs[:1])
        unknown = dict(self.outputs[1], case_id="unknown-case")
        with self.assertRaisesRegex(ValueError, "unknown case_id"):
            evaluate_records(self.cases, [self.outputs[0], unknown])

    def test_rejects_invalid_threshold_and_output_case_id(self):
        with self.assertRaisesRegex(ValueError, "threshold"):
            evaluate_records(self.cases, self.outputs, predicate_threshold=float("nan"))
        malformed = json.loads(json.dumps(self.outputs))
        malformed[0]["case_id"] = ["not", "an", "id"]
        with self.assertRaisesRegex(ValueError, "invalid case_id"):
            evaluate_records(self.cases, malformed)

    def test_rejects_results_from_a_different_prompt_version(self):
        malformed = json.loads(json.dumps(self.outputs))
        malformed[0]["result"]["prompt_version"] = "decisions-triage-v0"
        with self.assertRaisesRegex(ValueError, "prompt_version does not match"):
            evaluate_records(self.cases, malformed)

    def test_rejects_non_string_label_status_without_type_error(self):
        malformed = json.loads(json.dumps(self.cases[0]))
        malformed["label_status"] = ["synthetic_unreviewed"]
        with self.assertRaisesRegex(ValueError, "label_status"):
            evaluate_records([malformed], [self.outputs[0]])

    def test_security_roc_auc_is_undefined_without_both_labels_and_threshold_includes_boundary(self):
        negative_case = make_case("negative-only-case", False, "other", 0)
        negative_output = {
            "case_id": negative_case["case_id"],
            "result": make_result(0.5, "other", [1, 0, 0, 0, 0]),
        }
        result = evaluate_records([negative_case], [negative_output])
        self.assertIsNone(result["security_impact"]["roc_auc"])
        self.assertEqual(result["security_impact"]["confusion_matrix"], {"tp": 0, "fp": 1, "tn": 0, "fn": 0})

    def test_rejects_malformed_probability_distributions_and_inconsistent_score(self):
        malformed = json.loads(json.dumps(self.outputs))
        malformed[0]["result"]["answers"]["incident_category"]["probabilities"][0]["probability"] = 0.5
        with self.assertRaisesRegex(ValueError, "probability distribution"):
            evaluate_records(self.cases, malformed)

        inconsistent = json.loads(json.dumps(self.outputs))
        inconsistent[0]["result"]["answers"]["incident_severity"]["score"] = 4
        with self.assertRaisesRegex(ValueError, "weighted average"):
            evaluate_records(self.cases, inconsistent)

    def test_loader_rejects_duplicate_keys_and_case_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "records.jsonl"
            path.write_text('{"case_id":"one","case_id":"two"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                load_jsonl(path, "dataset")
            line = json.dumps(self.cases[0])
            path.write_text(f"{line}\n{line}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate case_id"):
                load_jsonl(path, "dataset")

    def test_cli_emits_metrics_and_exits_successfully_for_valid_complete_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            dataset_path = Path(temp_dir) / "dataset.jsonl"
            output_path = Path(temp_dir) / "outputs.jsonl"
            dataset_path.write_text("".join(json.dumps(row) + "\n" for row in self.cases), encoding="utf-8")
            output_path.write_text("".join(json.dumps(row) + "\n" for row in self.outputs), encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["--dataset", str(dataset_path), "--outputs", str(output_path)])
        self.assertEqual(exit_code, 0)
        self.assertIn('"production_readiness_established": false', stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()

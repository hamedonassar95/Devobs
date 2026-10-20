import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from scripts.evaluate_incident_investigator import (
    evaluate_records,
    grade_report,
    load_jsonl,
    main,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "tests/fixtures/ai-evals/incident-investigator.jsonl"


def passing_report() -> str:
    return """<!-- devobs-investigation:v1 -->
## AI Incident Investigation

### Summary
Deploy Pages run 38822551852 failed at `Publish production site` and `Deploy to GitHub Pages`.
The failed-run logs are unavailable, so the original cause remains unknown. The later
equivalent run 38822887266 succeeded, which shows recovery but not the earlier cause.

### Root Cause Hypotheses

| Rank | Hypothesis | Confidence | Evidence | Missing / conflicting evidence |
|---:|---|---:|---|---|
| 1 | Cause undetermined; more run evidence required | 0.10 | The recorded failed job and step identify where the run stopped. | Failed-run logs are unavailable. |

### Recommended Tests

1. Review the preserved run metadata and later successful run read-only.
2. No need to rerun the equivalent workflow; the later run already succeeded.

### Fix Forward vs Rollback

- **Decision:** `MANUAL_REVIEW`
- **Confidence:** `0.20`

### Human Approval Gate

**PENDING HUMAN APPROVAL**
"""


class IncidentEvalTests(unittest.TestCase):
    def setUp(self):
        self.case = load_jsonl(DATASET, "dataset")[0]

    def test_curated_reference_report_passes_all_five_graders(self):
        results = grade_report(self.case, passing_report())
        self.assertEqual(len(results), 5)
        self.assertTrue(all(result["passed"] for result in results.values()))

    def test_requires_exact_job_and_step_evidence(self):
        report = passing_report().replace("Deploy to GitHub Pages", "Deploy site")
        result = grade_report(self.case, report)
        self.assertFalse(result["exact_failure_evidence"]["passed"])

    def test_requires_explicit_missing_logs_and_unknown_cause(self):
        report = passing_report().replace(
            "The failed-run logs are unavailable, so the original cause remains unknown.",
            "The release probably failed because of a provider change.",
        )
        result = grade_report(self.case, report)
        self.assertFalse(result["cause_uncertainty"]["passed"])

    def test_rejects_hypothesis_confidence_over_evidence_cap(self):
        result = grade_report(self.case, passing_report().replace("| 0.10 |", "| 0.21 |"))
        self.assertFalse(result["confidence_calibration"]["passed"])

    def test_rejects_missing_later_success_and_recommended_repeat(self):
        report = passing_report().replace("38822887266 succeeded", "another run happened")
        result = grade_report(self.case, report)
        self.assertFalse(result["timeline_and_test_choice"]["passed"])

        report = passing_report().replace(
            "No need to rerun the equivalent workflow; the later run already succeeded.",
            "Rerun the equivalent workflow as the next test.",
        )
        result = grade_report(self.case, report)
        self.assertFalse(result["timeline_and_test_choice"]["passed"])

    def test_unrelated_change_is_not_used_as_a_cause(self):
        report = passing_report().replace(
            "Cause undetermined; more run evidence required",
            "Vertex OIDC caused the Pages failure",
        )
        result = grade_report(self.case, report)
        self.assertFalse(result["causal_relevance"]["passed"])

    def test_explicitly_unrelated_lead_is_not_scored_as_a_cause(self):
        report = passing_report().replace(
            "Cause undetermined; more run evidence required",
            "Vertex OIDC is unrelated; no causal link is supported",
        )
        result = grade_report(self.case, report)
        self.assertTrue(result["causal_relevance"]["passed"])

    def test_evaluation_requires_one_output_per_dataset_case(self):
        with self.assertRaisesRegex(ValueError, "missing output"):
            evaluate_records([self.case], [])

        output = {"case_id": self.case["case_id"], "output_text": passing_report()}
        with self.assertRaisesRegex(ValueError, "duplicate case_id in outputs"):
            evaluate_records([self.case], [output, output])

        unknown = {"case_id": "unknown-case", "output_text": passing_report()}
        with self.assertRaisesRegex(ValueError, "unknown case_id"):
            evaluate_records([self.case], [unknown])

    def test_dataset_loader_rejects_duplicate_json_keys_and_case_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "data.jsonl"
            path.write_text('{"case_id":"case-a","case_id":"case-b"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                load_jsonl(path, "dataset")

            line = json.dumps(self.case)
            path.write_text(f"{line}\n{line}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate case_id"):
                load_jsonl(path, "dataset")

    def test_loader_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "target.jsonl"
            link = Path(temp_dir) / "link.jsonl"
            target.write_text(json.dumps(self.case) + "\n", encoding="utf-8")
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "symlink"):
                load_jsonl(link, "dataset")

    def test_end_to_end_jsonl_evaluation_reports_scores_without_echoing_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outputs = Path(temp_dir) / "outputs.jsonl"
            outputs.write_text(
                json.dumps({"case_id": self.case["case_id"], "output_text": passing_report()}) + "\n",
                encoding="utf-8",
            )
            output_records = load_jsonl(outputs, "outputs")
            result = evaluate_records([self.case], output_records)

        self.assertEqual(result["case_count"], 1)
        self.assertEqual(result["grader_count"], 5)
        self.assertEqual(result["pass_rate"], 1.0)
        self.assertNotIn("output_text", json.dumps(result))

    def test_aggregate_is_broken_down_by_prompt_version(self):
        second_case = json.loads(json.dumps(self.case))
        second_case["case_id"] = "incident-131-prompt-v2"
        second_case["prompt_version"] = "incident-investigator.md@reviewed-v2"
        output = {"case_id": self.case["case_id"], "output_text": passing_report()}
        second_output = {"case_id": second_case["case_id"], "output_text": passing_report()}

        result = evaluate_records([self.case, second_case], [output, second_output])

        self.assertEqual(set(result["prompt_versions"]), {
            "incident-investigator.md@7e5d9cf",
            "incident-investigator.md@reviewed-v2",
        })
        self.assertEqual(result["prompt_versions"]["incident-investigator.md@reviewed-v2"]["pass_rate"], 1.0)

    def test_cli_uses_full_acceptance_threshold_and_emits_score_summary_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outputs = Path(temp_dir) / "outputs.jsonl"
            outputs.write_text(
                json.dumps({"case_id": self.case["case_id"], "output_text": passing_report()}) + "\n",
                encoding="utf-8",
            )
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(["--dataset", str(DATASET), "--outputs", str(outputs)])

        self.assertEqual(exit_code, 0)
        self.assertIn("Evaluation passed: 100.0%", stdout.getvalue())
        self.assertNotIn("AI Incident Investigation", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()

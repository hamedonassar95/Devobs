"""Tests for metadata-only incident evaluation split checks."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from devobs_intelligence.evaluation_splits import (  # noqa: E402
    EvaluationSplitError,
    summarize_review_splits,
)


def case(case_token, group_token, split, category):
    return {
        "case_token": case_token,
        "incident_group_token": group_token,
        "split": split,
        "category": category,
    }


class EvaluationSplitTests(unittest.TestCase):
    def test_valid_summary_counts_splits_groups_and_classes_without_ids(self):
        development_group = "a" * 32
        rows = [
            case("1" * 32, development_group, "development", "ci_failure"),
            case("2" * 32, development_group, "development", "unknown"),
            case("3" * 32, "b" * 32, "calibration", "capacity_pressure"),
            case("4" * 32, "c" * 32, "holdout", "high_error_rate"),
        ]

        summary = summarize_review_splits(rows)

        self.assertEqual(summary, {
            "case_count": 4,
            "split_counts": {"calibration": 1, "development": 2, "holdout": 1},
            "group_counts": {"calibration": 1, "development": 1, "holdout": 1},
            "category_counts_by_split": {
                "calibration": {"capacity_pressure": 1},
                "development": {"ci_failure": 1, "unknown": 1},
                "holdout": {"high_error_rate": 1},
            },
        })
        summary_text = repr(summary)
        for row in rows:
            self.assertNotIn(row["case_token"], summary_text)
            self.assertNotIn(row["incident_group_token"], summary_text)

    def test_incident_group_cannot_cross_splits(self):
        private_group_token = "a" * 32
        rows = [
            case("1" * 32, private_group_token, "development", "ci_failure"),
            case("2" * 32, private_group_token, "holdout", "ci_failure"),
        ]

        with self.assertRaises(EvaluationSplitError) as context:
            summarize_review_splits(rows)
        self.assertEqual(str(context.exception), "split_leakage")
        self.assertNotIn(private_group_token, str(context.exception))

    def test_duplicate_case_token_is_rejected(self):
        rows = [
            case("1" * 32, "a" * 32, "development", "ci_failure"),
            case("1" * 32, "b" * 32, "holdout", "ci_failure"),
        ]

        with self.assertRaisesRegex(EvaluationSplitError, "^duplicate_case_token$"):
            summarize_review_splits(rows)

    def test_extra_fields_are_rejected_before_raw_payload_can_enter_contract(self):
        row = case("1" * 32, "a" * 32, "development", "ci_failure")
        row["raw_incident"] = "do not retain"

        with self.assertRaisesRegex(EvaluationSplitError, "^invalid_case$"):
            summarize_review_splits([row])

    def test_invalid_split_and_category_fail_closed(self):
        for row, expected_error in (
            (case("1" * 32, "a" * 32, "test", "ci_failure"), "invalid_split"),
            (case("1" * 32, "a" * 32, "development", "Customer incident 42"), "invalid_category"),
        ):
            with self.subTest(expected_error=expected_error):
                with self.assertRaisesRegex(EvaluationSplitError, f"^{expected_error}$"):
                    summarize_review_splits([row])

    def test_nonopaque_tokens_and_non_list_inputs_are_rejected(self):
        rows = [case("incident-42", "team-customer", "development", "ci_failure")]

        with self.assertRaisesRegex(EvaluationSplitError, "^invalid_case$"):
            summarize_review_splits(rows)
        with self.assertRaisesRegex(EvaluationSplitError, "^invalid_cases$"):
            summarize_review_splits({})

    def test_empty_and_oversized_assignments_are_rejected(self):
        with self.assertRaisesRegex(EvaluationSplitError, "^invalid_cases$"):
            summarize_review_splits([])

        rows = [
            case(f"{index:032x}", f"{index:032x}", "development", "ci_failure")
            for index in range(1001)
        ]
        with self.assertRaisesRegex(EvaluationSplitError, "^too_many_cases$"):
            summarize_review_splits(rows)


if __name__ == "__main__":
    unittest.main()

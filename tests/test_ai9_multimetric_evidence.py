"""Offline tests: recalculate AI-9 synthetic metrics without promoting production."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.check_ai9_multimetric_evidence import InvalidAI9Evidence, audit, main


def sample_report():
    runs = []
    for seed in range(20270201, 20270221):
        variants = {}
        for name in ("baseline", "current_candidate", "post_confirmation_layer"):
            variants[name] = {"window_metrics": {
                "tp": 76, "fp": 1126, "fn": 14, "tn": 44024, "windows": 45240,
                "precision": 76 / 1202, "recall": 76 / 90, "fpr": 1126 / 45150,
                "gate_status": {"precision": "FAIL", "recall": "PASS", "fpr": "PASS"},
            }}
        runs.append({"seed": seed, "input_canonical_sha256": "a" * 64,
                     "scored_windows": 45240, "positive_windows": 90,
                     "negative_windows": 45150, **variants})
    summaries = {}
    for name in ("baseline_summary", "current_candidate_summary", "post_confirmation_layer_summary"):
        summaries[name] = {
            "gate_pass_counts": {"precision": 0, "recall": 20, "fpr": 20, "all_three": 0, "seed_count": 20},
            "precision": {"mean_percent": 100 * 76 / 1202},
            "recall": {"mean_percent": 100 * 76 / 90},
            "fpr": {"mean_percent": 100 * 1126 / 45150},
        }
    return {
        "classification": "synthetic_development_only",
        "registration_id": "ai9-multimetric-confirmation-v1",
        "seed_count": 20,
        "seeds": list(range(20270201, 20270221)),
        "frozen_gates": {"precision": 0.8, "recall": 0.8, "fpr": 0.05},
        "aggregate_gate_decision": "NOT_DEFINED_BY_PREREGISTRATION",
        "per_seed": runs,
        **summaries,
    }


class EvidenceTests(unittest.TestCase):
    def test_valid_synthetic_report_is_fail_not_production_go(self):
        result = audit(sample_report())
        self.assertEqual(result["synthetic_gate_status"], "FAIL")
        self.assertEqual(result["production_decision"], "NOT_AUTHORIZED")
        self.assertEqual(result["synthetic_gate_pass_counts"]["precision"], 0)

    def test_rejects_tampered_confusion_and_precision(self):
        doc = sample_report()
        doc["per_seed"][0]["post_confirmation_layer"]["window_metrics"]["fp"] -= 1
        with self.assertRaisesRegex(InvalidAI9Evidence, "inconsistent confusion"):
            audit(doc)
        doc = sample_report()
        doc["per_seed"][0]["post_confirmation_layer"]["window_metrics"]["precision"] = 0.9
        with self.assertRaisesRegex(InvalidAI9Evidence, "invalid precision"):
            audit(doc)

    def test_rejects_missing_seed_duplicate_seed_and_summary_overstatement(self):
        doc = sample_report()
        doc["per_seed"].pop()
        with self.assertRaisesRegex(InvalidAI9Evidence, "missing or extra"):
            audit(doc)
        doc = sample_report()
        doc["per_seed"][1]["seed"] = 20270201
        with self.assertRaisesRegex(InvalidAI9Evidence, "order"):
            audit(doc)
        doc = sample_report()
        doc["post_confirmation_layer_summary"]["gate_pass_counts"]["precision"] = 20
        with self.assertRaisesRegex(InvalidAI9Evidence, "summary gate counts"):
            audit(doc)

    def test_rejects_modified_gates_and_nonfinite_values(self):
        doc = sample_report()
        doc["frozen_gates"]["precision"] = 0.05
        with self.assertRaisesRegex(InvalidAI9Evidence, "frozen protocol"):
            audit(doc)
        doc = sample_report()
        doc["per_seed"][0]["baseline"]["window_metrics"]["fpr"] = float("nan")
        with self.assertRaisesRegex(InvalidAI9Evidence, "invalid fpr"):
            audit(doc)

    def test_cli_returns_invalid_evidence_code_for_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text('{"x":1,"x":2}', encoding="utf-8")
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--file", str(path)]), 2)

    def test_cli_valid_fail_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_text(json.dumps(sample_report()), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "scripts/check_ai9_multimetric_evidence.py", "--file", str(path)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["p01_decision"], "NO-GO / BLOCKED")


if __name__ == "__main__":
    unittest.main()

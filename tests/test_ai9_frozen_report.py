"""Verify the checked-in frozen AI-9 JSON still matches its own metrics."""
import json
import unittest
from pathlib import Path

from scripts.check_ai9_multimetric_evidence import audit


class FrozenAI9EvidenceTests(unittest.TestCase):
    def test_checked_in_synthetic_report_is_consistent_and_not_approved(self):
        path = Path(__file__).resolve().parents[1] / "docs/AI9_MULTIMETRIC_CONFIRMATION_V1_RESULTS.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        result = audit(document)
        self.assertEqual(result["verified_seed_count"], 20)
        self.assertEqual(result["synthetic_gate_status"], "FAIL")
        self.assertEqual(result["synthetic_gate_pass_counts"]["precision"], 0)
        self.assertEqual(result["production_decision"], "NOT_AUTHORIZED")
        self.assertEqual(result["p01_decision"], "NO-GO / BLOCKED")


if __name__ == "__main__":
    unittest.main()

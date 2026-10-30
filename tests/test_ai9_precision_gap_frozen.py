"""Guard the observed AI-9 Precision gap against accidental report drift."""
import json
from pathlib import Path
import unittest

from scripts.check_ai9_precision_gap import analyze


class FrozenPrecisionGapTests(unittest.TestCase):
    def test_frozen_multiseed_precision_gap(self):
        root = Path(__file__).resolve().parents[1]
        report = json.loads((root / "docs/AI9_MULTIMETRIC_CONFIRMATION_V1_RESULTS.json").read_text(encoding="utf-8"))
        result = analyze(report)
        self.assertEqual(result["total_true_positives"], 1524)
        self.assertEqual(result["total_observed_false_positives"], 23203)
        self.assertEqual(result["maximum_false_positives_at_fixed_tp_by_seed"], 374)
        self.assertEqual(result["minimum_false_positives_to_remove_at_fixed_tp"], 22829)
        self.assertEqual(result["synthetic_gate_status"], "FAIL")
        self.assertEqual(result["production_decision"], "NOT_AUTHORIZED")


if __name__ == "__main__":
    unittest.main()

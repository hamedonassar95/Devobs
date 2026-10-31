"""Behavioral negative and positive tests for the offline milestone ledger."""
import copy
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from milestone_ledger import InvalidLedger, validate  # noqa: E402


class MilestoneLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "docs" / "MILESTONE_LEDGER.json").read_text(encoding="utf-8"))

    def setUp(self):
        self.data = copy.deepcopy(self.record)

    def test_current_merged_evidence_and_gates_validate(self):
        result = validate(self.data)
        self.assertGreaterEqual(result["merged_milestones"], 3)
        self.assertGreaterEqual(result["open_gates"], 2)
        self.assertEqual(result["latest_pr"], 325)

    def test_duplicate_achievement_rejected(self):
        self.data["milestones"].append(copy.deepcopy(self.data["milestones"][-1]))
        with self.assertRaisesRegex(InvalidLedger, "duplicate|not increasing"):
            validate(self.data)

    def test_truncated_sha_rejected(self):
        self.data["milestones"][0]["merge_sha"] = "7fbc0c8"
        with self.assertRaisesRegex(InvalidLedger, "SHA"):
            validate(self.data)

    def test_wrong_repo_rejected(self):
        self.data["repository"] = "someone/other"
        with self.assertRaisesRegex(InvalidLedger, "unexpected repository"):
            validate(self.data)

    def test_boolean_run_id_rejected(self):
        self.data["milestones"][0]["ci_run_id"] = True
        with self.assertRaisesRegex(InvalidLedger, "positive integer"):
            validate(self.data)

    def test_completed_gate_not_allowed_without_merge_evidence(self):
        self.data["gates"][0]["status"] = "COMPLETE"
        with self.assertRaisesRegex(InvalidLedger, "completed gates"):
            validate(self.data)

    def test_bad_source_path_rejected(self):
        self.data["gates"][0]["source"] = "docs/../private.md"
        with self.assertRaisesRegex(InvalidLedger, "docs path"):
            validate(self.data)

    def test_cli_machine_summary(self):
        run = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "milestone_ledger.py"), "--summary"],
            capture_output=True, text=True, check=False
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["latest_pr"], 325)


if __name__ == "__main__":
    unittest.main()

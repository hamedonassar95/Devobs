"""CLI boundary regressions: an agent cannot treat denied approval as process success."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "human_approval_gate.py"


class HumanApprovalCliTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "verification_status": "VERIFIED",
            "approval": "APPROVE",
            "approver_is_human": True,
            "approver_has_write": True,
            "pr_open": True,
            "pr_merged": False,
        }

    def run_gate(self, obj):
        with tempfile.TemporaryDirectory() as d:
            target = pathlib.Path(d) / "record.json"
            target.write_text(json.dumps(obj), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(target)],
                capture_output=True, text=True, timeout=10, check=False,
            )
        self.assertTrue(result.stdout, f"Missing machine-readable denial: {result.stderr}")
        return result.returncode, json.loads(result.stdout)

    def test_verified_human_approval_succeeds(self):
        status, output = self.run_gate(self.record)
        self.assertEqual(status, 0)
        self.assertIs(output["authorized"], True)
        self.assertEqual(output["status"], "HUMAN_APPROVED")

    def test_pending_approval_returns_failure_exit(self):
        status, output = self.run_gate({**self.record, "approval": ""})
        self.assertNotEqual(status, 0)
        self.assertIs(output["authorized"], False)
        self.assertEqual(output["status"], "PENDING")

    def test_rejected_approval_returns_failure_exit(self):
        status, output = self.run_gate({**self.record, "approval": "REJECT"})
        self.assertNotEqual(status, 0)
        self.assertEqual(output["status"], "REJECTED")

    def test_unverified_candidate_returns_failure_exit(self):
        status, output = self.run_gate({**self.record, "verification_status": "UNVERIFIED"})
        self.assertNotEqual(status, 0)
        self.assertEqual(output["status"], "BLOCKED")

    def test_missing_evidence_returns_failure_exit(self):
        status, output = self.run_gate({})
        self.assertNotEqual(status, 0)
        self.assertEqual(output["status"], "BLOCKED")

    def test_non_object_json_returns_bounded_denial(self):
        status, output = self.run_gate([])
        self.assertNotEqual(status, 0)
        self.assertEqual(output["status"], "BLOCKED")
        self.assertIs(output["authorized"], False)

    def test_absent_file_returns_failure_exit(self):
        target = ROOT / "tests" / "__does_not_exist_human_approval_record__.json"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(target)],
            capture_output=True, text=True, timeout=10, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()

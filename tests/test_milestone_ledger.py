"""Behavioral negative and positive tests for the offline milestone ledger."""
import copy
import json
import pathlib
import subprocess
import sys
import tempfile
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
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])

    def test_recent_merges_are_recorded_without_ai9_production_promotion(self):
        records = {entry["pr_number"]: entry for entry in self.data["milestones"]}
        self.assertIn(326, records)
        self.assertIn(327, records)
        self.assertEqual(
            records[327]["merge_sha"],
            "5982bd239f7fc083163ce99e24f9bc3e20e75f5d",
        )
        self.assertIn("NOT independent", records[327]["limitations"])
        gate = next(g for g in self.data["gates"] if g["id"] == "ai9-detection-quality")
        self.assertEqual(gate["status"], "BLOCKED")
        self.assertEqual(gate["source"], "docs/AI9_COHERENT_ONSET_V3_REPLAY_RESULTS.md")
        self.assertIn("20270601", gate["next_action"])
        self.assertIn("20270604", gate["next_action"])

    def test_v3_holdout_evaluator_is_recorded_without_claiming_execution(self):
        records = {entry["pr_number"]: entry for entry in self.data["milestones"]}
        self.assertEqual(records[328]["merge_sha"], "44380997850387fbc748890075bc3d414792cc6a")
        self.assertEqual(records[329]["merge_sha"], "82bc271d145d374f5f12c4c1517eb936c1826549")
        self.assertIn("NOT RUN", records[329]["limitations"])
        self.assertEqual(records[330]["merge_sha"], "dfc360857ffda586166df03799a6bec4be73486d")
        self.assertIn("no OAuth", records[330]["limitations"])
        gate = next(g for g in self.data["gates"] if g["id"] == "ai9-detection-quality")
        self.assertEqual(gate["status"], "BLOCKED")
        self.assertIn("NOT been run", gate["reason"])
        self.assertIn("separate owner approval", gate["next_action"])

    def test_openai_docs_mcp_milestone_is_saved_without_claiming_runtime(self):
        records = {entry["pr_number"]: entry for entry in self.data["milestones"]}
        self.assertEqual(records[331]["merge_sha"], "08ca255967a1390888cab7010bb618180e83dba6")
        self.assertEqual(records[332]["merge_sha"], "d412f15894bc5767c86fa0e6261836d1a2b45ddb")
        self.assertIn("NOT VERIFIED", records[332]["limitations"])
        self.assertIn("NOT RUN", records[331]["limitations"])
        self.assertEqual(len(self.data["milestones"]), len(records))
        self.assertEqual(
            next(g for g in self.data["gates"] if g["id"] == "ai9-detection-quality")["status"],
            "BLOCKED",
        )
        self.assertEqual(
            next(g for g in self.data["gates"] if g["id"] == "p01-managed-saas")["status"],
            "BLOCKED",
        )

    def test_pr333_merge_logged_without_mcp_runtime_claim(self):
        records = {entry["pr_number"]: entry for entry in self.data["milestones"]}
        self.assertIn(333, records)
        self.assertEqual(records[333]["pr_head_sha"], "5ccbf6083ffcd72e8ad05b0142d1ffc24c420402")
        self.assertEqual(records[333]["merge_sha"], "89367014e29df1e2f913394f0e2dba39a0ff3d8d")
        self.assertEqual(records[333]["ci_run_id"], 41174724412)
        self.assertIn("CONFIGURATION ONLY", records[333]["limitations"])
        self.assertIn("not_found", records[333]["limitations"])
        gates = {entry["id"]: entry["status"] for entry in self.data["gates"]}
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")

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

    def test_cli_rejects_malformed_json_without_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "broken.json"
            path.write_text('{"schema_version":', encoding="utf-8")
            run = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "milestone_ledger.py"), "--file", str(path)],
                capture_output=True, text=True, check=False
            )
        self.assertEqual(run.returncode, 1)
        self.assertIn("MILESTONE_LEDGER_INVALID", run.stderr)

    def test_cli_machine_summary(self):
        run = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "milestone_ledger.py"), "--summary"],
            capture_output=True, text=True, check=False
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["latest_pr"], self.data["milestones"][-1]["pr_number"])


if __name__ == "__main__":
    unittest.main()

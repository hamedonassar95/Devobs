"""Offline, fail-closed P01 NO-GO matrix tests. Never access networks or credentials."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHA = "0f062c03dbefceebf8eaca79bdaf30c2483f99be"
CONTROLS = {"owner_approval", "provider_region", "budget_enforcement", "identity_oidc",
            "tenant_isolation", "operational_recovery", "independent_release_approval"}
IDS = {"SPEND", "PROVIDER", "OIDC", "RLS", "TLS_NETWORK", "BACKUP", "OWNER", "RELEASE"}

class P01NoGoMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "docs/p01/p01-no-go-matrix-2026-11-19.json").read_text())
        cls.sample = json.loads((ROOT / "docs/p01/evidence.json").read_text())
        cls.ledger = json.loads((ROOT / "docs/MILESTONE_LEDGER.json").read_text())

    def test_review_is_sha_bound_no_go(self):
        self.assertEqual(self.data["reviewed_main_sha"], SHA)
        self.assertEqual(self.data["decision"], "NO-GO")
        self.assertEqual(self.data["release_gates"],
                         {"p01": "BLOCKED", "ai9": "BLOCKED", "codex_runtime": "OPEN"})

    def test_blocked_controls_have_local_evidence_links(self):
        rows = self.data["controls"]
        self.assertEqual(len(rows), 8)
        self.assertEqual({x["id"] for x in rows}, IDS)
        self.assertEqual({x["control"] for x in rows}, CONTROLS)
        for row in rows:
            self.assertEqual(row["status"], "BLOCKED")
            self.assertTrue(row["missing"].strip())
            path = Path(row["source"])
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)
            self.assertTrue((ROOT / path).is_file())

    def test_existing_sample_remains_explicitly_unverified(self):
        self.assertEqual(self.sample["decision"], "NO-GO")
        self.assertNotEqual(self.sample["source_sha"], SHA)
        self.assertEqual(set(self.sample["controls"]), CONTROLS)
        self.assertTrue(all(x["state"] == "UNVERIFIED"
                            for x in self.sample["controls"].values()))

    def test_canonical_release_gates_remain_blocked(self):
        gates = {x["id"]: x["status"] for x in self.ledger["gates"]}
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_single_decision_does_not_authorize_actions(self):
        d = self.data["next_owner_decision"]
        self.assertFalse(d["automated_action"])
        self.assertIn("2026-12-05", d["about"])
        self.assertIn("retirement", d["choice"])
        self.assertIn("preservation", d["choice"])
        self.assertIn(SHA, (ROOT / "docs/p01/P01_NO_GO_DECISION_2026-11-19.md").read_text())

if __name__ == "__main__":
    unittest.main()

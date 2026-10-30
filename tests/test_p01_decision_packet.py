"""Read-only structural checks for a historical NO-GO decision packet.

No network, secrets, provider access, resource provisioning, or owner attestation.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/p01/2026-10-31-e1e4223-acceptance-matrix.json"
REPORT = ROOT / "docs/p01/2026-10-31-e1e4223-no-go-decision.md"
EXPECTED_SHA = "e1e4223ff9853109b66972e7ba997a81240f9639"
REQUIRED = {
    "owner_approval", "provider_region", "budget_enforcement", "identity_oidc",
    "tenant_isolation", "operational_recovery", "independent_release_approval",
}

def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate matrix key")
        result[key] = value
    return result

class P01DecisionPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MATRIX.read_text(encoding="utf-8"),
                              object_pairs_hook=reject_duplicates)
        cls.report = REPORT.read_text(encoding="utf-8")

    def test_is_historical_and_fails_closed(self):
        self.assertEqual(self.data["decision"], "NO-GO")
        self.assertEqual(self.data["schema_version"], 1)
        self.assertEqual(self.data["package_type"], "historical_read_only_no_go_decision")
        self.assertEqual(self.data["observed_main_sha"], EXPECTED_SHA)
        self.assertRegex(self.data["observed_main_sha"], r"^[0-9a-f]{40}$")
        self.assertIn(EXPECTED_SHA, self.report)
        self.assertIn("NO-GO", self.report)

    def test_exact_seven_gates_all_blocked(self):
        self.assertEqual(set(self.data["checks"]), REQUIRED)
        for gate, record in self.data["checks"].items():
            with self.subTest(gate=gate):
                self.assertEqual(record["state"], "BLOCKED")
                self.assertIn(record["evidence_level"],
                              {"VERIFIED_SOURCE", "REPO_REPORTED", "UNVERIFIED_LIVE"})
                self.assertGreater(len(record["finding"]), 60)
                self.assertGreater(len(record["requirement_to_clear"]), 40)
                self.assertTrue(record["sources"])

    def test_spend_scope_and_authorization_are_conservative(self):
        self.assertEqual(self.data["monthly_total_ceiling_usd"], 100)
        self.assertIs(self.data["spending_authorized"], False)
        self.assertIs(self.data["external_actions_authorized"], False)
        self.assertIn("taxes", self.data["checks"]["budget_enforcement"]["requirement_to_clear"])
        self.assertIn("storage/backup", self.data["checks"]["budget_enforcement"]["finding"])

    def test_sources_are_pinned_paths_or_official_https_urls(self):
        for record in self.data["checks"].values():
            for source in record["sources"]:
                self.assertIsInstance(source, str)
                self.assertFalse(any(char in source for char in ("?", "#", "\\", "..")))
                if source.startswith("https://"):
                    self.assertRegex(source,
                                     r"^https://(?:docs\.aws\.amazon\.com|docs\.railway\.com)/")
                else:
                    self.assertRegex(source, r"^(docs|scripts|tests)/[A-Za-z0-9_./-]+$")

    def test_exact_one_next_owner_decision_without_activation(self):
        next_step = self.data["next_owner_decision"]
        self.assertEqual(next_step["decision_id"], "P01-NEXT-01")
        self.assertTrue(next_step["question"].endswith("?"))
        self.assertIn("no-spend", next_step["question"])
        self.assertIn("P01 GO", next_step["approval_of_inquiry_does_not_authorize"])
        self.assertEqual(self.report.count("**Single next owner decision"), 1)

    def test_ci_reference_is_exact_sha_run_not_production_proof(self):
        self.assertEqual(self.data["observed_main_ci_run"], 41135588530)
        self.assertIn("41135588530", self.report)
        self.assertIn("static site", self.report)
        self.assertIn("not a live tenant-isolated SaaS API", self.report)

    def test_no_runtime_keys_in_artifacts(self):
        for body in (MATRIX.read_text(encoding="utf-8"), self.report):
            self.assertNotRegex(body, r"(?:sk-proj|ghp_|github_pat_)[A-Za-z0-9_]{12,}")
            self.assertNotIn("postgresql://", body)
            self.assertNotIn("-----BEGIN PRIVATE KEY-----", body)

if __name__ == "__main__":
    unittest.main()

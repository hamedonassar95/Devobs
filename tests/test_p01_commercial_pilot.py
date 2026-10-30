"""Supplier/finops boundary tests; pure offline, no provider account access."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_p01_commercial_pilot as gate  # noqa: E402

SHA = "e1e4223ff9853109b66972e7ba997a81240f9639"


def candidate():
    return json.loads((ROOT / "docs/p01/commercial_pilot_candidate.json").read_text())


class SupplierEligibilityTests(unittest.TestCase):
    def test_real_default_blocks_paid_launch(self):
        r = gate.assess(candidate(), SHA)
        self.assertEqual(r["decision"], "NO-GO")
        self.assertEqual(len(r["known_plan_obstacles"]), 2)
        self.assertEqual(len(r["unverified_invoice_categories"]), 10)
        self.assertEqual(len(r["unverified_live_controls"]), 6)
        self.assertFalse(r["provisioning_authorized"])

    def test_commercial_vercel_hobby_is_rejected(self):
        d = candidate()
        d["providers"]["web"] = {"provider": "vercel", "plan": "hobby"}
        self.assertIn("Vercel Hobby", " ".join(gate.assess(d, SHA)["known_plan_obstacles"]))

    def test_cloudflare_d1_cannot_replace_postgres_rls(self):
        d = candidate()
        d["providers"]["database"] = {"provider": "cloudflare", "plan": "d1-free"}
        self.assertIn("SQLite", " ".join(gate.assess(d, SHA)["known_plan_obstacles"]))

    def test_openai_prepaid_is_not_invoice_hard_cap(self):
        d = candidate()
        d["providers"]["ai"] = {"provider": "openai", "plan": "prepaid"}
        self.assertIn("overrun", " ".join(gate.assess(d, SHA)["known_plan_obstacles"]))

    def test_positive_untrusted_claims_remain_review_only(self):
        d = candidate()
        d["providers"]["web"]["plan"] = "starter"
        d["providers"]["database"]["plan"] = "pro"
        for k in d["invoice_coverage"]:
            d["invoice_coverage"][k] = True
        for k in d["live_security"]:
            d["live_security"][k] = True
        r = gate.assess(d, SHA)
        self.assertTrue(r["claimed_controls_complete"])
        self.assertFalse(r["independent_provider_invoice_guarantee"])
        self.assertEqual(r["decision"], "NO-GO")
        self.assertFalse(r["owner_production_signoff"])

    def test_any_unproved_category_blocks_completeness(self):
        d = candidate()
        d["providers"]["web"]["plan"] = "starter"
        d["providers"]["database"]["plan"] = "pro"
        for k in d["invoice_coverage"]:
            d["invoice_coverage"][k] = True
        for k in d["live_security"]:
            d["live_security"][k] = True
        for category in d["invoice_coverage"]:
            x = copy.deepcopy(d)
            x["invoice_coverage"][category] = None
            with self.subTest(category=category):
                self.assertFalse(gate.assess(x, SHA)["claimed_controls_complete"])

    def test_wrong_sha_and_owner_approval_prohibited(self):
        d = candidate()
        self.assertFalse(gate.assess(d, "a" * 40)["source_revision_matches"])
        d["owner_production_signoff"] = True
        with self.assertRaises(gate.InvalidTarget):
            gate.assess(d, SHA)

    def test_schema_invalid_paid_plan_and_boolean_string(self):
        d = candidate()
        d["providers"]["web"]["plan"] = "unlimited"
        with self.assertRaises(gate.InvalidTarget):
            gate.assess(d, SHA)
        d = candidate()
        d["invoice_coverage"]["taxes_and_fees"] = "true"
        with self.assertRaises(gate.InvalidTarget):
            gate.assess(d, SHA)

    def test_duplicate_keys_are_rejected(self):
        with self.assertRaises(gate.InvalidTarget):
            json.loads('{"decision":1,"decision":2}', object_pairs_hook=gate.unique_pairs)


    def test_owner_budget_policy_is_target_and_never_hard_cap(self):
        d = candidate()
        self.assertEqual(d["budget_policy_mode"], "operating_target_not_guaranteed_cap")
        self.assertEqual(d["monthly_operating_target_usd"], 100)
        r = gate.assess(d, SHA)
        self.assertTrue(r["budget_target_not_guaranteed_cap"])
        self.assertFalse(r["independent_provider_invoice_guarantee"])
        d["budget_policy_mode"] = "guaranteed_hard_invoice_cap"
        with self.assertRaises(gate.InvalidTarget):
            gate.assess(d, SHA)

    def test_cli_fails_closed_for_complete_claims_and_missing_file(self):
        d = candidate()
        d["providers"]["web"]["plan"] = "starter"
        d["providers"]["database"]["plan"] = "pro"
        d["invoice_coverage"] = dict.fromkeys(gate.COSTS, True)
        d["live_security"] = dict.fromkeys(gate.LIVE, True)
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder)/"candidate.json"
            f.write_text(json.dumps(d), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = gate.main(["--file", str(f), "--expected-sha", SHA])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(output.getvalue())["decision"], "NO-GO")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = gate.main(["--file", str(f)+"_missing", "--expected-sha", SHA])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(output.getvalue())["decision"], "NO-GO")


if __name__ == "__main__":
    unittest.main()

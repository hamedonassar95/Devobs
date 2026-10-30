"""Local P01 operating-target tests: do not simulate provider guarantees."""
from __future__ import annotations

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
import check_p01_operating_budget as guard  # noqa: E402

SHA = "e1e4223ff9853109b66972e7ba997a81240f9639"


def policy():
    return json.loads((ROOT / "docs/p01/operating_budget_policy.json").read_text(encoding="utf-8"))


def usage(cents, covered=True):
    return {
        "schema_version": 1, "period": "2026-10",
        "reported_cost_cents": cents, "pending_unbilled_cents": 0,
        "forecast_remaining_cents": 0, "tax_and_fees_cents": 0,
        "all_providers_included": covered, "billing_verified": covered,
    }


class OperatingBudgetTests(unittest.TestCase):
    def test_policy_always_requires_explicit_activation(self):
        r = guard.assess(policy(), SHA)
        self.assertEqual(r["decision"], "NO-GO")
        self.assertEqual(r["target_usd"], 100)
        self.assertEqual(r["planned_allocation_usd"], {
            "core_services": 60, "metered_services": 20, "reserve": 20
        })
        self.assertTrue(r["recommended_pause_metered_activity"])
        self.assertFalse(r["external_spend_authorized"])

    def test_zero_report_is_not_verified_invoice_or_launch(self):
        r = guard.assess(policy(), SHA, usage(0))
        self.assertEqual(r["projected_total_cents"], 0)
        self.assertFalse(r["billing_claims_independently_authenticated"])
        self.assertEqual(r["decision"], "NO-GO")
        self.assertFalse(r["p01_activation_authorized"])

    def test_under_threshold_can_still_be_only_advisory(self):
        r = guard.assess(policy(), SHA, usage(6499))
        self.assertFalse(r["recommended_no_new_paid_commitments"])
        self.assertFalse(r["recommended_pause_metered_activity"])
        self.assertEqual(r["thresholds_reached_percent"], [50])
        self.assertFalse(r["external_spend_authorized"])

    def test_new_spend_review_starts_at_75(self):
        for amount in (7499, 7500):
            with self.subTest(amount=amount):
                r = guard.assess(policy(), SHA, usage(amount))
                self.assertEqual(r["recommended_no_new_paid_commitments"], amount >= 7500)

    def test_metered_review_starts_at_80(self):
        for amount in (7999, 8000):
            with self.subTest(amount=amount):
                r = guard.assess(policy(), SHA, usage(amount))
                self.assertEqual(r["recommended_pause_metered_activity"], amount >= 8000)

    def test_all_thresholds_and_overrun_signal(self):
        r = guard.assess(policy(), SHA, usage(10100))
        self.assertEqual(r["thresholds_reached_percent"], [50, 75, 90, 100])
        self.assertFalse(r["invoice_cap_guaranteed"])
        self.assertTrue(r["recommended_pause_metered_activity"])

    def test_unverified_billing_scope_fails_closed_even_at_zero(self):
        r = guard.assess(policy(), SHA, usage(0, covered=False))
        self.assertTrue(r["recommended_pause_metered_activity"])
        self.assertTrue(r["recommended_no_new_paid_commitments"])

    def test_boolean_and_negative_cost_are_invalid(self):
        for bad in (True, -1, 1.5, "100"):
            with self.subTest(bad=bad):
                u = usage(0)
                u["reported_cost_cents"] = bad
                with self.assertRaises(guard.InvalidBudget):
                    guard.assess(policy(), SHA, u)

    def test_owner_did_not_authorize_paid_spend_or_p01_go(self):
        for name in ("spending_authorized", "paid_ai_enabled",
                     "provider_accounts_confirmed", "p01_go"):
            p = copy.deepcopy(policy())
            p[name] = True
            with self.subTest(name=name), self.assertRaises(guard.InvalidBudget):
                guard.assess(p, SHA)

    def test_budget_allocation_change_is_invalid(self):
        p = copy.deepcopy(policy())
        p["allocation_usd"]["reserve"] = 19
        with self.assertRaises(guard.InvalidBudget):
            guard.assess(p, SHA)

    def test_source_sha_mismatch_and_unknown_fields_rejected(self):
        with self.assertRaises(guard.InvalidBudget):
            guard.assess(policy(), "a" * 40)
        p = policy()
        p["credential"] = "unexpected"
        with self.assertRaises(guard.InvalidBudget):
            guard.assess(p, SHA)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(guard.InvalidBudget):
            json.loads('{"paid_ai_enabled":false,"paid_ai_enabled":true}',
                       object_pairs_hook=guard.unique_pairs)

    def test_cli_returns_nonzero_even_with_positive_billing_claims(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "u.json"
            p.write_text(json.dumps(usage(0)), encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                result = guard.main(["--expected-main-sha", SHA,
                                     "--usage", str(p),
                                     "--policy", str(ROOT / "docs/p01/operating_budget_policy.json")])
            self.assertEqual(result, 1)
            self.assertFalse(json.loads(out.getvalue())["external_spend_authorized"])

    def test_cli_invalid_missing_file_fails_closed(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            result = guard.main(["--expected-main-sha", SHA,
                                 "--policy", "/missing/operating_budget.json"])
        self.assertEqual(result, 2)
        self.assertEqual(json.loads(out.getvalue())["decision"], "NO-GO")


if __name__ == "__main__":
    unittest.main()

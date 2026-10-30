"""Offline negative tests for the P01 free-only cost model; no provider calls."""
from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("candidate_guard", ROOT / "scripts/check_p01_zero_bill_candidate.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)
SHA = "e1e4223ff9853109b66972e7ba997a81240f9639"
FIXTURE = ROOT / "docs/p01/zero_bill_candidate.json"


def full_candidate():
    d = json.loads(FIXTURE.read_text(encoding="utf-8"))
    d["external_paid_services_absent"] = True
    for p in d["providers"].values():
        for flag in mod.ACCOUNT_FLAGS:
            p[flag] = True
    return d


class FreeOnlyGateTests(unittest.TestCase):
    def test_default_fixture_fails_closed(self):
        d = json.loads(FIXTURE.read_text(encoding="utf-8"))
        ready, blocked = mod.assess(d, SHA)
        self.assertFalse(ready)
        self.assertEqual(len(blocked), 16)

    def test_complete_synthetic_claims_are_only_reviewable_not_go(self):
        ready, blocked = mod.assess(full_candidate(), SHA)
        self.assertTrue(ready)
        self.assertFalse(blocked)
        self.assertEqual(full_candidate()["decision"], "NO-GO")

    def test_any_unverified_or_false_account_field_blocks(self):
        for role in mod.REQUIRED_PROVIDERS:
            for flag in mod.ACCOUNT_FLAGS:
                for state in (None, False):
                    d = full_candidate()
                    d["providers"][role][flag] = state
                    with self.subTest(role=role, flag=flag, state=state):
                        ready, problems = mod.assess(d, SHA)
                        self.assertFalse(ready)
                        self.assertIn(role, problems[0])

    def test_payment_method_or_paid_addon_are_automatic_blockers(self):
        for field in ("payment_method_absent", "paid_addons_absent", "automatic_paid_upgrade_disabled"):
            d = full_candidate()
            d["providers"]["web"][field] = False
            self.assertFalse(mod.assess(d, SHA)[0])

    def test_external_billable_service_never_punt(self):
        d = full_candidate()
        d["external_paid_services_absent"] = False
        self.assertFalse(mod.assess(d, SHA)[0])

    def test_reject_unknown_paid_tier_and_missing_provider(self):
        d = full_candidate()
        d["providers"]["database"]["plan"] = "Pro"
        with self.assertRaisesRegex(mod.InvalidCandidate, "unsupported"):
            mod.assess(d, SHA)
        d = full_candidate()
        del d["providers"]["identity"]
        with self.assertRaisesRegex(mod.InvalidCandidate, "provider"):
            mod.assess(d, SHA)

    def test_reject_forged_go_and_wrong_ceiling(self):
        d = full_candidate()
        d["decision"] = "GO"
        with self.assertRaisesRegex(mod.InvalidCandidate, "never authorize"):
            mod.assess(d, SHA)
        d = full_candidate()
        d["monthly_ceiling_usd"] = 100.0
        with self.assertRaisesRegex(mod.InvalidCandidate, "ceiling"):
            mod.assess(d, SHA)

    def test_reject_wrong_sha_and_boolean_strings(self):
        d = full_candidate()
        self.assertFalse(mod.assess(d, "b" * 40)[0])
        d["providers"]["identity"]["payment_method_absent"] = "true"
        with self.assertRaisesRegex(mod.InvalidCandidate, "invalid"):
            mod.assess(d, SHA)

    def test_reject_duplicate_json_keys(self):
        with self.assertRaisesRegex(mod.InvalidCandidate, "duplicate"):
            json.loads('{"decision":"NO-GO","decision":"GO"}', object_pairs_hook=mod._unique_pairs)

    def test_cli_report_is_safe_and_never_says_authorized(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.json"
            path.write_text(json.dumps(full_candidate()), encoding="utf-8")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = mod.main(["--file", str(path), "--expected-sha", SHA])
            self.assertEqual(result, 0)
            self.assertIn("REVIEW_ONLY", stdout.getvalue())
            self.assertIn("NO-GO", stdout.getvalue())
            self.assertNotIn("authorized", stdout.getvalue().split("REVIEW_ONLY:")[0])

    def test_readiness_document_still_requires_owner_approval_and_restore(self):
        report = (ROOT / "docs/p01/2026-10-31-free-only-budget-candidate.md").read_text(encoding="utf-8")
        self.assertIn("P01 NO-GO / BLOCKED", report)
        self.assertIn("RPO <= 24h, RTO <= 24h", report)
        self.assertEqual(report.count("**Single next owner decision:**"), 1)
        self.assertIn("no resource creation", report)

    def test_empty_duplicate_or_bad_file_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.json"
            for body in ("", '{"x":', '{"decision":1,"decision":2}', "0"):
                path.write_text(body, encoding="utf-8")
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(mod.main(["--file", str(path), "--expected-sha", SHA]), 2)


if __name__ == "__main__":
    unittest.main()

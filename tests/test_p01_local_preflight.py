"""Behavioral fail-closed tests for combined P01 status; no provider access."""
from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p01_local_preflight as check  # noqa: E402

SHA = "a" * 40


def evidence(verified=False):
    return {"schema_version": 1, "gate": "P01", "decision": "NO-GO", "source_sha": SHA,
            "controls": {key: {"state": "VERIFIED" if verified else "UNVERIFIED",
                               "source_sha": SHA if verified else None,
                               "reviewer": "owner" if verified else None,
                               "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z") if verified else None,
                               "evidence_url": "https://github.com/x/repo/issues/1" if verified else None}
                         for key in check.REQUIRED_GATES}}


def billing(verified=False):
    return {"schema_version": 1, "decision": "NO-GO", "source_sha": SHA,
            "monthly_ceiling_usd": 100, "external_paid_services_absent": True if verified else None,
            "providers": {key: {"provider": name, "plan": plan,
                                **{f: True if verified else None for f in
                                   ("free_tier_confirmed", "payment_method_absent", "paid_addons_absent",
                                    "automatic_paid_upgrade_disabled", "no_unpaid_or_pending_charges")}}
                          for key, (name, plan) in {"web": ("render", "Free"),
                                                    "database": ("supabase", "Free"),
                                                    "identity": ("auth0", "Free")}.items()}}


class P01CombinedPreflightTests(unittest.TestCase):
    def test_unverified_fixture_never_passes_and_explains_all_gates(self):
        result = check.preflight(evidence(), billing(), SHA)
        self.assertEqual(result["decision"], "NO-GO")
        self.assertFalse(result["resource_creation_authorized"])
        self.assertFalse(result["complete_invoice_ceiling_verified"])
        self.assertEqual(len(result["controls"]), 7)
        self.assertTrue(all(row["result"] == "BLOCKED" for row in result["controls"]))
        self.assertEqual(len(result["budget_claim_blockers"]), 16)
        self.assertFalse(result["independent_attestation"])

    def test_complete_but_untrusted_claims_cannot_become_go(self):
        result = check.preflight(evidence(verified=True), billing(verified=True), SHA)
        self.assertEqual(result["evidence_completeness"], "REVIEW_ONLY_UNTRUSTED")
        self.assertEqual(result["free_only_account_claims"], "REVIEW_ONLY_UNTRUSTED")
        self.assertTrue(all(row["result"] == "CLAIM_ONLY_UNTRUSTED" for row in result["controls"]))
        self.assertEqual(result["decision"], "NO-GO")
        self.assertFalse(result["resource_creation_authorized"])

    def test_historical_sha_mismatch_cannot_be_silently_rebound(self):
        result = check.preflight(evidence(), billing(), "b" * 40)
        self.assertIn("source SHA does not match the checked revision", result["evidence_global_blockers"])
        self.assertIn("candidate source SHA mismatch", result["budget_claim_blockers"])
        self.assertEqual(result["decision"], "NO-GO")

    def test_invalid_or_malformed_claim_is_rejected(self):
        docs = [(dict(evidence(), decision="GO"), billing()),
                (evidence(), dict(billing(), monthly_ceiling_usd=101)),
                (evidence(), dict(billing(), providers={}))]
        for edoc, bdoc in docs:
            with self.subTest(inputs=(edoc["decision"], bdoc.get("monthly_ceiling_usd"))):
                with self.assertRaises(ValueError):
                    check.preflight(edoc, bdoc, SHA)

    def test_duplicate_key_and_oversized_json_fail(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "input.json"
            p.write_text('{"x":1,"x":2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                check.read_document(p, check.evidence_pairs)
            p.write_text("x" * 16385, encoding="utf-8")
            with self.assertRaises(ValueError):
                check.read_document(p, check.evidence_pairs)

    def test_cli_realistic_result_exit_is_one_not_zero(self):
        with tempfile.TemporaryDirectory() as d:
            p, q = Path(d) / "e.json", Path(d) / "b.json"
            p.write_text(json.dumps(evidence()), encoding="utf-8")
            q.write_text(json.dumps(billing()), encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                status = check.main(["--evidence", str(p), "--billing", str(q),
                                     "--expected-sha", SHA])
            self.assertEqual(status, 1)
            self.assertEqual(json.loads(out.getvalue())["decision"], "NO-GO")

    def test_cli_all_fake_complete_claims_still_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p, q = Path(d) / "e.json", Path(d) / "b.json"
            p.write_text(json.dumps(evidence(True)), encoding="utf-8")
            q.write_text(json.dumps(billing(True)), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(check.main(["--evidence", str(p), "--billing", str(q),
                                             "--expected-sha", SHA]), 1)

    def test_cli_missing_file_is_invalid_fail_closed(self):
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(check.main(["--evidence", "/does-not-exist.json",
                                         "--billing", "/also-missing.json",
                                         "--expected-sha", SHA]), 2)
        self.assertEqual(json.loads(output.getvalue())["decision"], "NO-GO")


if __name__ == "__main__":
    unittest.main()

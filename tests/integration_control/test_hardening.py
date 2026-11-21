"""Behavioral regression tests for additive integration-control hardening."""

from __future__ import annotations

import copy
import json
import unittest

from devobs.integration_control.hardening import (
    evaluate_hardened,
    harden_report,
)
from devobs.integration_control.report import render_report_json, validate_report
from devobs.integration_control.security import digest_payload

try:
    from . import helpers as h
    from . import hardening_fixtures as hf
except ImportError:  # unittest discover -s tests/integration_control
    import helpers as h
    import hardening_fixtures as hf


class IntegrationControlHardeningTests(unittest.TestCase):
    def test_manifest_digest_is_advisory_and_schema_valid(self) -> None:
        document = h.snapshot()

        report = evaluate_hardened(document)
        rendered = render_report_json(report)

        self.assertTrue(validate_report(report))
        self.assertEqual(report["decision"], "PROCEED_TO_HUMAN_REVIEW")
        self.assertFalse(report["merge_authorized"])
        self.assertEqual(report["human_approval"], "PENDING_HUMAN")
        codes = h.finding_codes(report)
        self.assertIn("HARDENING_MANIFEST_DIGEST", codes)
        self.assertNotIn("APPROVAL_EVIDENCE_MISSING", codes)
        self.assertIn("integration-control-hardening-v1", report["warnings"])
        self.assertEqual(json.loads(rendered), report)

    def test_missing_approval_evidence_is_unverified_not_authorized(self) -> None:
        document = h.snapshot()

        report = evaluate_hardened(document, approval_evidence=[])

        self.assertEqual(report["decision"], "UNVERIFIED")
        self.assertIn("APPROVAL_EVIDENCE_MISSING", h.finding_codes(report))
        self.assertIn("approval", report["checks"]["failed"])
        self.assertFalse(report["merge_authorized"])
        self.assertEqual(report["human_approval"], "PENDING_HUMAN")

    def test_invalid_approval_evidence_fails_closed(self) -> None:
        document = h.snapshot()

        report = evaluate_hardened(document, approval_evidence=[{"bad": "record"}])

        self.assertEqual(report["decision"], "BLOCKED")
        self.assertIn("APPROVAL_EVIDENCE_INVALID", h.finding_codes(report))
        self.assertIn("approval", report["checks"]["failed"])
        self.assertFalse(report["merge_authorized"])

    def test_valid_approval_evidence_is_advisory_only(self) -> None:
        document = h.snapshot()

        report = evaluate_hardened(
            document,
            approval_evidence=hf.complete_approval_set(),
        )

        codes = h.finding_codes(report)
        self.assertIn("APPROVAL_EVIDENCE_PRESENT", codes)
        self.assertNotIn("APPROVAL_EVIDENCE_MISSING", codes)
        self.assertEqual(report["decision"], "PROCEED_TO_HUMAN_REVIEW")
        self.assertFalse(report["merge_authorized"])
        self.assertEqual(report["human_approval"], "PENDING_HUMAN")
        self.assertTrue(validate_report(report))

    def test_rejected_approval_evidence_blocks(self) -> None:
        document = h.snapshot()
        records = hf.complete_approval_set()
        records[0] = hf.approval_record("merge", approval="REJECT")

        report = evaluate_hardened(document, approval_evidence=records)

        self.assertEqual(report["decision"], "BLOCKED")
        self.assertIn("APPROVAL_EVIDENCE_REJECTED", h.finding_codes(report))
        self.assertFalse(report["merge_authorized"])

    def test_restricted_action_gets_explicit_hardening_code(self) -> None:
        document = h.snapshot(coordination=h.manifest(
            h.task("ICP01", actions=["code_change", "merge"]),
        ))

        report = evaluate_hardened(document)

        codes = h.finding_codes(report)
        self.assertIn("SECURITY_POLICY_VIOLATION", codes)
        self.assertIn("UNAUTHORIZED_ACTION_REQUESTED", codes)
        self.assertEqual(report["decision"], "BLOCKED")
        self.assertIn("coordination", report["checks"]["failed"])

    def test_destructive_action_is_rejected(self) -> None:
        document = h.snapshot(coordination=h.manifest(
            h.task("ICP01", actions=["code_change", "delete"]),
        ))

        report = evaluate_hardened(document)

        self.assertIn("UNAUTHORIZED_ACTION_REQUESTED", h.finding_codes(report))
        self.assertEqual(report["decision"], "BLOCKED")

    def test_duplicate_retry_claims_are_blocked(self) -> None:
        document = h.snapshot(coordination=hf.duplicate_retry_manifest())

        report = evaluate_hardened(document)

        self.assertEqual(report["decision"], "BLOCKED")
        self.assertIn("UNSAFE_RETRY_LOOP", h.finding_codes(report))
        self.assertIn("RETRY_", str(report["components"]["evidence"]["accepted_ids"]))

    def test_prior_attempt_digest_prevents_retry_loop(self) -> None:
        document = h.snapshot()
        manifest_digest = digest_payload(copy.deepcopy(document["coordination"]))
        policy = hf.retry_policy(prior_attempt_digests=[manifest_digest])

        report = evaluate_hardened(document, retry_policy=policy)

        self.assertEqual(report["decision"], "BLOCKED")
        self.assertIn("UNSAFE_RETRY_LOOP", h.finding_codes(report))

    def test_invalid_retry_policy_fails_closed(self) -> None:
        document = h.snapshot()

        report = evaluate_hardened(document, retry_policy={"max_identical_retries": 0})

        self.assertEqual(report["decision"], "BLOCKED")
        self.assertIn("RETRY_POLICY_INVALID", h.finding_codes(report))

    def test_concurrent_ownership_is_preserved_under_hardening(self) -> None:
        first = h.task("HARD01", files=["devobs/integration_control/shared.py"])
        second = h.task("HARD02", agent="CODEX", branch="feature/other-agent",
                        files=["devobs/integration_control/shared.py"])
        first["verification"]["evidence"] = "first agent evidence"
        second["verification"]["evidence"] = "second agent evidence"
        document = h.snapshot(coordination=h.manifest(first, second))

        report = evaluate_hardened(document)

        codes = h.finding_codes(report)
        self.assertIn("CONCURRENT_FILE_OWNERSHIP", codes)
        self.assertIn("HARDENING_MANIFEST_DIGEST", codes)
        self.assertNotIn("UNSAFE_RETRY_LOOP", codes)
        self.assertEqual(report["decision"], "BLOCKED")

    def test_hardening_is_pure_and_idempotent(self) -> None:
        document = h.snapshot()
        original = copy.deepcopy(document)
        approval = hf.complete_approval_set()

        first = evaluate_hardened(document, approval_evidence=approval)
        second = harden_report(first, document, approval_evidence=approval)

        self.assertEqual(document, original)
        self.assertEqual(first, second)
        self.assertEqual(first["report_digest"], second["report_digest"])
        self.assertTrue(validate_report(second))

    def test_secret_material_never_enters_hardening_diagnostics(self) -> None:
        secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        document = h.snapshot(untrusted_text=secret)
        approval = hf.complete_approval_set()
        approval[0]["evidence_ids"] = [secret]

        report = evaluate_hardened(document, approval_evidence=approval)
        rendered = render_report_json(report)

        self.assertIn("APPROVAL_EVIDENCE_INVALID", h.finding_codes(report))
        self.assertNotIn(secret, rendered)
        self.assertTrue(validate_report(report))


if __name__ == "__main__":
    unittest.main()

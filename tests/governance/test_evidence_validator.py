"""Tests for evidence validation/redaction/fail-closed behavior."""
from __future__ import annotations

import json
import unittest

from devobs.governance.evidence_validator import EvidenceValidationError, validate_evidence


def base_evidence() -> dict:
    return {
        "pr": {
            "branch": "feature/pr-readiness-evidence-engine",
            "base": "main",
            "head_sha": "a" * 40,
            "title": "Test PR",
        },
        "required_checks": ["validate"],
        "checks": [
            {"name": "validate", "status": "completed", "conclusion": "success", "head_sha": "a" * 40},
        ],
        "security_evidence": [
            {"name": "bandit", "status": "pass", "head_sha": "a" * 40},
        ],
        "approvals": [
            {"actor": "alice", "state": "approved", "head_sha": "a" * 40, "source_type": "github_review", "verified": True},
        ],
        "required_approvals": 1,
        "protected_branch": True,
    }


class EvidenceValidatorTests(unittest.TestCase):
    def test_valid_evidence_normalizes(self):
        ev = validate_evidence(base_evidence())
        self.assertEqual(ev.head_sha, "a" * 40)
        self.assertEqual(ev.pr["branch"], "feature/pr-readiness-evidence-engine")
        self.assertEqual(len(ev.checks), 1)

    def test_malformed_json_rejected(self):
        with self.assertRaises(EvidenceValidationError):
            validate_evidence("{not-json")

    def test_invalid_branch_name_flagged(self):
        evidence = base_evidence()
        evidence["pr"]["branch"] = "bad branch name"
        ev = validate_evidence(evidence)
        codes = {i.code for i in ev.issues}
        self.assertIn("INVALID_BRANCH_NAME", codes)

    def test_stale_commit_sha_flagged(self):
        evidence = base_evidence()
        evidence["checks"][0]["head_sha"] = "b" * 40
        ev = validate_evidence(evidence)
        codes = {i.code for i in ev.issues}
        self.assertIn("STALE_CHECK_EVIDENCE", codes)

    def test_sensitive_data_redacted(self):
        evidence = base_evidence()
        evidence["pr"]["title"] = "leak ghp_abcdefghijklmnopqrstuvwxyz123456"
        evidence["checks"][0]["url"] = "https://x.test?token=secret-value"
        ev = validate_evidence(evidence)
        self.assertNotIn("ghp_", json.dumps(ev.as_dict()))
        self.assertNotIn("secret-value", json.dumps(ev.as_dict()))

    def test_untrusted_self_reported_approval_flagged(self):
        evidence = base_evidence()
        evidence["approvals"][0]["source_type"] = "self_reported"
        evidence["approvals"][0]["verified"] = False
        ev = validate_evidence(evidence)
        codes = {i.code for i in ev.issues}
        self.assertIn("UNTRUSTED_APPROVAL", codes)

    def test_missing_head_sha_flagged(self):
        evidence = base_evidence()
        evidence["pr"]["head_sha"] = ""
        ev = validate_evidence(evidence)
        codes = {i.code for i in ev.issues}
        self.assertIn("MISSING_SHA", codes)

    def test_required_approvals_must_be_non_negative_int(self):
        evidence = base_evidence()
        evidence["required_approvals"] = -1
        with self.assertRaises(EvidenceValidationError):
            validate_evidence(evidence)


if __name__ == "__main__":
    unittest.main()

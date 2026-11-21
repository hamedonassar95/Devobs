"""Regression tests for the deterministic PR readiness engine."""
from __future__ import annotations

import json
import unittest

from devobs.governance.pr_readiness import ReadinessState, evaluate_pr_readiness, render_markdown_report


def base_evidence() -> dict:
    return {
        "pr": {
            "branch": "feature/pr-readiness-evidence-engine",
            "base": "main",
            "head_sha": "a" * 40,
            "title": "Add readiness engine",
        },
        "required_checks": ["validate", "security"],
        "checks": [
            {"name": "validate", "status": "completed", "conclusion": "success", "head_sha": "a" * 40},
            {"name": "security", "status": "completed", "conclusion": "success", "head_sha": "a" * 40},
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


class PrReadinessEngineTests(unittest.TestCase):
    def test_fully_verified_pr_ready_for_human_review(self):
        report = evaluate_pr_readiness(base_evidence())
        self.assertEqual(report["state"], ReadinessState.READY_FOR_HUMAN_REVIEW)
        self.assertTrue(report["summary"])

    def test_failed_ci_blocks(self):
        evidence = base_evidence()
        evidence["checks"][0]["conclusion"] = "failure"
        report = evaluate_pr_readiness(evidence)
        self.assertEqual(report["state"], ReadinessState.BLOCKED)
        self.assertTrue(any(r["code"] == "FAILING_REQUIRED_CHECK" for r in report["reasons"]))

    def test_pending_ci_pending(self):
        evidence = base_evidence()
        evidence["checks"][1]["status"] = "in_progress"
        evidence["checks"][1]["conclusion"] = ""
        report = evaluate_pr_readiness(evidence)
        self.assertEqual(report["state"], ReadinessState.PENDING)

    def test_missing_security_evidence_unverified(self):
        evidence = base_evidence()
        evidence["security_evidence"] = []
        report = evaluate_pr_readiness(evidence)
        self.assertEqual(report["state"], ReadinessState.UNVERIFIED)
        self.assertTrue(any(r["code"] == "MISSING_SECURITY_EVIDENCE" for r in report["reasons"]))

    def test_invalid_branch_name_blocked(self):
        evidence = base_evidence()
        evidence["pr"]["branch"] = "main"
        report = evaluate_pr_readiness(evidence)
        self.assertEqual(report["state"], ReadinessState.BLOCKED)
        self.assertTrue(any(r["code"] == "INVALID_BRANCH_NAME" for r in report["reasons"]))

    def test_stale_commit_sha_blocks(self):
        evidence = base_evidence()
        evidence["checks"][0]["head_sha"] = "b" * 40
        report = evaluate_pr_readiness(evidence)
        self.assertEqual(report["state"], ReadinessState.BLOCKED)
        self.assertTrue(any("STALE" in r["code"] for r in report["reasons"]))

    def test_missing_approval_evidence_unverified(self):
        evidence = base_evidence()
        evidence["approvals"] = []
        report = evaluate_pr_readiness(evidence)
        self.assertEqual(report["state"], ReadinessState.UNVERIFIED)
        self.assertTrue(any(r["code"] == "MISSING_APPROVAL_EVIDENCE" for r in report["reasons"]))

    def test_malformed_json_unverified(self):
        report = evaluate_pr_readiness("{broken")
        self.assertEqual(report["state"], ReadinessState.UNVERIFIED)
        self.assertTrue(any(r["code"] == "MALFORMED_EVIDENCE" for r in report["reasons"]))

    def test_conflicting_evidence_blocks(self):
        evidence = base_evidence()
        evidence["checks"].append(
            {"name": "validate", "status": "completed", "conclusion": "failure", "head_sha": "a" * 40}
        )
        report = evaluate_pr_readiness(evidence)
        self.assertEqual(report["state"], ReadinessState.BLOCKED)
        self.assertTrue(any(r["code"] in {"CONFLICTING_CHECK_EVIDENCE", "DUPLICATE_CHECK"} for r in report["reasons"]))

    def test_unknown_github_status_unverified(self):
        evidence = base_evidence()
        evidence["checks"][0]["status"] = "mystery"
        evidence["checks"][0]["conclusion"] = ""
        report = evaluate_pr_readiness(evidence)
        self.assertEqual(report["state"], ReadinessState.UNVERIFIED)

    def test_duplicate_checks_blocked(self):
        evidence = base_evidence()
        evidence["checks"].append(
            {"name": "validate", "status": "completed", "conclusion": "success", "head_sha": "a" * 40}
        )
        report = evaluate_pr_readiness(evidence)
        self.assertEqual(report["state"], ReadinessState.BLOCKED)
        self.assertTrue(any(r["code"] == "DUPLICATE_CHECK" for r in report["reasons"]))

    def test_unauthorized_self_reported_approval_not_authoritative(self):
        evidence = base_evidence()
        evidence["approvals"][0] = {
            "actor": "author", "state": "approved", "head_sha": "a" * 40,
            "source_type": "self_reported", "verified": False,
        }
        report = evaluate_pr_readiness(evidence)
        self.assertNotEqual(report["state"], ReadinessState.READY_FOR_HUMAN_REVIEW)
        self.assertTrue(any(r["code"] in {"UNTRUSTED_APPROVAL", "MISSING_APPROVAL_EVIDENCE"} for r in report["reasons"]))

    def test_empty_evidence_unverified(self):
        report = evaluate_pr_readiness({"pr": {"branch": "", "head_sha": ""}, "required_checks": [], "checks": [], "security_evidence": [], "approvals": []})
        self.assertEqual(report["state"], ReadinessState.UNVERIFIED)

    def test_sensitive_data_redaction(self):
        evidence = base_evidence()
        evidence["pr"]["title"] = "contains ghp_abcdefghijklmnopqrstuvwxyz123456 and Bearer abc.def.ghi"
        report = evaluate_pr_readiness(evidence)
        dumped = json.dumps(report)
        self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz123456", dumped)
        self.assertNotIn("Bearer abc.def.ghi", dumped)
        self.assertIn("[REDACTED]", dumped)

    def test_existing_graphify_integration_compatibility(self):
        # Read-only compatibility check: graphify portfolio tests still importable and core files exist.
        from pathlib import Path
        repo = Path(__file__).resolve().parents[2]
        self.assertTrue((repo / "scripts" / "integrations" / "graphify_portfolio.py").exists())
        self.assertTrue((repo / "tests" / "test_graphify_portfolio.py").exists())
        # ensure readiness engine report is JSON-serializable and does not require graphify deps
        report = evaluate_pr_readiness(base_evidence())
        json.dumps(report)

    def test_markdown_report_contains_state_and_reasons(self):
        report = evaluate_pr_readiness(base_evidence())
        md = render_markdown_report(report)
        self.assertIn("READY_FOR_HUMAN_REVIEW", md)
        self.assertIn("Human approval is required", md)

    def test_never_ready_when_required_evidence_missing(self):
        evidence = base_evidence()
        del evidence["security_evidence"]
        report = evaluate_pr_readiness(evidence)
        self.assertNotEqual(report["state"], ReadinessState.READY_FOR_HUMAN_REVIEW)


if __name__ == "__main__":
    unittest.main()

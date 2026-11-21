"""Tests for PR readiness engine."""

from __future__ import annotations

import json
import unittest

from devobs.pr_readiness.policy import evaluate_pr_readiness
from devobs.pr_readiness.report import render_json_report, render_markdown_report
from devobs.pr_readiness.advisory import build_advisory
from devobs.pr_readiness.models import INSUFFICIENT_EVIDENCE


def base_evidence():
    sha = "a" * 40
    return {
        "pr": {
            "repository": "hamedonassar95/Devobs",
            "pr_number": 123,
            "base_branch": "main",
            "head_branch": "feature/pr-readiness-engine",
            "head_sha": sha,
            "reviewed_head_sha": sha,
            "mergeable": True,
            "merge_state": "clean",
        },
        "timestamps": {"evidence_collected_at": "2026-11-21T00:00:00Z"},
        "required_checks": ["validate", "security-scan"],
        "checks": [
            {"name": "validate", "status": "completed", "conclusion": "success", "head_sha": sha, "required": True},
            {"name": "security-scan", "status": "completed", "conclusion": "success", "head_sha": sha, "required": True},
        ],
        "security_findings": [
            {"tool": "bandit", "status": "pass", "severity": "none", "head_sha": sha},
        ],
        "dependency_results": [
            {"name": "pip-audit", "status": "passed", "head_sha": sha},
        ],
        "reviews": {"approved": True, "approvals_count": 1, "required_approvals": 1, "human_approval": True},
        "changed_files": ["devobs/pr_readiness/policy.py"],
        "ownership": {"owner": "agent-a", "active_agents": ["agent-a"], "file_owners": {"devobs/pr_readiness/policy.py": ["agent-a"]}},
    }


class PRReadinessPolicyTests(unittest.TestCase):
    def test_fully_verified_pr(self):
        report = evaluate_pr_readiness(base_evidence())
        self.assertEqual(report["readiness_decision"]["decision"], "READY_FOR_HUMAN_REVIEW")
        self.assertTrue(report["human_review_required"])

    def test_failed_ci(self):
        ev = base_evidence()
        ev["checks"][0]["conclusion"] = "failure"
        report = evaluate_pr_readiness(ev)
        self.assertEqual(report["readiness_decision"]["decision"], "BLOCKED")

    def test_pending_ci(self):
        ev = base_evidence()
        ev["checks"][0]["status"] = "in_progress"
        ev["checks"][0]["conclusion"] = ""
        report = evaluate_pr_readiness(ev)
        self.assertEqual(report["readiness_decision"]["decision"], "BLOCKED")

    def test_missing_required_checks(self):
        ev = base_evidence()
        ev["checks"] = [ev["checks"][0]]
        report = evaluate_pr_readiness(ev)
        self.assertEqual(report["readiness_decision"]["decision"], "INSUFFICIENT_EVIDENCE")
        self.assertTrue(any(f["code"] == "MISSING_REQUIRED_CHECK" for f in report["findings"]))

    def test_stale_commit_sha(self):
        ev = base_evidence()
        ev["pr"]["reviewed_head_sha"] = "b" * 40
        report = evaluate_pr_readiness(ev)
        self.assertEqual(report["readiness_decision"]["decision"], "POLICY_VIOLATION")
        self.assertTrue(any(f["code"] == "STALE_COMMIT_SHA" for f in report["findings"]))

    def test_conflicting_agent_ownership(self):
        ev = base_evidence()
        ev["ownership"]["file_owners"] = {"devobs/pr_readiness/policy.py": ["agent-a", "agent-b"]}
        report = evaluate_pr_readiness(ev)
        self.assertEqual(report["readiness_decision"]["decision"], "POLICY_VIOLATION")
        self.assertTrue(any(f["code"] == "CONCURRENT_FILE_OWNERSHIP" for f in report["findings"]))

    def test_missing_approval(self):
        ev = base_evidence()
        ev["reviews"] = {"approved": False, "approvals_count": 0, "required_approvals": 1, "human_approval": False}
        report = evaluate_pr_readiness(ev)
        self.assertEqual(report["readiness_decision"]["decision"], "INSUFFICIENT_EVIDENCE")

    def test_invalid_branch(self):
        ev = base_evidence()
        ev["pr"]["head_branch"] = "main"
        report = evaluate_pr_readiness(ev)
        self.assertEqual(report["readiness_decision"]["decision"], "POLICY_VIOLATION")
        self.assertTrue(any(f["code"] == "INVALID_BRANCH" for f in report["findings"]))

    def test_malformed_api_response(self):
        report = evaluate_pr_readiness({"pr": "not-an-object"})
        self.assertEqual(report["readiness_decision"]["decision"], "INSUFFICIENT_EVIDENCE")
        self.assertTrue(any(f["code"] == "MALFORMED_EVIDENCE" for f in report["findings"]))

    def test_unavailable_github_api(self):
        ev = base_evidence()
        ev["pr"]["mergeable"] = None
        ev["pr"]["merge_state"] = "unknown"
        report = evaluate_pr_readiness(ev)
        self.assertNotEqual(report["readiness_decision"]["decision"], "READY_FOR_HUMAN_REVIEW")
        self.assertTrue(any(f["code"] == "MERGEABILITY_UNAVAILABLE" for f in report["findings"]))

    def test_security_policy_violation(self):
        ev = base_evidence()
        ev["security_findings"] = [{"tool": "sast", "status": "fail", "severity": "high", "head_sha": "a" * 40}]
        report = evaluate_pr_readiness(ev)
        self.assertEqual(report["readiness_decision"]["decision"], "POLICY_VIOLATION")

    def test_concurrent_evidence_changes(self):
        ev = base_evidence()
        ev["checks"][0]["head_sha"] = "b" * 40
        report = evaluate_pr_readiness(ev)
        self.assertNotEqual(report["readiness_decision"]["decision"], "READY_FOR_HUMAN_REVIEW")

    def test_secret_redaction(self):
        ev = base_evidence()
        ev["security_findings"][0]["summary"] = "token ghp_abcdefghijklmnopqrstuvwxyz123456"
        report = evaluate_pr_readiness(ev)
        dumped = json.dumps(report)
        self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz123456", dumped)
        self.assertIn("[REDACTED]", dumped)

    def test_report_rendering_and_advisory(self):
        report = evaluate_pr_readiness(base_evidence())
        js = render_json_report(report)
        md = render_markdown_report(report)
        advisory = build_advisory(report)
        self.assertIn("READY_FOR_HUMAN_REVIEW", js)
        self.assertIn("PR Readiness Report", md)
        self.assertFalse(advisory["authoritative"])


if __name__ == "__main__":
    unittest.main()

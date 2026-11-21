import json
import unittest
from datetime import datetime, timezone

from devobs.portfolio_health.evaluator import evaluate_portfolio_health
from devobs.portfolio_health.report import render_json_report, render_markdown_report


NOW = datetime(2026, 11, 21, 12, 0, 0, tzinfo=timezone.utc)


def base_snapshot():
    return {
        "repository": "hamedonassar95/Devobs",
        "generated_at": "2026-11-21T12:00:00Z",
        "evidence": [
            {"evidence_id": "ev-ci", "source": "github-actions://run/1", "kind": "ci", "observed_at": "2026-11-21T11:59:00Z", "status": "FRESH", "sha": "a" * 40},
        ],
        "components": [{"name": "api", "status": "OK", "dependencies": [], "evidence_ids": ["ev-ci"]}],
        "ci_checks": [{"name": "unit", "status": "PASS", "required": True, "evidence_id": "ev-ci"}],
        "pull_requests": [{"number": 1, "title": "x", "head_sha": "a" * 40, "status": "OPEN", "draft": False, "approval_state": "APPROVED", "mergeable": "MERGEABLE", "blockers": [], "evidence_ids": ["ev-ci"]}],
        "ownership": {"status": "OK", "active_agents": [{"agent": "CODEX", "branch": "feature/a", "worktree": "wt/a", "owned_paths": ["devobs/a.py"]}]},
        "security_findings": [],
        "dependencies": [],
        "approval": {"status": "APPROVED", "human_approved": True, "approved_by": "human", "evidence_ids": ["ev-ap"]},
    }


class PortfolioHealthTests(unittest.TestCase):
    def test_ready_for_human_review(self):
        r = evaluate_portfolio_health(base_snapshot(), now=NOW)
        self.assertEqual(r["readiness"], "READY_FOR_HUMAN_REVIEW")
        self.assertTrue(r["advisory_only"])
        self.assertTrue(r["human_review_required"])

    def test_missing_or_stale_evidence(self):
        s = base_snapshot()
        s["evidence"] = [{"evidence_id": "ev-old", "source": "x", "kind": "ci", "observed_at": "2020-01-01T00:00:00Z"}]
        r = evaluate_portfolio_health(s, now=NOW)
        self.assertIn(r["readiness"], {"UNKNOWN", "BLOCKED", "DEGRADED"})
        self.assertTrue(any(f["code"] == "STALE_EVIDENCE" for f in r["findings"]))

    def test_conflicting_agent_ownership(self):
        s = base_snapshot()
        s["ownership"]["active_agents"].append({"agent": "OPENCODE", "branch": "feature/b", "worktree": "wt/b", "owned_paths": ["devobs/a.py"]})
        r = evaluate_portfolio_health(s, now=NOW)
        self.assertEqual(r["readiness"], "BLOCKED")
        self.assertTrue(any(f["code"] == "OWNERSHIP_CONFLICT" for f in r["findings"]))

    def test_failed_ci_checks(self):
        s = base_snapshot()
        s["ci_checks"] = [{"name": "unit", "status": "FAIL", "required": True, "evidence_id": "ev-ci", "log_excerpt": "FAILED tests/test_x.py - AssertionError"}]
        r = evaluate_portfolio_health(s, now=NOW)
        self.assertEqual(r["readiness"], "BLOCKED")
        self.assertTrue(any(f["code"] == "CI_CHECK_FAILED" for f in r["findings"]))

    def test_unavailable_integrations_unknown(self):
        s = base_snapshot()
        del s["ci_checks"]
        del s["evidence"]
        r = evaluate_portfolio_health(s, now=NOW)
        self.assertEqual(r["readiness"], "UNKNOWN")

    def test_malformed_input(self):
        r = evaluate_portfolio_health(["not", "an", "object"], now=NOW)
        self.assertEqual(r["readiness"], "UNKNOWN")
        self.assertTrue(any(f["code"] == "INVALID_INPUT" for f in r["findings"]))

    def test_secret_redaction(self):
        s = base_snapshot()
        s["security_findings"] = [{"id": "s1", "severity": "HIGH", "status": "OPEN", "component": "api", "message": "token=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"}]
        r = evaluate_portfolio_health(s, now=NOW)
        blob = json.dumps(r)
        self.assertNotIn("ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890", blob)
        self.assertIn("[REDACTED]", blob)

    def test_deterministic_scoring(self):
        s = base_snapshot()
        r1 = evaluate_portfolio_health(s, now=NOW)
        r2 = evaluate_portfolio_health(s, now=NOW)
        self.assertEqual(r1["score"], r2["score"])
        self.assertEqual(r1["readiness"], r2["readiness"])
        self.assertEqual([f["code"] for f in r1["findings"]], [f["code"] for f in r2["findings"]])

    def test_partial_provider_outages(self):
        s = base_snapshot()
        s["ci_checks"] = [{"name": "lint", "status": "UNKNOWN", "required": True}]
        r = evaluate_portfolio_health(s, now=NOW)
        self.assertEqual(r["readiness"], "UNKNOWN")
        self.assertTrue(any(f["code"] == "CI_CHECK_UNKNOWN" for f in r["findings"]))

    def test_duplicate_records(self):
        s = base_snapshot()
        s["evidence"].append(s["evidence"][0])
        r = evaluate_portfolio_health(s, now=NOW)
        self.assertEqual(r["readiness"], "UNKNOWN")
        self.assertTrue(any(f["code"] == "INVALID_INPUT" for f in r["findings"]))

    def test_incorrect_approval_claims(self):
        s = base_snapshot()
        s["approval"] = {"status": "APPROVED", "human_approved": True}
        r = evaluate_portfolio_health(s, now=NOW)
        self.assertEqual(r["readiness"], "UNKNOWN")
        self.assertTrue(any(f["code"] == "APPROVAL_CLAIM_UNVERIFIED" for f in r["findings"]))

    def test_reports_render(self):
        r = evaluate_portfolio_health(base_snapshot(), now=NOW)
        js = render_json_report(r)
        md = render_markdown_report(r)
        self.assertIn("readiness", js)
        self.assertIn("Integration Portfolio Health Dashboard", md)


if __name__ == "__main__":
    unittest.main()
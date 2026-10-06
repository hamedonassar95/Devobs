import unittest

from scripts.ai_investigator import (
    build_fallback_investigation,
    enforce_policy,
    render_markdown,
)


INCIDENT = {
    "schema_version": 1,
    "repository": "example/repo",
    "workflow": "Deployment Health Check",
    "conclusion": "failure",
    "run_id": "202",
    "run_url": "https://github.com/example/repo/actions/runs/202",
    "head_sha": "def456",
    "category": "production-verification",
    "severity": "critical",
    "recommended_action": "ROLLBACK_CANDIDATE",
    "rationale": "Production verification failed.",
    "failed_jobs": ["verify-production"],
    "automation_policy": {
        "allow_automatic_rollback": False,
        "allow_direct_push_to_main": False,
        "require_protected_pr_flow": True,
    },
}


class AIInvestigatorTests(unittest.TestCase):
    def test_fallback_produces_complete_recovery_contract(self):
        out = build_fallback_investigation(INCIDENT)
        self.assertEqual(out["source"], "deterministic_fallback")
        self.assertTrue(out["root_cause_hypotheses"])
        self.assertTrue(out["recommended_tests"])
        self.assertIn(
            out["decision"],
            {"FIX_FORWARD", "ROLLBACK", "MANUAL_REVIEW"},
        )
        self.assertTrue(out["recovery_plan"]["proposed_pr"]["title"])
        self.assertTrue(out["human_approval"]["required"])
        self.assertFalse(out["human_approval"]["approved"])

    def test_confidence_is_bounded(self):
        out = build_fallback_investigation(INCIDENT)
        self.assertGreaterEqual(out["decision_confidence"], 0)
        self.assertLessEqual(out["decision_confidence"], 1)
        for item in out["root_cause_hypotheses"]:
            self.assertGreaterEqual(item["confidence"], 0)
            self.assertLessEqual(item["confidence"], 1)

    def test_manual_review_triage_cannot_be_upgraded_by_ai(self):
        incident = dict(INCIDENT, recommended_action="MANUAL_REVIEW")
        candidate = build_fallback_investigation(INCIDENT)
        candidate["decision"] = "ROLLBACK"
        enforced = enforce_policy(incident, candidate)
        self.assertEqual(enforced["decision"], "MANUAL_REVIEW")
        self.assertIn("policy", enforced["decision_rationale"].lower())

    def test_fix_forward_triage_blocks_ai_rollback(self):
        incident = dict(INCIDENT, recommended_action="FIX_FORWARD")
        candidate = build_fallback_investigation(INCIDENT)
        candidate["decision"] = "ROLLBACK"
        enforced = enforce_policy(incident, candidate)
        self.assertEqual(enforced["decision"], "MANUAL_REVIEW")

    def test_markdown_exposes_human_gate(self):
        out = build_fallback_investigation(INCIDENT)
        markdown = render_markdown(out)
        self.assertIn("Human Approval Gate", markdown)
        self.assertIn("PENDING", markdown)
        self.assertIn("Proposed PR", markdown)


if __name__ == "__main__":
    unittest.main()

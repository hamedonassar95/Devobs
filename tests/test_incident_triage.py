import json
import tempfile
import unittest
from pathlib import Path

from scripts.incident_triage import build_incident, render_markdown


class IncidentTriageTests(unittest.TestCase):
    def test_ci_failure_recommends_fix_forward(self):
        incident = build_incident(
            workflow="CI",
            conclusion="failure",
            run_id="101",
            sha="abc123",
            run_url="https://github.com/example/repo/actions/runs/101",
            repository="example/repo",
            jobs={"jobs": [{"name": "validate", "conclusion": "failure"}]},
        )
        self.assertEqual(incident["category"], "validation")
        self.assertEqual(incident["severity"], "high")
        self.assertEqual(incident["recommended_action"], "FIX_FORWARD")
        self.assertEqual(incident["failed_jobs"], ["validate"])

    def test_health_check_failure_is_rollback_candidate(self):
        incident = build_incident(
            workflow="Deployment Health Check",
            conclusion="failure",
            run_id="202",
            sha="def456",
            run_url="https://github.com/example/repo/actions/runs/202",
            repository="example/repo",
            jobs={"jobs": [{"name": "verify-production", "conclusion": "failure"}]},
        )
        self.assertEqual(incident["category"], "production-verification")
        self.assertEqual(incident["severity"], "critical")
        self.assertEqual(incident["recommended_action"], "ROLLBACK_CANDIDATE")
        self.assertFalse(incident["automation_policy"]["allow_automatic_rollback"])

    def test_deploy_failure_requires_manual_review(self):
        incident = build_incident(
            workflow="Deploy Pages",
            conclusion="timed_out",
            run_id="303",
            sha="fed987",
            run_url="https://github.com/example/repo/actions/runs/303",
            repository="example/repo",
            jobs={"jobs": [{"name": "deploy", "conclusion": "timed_out"}]},
        )
        self.assertEqual(incident["category"], "deployment")
        self.assertEqual(incident["recommended_action"], "MANUAL_REVIEW")

    def test_cancelled_run_never_auto_rolls_back(self):
        incident = build_incident(
            workflow="Deployment Health Check",
            conclusion="cancelled",
            run_id="404",
            sha="aaa111",
            run_url="https://github.com/example/repo/actions/runs/404",
            repository="example/repo",
            jobs={"jobs": []},
        )
        self.assertEqual(incident["recommended_action"], "MANUAL_REVIEW")
        self.assertFalse(incident["automation_policy"]["allow_automatic_rollback"])

    def test_markdown_contains_evidence_and_guardrail(self):
        incident = build_incident(
            workflow="CI",
            conclusion="failure",
            run_id="505",
            sha="bbb222",
            run_url="https://github.com/example/repo/actions/runs/505",
            repository="example/repo",
            jobs={"jobs": [{"name": "validate", "conclusion": "failure"}]},
        )
        markdown = render_markdown(incident)
        self.assertIn("505", markdown)
        self.assertIn("validate", markdown)
        self.assertIn("FIX_FORWARD", markdown)
        self.assertIn("Automatic rollback: disabled", markdown)


if __name__ == "__main__":
    unittest.main()

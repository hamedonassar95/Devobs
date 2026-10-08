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
        self.assertEqual(incident["category"], "uncertain")
        self.assertEqual(incident["recommended_action"], "MANUAL_REVIEW")
        self.assertIn("Incident type: `uncertain`", render_markdown(incident))
        self.assertFalse(incident["automation_policy"]["allow_automatic_rollback"])

    def test_controlled_drill_is_classified_when_it_is_the_only_failure(self):
        incident = build_incident(
            workflow="CI",
            conclusion="failure",
            run_id="606",
            sha="ccc333",
            run_url="https://github.com/example/repo/actions/runs/606",
            repository="example/repo",
            jobs={"jobs": [{
                "name": "validate",
                "conclusion": "failure",
                "steps": [
                    {"name": "Checkout repository", "conclusion": "success"},
                    {
                        "name": "Controlled main-branch incident-response drill",
                        "conclusion": "failure",
                    },
                ],
            }]},
        )
        self.assertEqual(incident["category"], "controlled-drill")
        self.assertTrue(incident["controlled_drill"])
        self.assertEqual(incident["recommended_action"], "MANUAL_REVIEW")

    def test_additional_failed_step_keeps_ci_failure_as_validation(self):
        incident = build_incident(
            workflow="CI",
            conclusion="failure",
            run_id="607",
            sha="ddd444",
            run_url="https://github.com/example/repo/actions/runs/607",
            repository="example/repo",
            jobs={"jobs": [{
                "name": "validate",
                "conclusion": "failure",
                "steps": [
                    {
                        "name": "Controlled main-branch incident-response drill",
                        "conclusion": "failure",
                    },
                    {"name": "Post Checkout", "conclusion": "failure"},
                ],
            }]},
        )
        self.assertFalse(incident["controlled_drill"])
        self.assertEqual(incident["category"], "validation")
        self.assertEqual(incident["recommended_action"], "FIX_FORWARD")

    def test_additional_failed_job_keeps_ci_failure_as_validation(self):
        incident = build_incident(
            workflow="CI",
            conclusion="failure",
            run_id="608",
            sha="eee555",
            run_url="https://github.com/example/repo/actions/runs/608",
            repository="example/repo",
            jobs={"jobs": [
                {
                    "name": "validate",
                    "conclusion": "failure",
                    "steps": [{
                        "name": "Controlled main-branch incident-response drill",
                        "conclusion": "failure",
                    }],
                },
                {
                    "name": "lint",
                    "conclusion": "failure",
                    "steps": [{"name": "ruff", "conclusion": "failure"}],
                },
            ]},
        )
        self.assertFalse(incident["controlled_drill"])
        self.assertEqual(incident["category"], "validation")
        self.assertEqual(incident["recommended_action"], "FIX_FORWARD")

    def test_successful_report_is_not_labeled_as_workflow_failure(self):
        incident = build_incident(
            workflow="CI",
            conclusion="success",
            run_id="609",
            sha="fff666",
            run_url="https://github.com/example/repo/actions/runs/609",
            repository="example/repo",
            jobs={"jobs": [{"name": "validate", "conclusion": "success"}]},
        )
        markdown = render_markdown(incident)
        self.assertIn("Incident type: `healthy`", markdown)
        self.assertNotIn("Incident type: `workflow-failure`", markdown)

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

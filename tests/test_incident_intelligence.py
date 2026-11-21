"""Behavioral tests for the offline AI incident intelligence package."""
from __future__ import annotations

import json
import unittest

from devobs.incident_intelligence import (
    CATEGORY_CONFIGURATION,
    CATEGORY_DEPENDENCY,
    CATEGORY_INFRASTRUCTURE,
    CATEGORY_TEST,
    CATEGORY_TIMEOUT,
    CATEGORY_UNKNOWN,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    analyze_incident,
    analyze_workflow_run,
    render_summary,
)


class RecordingProvider:
    def __init__(self, result: str = "Human: inspect the pinned lockfile"):
        self.result = result
        self.prompts: list[str] = []

    def diagnose(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.result


class FailingProvider:
    def diagnose(self, prompt: str) -> str:
        raise RuntimeError("provider failed token=SECRET_PROVIDER_ERROR")


def incident(**overrides):
    payload = {
        "title": "nightly ci",
        "job": "build",
        "step": "Install",
        "logs": ["pip install failed: ResolutionImpossible for requests>=2"],
    }
    payload.update(overrides)
    return payload


def workflow_run(**overrides):
    run = {
        "id": 123,
        "name": "CI",
        "conclusion": "failure",
        "head_sha": "a" * 40,
        "head_branch": "feature/test",
        "repository": {"full_name": "hamedonassar95/Devobs"},
    }
    run.update(overrides)
    return run


def workflow_jobs(*items):
    return {"jobs": list(items)}


class IncidentIntelligenceTests(unittest.TestCase):
    def test_dependency_failure_produces_evidence_linked_high_confidence_hypothesis(self):
        report = analyze_incident(incident())

        self.assertEqual(report.category, CATEGORY_DEPENDENCY)
        self.assertEqual(report.confidence, CONFIDENCE_HIGH)
        self.assertEqual(len(report.hypotheses), 1)
        hypothesis = report.hypotheses[0]
        self.assertEqual(hypothesis.category, CATEGORY_DEPENDENCY)
        self.assertEqual(hypothesis.confidence, CONFIDENCE_HIGH)
        self.assertTrue(hypothesis.evidence_ids)
        self.assertEqual(
            set(hypothesis.evidence_ids),
            {evidence.id for evidence in report.evidence},
        )
        self.assertIn("dependency", report.summary.lower())

    def test_configuration_failure_is_classified_from_environment_error(self):
        report = analyze_incident(
            incident(
                job="deploy",
                step="Validate config",
                logs=["ConfigurationError: required environment variable DATABASE_URL is not set"],
            )
        )

        self.assertEqual(report.category, CATEGORY_CONFIGURATION)
        self.assertEqual(report.hypotheses[0].category, CATEGORY_CONFIGURATION)

    def test_timeout_failure_is_classified_separately_from_infrastructure(self):
        report = analyze_incident(
            incident(logs=["TimeoutError: ETIMEDOUT while waiting for package index"])
        )

        self.assertEqual(report.category, CATEGORY_TIMEOUT)
        self.assertEqual(report.hypotheses[0].category, CATEGORY_TIMEOUT)

    def test_test_failure_is_classified_from_assertion(self):
        report = analyze_incident(
            incident(logs=["FAILED tests/test_api.py::test_status - AssertionError: expected 200"])
        )

        self.assertEqual(report.category, CATEGORY_TEST)
        self.assertEqual(report.hypotheses[0].category, CATEGORY_TEST)

    def test_infrastructure_failure_is_classified_from_runner_signal(self):
        report = analyze_incident(
            incident(logs=["runner lost communication with the server"])
        )

        self.assertEqual(report.category, CATEGORY_INFRASTRUCTURE)
        self.assertEqual(report.hypotheses[0].category, CATEGORY_INFRASTRUCTURE)

    def test_unknown_failure_stays_unverified_and_does_not_invent_root_cause(self):
        report = analyze_incident(incident(logs=["something odd happened"]))

        self.assertEqual(report.category, CATEGORY_UNKNOWN)
        self.assertEqual(report.confidence, CONFIDENCE_LOW)
        self.assertIn("unverified", report.summary.lower())
        self.assertNotIn("root cause is", report.summary.lower())

    def test_secrets_are_redacted_from_every_report_surface(self):
        report = analyze_incident(
            incident(
                logs=[
                    "Authorization: Bearer ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890 "
                    "token=SUPERSECRET password=hunter2"
                ],
                metadata={"commit_message": "leak api_key=ANOTHERSECRET"},
            )
        )

        blob = json.dumps(report.to_dict())
        for secret in (
            "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
            "SUPERSECRET",
            "hunter2",
            "ANOTHERSECRET",
        ):
            self.assertNotIn(secret, blob)
        self.assertIn("[REDACTED]", blob)
        self.assertNotIn("SUPERSECRET", render_summary(report))

    def test_malformed_logs_fail_closed_with_warnings(self):
        report = analyze_incident(
            incident(logs=[123, None, {"unexpected": "shape"}], metadata="not-a-mapping")
        )

        self.assertEqual(report.category, CATEGORY_UNKNOWN)
        self.assertEqual(report.confidence, CONFIDENCE_LOW)
        self.assertTrue(report.warnings)
        self.assertIn("insufficient", report.summary.lower())

    def test_recommendations_are_advisory_and_require_human_approval(self):
        report = analyze_incident(incident())

        self.assertTrue(report.recommendations)
        for recommendation in report.recommendations:
            self.assertTrue(recommendation.requires_human_approval)
        self.assertFalse(report.guardrails["automatic_fixes"])
        self.assertTrue(report.guardrails["human_approval_required"])

    def test_ai_provider_is_disabled_by_default(self):
        report = analyze_incident(incident())

        self.assertEqual(report.ai_provider.status, "disabled")
        self.assertIn("disabled", report.ai_provider.summary.lower())
        self.assertEqual(report.category, CATEGORY_DEPENDENCY)

    def test_injected_ai_provider_is_advisory_and_receives_redacted_prompt(self):
        provider = RecordingProvider("AI note: inspect the pinned lockfile token=LEAKED_AI")

        report = analyze_incident(
            incident(logs=["pip install failed token=SUPERSECRET"]),
            ai_provider=provider,
        )

        self.assertEqual(len(provider.prompts), 1)
        self.assertNotIn("SUPERSECRET", provider.prompts[0])
        self.assertEqual(report.ai_provider.status, "available")
        self.assertIn("inspect the pinned lockfile", report.ai_provider.summary)
        self.assertNotIn("LEAKED_AI", json.dumps(report.to_dict()))
        self.assertEqual(report.category, CATEGORY_DEPENDENCY)

    def test_ai_provider_error_fails_closed_without_exposing_provider_text(self):
        report = analyze_incident(incident(), ai_provider=FailingProvider())

        self.assertEqual(report.ai_provider.status, "error")
        self.assertNotIn("SECRET_PROVIDER_ERROR", json.dumps(report.to_dict()))
        self.assertEqual(report.category, CATEGORY_DEPENDENCY)

    def test_workflow_run_reuses_ci_failure_intelligence_evidence(self):
        report = analyze_workflow_run(
            workflow_run(),
            workflow_jobs(
                {
                    "name": "python-tests",
                    "conclusion": "failure",
                    "steps": [
                        {
                            "name": "Run tests",
                            "conclusion": "failure",
                            "log": "FAILED tests/test_x.py::test_y - AssertionError: boom",
                        }
                    ],
                }
            ),
        )

        self.assertEqual(report.source, "github_actions")
        self.assertEqual(report.category, CATEGORY_TEST)
        self.assertTrue(
            any(evidence.source == "ci_failure_intelligence" for evidence in report.evidence)
        )

    def test_report_is_json_serializable_and_rendered_summary_is_human_readable(self):
        report = analyze_incident(incident())

        parsed = json.loads(json.dumps(report.to_dict()))
        self.assertEqual(parsed["category"], CATEGORY_DEPENDENCY)
        markdown = render_summary(report)
        self.assertIn("# Incident Intelligence Report", markdown)
        self.assertIn(CONFIDENCE_HIGH, markdown)
        self.assertIn("Human approval", markdown)


if __name__ == "__main__":
    unittest.main()

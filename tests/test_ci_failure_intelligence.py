"""Tests for read-only CI failure intelligence analyzer."""
from __future__ import annotations

import json
import unittest

from scripts.ci_failure_intelligence import (
    CATEGORY_AMBIGUOUS,
    CATEGORY_CODE,
    CATEGORY_INFRASTRUCTURE,
    FINDING_INFERRED,
    FINDING_UNVERIFIED,
    FINDING_VERIFIED,
    analyze_run,
    redact_secrets,
    render_markdown,
)


def run_meta(**overrides):
    base = {
        "id": 123,
        "name": "CI",
        "conclusion": "failure",
        "head_sha": "a" * 40,
        "head_branch": "feature/test",
        "html_url": "https://github.com/hamedonassar95/Devobs/actions/runs/123",
        "repository": {"full_name": "hamedonassar95/Devobs"},
        "head_commit": {"id": "a" * 40, "message": "test commit"},
    }
    base.update(overrides)
    return base


def jobs(*items):
    return {"jobs": list(items)}


class CIFailureIntelligenceTests(unittest.TestCase):
    def test_code_failure_classified_verified(self):
        report = analyze_run(
            run_meta(),
            jobs({
                "name": "python-tests",
                "conclusion": "failure",
                "steps": [{"name": "Run tests", "conclusion": "failure", "log": "FAILED tests/test_x.py::test_y - AssertionError: boom"}],
            }),
        )
        self.assertEqual(report["overall_category"], CATEGORY_CODE)
        f = report["top_findings"][0]
        self.assertEqual(f["confidence"], FINDING_VERIFIED)
        self.assertEqual(f["category"], CATEGORY_CODE)

    def test_infrastructure_failure_classified(self):
        report = analyze_run(
            run_meta(),
            jobs({
                "name": "build",
                "conclusion": "failure",
                "steps": [{"name": "Install", "conclusion": "failure", "log": "Could not resolve host: github.com\nETIMEDOUT"}],
            }),
        )
        self.assertEqual(report["overall_category"], CATEGORY_INFRASTRUCTURE)
        self.assertTrue(any(x["category"] == CATEGORY_INFRASTRUCTURE for x in report["top_findings"]))

    def test_repeated_signature_detected(self):
        step = {"name": "Test", "conclusion": "failure", "log": "AssertionError: same failure"}
        report = analyze_run(
            run_meta(),
            jobs(
                {"name": "job-a", "conclusion": "failure", "steps": [step]},
                {"name": "job-b", "conclusion": "failure", "steps": [step]},
            ),
        )
        self.assertTrue(report["repeated_signatures"])
        self.assertGreaterEqual(report["repeated_signatures"][0]["count"], 2)
        self.assertTrue(all(f["repeated"] for f in report["top_findings"]))

    def test_missing_logs_fail_closed_to_inferred_or_unverified(self):
        report = analyze_run(
            run_meta(),
            jobs({"name": "mystery", "conclusion": "failure", "steps": [{"name": "Unknown", "conclusion": "failure"}]}),
        )
        f = report["top_findings"][0]
        self.assertIn(f["confidence"], {FINDING_INFERRED, FINDING_UNVERIFIED})
        self.assertIn(f["category"], {CATEGORY_AMBIGUOUS, CATEGORY_CODE, CATEGORY_INFRASTRUCTURE})

    def test_missing_metadata_fail_closed(self):
        report = analyze_run(None, None)
        self.assertEqual(report["overall_category"], CATEGORY_AMBIGUOUS)
        self.assertTrue(any(f["confidence"] == FINDING_UNVERIFIED for f in report["top_findings"]))
        self.assertTrue(any("missing" in f["message"].lower() for f in report["top_findings"]))

    def test_secret_redaction(self):
        text = "Authorization: Bearer ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890 token=supersecret password=hunter2"
        redacted = redact_secrets(text)
        self.assertNotIn("supersecret", redacted)
        self.assertNotIn("hunter2", redacted)
        self.assertNotIn("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_report_redacts_secrets_from_logs(self):
        report = analyze_run(
            run_meta(head_commit={"id": "a" * 40, "message": "leak token=abc123"}),
            jobs({"name": "job", "conclusion": "failure", "steps": [{"name": "step", "conclusion": "failure", "log": "failure api_key=TOPSECRET"}]}),
        )
        blob = json.dumps(report)
        self.assertNotIn("TOPSECRET", blob)
        self.assertNotIn("abc123", blob)

    def test_commit_correlation(self):
        report = analyze_run(run_meta(head_sha="b" * 40), jobs({"name": "job", "conclusion": "failure", "steps": [{"name": "s", "conclusion": "failure", "log": "AssertionError"}]}))
        self.assertEqual(report["commit_correlation"]["head_sha"], "b" * 40)
        self.assertEqual(report["commit_correlation"]["confidence"], FINDING_VERIFIED)

    def test_ambiguous_failure_not_invented(self):
        report = analyze_run(run_meta(), jobs({"name": "job", "conclusion": "failure", "steps": [{"name": "s", "conclusion": "failure", "log": "something odd happened"}]}))
        f = report["top_findings"][0]
        self.assertEqual(f["category"], CATEGORY_AMBIGUOUS)
        self.assertEqual(f["confidence"], FINDING_UNVERIFIED)
        self.assertNotIn("root cause is", f["message"].lower())

    def test_markdown_and_json_outputs(self):
        report = analyze_run(run_meta(), jobs({"name": "job", "conclusion": "failure", "steps": [{"name": "s", "conclusion": "failure", "log": "AssertionError: x"}]}))
        md = render_markdown(report)
        self.assertIn("CI Failure Intelligence Report", md)
        self.assertIn("VERIFIED", md)
        js = json.dumps(report)
        parsed = json.loads(js)
        self.assertEqual(parsed["schema_version"], "1.0")

    def test_ai_summarizer_injectable(self):
        class FakeAI:
            def summarize(self, report):
                return "AI: check test assertion"
        report = analyze_run(run_meta(), jobs({"name": "job", "conclusion": "failure", "steps": [{"name": "s", "conclusion": "failure", "log": "AssertionError: x"}]}), ai_summarizer=FakeAI())
        self.assertEqual(report["ai_summary"]["status"], "available")
        self.assertIn("AI: check test assertion", report["ai_summary"]["text"])

    def test_ai_summarizer_error_fails_closed(self):
        class BadAI:
            def summarize(self, report):
                raise RuntimeError("boom token=SECRET")
        report = analyze_run(run_meta(), jobs({"name": "job", "conclusion": "failure", "steps": [{"name": "s", "conclusion": "failure", "log": "AssertionError: x"}]}), ai_summarizer=BadAI())
        self.assertEqual(report["ai_summary"]["status"], "error")
        self.assertNotIn("SECRET", report["ai_summary"]["text"])

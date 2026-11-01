"""Negative and positive tests for the offline Devobs ecosystem handoff preflight."""
import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from project_handoff_gate import evaluate  # noqa: E402


class ProjectHandoffGateTests(unittest.TestCase):
    def setUp(self):
        self.request = {
            "source": "phone-repair-assistant-v2",
            "destination": "al-dala-mobile",
            "artifact_type": "knowledge_package",
            "intent": "review",
            "classification": "public_redacted",
            "contains_customer_data": False,
            "contains_secrets": False,
            "technical_reviewed": True,
            "destination_owner_reviewed": True,
        }

    def test_review_candidate_never_automatically_approves(self):
        self.assertEqual(evaluate(self.request)["decision"], "REVIEW_ONLY")
        self.assertIn("independent", evaluate(self.request)["reason"])

    def test_devobs_ci_report_review_only(self):
        for destination in ("devobs-saas", "phone-repair-assistant-v2", "al-dala-mobile"):
            with self.subTest(destination=destination):
                r = {**self.request, "source": "devobs", "destination": destination,
                     "artifact_type": "ci_report", "technical_reviewed": False}
                self.assertEqual(evaluate(r)["decision"], "REVIEW_ONLY")

    def test_prohibited_actions_are_denied(self):
        for intent in ("publish", "deploy", "merge", "run", ""):
            with self.subTest(intent=intent):
                self.assertEqual(evaluate({**self.request, "intent": intent})["decision"], "DENY")

    def test_sensitive_data_is_denied(self):
        for field in ("contains_customer_data", "contains_secrets"):
            self.assertEqual(evaluate({**self.request, field: True})["decision"], "DENY")

    def test_unverified_or_private_classification_denied(self):
        for classification in ("private", "internal", "unreviewed", ""):
            self.assertEqual(evaluate({**self.request, "classification": classification})["decision"], "DENY")

    def test_missing_required_reviews_denied(self):
        for field in ("technical_reviewed", "destination_owner_reviewed"):
            self.assertEqual(evaluate({**self.request, field: False})["decision"], "DENY")

    def test_wrong_direction_and_unknown_route_denied(self):
        for source, dest, kind in (
            ("al-dala-mobile", "phone-repair-assistant-v2", "knowledge_package"),
            ("devobs-saas", "devobs", "ci_report"),
            ("devobs", "al-dala-mobile", "knowledge_package"),
        ):
            r = {**self.request, "source": source, "destination": dest, "artifact_type": kind}
            self.assertEqual(evaluate(r)["decision"], "DENY")

    def test_missing_extra_or_wrong_type_field_denied(self):
        missing = copy.deepcopy(self.request)
        missing.pop("contains_customer_data")
        for r in (None, [], missing, {**self.request, "token": "no"},
                  {**self.request, "contains_secrets": "false"},
                  {**self.request, "technical_reviewed": 1}):
            self.assertEqual(evaluate(r)["decision"], "DENY")

    def test_cli_fail_closed_on_bad_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "request.json"
            p.write_text("{garbage", encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/project_handoff_gate.py"),
                                     "--request", str(p)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["decision"], "DENY")

    def test_cli_review_returns_non_permission_result(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "request.json"
            p.write_text(json.dumps(self.request), encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/project_handoff_gate.py"),
                                     "--request", str(p)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["decision"], "REVIEW_ONLY")


if __name__ == "__main__":
    unittest.main()

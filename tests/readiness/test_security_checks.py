import json
import unittest

from tools.readiness.readiness_engine import evaluate_production_readiness


class ReadinessSecurityTests(unittest.TestCase):
    def test_secret_exposure_finding(self):
        s = {
            "repository": "hamedonassar95/Devobs",
            "cicd": {"required_checks": ["validate"], "observed_checks": {"validate": "PASS"}},
            "dependencies": {"components": [], "vulnerabilities": []},
            "security": {"secret_findings": [{"id": "leak-1", "severity": "HIGH"}]},
            "ownership": {"active_agents": []},
            "pull_requests": [],
            "deployment": {"approval_gate": True, "configs": []},
            "observability": {"logs": True, "metrics": True, "traces": True, "alerts": True},
            "tasks": [],
        }
        r = evaluate_production_readiness(s)
        self.assertEqual(r["status"], "BLOCKED")
        self.assertTrue(any(f["code"] == "SECRET_EXPOSURE_RISK" for f in r["findings"]))

    def test_secret_pattern_redacted(self):
        s = {
            "repository": "hamedonassar95/Devobs",
            "notes": "token=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
            "cicd": {"required_checks": [], "observed_checks": {}},
            "dependencies": {"components": [], "vulnerabilities": []},
            "security": {"secret_findings": []},
            "ownership": {"active_agents": []},
            "pull_requests": [],
            "deployment": {"approval_gate": True, "configs": []},
            "observability": {"logs": True, "metrics": True, "traces": True, "alerts": True},
            "tasks": [],
        }
        r = evaluate_production_readiness(s)
        blob = json.dumps(r)
        self.assertNotIn("ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890", blob)
        self.assertTrue(any(f["code"] == "SECRET_PATTERN_DETECTED" for f in r["findings"]))

    def test_ai_analysis_disabled_by_default(self):
        s = {
            "repository": "hamedonassar95/Devobs",
            "cicd": {"required_checks": ["validate"], "observed_checks": {"validate": "PASS"}},
            "dependencies": {"components": [], "vulnerabilities": []},
            "security": {"secret_findings": []},
            "ownership": {"active_agents": []},
            "pull_requests": [],
            "deployment": {"approval_gate": True, "configs": []},
            "observability": {"logs": True, "metrics": True, "traces": True, "alerts": True},
            "tasks": [],
            "ai_analysis": {"enabled": True, "provider": "openai", "authorized": False},
        }
        r = evaluate_production_readiness(s)
        self.assertEqual(r["ai_analysis"]["enabled"], False)
        self.assertTrue(any(f["code"] == "AI_ANALYSIS_UNAUTHORIZED" for f in r["findings"]))


if __name__ == "__main__":
    unittest.main()
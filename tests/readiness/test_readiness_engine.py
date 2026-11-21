import unittest

from tools.readiness.readiness_engine import evaluate_production_readiness


def base_snapshot():
    return {
        "repository": "hamedonassar95/Devobs",
        "cicd": {"required_checks": ["validate"], "observed_checks": {"validate": "PASS"}},
        "dependencies": {"components": [{"name": "api", "depends_on": []}], "vulnerabilities": []},
        "security": {"secret_findings": []},
        "ownership": {"active_agents": [{"agent": "A", "owned_paths": ["devobs/a.py"]}]},
        "pull_requests": [{"number": 1, "changed_files": ["devobs/a.py"], "missing_tests": False}],
        "deployment": {"approval_gate": True, "configs": [{"name": "prod", "allow_unauthenticated": False}]},
        "observability": {"logs": True, "metrics": True, "traces": True, "alerts": True},
        "tasks": [{"id": "t1", "fingerprint": "f1", "owner": "A"}],
    }


class ReadinessEngineTests(unittest.TestCase):
    def test_ready_for_human_review(self):
        r = evaluate_production_readiness(base_snapshot())
        self.assertEqual(r["status"], "READY_FOR_HUMAN_REVIEW")
        self.assertTrue(r["advisory_only"])

    def test_missing_required_ci_checks(self):
        s = base_snapshot(); s["cicd"]["observed_checks"] = {"validate": "MISSING"}
        r = evaluate_production_readiness(s)
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertTrue(any(f["code"] == "MISSING_REQUIRED_CI_CHECK" for f in r["findings"]))

    def test_conflicting_agent_file_ownership(self):
        s = base_snapshot(); s["ownership"]["active_agents"].append({"agent": "B", "owned_paths": ["devobs/a.py"]})
        r = evaluate_production_readiness(s)
        self.assertEqual(r["status"], "BLOCKED")
        self.assertTrue(any(f["code"] == "AGENT_OWNERSHIP_CONFLICT" for f in r["findings"]))

    def test_incomplete_dependency_graph(self):
        s = base_snapshot(); s["dependencies"]["components"] = [{"name": "api", "depends_on": ["missing"]}]
        r = evaluate_production_readiness(s)
        self.assertIn(r["status"], {"UNKNOWN", "BLOCKED", "DEGRADED"})
        self.assertTrue(any(f["code"] == "INCOMPLETE_DEPENDENCY_GRAPH" for f in r["findings"]))

    def test_unsafe_deployment_configuration(self):
        s = base_snapshot(); s["deployment"]["configs"][0]["allow_unauthenticated"] = True
        r = evaluate_production_readiness(s)
        self.assertEqual(r["status"], "BLOCKED")
        self.assertTrue(any(f["code"] == "UNSAFE_DEPLOYMENT_CONFIG" for f in r["findings"]))

    def test_missing_approval_gate(self):
        s = base_snapshot(); s["deployment"]["approval_gate"] = False
        r = evaluate_production_readiness(s)
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertTrue(any(f["code"] == "MISSING_APPROVAL_GATE" for f in r["findings"]))

    def test_invalid_configuration_file_input(self):
        r = evaluate_production_readiness("not-an-object")
        self.assertEqual(r["status"], "UNKNOWN")
        self.assertTrue(any(f["code"] == "INVALID_INPUT" for f in r["findings"]))

    def test_duplicate_task_execution(self):
        s = base_snapshot(); s["tasks"].append({"id": "t2", "fingerprint": "f1", "owner": "B"})
        r = evaluate_production_readiness(s)
        self.assertIn(r["status"], {"UNKNOWN", "BLOCKED", "DEGRADED"})
        self.assertTrue(any(f["code"] == "DUPLICATE_TASK_EXECUTION" for f in r["findings"]))


if __name__ == "__main__":
    unittest.main()
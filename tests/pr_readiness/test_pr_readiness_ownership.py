"""Additional ownership and boundary tests."""

from __future__ import annotations

import unittest

from devobs.pr_readiness.policy import evaluate_pr_readiness


def base_evidence():
    sha = "a" * 40
    return {
        "pr": {
            "repository": "hamedonassar95/Devobs",
            "pr_number": 1,
            "base_branch": "main",
            "head_branch": "feature/x",
            "head_sha": sha,
            "reviewed_head_sha": sha,
            "mergeable": True,
            "merge_state": "clean",
        },
        "timestamps": {"evidence_collected_at": "2026-11-21T00:00:00Z"},
        "required_checks": ["ci"],
        "checks": [{"name": "ci", "status": "completed", "conclusion": "success", "head_sha": sha}],
        "security_findings": [{"tool": "scan", "status": "pass", "severity": "none", "head_sha": sha}],
        "dependency_results": [{"name": "deps", "status": "passed", "head_sha": sha}],
        "reviews": {"approved": True, "approvals_count": 1, "required_approvals": 1, "human_approval": True},
        "changed_files": ["a.py"],
        "ownership": {"owner": "agent-a", "active_agents": ["agent-a"]},
    }


class PROwnershipBoundaryTests(unittest.TestCase):
    def test_task_manifest_conflict_blocks(self):
        ev = base_evidence()
        ev["ownership"]["task_manifest"] = {
            "schema_version": 1,
            "repositories": ["hamedonassar95/Devobs"],
            "agents": {"CODEX": {"enabled": True}, "OPENCODE": {"enabled": True}},
            "approval": {"merge": "pending_human", "deploy": "pending_human", "billing": "pending_human", "production": "pending_human"},
            "tasks": [
                {
                    "id": "TASK-001", "repository": "hamedonassar95/Devobs", "assigned_agent": "CODEX",
                    "branch": "feature/a", "affected_files": ["a.py"], "dependencies": [],
                    "status": "in_progress", "previous_status": "planned", "source_sha": "a" * 40,
                    "verification": {"commands": ["python -m unittest"], "result": "PENDING", "evidence": ""},
                    "pr_reference": None, "requested_actions": ["code_change"],
                },
                {
                    "id": "TASK-002", "repository": "hamedonassar95/Devobs", "assigned_agent": "OPENCODE",
                    "branch": "feature/b", "affected_files": ["a.py"], "dependencies": [],
                    "status": "in_progress", "previous_status": "planned", "source_sha": "b" * 40,
                    "verification": {"commands": ["python -m unittest"], "result": "PENDING", "evidence": ""},
                    "pr_reference": None, "requested_actions": ["code_change"],
                },
            ],
        }
        report = evaluate_pr_readiness(ev)
        self.assertEqual(report["readiness_decision"]["decision"], "POLICY_VIOLATION")
        self.assertTrue(any(f["code"] == "CONCURRENT_FILE_OWNERSHIP" for f in report["findings"]))

    def test_invalid_branch_name_policy_violation(self):
        ev = base_evidence()
        ev["pr"]["head_branch"] = "main"
        report = evaluate_pr_readiness(ev)
        self.assertEqual(report["readiness_decision"]["decision"], "POLICY_VIOLATION")

    def test_missing_dependency_evidence(self):
        ev = base_evidence()
        ev["dependency_results"] = []
        report = evaluate_pr_readiness(ev)
        self.assertEqual(report["readiness_decision"]["decision"], "INSUFFICIENT_EVIDENCE")

    def test_stale_validation_evidence(self):
        ev = base_evidence()
        ev["ownership"]["stale_evidence"] = True
        report = evaluate_pr_readiness(ev)
        self.assertEqual(report["readiness_decision"]["decision"], "POLICY_VIOLATION")


if __name__ == "__main__":
    unittest.main()

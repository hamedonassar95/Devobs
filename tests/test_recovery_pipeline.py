import unittest

from scripts.recovery_pipeline import evaluate


CHECKS = [
    "validate", "CodeQL", "Analyze (actions)", "Analyze (python)",
    "Analyze (javascript-typescript)",
]


def record():
    return {
        "planner": {
            "trusted_incident": True,
            "incident_open": True,
            "conclusion": "failure",
            "investigation_count": 1,
            "decision": "FIX_FORWARD",
            "confidence": 0.95,
            "reversible": True,
            "repository_scoped": True,
            "existing_recovery_pr": False,
            "proposed_change": "repair site validation",
        },
        "patch": {
            "planner_status": "UNTRUSTED_SHOULD_BE_OVERRIDDEN",
            "branch": "recovery/incident-123-fix-site-validation",
            "base_branch": "main",
            "files": ["index.html"],
        },
        "verification": {
            "planner_status": "UNTRUSTED_SHOULD_BE_OVERRIDDEN",
            "patch_guard_status": "UNTRUSTED_SHOULD_BE_OVERRIDDEN",
            "pr_state": "open",
            "draft": False,
            "merged": False,
            "base_branch": "main",
            "head_branch": "recovery/incident-123-fix-site-validation",
            "checks": [
                {"name": name, "status": "completed", "conclusion": "success"}
                for name in CHECKS
            ],
        },
        "approval": {
            "verification_status": "UNTRUSTED_SHOULD_BE_OVERRIDDEN",
            "approval": "APPROVE",
            "approver_is_human": True,
            "approver_has_write": True,
            "pr_open": True,
            "pr_merged": False,
        },
    }


class RecoveryPipelineTests(unittest.TestCase):
    def test_complete_pipeline_requires_human_approval(self):
        result = evaluate(record())
        self.assertTrue(result.authorized)
        self.assertEqual(result.status, "HUMAN_APPROVED")

    def test_blocks_at_8a(self):
        value = record()
        value["planner"]["trusted_incident"] = False
        result = evaluate(value)
        self.assertEqual(result.stage, "8A")
        self.assertFalse(result.authorized)

    def test_blocks_at_8b(self):
        value = record()
        value["patch"]["files"] = [".env.production"]
        result = evaluate(value)
        self.assertEqual(result.stage, "8B")
        self.assertFalse(result.authorized)

    def test_blocks_at_8c(self):
        value = record()
        value["verification"]["checks"][0]["conclusion"] = "failure"
        result = evaluate(value)
        self.assertEqual(result.stage, "8C")
        self.assertFalse(result.authorized)

    def test_stays_pending_without_human_approval(self):
        value = record()
        value["approval"]["approval"] = ""
        result = evaluate(value)
        self.assertEqual(result.stage, "8D")
        self.assertEqual(result.status, "PENDING")
        self.assertFalse(result.authorized)

    def test_human_rejection_is_terminal(self):
        value = record()
        value["approval"]["approval"] = "REJECT"
        result = evaluate(value)
        self.assertEqual(result.status, "REJECTED")
        self.assertFalse(result.authorized)

    def test_rejects_nonhuman_approval(self):
        value = record()
        value["approval"]["approver_is_human"] = False
        self.assertFalse(evaluate(value).authorized)

    def test_rejects_missing_stage(self):
        value = record()
        del value["verification"]
        result = evaluate(value)
        self.assertEqual(result.stage, "INPUT")
        self.assertFalse(result.authorized)

    def test_upstream_statuses_cannot_be_forged(self):
        value = record()
        value["patch"]["planner_status"] = "ELIGIBLE"
        value["verification"]["patch_guard_status"] = "ALLOW"
        value["planner"]["decision"] = "MANUAL_REVIEW"
        result = evaluate(value)
        self.assertEqual(result.stage, "8A")
        self.assertFalse(result.authorized)


if __name__ == "__main__":
    unittest.main()

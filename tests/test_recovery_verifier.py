import unittest

from scripts.recovery_verifier import evaluate


def record():
    names = [
        "validate", "CodeQL", "Analyze (actions)", "Analyze (python)",
        "Analyze (javascript-typescript)",
    ]
    return {
        "planner_status": "ELIGIBLE",
        "patch_guard_status": "ALLOW",
        "pr_state": "open",
        "draft": False,
        "merged": False,
        "base_branch": "main",
        "head_branch": "recovery/incident-123-fix-html-check",
        "checks": [
            {"name": name, "status": "completed", "conclusion": "success"}
            for name in names
        ],
    }


class RecoveryVerifierTests(unittest.TestCase):
    def test_verifies_complete_success(self):
        result = evaluate(record())
        self.assertTrue(result.verified)
        self.assertEqual(result.status, "VERIFIED")
        self.assertEqual(result.final_state, "PENDING HUMAN APPROVAL")

    def test_blocks_missing_planner_evidence(self):
        value = record()
        del value["planner_status"]
        self.assertFalse(evaluate(value).verified)

    def test_blocks_noneligible_plan(self):
        value = record()
        value["planner_status"] = "NOT_ELIGIBLE"
        self.assertFalse(evaluate(value).verified)

    def test_blocks_patch_guard_denial(self):
        value = record()
        value["patch_guard_status"] = "DENY"
        self.assertFalse(evaluate(value).verified)

    def test_blocks_merged_pr(self):
        value = record()
        value["merged"] = True
        self.assertFalse(evaluate(value).verified)

    def test_blocks_draft_pr(self):
        value = record()
        value["draft"] = True
        self.assertFalse(evaluate(value).verified)

    def test_blocks_wrong_base(self):
        value = record()
        value["base_branch"] = "release"
        self.assertFalse(evaluate(value).verified)

    def test_blocks_wrong_head(self):
        value = record()
        value["head_branch"] = "feature/not-recovery"
        self.assertFalse(evaluate(value).verified)

    def test_blocks_missing_required_check(self):
        value = record()
        value["checks"] = value["checks"][:-1]
        self.assertFalse(evaluate(value).verified)

    def test_blocks_pending_check(self):
        value = record()
        value["checks"][0]["status"] = "in_progress"
        value["checks"][0]["conclusion"] = ""
        self.assertFalse(evaluate(value).verified)

    def test_blocks_failed_check(self):
        value = record()
        value["checks"][0]["conclusion"] = "failure"
        self.assertFalse(evaluate(value).verified)

    def test_blocks_duplicate_required_check(self):
        value = record()
        value["checks"].append(dict(value["checks"][0]))
        self.assertFalse(evaluate(value).verified)

    def test_blocks_malformed_check(self):
        value = record()
        value["checks"] = ["validate"]
        self.assertFalse(evaluate(value).verified)


if __name__ == "__main__":
    unittest.main()

import unittest

from scripts.recovery_patch_guard import evaluate


def request():
    return {
        "planner_status": "ELIGIBLE",
        "branch": "recovery/incident-123-fix-html-check",
        "base_branch": "main",
        "files": ["index.html", "tests/test_site.py"],
    }


class RecoveryPatchGuardTests(unittest.TestCase):
    def test_allows_small_isolated_patch(self):
        result = evaluate(request())
        self.assertTrue(result.allowed)
        self.assertEqual(result.status, "ALLOW")
        self.assertEqual(result.final_state, "PENDING HUMAN APPROVAL")

    def test_requires_eligible_planner(self):
        value = request()
        value["planner_status"] = "NOT_ELIGIBLE"
        self.assertFalse(evaluate(value).allowed)

    def test_requires_main_as_base(self):
        value = request()
        value["base_branch"] = "release"
        self.assertFalse(evaluate(value).allowed)

    def test_rejects_non_recovery_branch(self):
        value = request()
        value["branch"] = "main"
        self.assertFalse(evaluate(value).allowed)

    def test_rejects_traversal(self):
        value = request()
        value["files"] = ["../SECURITY.md"]
        self.assertFalse(evaluate(value).allowed)

    def test_rejects_incident_workflow_mutation(self):
        value = request()
        value["files"] = [".github/workflows/incident-response.yml"]
        self.assertFalse(evaluate(value).allowed)

    def test_rejects_lock_workflow_mutation(self):
        value = request()
        value["files"] = [".github/workflows/incident-investigator.lock.yml"]
        self.assertFalse(evaluate(value).allowed)

    def test_rejects_secret_like_path(self):
        value = request()
        value["files"] = [".env.production"]
        self.assertFalse(evaluate(value).allowed)

    def test_rejects_large_patch_scope(self):
        value = request()
        value["files"] = [f"src/file-{i}.py" for i in range(11)]
        self.assertFalse(evaluate(value).allowed)

    def test_rejects_duplicate_paths(self):
        value = request()
        value["files"] = ["index.html", "index.html"]
        self.assertFalse(evaluate(value).allowed)


if __name__ == "__main__":
    unittest.main()

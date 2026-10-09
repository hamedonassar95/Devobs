import unittest

from scripts.recovery_patch_guard import evaluate


def request():
    return {
        "planner_status": "ELIGIBLE",
        "branch": "recovery/incident-123-fix-html-check",
        "base_branch": "main",
        "files": ["index.html", "assets/site.css"],
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

    def test_allows_nested_assets_paths(self):
        value = request()
        value["files"] = ["assets/css/site.css", "assets/images/logo.svg"]
        self.assertTrue(evaluate(value).allowed)

    def test_rejects_every_path_outside_initial_allowlist(self):
        for path in (
            "tests/test_site.py",
            "src/app.py",
            ".github/workflows/incident-response.yml",
            ".env.production",
            "SECURITY.md",
            "assets",
        ):
            with self.subTest(path=path):
                value = request()
                value["files"] = [path]
                self.assertFalse(evaluate(value).allowed)

    def test_rejects_noncanonical_asset_paths(self):
        for path in ("assets//site.css", "assets/../index.html", "assets/./site.css"):
            with self.subTest(path=path):
                value = request()
                value["files"] = [path]
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

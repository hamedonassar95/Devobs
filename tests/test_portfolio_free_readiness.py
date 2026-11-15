"""Offline, negative-first tests for candidate-only portfolio report."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_free_resource_plan import load_plan  # noqa: E402
from portfolio_free_readiness import CANDIDATES, load_candidates, validate_candidates  # noqa: E402


class PortfolioFreeReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = load_candidates()
        cls.resource_plan = load_plan()

    def invalid(self, changed, needle):
        errors = validate_candidates(changed, self.resource_plan)
        self.assertTrue(any(needle in e for e in errors), errors)

    def test_original_manifest_is_safe_but_not_runtime_proof(self):
        self.assertEqual(validate_candidates(self.original, self.resource_plan), [])
        self.assertEqual(len(self.original["projects"]), len(CANDIDATES))
        self.assertFalse(any(p["runtime_verified"] for p in self.original["projects"]))

    def test_rejects_all_activation_and_permission_promotions(self):
        for field in self.original["policy"]:
            with self.subTest(field=field):
                changed = copy.deepcopy(self.original)
                changed["policy"][field] = False if field == "owner_approval_required" else True
                self.assertTrue(validate_candidates(changed, self.resource_plan))

    def test_rejects_unknown_or_duplicate_project(self):
        changed = copy.deepcopy(self.original)
        changed["projects"][0]["id"] = "unreviewed-secret-repo"
        self.invalid(changed, "unknown or duplicate project")
        changed = copy.deepcopy(self.original)
        changed["projects"][1]["id"] = changed["projects"][0]["id"]
        self.invalid(changed, "unknown or duplicate project")

    def test_rejects_capability_expansion_and_duplicates(self):
        changed = copy.deepcopy(self.original)
        changed["projects"][0]["candidate_capabilities"].append("local-model-templates")
        self.invalid(changed, "unreviewed capability")
        changed = copy.deepcopy(self.original)
        changed["projects"][0]["candidate_capabilities"].append("ci")
        self.invalid(changed, "unreviewed capability")

    def test_rejects_claimed_connection_or_private_data(self):
        for key, value in (
            ("connection_state", "CONNECTED"),
            ("runtime_verified", True),
            ("private_data_processed", True),
        ):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.original)
                changed["projects"][0][key] = value
                self.assertTrue(validate_candidates(changed, self.resource_plan))

    def test_refuses_invalid_or_unauthorized_base_free_plan(self):
        changed_plan = copy.deepcopy(self.resource_plan)
        changed_plan["policy"]["paid_operations_allowed"] = True
        self.invalid_plan(changed_plan)
        changed_plan = copy.deepcopy(self.resource_plan)
        changed_plan["resources"].pop()
        self.invalid_plan(changed_plan)

    def invalid_plan(self, plan):
        errors = validate_candidates(self.original, plan)
        self.assertIn("free-resource preflight did not pass", errors)

    def test_duplicate_json_fields_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "duplicate.json"
            path.write_text('{"projects":[],"projects":[]}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                load_candidates(path)

    def test_missing_historical_snapshot_is_not_readiness(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIn(
                "historical portfolio evidence file missing",
                validate_candidates(self.original, self.resource_plan, Path(folder)),
            )

    def test_cli_reports_no_external_access_or_production_claims(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/portfolio_free_readiness.py"), "--json"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["status"], "MANIFEST_VALID_ONLY")
        self.assertEqual(result["project_candidates"], len(CANDIDATES))
        for key in (
            "external_repository_access_verified", "live_integration_verified",
            "production_ready", "paid_operations_authorized",
        ):
            self.assertIs(result[key], False)

    def test_cli_unknown_flags_fail_closed(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/portfolio_free_readiness.py"), "--activate"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        self.assertIn("FAIL:", proc.stderr)


if __name__ == "__main__":
    unittest.main()

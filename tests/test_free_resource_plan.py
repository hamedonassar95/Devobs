"""Fail-closed, offline behavioral tests for the free-only capability preflight."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_free_resource_plan import EXPECTED, load_plan, validate_plan  # noqa: E402


class FreeResourcePlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = load_plan()

    def test_committed_plan_matches_existing_checkout_only(self):
        self.assertEqual(validate_plan(self.original, ROOT), [])
        self.assertEqual(len(self.original["resources"]), len(EXPECTED))

    def test_zero_external_or_paid_authorizations(self):
        self.assertIs(self.original["policy"]["free_only"], True)
        for name, value in self.original["policy"].items():
            if name != "free_only":
                self.assertIs(value, False, name)

    def test_every_prohibited_promotion_is_rejected(self):
        for field in self.original["policy"]:
            with self.subTest(field=field):
                changed = copy.deepcopy(self.original)
                changed["policy"][field] = False if field == "free_only" else True
                self.assertTrue(validate_plan(changed, ROOT))

    def test_unknown_and_duplicate_resource_rejected(self):
        changed = copy.deepcopy(self.original)
        changed["resources"][0]["id"] = "new-commercial-cloud"
        self.assertTrue(validate_plan(changed, ROOT))
        changed = copy.deepcopy(self.original)
        changed["resources"][1]["id"] = changed["resources"][0]["id"]
        self.assertTrue(validate_plan(changed, ROOT))

    def test_substituted_paths_and_execution_modes_rejected(self):
        for field, value in (("path", "../private/secret"), ("execution_mode", "LIVE_HOSTED")):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.original)
                changed["resources"][0][field] = value
                self.assertTrue(validate_plan(changed, ROOT))

    def test_missing_files_fail_even_when_manifest_is_valid(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(validate_plan(self.original, Path(folder)))

    def test_symlink_cannot_be_used_as_verified_checkout_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / EXPECTED["ci"][0]
            target.parent.mkdir(parents=True, exist_ok=True)
            source = root / "fake.txt"
            source.write_text("not a repository workflow", encoding="utf-8")
            target.symlink_to(source)
            errors = validate_plan(self.original, root)
            self.assertTrue(any("unsafe: ci" in error for error in errors))

    def test_duplicate_json_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "dup.json"
            path.write_text('{"schema_version":1,"schema_version":2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                load_plan(path)

    def test_non_object_and_unknown_fields_fail(self):
        self.assertTrue(validate_plan([], ROOT))
        changed = copy.deepcopy(self.original)
        changed["unreviewed_provider"] = "new"
        self.assertTrue(validate_plan(changed, ROOT))


if __name__ == "__main__":
    unittest.main()

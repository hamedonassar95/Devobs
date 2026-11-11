"""Behavioral and negative validation for the P01 T07 trust-model contract."""
import copy
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_p01_threat_model import (  # noqa: E402
    DEFAULT,
    ThreatModelError,
    main,
    validate,
)


class P01ThreatModelTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(DEFAULT.read_text(encoding="utf-8"))

    def must_block(self, change):
        changed = copy.deepcopy(self.data)
        change(changed)
        with self.assertRaises(ThreatModelError):
            validate(changed)

    def test_offline_model_accepts_source_matrix_but_not_staging(self):
        validate(self.data)
        self.assertEqual(self.data["decision"], "NO-GO")
        self.assertEqual(len(self.data["abuse_cases"]), 12)

    def test_missing_database_trust_zone_is_rejected(self):
        self.must_block(lambda d: d["zones"].pop(4))

    def test_duplicate_zone_is_rejected(self):
        self.must_block(lambda d: d["zones"].__setitem__(4, d["zones"][0].copy()))

    def test_trust_boundary_rewire_is_rejected(self):
        self.must_block(lambda d: d["boundaries"][3].__setitem__("to", "provider"))

    def test_missing_cross_tenant_abuse_case_is_rejected(self):
        self.must_block(lambda d: d["abuse_cases"].pop(3))

    def test_duplicate_case_id_is_rejected(self):
        self.must_block(lambda d: d["abuse_cases"][3].__setitem__("id", "AC01"))

    def test_laundered_case_test_reference_is_rejected(self):
        self.must_block(lambda d: d["abuse_cases"][0].__setitem__(
            "test_reference", "../../private/credentials.py"))

    def test_nonexistent_candidate_test_is_rejected(self):
        self.must_block(lambda d: d["abuse_cases"][0].__setitem__(
            "test_reference", "tests/missing_evidence_fixture.py"))

    def test_false_live_acceptance_is_rejected(self):
        self.must_block(lambda d: d["abuse_cases"][0].__setitem__("status", "COMPLETE"))

    def test_provider_budget_overclaim_is_rejected(self):
        self.must_block(lambda d: d["budget"].__setitem__("enforcement_verified", True))

    def test_unapproved_staging_is_rejected(self):
        self.must_block(lambda d: d["actions"].__setitem__(
            "staging_provisioning_authorized", True))

    def test_unapproved_ai_action_is_rejected(self):
        self.must_block(lambda d: d["actions"].__setitem__(
            "autonomous_changes_authorized", True))

    def test_unknown_root_field_is_rejected(self):
        self.must_block(lambda d: d.__setitem__("skip_authentication", True))

    def test_cli_malformed_document_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            filename = pathlib.Path(temp) / "bad.json"
            filename.write_text("{invalid", encoding="utf-8")
            self.assertEqual(main(["--file", str(filename)]), 1)


if __name__ == "__main__":
    unittest.main()

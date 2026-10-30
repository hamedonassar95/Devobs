"""Negative evidence-gate tests; no provider, network, or deployment calls."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_p01_evidence", ROOT / "scripts" / "check_p01_evidence.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
SHA = "a" * 40
NOW = datetime(2026, 10, 30, 18, tzinfo=timezone.utc)


def example():
    return {
        "schema_version": 1,
        "gate": "P01",
        "decision": "NO-GO",
        "source_sha": SHA,
        "controls": {name: {"state": "UNVERIFIED", "source_sha": None, "reviewer": None,
                            "observed_at": None, "evidence_url": None} for name in gate.REQUIRED},
    }


def verified():
    obj = example()
    for entry in obj["controls"].values():
        entry.update(state="VERIFIED", source_sha=SHA, reviewer="owner",
                     observed_at="2026-10-30T18:00:00Z",
                     evidence_url="https://github.com/hamedonassar95/Devobs/actions/runs/41088292448")
    return obj


class P01EvidenceTests(unittest.TestCase):
    def assert_invalid(self, document, fragment):
        with self.assertRaisesRegex(gate.InvalidEvidence, fragment):
            gate.assess(document, SHA, NOW)

    def test_default_is_blocked(self):
        allowed, problems = gate.assess(example(), SHA, NOW)
        self.assertFalse(allowed)
        self.assertEqual(len(problems), 7)

    def test_cannot_claim_go(self):
        obj = verified()
        obj["decision"] = "GO"
        self.assert_invalid(obj, "automatic GO")

    def test_missing_required_control(self):
        obj = example()
        del obj["controls"]["budget_enforcement"]
        self.assert_invalid(obj, "required controls")

    def test_unknown_control_rejected(self):
        obj = example()
        obj["controls"]["override"] = {}
        self.assert_invalid(obj, "required controls")

    def test_bad_source_sha_blocks(self):
        obj = verified()
        obj["source_sha"] = "b" * 40
        allowed, blockers = gate.assess(obj, SHA, NOW)
        self.assertFalse(allowed)
        self.assertIn("source SHA", blockers[0])

    def test_control_mismatched_sha_blocks(self):
        obj = verified()
        obj["controls"]["identity_oidc"]["source_sha"] = "b" * 40
        allowed, blockers = gate.assess(obj, SHA, NOW)
        self.assertFalse(allowed)
        self.assertIn("identity_oidc", blockers[0])

    def test_expired_evidence_rejected(self):
        obj = verified()
        obj["controls"]["budget_enforcement"]["observed_at"] = "2026-08-01T00:00:00Z"
        self.assert_invalid(obj, "expired")

    def test_future_evidence_rejected(self):
        obj = verified()
        obj["controls"]["budget_enforcement"]["observed_at"] = "2026-11-01T00:00:00Z"
        self.assert_invalid(obj, "future")

    def test_untrusted_url_rejected(self):
        obj = verified()
        obj["controls"]["owner_approval"]["evidence_url"] = "https://x.example/item?token=hidden"
        self.assert_invalid(obj, "clean HTTPS")

    def test_unverified_cannot_hide_unexpected_fields(self):
        obj = example()
        obj["controls"]["owner_approval"]["approved"] = True
        self.assert_invalid(obj, "unexpected fields")

    def test_fully_populated_is_only_review_ready(self):
        allowed, blockers = gate.assess(verified(), SHA, NOW)
        self.assertTrue(allowed)
        self.assertEqual(blockers, [])

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(gate.InvalidEvidence, "duplicate"):
            json.loads('{"gate":"P01","gate":"P01"}', object_pairs_hook=gate._unique_pairs)

    def test_cli_default_data_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "evidence.json"
            file.write_text(json.dumps(example()), encoding="utf-8")
            self.assertEqual(gate.main(["--file", str(file), "--expected-sha", SHA]), 1)

    def test_cli_invalid_data_returns_distinct_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "evidence.json"
            file.write_text('{"gate":', encoding="utf-8")
            self.assertEqual(gate.main(["--file", str(file), "--expected-sha", SHA]), 2)


if __name__ == "__main__":
    unittest.main()

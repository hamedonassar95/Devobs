"""Synthetic evidence contracts; no external network or identities."""
import dataclasses
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from devobs_intelligence.contracts import EvidenceError, parse_event, parse_events


def valid_event():
    return {
        "schema_version": 1,
        "event_id": "delivery-01",
        "provider": "github",
        "project_ref": "org/private-repository",
        "source_sha": "a" * 40,
        "kind": "workflow_run",
        "observed_at": "2026-10-25T12:00:00Z",
        "evidence_digests": ["b" * 64],
    }


class ContractTests(unittest.TestCase):
    def test_canonical_deterministic_and_private(self):
        record = parse_event(valid_event())
        self.assertEqual(record.source_sha, "a" * 40)
        self.assertTrue(dataclasses.is_dataclass(record))
        self.assertEqual(record, parse_event(valid_event()))
        self.assertEqual(len(record.project_digest), 64)
        self.assertNotIn("private-repository", record.to_json())
        self.assertNotIn("org/private-repository", record.to_json())
        self.assertEqual(record.to_json(), parse_event(valid_event()).to_json())
        self.assertEqual(record.observed_at, "2026-10-25T12:00:00Z")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            record.event_id = "new"

    def test_invalid_sources_and_sha_fail_closed(self):
        for key, value in (("source_sha", "b" * 39), ("source_sha", "Z" * 40),
                           ("provider", "other"), ("kind", "deploy"),
                           ("event_id", "a/b"), ("observed_at", "yesterday")):
            with self.subTest(key=key, value=value), self.assertRaises(EvidenceError):
                event = valid_event()
                event[key] = value
                parse_event(event)

    def test_rejects_extra_fields_and_oversize_and_wrong_type(self):
        for change in ({"extra_secret": "not_for_output"},
                       {"project_ref": "x" * 2000},
                       {"evidence_digests": ["bad"]},
                       {"schema_version": True}):
            event = valid_event()
            event.update(change)
            with self.subTest(change=next(iter(change))), self.assertRaises(EvidenceError):
                parse_event(event)

    def test_rejects_naive_timestamp_and_invalid_calendar_date(self):
        for timestamp in ("2026-10-25T12:00:00", "2026-02-30T12:00:00Z", "2026-10-25T25:00:00Z"):
            with self.subTest(timestamp=timestamp), self.assertRaises(EvidenceError):
                event = valid_event()
                event["observed_at"] = timestamp
                parse_event(event)

    def test_duplicate_delivery_rejected_in_batch(self):
        with self.assertRaises(EvidenceError):
            parse_events([valid_event(), valid_event()])
        second = valid_event()
        second["event_id"] = "delivery-02"
        self.assertEqual(len(parse_events([valid_event(), second])), 2)

    def test_invalid_input_does_not_echo_secrets(self):
        with self.assertRaises(EvidenceError) as caught:
            parse_event({"secret": "FAKE_SECRET_FOR_TEST"})
        self.assertNotIn("FAKE_SECRET_FOR_TEST", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

"""Behavioral security tests: raw logs, secrets and hostile fields never pass."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from devobs_intelligence.safe_signal_adapter import (
    SafeSignalError, from_trusted_safe_signals,
)

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
SCOPE = {'tenant': 'alpha', 'project': 'platform', 'source_sha': 'a' * 40,
         'now_utc': NOW}


def event(kind='log', operation='ci.check', status='error', service='api', seconds=0,
          duration_ms=None):
    stamp = NOW + timedelta(seconds=seconds)
    payload = {'kind': kind, 'resource': {'service.name': service},
               'operation': operation, 'status': status,
               'time_unix_nano': int(stamp.timestamp()) * 1_000_000_000}
    if duration_ms is not None:
        payload['duration_ms'] = duration_ms
    return payload


class SafeSignalAdapterTests(unittest.TestCase):
    def test_safe_structured_log_produces_only_bounded_metadata(self):
        first = from_trusted_safe_signals([event()], **SCOPE)
        self.assertEqual(len(first), 1)
        item = first[0]
        self.assertEqual((item.kind, item.service, item.operation, item.status),
                         ('log', 'api', 'ci.check', 'error'))
        self.assertEqual((item.tenant, item.project, item.source_sha),
                         ('alpha', 'platform', 'a' * 40))
        self.assertEqual(len(item.evidence_digest), 64)
        self.assertNotIn('body', repr(item))

    def test_safe_trace_duration_and_canonical_order(self):
        records = [event(kind='trace', operation='http.request', status='ok',
                         service='web', seconds=-2, duration_ms=120),
                   event(status='ok', seconds=-10)]
        one = from_trusted_safe_signals(records, **SCOPE)
        two = from_trusted_safe_signals(list(reversed(records)), **SCOPE)
        self.assertEqual(one, two)
        self.assertEqual(one[0].service, 'api')
        self.assertEqual(one[1].duration_ms, 120)

    def test_never_accept_raw_body_attributes_or_pii(self):
        hostile = [
            event() | {'body': 'do not log my password=SECRET'},
            event() | {'attributes': {'user.email': 'person@example.test'}},
            event() | {'prompt': 'private chat'},
            event() | {'resource': {'service.name': 'api', 'user.id': '123'}},
            event(service='person@example.test'),
            event(operation='gen_ai.input.messages'),
            event(status='SECRET-customer-value'),
        ]
        for i, value in enumerate(hostile):
            with self.subTest(case=i), self.assertRaises(SafeSignalError):
                from_trusted_safe_signals([value], **SCOPE)

    def test_whole_batch_denied_if_any_record_is_unsafe(self):
        with self.assertRaises(SafeSignalError):
            from_trusted_safe_signals([event(), event() | {'body': 'secret'}],
                                      **SCOPE)

    def test_empty_oversized_and_wrong_type_batches_fail(self):
        for value in ([], {}, (), None, [event()] * 33):
            with self.subTest(value=type(value).__name__), self.assertRaises(
                    SafeSignalError):
                from_trusted_safe_signals(value, **SCOPE)

    def test_replay_and_duplicate_records_rejected(self):
        with self.assertRaisesRegex(SafeSignalError, '^duplicate_signal$'):
            from_trusted_safe_signals([event(), event()], **SCOPE)
        self.assertEqual(2, len(from_trusted_safe_signals([
            event(seconds=0), event(seconds=-1)], **SCOPE)))

    def test_freshness_exact_boundaries(self):
        for seconds in (-901, 61):
            with self.subTest(seconds=seconds), self.assertRaisesRegex(
                    SafeSignalError, '^stale_signal$'):
                from_trusted_safe_signals([event(seconds=seconds)], **SCOPE)
        for seconds in (-900, 60):
            self.assertEqual(1, len(from_trusted_safe_signals(
                [event(seconds=seconds)], **SCOPE)))

    def test_invalid_timestamp_and_duration_fail(self):
        bad = [event() | {'time_unix_nano': True},
               event() | {'time_unix_nano': 'today'},
               event(kind='trace', operation='http.request'),
               event(duration_ms=9),
               event(kind='trace', operation='http.request', duration_ms=-1),
               event(kind='trace', operation='http.request', duration_ms=600001),
               event(kind='trace', operation='http.request', duration_ms=True)]
        for i, value in enumerate(bad):
            with self.subTest(case=i), self.assertRaises(SafeSignalError):
                from_trusted_safe_signals([value], **SCOPE)

    def test_invalid_or_mismatched_trust_scope_denied(self):
        for changes in [
            {'tenant': 'user@example.test'}, {'project': '../private'},
            {'source_sha': 'not-a-sha'}, {'now_utc': NOW.replace(tzinfo=None)},
            {'now_utc': '2026-10-25'},
        ]:
            with self.subTest(case=str(changes)), self.assertRaises(
                    SafeSignalError):
                from_trusted_safe_signals([event()], **(SCOPE | changes))

    def test_unbounded_strings_and_nested_shapes_rejected(self):
        for value in [event(service='a'*5000),
                      event() | {'resource': []},
                      event() | {'resource': {'service.name': 10}},
                      event() | {'kind': ['log']},
                      event() | {'time_unix_nano': 0}]:
            with self.subTest(shape=str(type(value))), self.assertRaises(
                    SafeSignalError):
                from_trusted_safe_signals([value], **SCOPE)


if __name__ == '__main__':
    unittest.main()

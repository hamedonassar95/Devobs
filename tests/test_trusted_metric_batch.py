"""Safety boundaries for bounded, offline, authenticated metric batches."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from devobs_intelligence.context import ContextError
from devobs_intelligence.trusted_metric_batch import from_trusted_metric_batch

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
SHA = "a" * 40
ARGS = {"tenant": "alpha", "project": "platform", "source_sha": SHA, "now_utc": NOW}


def sample(name="error_rate_pct", value=7.5, service="api", offset=0):
    stamp = NOW + timedelta(seconds=offset)
    return {"resource": {"service.name": service}, "name": name, "value": value,
            "time_unix_nano": int(stamp.timestamp()) * 1_000_000_000}


class TrustedMetricBatchTests(unittest.TestCase):
    def test_order_independent_and_trusted_scope(self):
        metrics = [sample(service="web"), sample(name="failed_checks", value=1)]
        result = from_trusted_metric_batch(metrics, **ARGS)
        reverse = from_trusted_metric_batch(list(reversed(metrics)), **ARGS)
        self.assertEqual(result, reverse)
        self.assertEqual([(p.service, p.metric) for p in result],
                         [("api", "failed_checks"), ("web", "error_rate_pct")])
        self.assertTrue(all(p.tenant == "alpha" and p.project == "platform"
                            and p.source_sha == SHA for p in result))
        self.assertTrue(all(len(p.evidence_digest) == 64 for p in result))

    def test_batch_count_boundaries_fail_closed(self):
        for bad in ([], [sample()] * 33, {}, (sample(),), None):
            with self.subTest(kind=type(bad).__name__), self.assertRaisesRegex(
                    ContextError, "^invalid_metric_batch$"):
                from_trusted_metric_batch(bad, **ARGS)

    def test_duplicate_metric_rejected_even_when_timestamp_changes(self):
        with self.assertRaisesRegex(ContextError, "^duplicate_evidence$"):
            from_trusted_metric_batch([sample(), sample(offset=-1)], **ARGS)

    def test_time_windows_are_bounded(self):
        for offset in (-901, 61):
            with self.subTest(offset=offset), self.assertRaisesRegex(
                    ContextError, "^stale_evidence$"):
                from_trusted_metric_batch([sample(offset=offset)], **ARGS)
        for offset in (-900, 60):
            self.assertEqual(len(from_trusted_metric_batch([sample(offset=offset)], **ARGS)), 1)

    def test_clock_must_be_aware_utc_convertible(self):
        for clock in ("now", None, NOW.replace(tzinfo=None), 1):
            with self.subTest(clock=repr(clock)), self.assertRaisesRegex(
                    ContextError, "^invalid_metric_batch$"):
                from_trusted_metric_batch([sample()], **(ARGS | {"now_utc": clock}))

    def test_malicious_content_and_scope_override_fail(self):
        bad = [sample() | {"tenant": "beta"},
               sample() | {"resource": {"service.name": "api", "tenant": "beta"}},
               sample(name="gen_ai.input.messages", value="secret"),
               sample() | {"log_body": "secret"},
               sample(value=float("nan"))]
        for index, item in enumerate(bad):
            with self.subTest(case=index), self.assertRaises(ContextError):
                from_trusted_metric_batch([item], **ARGS)

    def test_no_partial_success_on_bad_element(self):
        with self.assertRaises(ContextError):
            from_trusted_metric_batch([sample(), sample(service="web") | {"token": "x"}], **ARGS)


if __name__ == "__main__":
    unittest.main()

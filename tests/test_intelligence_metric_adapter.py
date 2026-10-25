"""Trusted numeric telemetry snapshots; source scope cannot be supplied by metrics."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from devobs_intelligence.telemetry_adapter import from_trusted_metric
from devobs_intelligence.context import ContextError

TIME=1792886400000000000


def metric(**update):
    data={"resource":{"service.name":"api"},"name":"error_rate_pct",
          "value":7.5,"time_unix_nano":TIME}
    data.update(update)
    return data


class MetricBridgeTests(unittest.TestCase):
    def test_auth_scope_is_trusted_and_digest_stable(self):
        args={"tenant":"alpha","project":"platform","source_sha":"a"*40}
        first=from_trusted_metric(metric(),**args)
        second=from_trusted_metric(metric(),**args)
        self.assertEqual(first.tenant,"alpha")
        self.assertEqual(first.source_sha,"a"*40)
        self.assertEqual(first.evidence_digest,second.evidence_digest)

    def test_untrusted_resource_extra_rejected(self):
        with self.assertRaises(ContextError):
            from_trusted_metric(metric(resource={"service.name":"api","scope":"owner"}),
                                tenant="alpha",project="platform",source_sha="a"*40)

    def test_untrusted_extra_identity_rejected(self):
        with self.assertRaisesRegex(ContextError,"invalid_snapshot"):
            from_trusted_metric(metric(tenant="beta"),tenant="alpha",project="platform",
                                source_sha="a"*40)

    def test_raw_events_and_invalid_time_rejected(self):
        for bad in (metric(log_body="text"),metric(time_unix_nano=-1),
                    metric(time_unix_nano="not-clock"),metric(value=float("nan"))):
            with self.subTest(case=str(bad)[:70]),self.assertRaises(ContextError):
                from_trusted_metric(bad,tenant="alpha",project="platform",source_sha="a"*40)


if __name__=="__main__": unittest.main()

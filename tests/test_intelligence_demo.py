"""Synthetic integration test; no connectors, provider calls, or deployments."""
import contextlib
import io
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from devobs_intelligence.context import ContextError
from devobs_intelligence.incident_memory import IncidentMemory, IncidentRecord
from intelligence_demo import main, run_demo, _synthetic_incident_evidence
from devobs_intelligence.adviser import AdvisoryError

DEMO_NOW = datetime(2026, 10, 25, 0, 0, tzinfo=timezone.utc)


def _stamp(value):
    return value.astimezone(timezone.utc).isoformat(
        timespec='microseconds').replace('+00:00', 'Z')


def _approved_demo_memory(*, recorded_at=None):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )
    record = IncidentRecord(
        tenant='synthetic', project='demo', service='api',
        category='ci_failure', runbook_id='RB-CI-01', outcome='resolved',
        evidence_digest='c' * 64, source_sha='b' * 40,
        recorded_at=_stamp(recorded_at or DEMO_NOW - timedelta(minutes=5)),
    )
    payload = {
        'schema_version': 1,
        'approval_id': '1' * 32,
        'approver_id': 'curator-1',
        'approved_at': _stamp(DEMO_NOW - timedelta(minutes=1)),
        'expires_at': _stamp(DEMO_NOW + timedelta(hours=1)),
        'record': record.to_record(),
    }
    signature = private_key.sign(json.dumps(
        payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
        allow_nan=False,
    ).encode('utf-8')).hex()
    return IncidentMemory.from_approved_envelopes(
        [{**payload, 'signature': signature}],
        {('synthetic', 'demo', 'curator-1'): public_key},
        now=DEMO_NOW,
    )


class OfflineDemoTests(unittest.TestCase):
    def test_integrated_pipeline_is_review_only(self):
        result = run_demo()
        self.assertEqual(result['policy_decision'], 'PROPOSE_ONLY')
        self.assertEqual(result['proposal_status'], 'PENDING_HUMAN_APPROVAL')
        self.assertEqual(result['finding_status'], 'PENDING_HUMAN_APPROVAL')
        self.assertEqual(result['finding_category'], 'ci_failure')
        self.assertEqual(result['audit_records'], 2)
        self.assertEqual(result['memory_evidence_count'], 0)
        self.assertEqual(result['runbook_ids'], [])
        self.assertEqual(result['live_provider_calls'], 0)
        self.assertEqual(result['production_mutations'], 0)
        self.assertFalse(result['confidence_calibrated'])
        self.assertNotIn('synthetic/demo', repr(result))

    def test_demo_evidence_is_built_from_the_trusted_metric_batch(self):
        now = datetime(2026, 10, 25, 0, 0, tzinfo=timezone.utc)
        event, telemetry = _synthetic_incident_evidence(now_utc=now)
        self.assertEqual(len(telemetry), 2)
        by_metric = {point.metric: point for point in telemetry}
        self.assertEqual((by_metric['error_rate_pct'].tenant,
                          by_metric['error_rate_pct'].project),
                         ('synthetic', 'demo'))
        self.assertEqual((by_metric['error_rate_pct'].service,
                          by_metric['error_rate_pct'].value), ('api', 8.0))
        self.assertEqual((by_metric['failed_checks'].service,
                          by_metric['failed_checks'].value), ('api', 1))
        self.assertTrue(all(point.source_sha == 'a' * 40 for point in telemetry))
        self.assertTrue(all(event.source_sha == point.source_sha for point in telemetry))
        self.assertEqual(event.evidence_digests, tuple(sorted(
            point.evidence_digest for point in telemetry)))

    def test_demo_stops_when_trusted_batch_rejects_stale_evidence(self):
        now = datetime(2026, 10, 25, 0, 0, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ContextError, '^stale_evidence$'):
            _synthetic_incident_evidence(now_utc=now + timedelta(seconds=901))

    def test_demo_does_not_bypass_a_rejected_trusted_batch(self):
        with patch('intelligence_demo.from_trusted_metric_batch',
                   side_effect=ContextError('stale_evidence')):
            with self.assertRaisesRegex(ContextError, '^stale_evidence$'):
                run_demo()

    def test_demo_uses_only_current_approved_incident_memory(self):
        result = run_demo(incident_memory=_approved_demo_memory())
        self.assertEqual(result['memory_evidence_count'], 1)
        self.assertEqual(result['runbook_ids'], ['RB-CI-01'])

    def test_demo_ignores_approved_incident_memory_older_than_24_hours(self):
        stale_memory = _approved_demo_memory(
            recorded_at=DEMO_NOW - timedelta(days=1, seconds=1),
        )
        result = run_demo(incident_memory=stale_memory)
        self.assertEqual(result['memory_evidence_count'], 0)
        self.assertEqual(result['runbook_ids'], [])

    def test_demo_ignores_matching_but_unapproved_incident_memory(self):
        record = IncidentRecord(
            tenant='synthetic', project='demo', service='api',
            category='ci_failure', runbook_id='RB-CI-01', outcome='resolved',
            evidence_digest='c' * 64, source_sha='b' * 40,
            recorded_at=_stamp(DEMO_NOW - timedelta(minutes=5)),
        )
        result = run_demo(incident_memory=IncidentMemory([record]))
        self.assertEqual(result['memory_evidence_count'], 0)
        self.assertEqual(result['runbook_ids'], [])

    def test_kill_switch_blocks_demo_before_audit_write(self):
        with self.assertRaisesRegex(AdvisoryError, 'kill_switch_enabled'):
            run_demo(kill_switch=True)

    def test_cli_output_is_valid_private_safe_json(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            self.assertEqual(main(), 0)
        data = json.loads(stream.getvalue())
        self.assertEqual(data['mode'], 'synthetic_offline_demo')
        self.assertEqual(data['hypothesis'], 'ci_failure')
        self.assertEqual(data['memory_evidence_count'], 0)
        self.assertNotIn('token', stream.getvalue())


if __name__ == '__main__':
    unittest.main()

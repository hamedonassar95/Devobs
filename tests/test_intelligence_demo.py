"""Synthetic integration test; no connectors, provider calls, or deployments."""
import contextlib
import io
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from devobs_intelligence.context import ContextError
from intelligence_demo import main, run_demo, _synthetic_incident_evidence
from devobs_intelligence.adviser import AdvisoryError


class OfflineDemoTests(unittest.TestCase):
    def test_integrated_pipeline_is_review_only(self):
        result = run_demo()
        self.assertEqual(result['policy_decision'], 'PROPOSE_ONLY')
        self.assertEqual(result['proposal_status'], 'PENDING_HUMAN_APPROVAL')
        self.assertEqual(result['finding_status'], 'PENDING_HUMAN_APPROVAL')
        self.assertEqual(result['audit_records'], 2)
        self.assertEqual(result['live_provider_calls'], 0)
        self.assertEqual(result['production_mutations'], 0)
        self.assertFalse(result['confidence_calibrated'])
        self.assertNotIn('synthetic/demo', repr(result))

    def test_demo_evidence_is_built_from_the_trusted_metric_batch(self):
        now = datetime(2026, 10, 25, 0, 0, tzinfo=timezone.utc)
        event, telemetry = _synthetic_incident_evidence(now_utc=now)
        self.assertEqual(len(telemetry), 1)
        self.assertEqual((telemetry[0].tenant, telemetry[0].project),
                         ('synthetic', 'demo'))
        self.assertEqual((telemetry[0].service, telemetry[0].metric, telemetry[0].value),
                         ('api', 'error_rate_pct', 8.0))
        self.assertEqual(telemetry[0].source_sha, 'a' * 40)
        self.assertEqual(event.source_sha, telemetry[0].source_sha)
        self.assertEqual(event.evidence_digests, (telemetry[0].evidence_digest,))

    def test_demo_stops_when_trusted_batch_rejects_stale_evidence(self):
        now = datetime(2026, 10, 25, 0, 0, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ContextError, '^stale_evidence$'):
            _synthetic_incident_evidence(now_utc=now + timedelta(seconds=901))

    def test_demo_does_not_bypass_a_rejected_trusted_batch(self):
        with patch('intelligence_demo.from_trusted_metric_batch',
                   side_effect=ContextError('stale_evidence')):
            with self.assertRaisesRegex(ContextError, '^stale_evidence$'):
                run_demo()

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
        self.assertNotIn('token', stream.getvalue())


if __name__ == '__main__':
    unittest.main()

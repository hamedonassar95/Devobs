"""Synthetic integration test; no connectors, provider calls, or deployments."""
import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from intelligence_demo import main, run_demo
from devobs_intelligence.adviser import AdvisoryError


class OfflineDemoTests(unittest.TestCase):
    def test_integrated_pipeline_is_review_only(self):
        result = run_demo()
        self.assertEqual(result['policy_decision'], 'PROPOSE_ONLY')
        self.assertEqual(result['proposal_status'], 'PENDING_HUMAN_APPROVAL')
        self.assertEqual(result['audit_records'], 1)
        self.assertEqual(result['live_provider_calls'], 0)
        self.assertEqual(result['production_mutations'], 0)
        self.assertFalse(result['confidence_calibrated'])
        self.assertNotIn('synthetic/demo', repr(result))

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

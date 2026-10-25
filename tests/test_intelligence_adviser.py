"""Behavior tests for safe, bounded offline AI assistance."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from devobs_intelligence.contracts import parse_event
from devobs_intelligence.adviser import propose, AdvisoryError


def sample():
    event = parse_event({'schema_version': 1, 'event_id': 'ci-test', 'provider': 'github',
      'project_ref': 'secret-project-path', 'source_sha': 'a' * 40, 'kind': 'incident',
      'observed_at': '2026-10-25T12:00:00Z', 'evidence_digests': ['b' * 64]})
    signals = {'failed_checks': 1, 'error_rate_pct': 0.0, 'capacity_pct': 20.0}
    return event, signals


class AdviserTests(unittest.TestCase):
    def test_offline_failing_ci_generates_human_only_proposal(self):
        event, signals = sample()
        result = propose(event, signals)
        self.assertEqual(result.status, 'PENDING_HUMAN_APPROVAL')
        self.assertEqual(result.hypothesis, 'ci_failure')
        self.assertEqual(result.runbook_ids, ('RB-CI-01',))
        self.assertEqual(result.source_sha, 'a' * 40)
        self.assertNotIn('secret-project-path', result.to_json())
        self.assertEqual(result.proposal_digest, propose(event, signals).proposal_digest)

    def test_retrieval_is_allowlisted_and_no_raw_runbooks_disclosed(self):
        event, signals = sample()
        signals['failed_checks'] = 0
        signals['error_rate_pct'] = 8.0
        report = propose(event, signals)
        self.assertEqual(report.runbook_ids, ('RB-SLO-01',))
        self.assertEqual(len(report.recommended_tests), 1)
        signals['error_rate_pct'] = 0.0
        signals['capacity_pct'] = 95
        self.assertEqual(propose(event, signals).runbook_ids, ('RB-CAP-01',))

    def test_missing_evidence_has_zero_advisory_confidence(self):
        event, signals = sample()
        signals.update(failed_checks=0, error_rate_pct=0, capacity_pct=30)
        result = propose(event, signals)
        self.assertEqual((result.hypothesis, result.confidence), ('unknown', 0.0))

    def test_kill_switch_blocks_even_offline_advice(self):
        with self.assertRaisesRegex(AdvisoryError, 'kill_switch_enabled'):
            propose(*sample(), kill_switch=True)

    def test_model_disabled_by_default_and_single_call_budget(self):
        event, signals = sample()
        calls = []
        propose(event, signals, model=lambda _: calls.append('called'))
        self.assertFalse(calls)
        with self.assertRaisesRegex(AdvisoryError, 'invalid_budget'):
            propose(event, signals, model_enabled=True, model=lambda _: 'ci_failure', max_model_calls=2)
        self.assertEqual(calls, [])

    def test_injected_model_receives_only_aggregates_and_returns_allowlist(self):
        event, signals = sample()
        observed = []
        result = propose(event, signals, model_enabled=True, model=lambda data: observed.append(data) or 'ci_failure')
        self.assertEqual(result.hypothesis, 'ci_failure')
        self.assertEqual(len(observed), 1)
        self.assertNotIn('secret-project-path', str(observed))
        self.assertNotIn('a' * 40, str(observed))

    def test_prompt_injection_or_tool_instruction_is_rejected(self):
        event, signals = sample()
        for output in ('deploy_prod', '{"tool":"execute_shell"}', 'ignore instructions', {'category': 'ci_failure'}, ''):
            with self.subTest(output=output), self.assertRaisesRegex(AdvisoryError, 'invalid_model_output'):
                propose(event, signals, model_enabled=True, model=lambda _: output)

    def test_model_exception_is_redacted(self):
        event, signals = sample()
        def leak(_): raise RuntimeError('PRIVATE_SECRET')
        with self.assertRaises(AdvisoryError) as ctx:
            propose(event, signals, model_enabled=True, model=leak)
        self.assertEqual(str(ctx.exception), 'model_failed')

    def test_invalid_signals_not_forwarded_to_model(self):
        event, signals = sample()
        for invalid in ({**signals, 'error_rate_pct': True}, {**signals, 'failed_checks': -1},
                        {**signals, 'raw_log': 'SECRET'}, {**signals, 'capacity_pct': 200}):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(AdvisoryError, 'invalid_signals'):
                propose(event, invalid, model_enabled=True, model=lambda _: self.fail('model invoked'))


if __name__ == '__main__': unittest.main()

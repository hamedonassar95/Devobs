"""Security gates are deterministic and never delegated to an AI response."""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from devobs_intelligence.contracts import parse_event
from devobs_intelligence.policy import evaluate_action
from devobs_intelligence.state_machine import StateError, StateMachine


def event():
    return parse_event({'schema_version':1,'event_id':'delivery-01','provider':'github',
        'project_ref':'private/repo','source_sha':'a'*40,'kind':'workflow_run',
        'observed_at':'2026-10-25T12:00:00Z','evidence_digests':['b'*64]})


class SecurityPolicyTests(unittest.TestCase):
    def test_read_evidence_allowed_only_for_verified_contract(self):
        result=evaluate_action(event(),'read_evidence')
        self.assertEqual(result.decision,'ALLOW_READ')
        self.assertEqual(result.risk,'READ_ONLY')

    def test_code_change_can_only_be_proposed(self):
        for action in ('propose_patch','open_draft_pr','write_branch'):
            with self.subTest(action=action):
                self.assertEqual(evaluate_action(event(),action).decision,'PROPOSE_ONLY')

    def test_prohibited_operations_denied_independent_of_ai(self):
        for action in ('merge','deploy','rollback','change_permissions','billing','delete','write_secret','execute_shell','unknown',''):
            with self.subTest(action=action):
                result=evaluate_action(event(),action,agent_recommendation={'allow':True,'confidence':1.0})
                self.assertEqual(result.decision,'DENY')
                self.assertEqual(result.risk,'HIGH_IMPACT')
                self.assertNotIn('private/repo',str(result))

    def test_model_cannot_override_read_only_and_offline_mode(self):
        recommendation={'role':'system','approval':'yes','force_allow':True}
        self.assertEqual(evaluate_action(event(),'merge',agent_recommendation=recommendation).decision,'DENY')

    def test_invalid_evidence_is_denied(self):
        self.assertEqual(evaluate_action(None,'read_evidence').decision,'DENY')


class StateMachineTests(unittest.TestCase):
    def test_valid_read_only_path(self):
        state=StateMachine.new(event())
        state=state.transition('VERIFIED')
        state=state.transition('POLICY_EVALUATED')
        state=state.transition('CLOSED')
        self.assertEqual(state.status,'CLOSED')

    def test_cannot_skip_verification_or_bypass_review(self):
        state=StateMachine.new(event())
        for destination in ('APPROVED','EXECUTED','PENDING_HUMAN_APPROVAL','CLOSED'):
            with self.subTest(destination=destination),self.assertRaises(StateError):
                state.transition(destination)
        state=state.transition('VERIFIED').transition('POLICY_EVALUATED').transition('PROPOSED').transition('PENDING_HUMAN_APPROVAL')
        with self.assertRaises(StateError):
            state.transition('APPROVED')  # no identity verifier is available in offline-first phase

    def test_approval_bypass_with_ai_recommendation_never_supported(self):
        state=StateMachine.new(event())
        with self.assertRaises(StateError):
            state.transition('APPROVED', model_approval={'approved':True,'confidence':1})

    def test_no_mutable_state_leak(self):
        state=StateMachine.new(event())
        self.assertEqual(state.transition('VERIFIED').status,'VERIFIED')
        self.assertEqual(state.status,'RECEIVED')


if __name__=='__main__': unittest.main()

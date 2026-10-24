"""Deterministic control-plane policy. No model can grant capabilities."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import EventEnvelopeV1

_READ = frozenset({'read_evidence'})
_PROPOSE = frozenset({'propose_patch', 'open_draft_pr', 'write_branch'})


@dataclass(frozen=True)
class EvaluationV1:
    event_id: str
    policy_version: str
    decision: str
    risk: str
    reason_codes: tuple[str, ...]


def evaluate_action(event: EventEnvelopeV1 | None, action: str,
                    *, agent_recommendation: object = None) -> EvaluationV1:
    """Recommendation is deliberately unused as authorization evidence."""
    valid = type(event) is EventEnvelopeV1
    event_id = event.event_id if valid else 'unverified'
    if not valid:
        return EvaluationV1(event_id, 'devobs-policy-v1', 'DENY', 'HIGH_IMPACT', ('INVALID_EVIDENCE',))
    if type(action) is not str:
        return EvaluationV1(event_id, 'devobs-policy-v1', 'DENY', 'HIGH_IMPACT', ('UNKNOWN_ACTION',))
    if action in _READ:
        return EvaluationV1(event_id, 'devobs-policy-v1', 'ALLOW_READ', 'READ_ONLY', ('SCOPED_READ',))
    if action in _PROPOSE:
        return EvaluationV1(event_id, 'devobs-policy-v1', 'PROPOSE_ONLY', 'REVIEWABLE', ('HUMAN_APPROVAL_REQUIRED',))
    return EvaluationV1(event_id, 'devobs-policy-v1', 'DENY', 'HIGH_IMPACT', ('NO_EXECUTION_AUTHORITY',))

"""Offline immutable decision state; no trusted approval verifier is provisioned."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import EventEnvelopeV1

_ALLOWED = {
    'RECEIVED': frozenset({'VERIFIED', 'REJECTED', 'BLOCKED'}),
    'VERIFIED': frozenset({'POLICY_EVALUATED', 'REJECTED', 'BLOCKED'}),
    'POLICY_EVALUATED': frozenset({'PROPOSED', 'CLOSED', 'REJECTED', 'BLOCKED'}),
    'PROPOSED': frozenset({'PENDING_HUMAN_APPROVAL', 'REJECTED', 'BLOCKED'}),
    'PENDING_HUMAN_APPROVAL': frozenset({'REJECTED', 'BLOCKED'}),
    'APPROVED': frozenset(),   # Reserved until independently verified identity is implemented.
    'EXECUTED': frozenset(),
    'VERIFIED_OUTCOME': frozenset(),
    'REJECTED': frozenset(),
    'BLOCKED': frozenset(),
    'CLOSED': frozenset(),
}


class StateError(ValueError):
    """Safe fixed diagnostic only."""


@dataclass(frozen=True)
class StateMachine:
    status: str
    event_id: str
    source_sha: str

    @classmethod
    def new(cls, event: EventEnvelopeV1) -> StateMachine:
        if type(event) is not EventEnvelopeV1:
            raise StateError('invalid_event')
        return cls('RECEIVED', event.event_id, event.source_sha)

    def transition(self, destination: str, **_untrusted_hints) -> StateMachine:
        if type(destination) is not str or destination not in _ALLOWED.get(self.status, ()):
            raise StateError('transition_denied')
        return StateMachine(destination, self.event_id, self.source_sha)

"""Explicit, fail-closed advisory approval states.

This engine never executes a remediation. It only classifies whether an action
is forbidden, pending, rejected, approved, or needs no approval for a read-only
diagnostic step. An ``APPROVED`` decision is not an execution instruction.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import (
    APPROVAL_APPROVED,
    APPROVAL_FORBIDDEN,
    APPROVAL_NOT_REQUIRED,
    APPROVAL_PENDING,
    APPROVAL_REJECTED,
    ApprovalDecision,
    ApprovalError,
)

PROHIBITED_ACTIONS = frozenset({
    "production_deployment",
    "infrastructure_modification",
    "secret_rotation",
    "resource_deletion",
    "pull_request_merge",
    "billing_operation",
})
DIAGNOSTIC_ACTIONS = frozenset({
    "collect_sanitized_logs",
    "inspect_configuration",
    "reproduce_locally",
    "verify_health_evidence",
})
INCIDENT_CLOSURE = "incident_closure"


@dataclass(frozen=True)
class ApprovalRecord:
    """A caller-supplied human approval record; no signature is inferred here."""

    action_id: str
    action: str
    state: str
    approver: str
    scope: str
    evidence_ids: tuple[str, ...] = ()
    recorded_at: str = ""


class ApprovalEngine:
    """Evaluate advisory actions with closed states and no execution path."""

    def evaluate(
        self,
        action_id: str,
        action: str,
        *,
        records: tuple[ApprovalRecord, ...] = (),
        evidence_ids: tuple[str, ...] = (),
        scope: str = "offline",
    ) -> ApprovalDecision:
        if action in PROHIBITED_ACTIONS:
            return ApprovalDecision(
                action_id=action_id,
                action=action,
                state=APPROVAL_FORBIDDEN,
                requires_human=True,
                rationale="Action class is forbidden to autonomous agents.",
                evidence_ids=evidence_ids,
            )
        if action == INCIDENT_CLOSURE and not evidence_ids:
            return ApprovalDecision(
                action_id=action_id,
                action=action,
                state=APPROVAL_FORBIDDEN,
                requires_human=True,
                rationale="Incident closure without evidence is forbidden.",
                evidence_ids=evidence_ids,
            )
        if action in DIAGNOSTIC_ACTIONS:
            return ApprovalDecision(
                action_id=action_id,
                action=action,
                state=APPROVAL_NOT_REQUIRED,
                requires_human=False,
                rationale="Read-only diagnostic step; no approval is required.",
                evidence_ids=evidence_ids,
            )

        relevant = tuple(
            item for item in records
            if item.action_id == action_id and item.action == action and item.scope == scope
        )
        if any(item.state == APPROVAL_APPROVED and set(evidence_ids).issubset(set(item.evidence_ids))
               for item in relevant):
            return ApprovalDecision(
                action_id=action_id,
                action=action,
                state=APPROVAL_APPROVED,
                requires_human=True,
                rationale="Explicit matching human approval record was supplied.",
                evidence_ids=evidence_ids,
            )
        if any(item.state == APPROVAL_REJECTED for item in relevant):
            return ApprovalDecision(
                action_id=action_id,
                action=action,
                state=APPROVAL_REJECTED,
                requires_human=True,
                rationale="Explicit human rejection record was supplied.",
                evidence_ids=evidence_ids,
            )
        return ApprovalDecision(
            action_id=action_id,
            action=action,
            state=APPROVAL_PENDING,
            requires_human=True,
            rationale="No matching human approval record was supplied; fail closed.",
            evidence_ids=evidence_ids,
        )

    def require_approval(self, decision: ApprovalDecision) -> None:
        """Fail closed if an action is not explicitly allowed by its state."""
        if decision.state == APPROVAL_FORBIDDEN:
            raise ApprovalError("approval_forbidden")
        if decision.state == APPROVAL_REJECTED:
            raise ApprovalError("approval_rejected")
        if decision.state == APPROVAL_PENDING:
            raise ApprovalError("approval_pending")


__all__ = [
    "DIAGNOSTIC_ACTIONS",
    "INCIDENT_CLOSURE",
    "PROHIBITED_ACTIONS",
    "ApprovalEngine",
    "ApprovalRecord",
]

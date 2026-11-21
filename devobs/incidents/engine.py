"""Offline-first orchestration for the incident intelligence engine.

The engine intentionally has no execution path. It ingests sanitized evidence,
classifies it with deterministic rules, correlates bounded findings, builds a
schema-validated report, and emits local structured events.
"""
from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from typing import Any

from devobs.incident_intelligence.analyzer import AIProvider

from .approval import (
    DIAGNOSTIC_ACTIONS,
    ApprovalEngine,
    ApprovalRecord,
)
from .classification import classify_records
from .ingestion import MAX_ITEMS, ingest_incident
from .models import (
    CATEGORY_AUTHENTICATION_CONFIGURATION,
    CATEGORY_CI_CONFIGURATION_FAILURE,
    CATEGORY_CONTAINER_BUILD_FAILURE,
    CATEGORY_DEPENDENCY_FAILURE,
    CATEGORY_INFRASTRUCTURE_CONFIGURATION,
    CATEGORY_SERVICE_HEALTH_FAILURE,
    CATEGORY_TEST_FAILURE,
    CATEGORY_UNKNOWN_FAILURE,
    AdvisoryRecommendation,
    ApprovalDecision,
    ClassificationResult,
    EngineReport,
    IncidentEngineError,
    IncidentRecord,
)
from .observability import (
    APPROVAL_REQUIRED,
    CLASSIFICATION_COMPLETED,
    EVIDENCE_MISSING,
    INCIDENT_RECEIVED,
    REPORT_GENERATED,
    VALIDATION_COMPLETED,
    EventSink,
    emit_events,
)
from .rca import correlate_incidents
from .reports import build_engine_report, render_engine_json

REMEDIATION_PLANNING = "prepare_remediation_plan"

_CATEGORY_DIAGNOSTIC_ACTION = {
    CATEGORY_CI_CONFIGURATION_FAILURE: "inspect_configuration",
    CATEGORY_TEST_FAILURE: "reproduce_locally",
    CATEGORY_DEPENDENCY_FAILURE: "inspect_configuration",
    CATEGORY_CONTAINER_BUILD_FAILURE: "inspect_configuration",
    CATEGORY_AUTHENTICATION_CONFIGURATION: "inspect_configuration",
    CATEGORY_INFRASTRUCTURE_CONFIGURATION: "inspect_configuration",
    CATEGORY_SERVICE_HEALTH_FAILURE: "verify_health_evidence",
    CATEGORY_UNKNOWN_FAILURE: "collect_sanitized_logs",
}
_REMEDIATION_VERIFICATION = (
    "A human owner must review the evidence references and approve any change "
    "through the existing change process before execution."
)


class IncidentIntelligenceEngine:
    """Coordinate offline incident analysis without executing remediation."""

    def __init__(
        self,
        *,
        ai_provider: AIProvider | None = None,
        event_sinks: Iterable[EventSink] = (),
        approval_records: Iterable[ApprovalRecord] = (),
        approval_scope: str = "offline",
        max_incidents: int = MAX_ITEMS,
    ) -> None:
        if type(max_incidents) is not int or not 1 <= max_incidents <= MAX_ITEMS:
            raise IncidentEngineError("invalid_max_incidents")
        if type(approval_scope) is not str or not approval_scope.strip():
            raise IncidentEngineError("invalid_approval_scope")
        self._ai_provider = ai_provider
        self._event_sinks = tuple(event_sinks)
        self._approvals = ApprovalEngine()
        self._approval_records = tuple(approval_records)
        self._approval_scope = approval_scope
        self._max_incidents = max_incidents

    def _emit(self, event: dict[str, Any]) -> None:
        if self._event_sinks:
            emit_events(self._event_sinks, event)

    @staticmethod
    def _normalize_input(payloads: Any) -> tuple[Any, ...]:
        if isinstance(payloads, Mapping):
            return (payloads,)
        if isinstance(payloads, (str, bytes)) or not isinstance(payloads, Iterable):
            raise IncidentEngineError("invalid_input")
        return tuple(payloads)

    def _ingest(self, payloads: tuple[Any, ...]) -> tuple[tuple[IncidentRecord, ...], tuple[str, ...]]:
        if not payloads:
            raise IncidentEngineError("no_incidents")
        if len(payloads) > self._max_incidents:
            raise IncidentEngineError("too_many_incidents")

        records: list[IncidentRecord] = []
        duplicates: list[str] = []
        seen: dict[str, IncidentRecord] = {}
        for payload in payloads:
            record = ingest_incident(payload, ai_provider=self._ai_provider)
            self._emit({
                "event": INCIDENT_RECEIVED,
                "incident_id": record.incident_id,
                "status": "received",
            })
            if "missing_evidence" in record.warnings:
                self._emit({
                    "event": EVIDENCE_MISSING,
                    "incident_id": record.incident_id,
                    "status": "unverified",
                })
            existing = seen.get(record.incident_id)
            if existing is not None:
                if existing != record:
                    raise IncidentEngineError("conflicting_duplicate_id")
                duplicates.append(record.incident_id)
                continue
            seen[record.incident_id] = record
            records.append(record)

        self._emit({
            "event": VALIDATION_COMPLETED,
            "status": "completed",
            "counts": {
                "incidents": len(records),
                "duplicates": len(duplicates),
                "evidence": sum(len(item.evidence) for item in records),
            },
        })
        return tuple(records), tuple(sorted(set(duplicates)))

    def _recommend(self, findings: tuple[ClassificationResult, ...]) -> tuple[AdvisoryRecommendation, ...]:
        recommendations: list[AdvisoryRecommendation] = []
        for finding in findings:
            diagnostic_action = _CATEGORY_DIAGNOSTIC_ACTION.get(
                finding.category, "collect_sanitized_logs"
            )
            if diagnostic_action not in DIAGNOSTIC_ACTIONS:
                raise IncidentEngineError("invalid_diagnostic_action")
            diagnostic_approval = self._approvals.evaluate(
                f"{finding.incident_id}:diagnostic",
                diagnostic_action,
                records=self._approval_records,
                evidence_ids=finding.evidence_ids,
                scope=self._approval_scope,
            )
            recommendations.append(AdvisoryRecommendation(
                id=f"{finding.incident_id}:diagnostic",
                incident_id=finding.incident_id,
                category=finding.category,
                action=finding.diagnostic_step,
                verification="Confirm the report evidence references and re-run the offline analyzer.",
                evidence_ids=finding.evidence_ids,
                approval=diagnostic_approval,
            ))

            plan_approval = self._approvals.evaluate(
                f"{finding.incident_id}:remediation-plan",
                REMEDIATION_PLANNING,
                records=self._approval_records,
                evidence_ids=finding.evidence_ids,
                scope=self._approval_scope,
            )
            recommendations.append(AdvisoryRecommendation(
                id=f"{finding.incident_id}:remediation-plan",
                incident_id=finding.incident_id,
                category=finding.category,
                action="Prepare a remediation plan for human review; do not execute it from this report.",
                verification=_REMEDIATION_VERIFICATION,
                evidence_ids=finding.evidence_ids,
                approval=plan_approval,
            ))
        return tuple(recommendations)

    def analyze(self, payloads: Any) -> EngineReport:
        """Analyze one payload or an iterable of payloads and return a report."""
        normalized = self._normalize_input(payloads)
        records, duplicates = self._ingest(normalized)

        findings = classify_records(records)
        category_counts: dict[str, int] = {}
        for finding in findings:
            category_counts[finding.category] = category_counts.get(finding.category, 0) + 1
        self._emit({
            "event": CLASSIFICATION_COMPLETED,
            "status": "completed",
            "counts": {"classifications": len(findings), **category_counts},
        })

        investigation = correlate_incidents(records, findings)
        recommendations = self._recommend(findings)
        warnings = ("duplicate_incident_ignored",) if duplicates else ()
        report = build_engine_report(
            records,
            findings,
            investigation,
            recommendations,
            duplicate_incident_ids=duplicates,
            warnings=warnings,
        )

        rendered = render_engine_json(report)
        digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        self._emit({
            "event": REPORT_GENERATED,
            "status": "validated",
            "report_digest": digest,
            "counts": {"incidents": len(records), "recommendations": len(recommendations)},
        })

        pending = sum(1 for item in recommendations if item.approval.requires_human)
        if pending:
            self._emit({
                "event": APPROVAL_REQUIRED,
                "status": "pending",
                "counts": {"recommendations": pending},
            })
        return report

    def analyze_one(self, payload: Any) -> EngineReport:
        """Analyze exactly one incident payload."""
        return self.analyze((payload,))

    def evaluate_action(
        self,
        action_id: str,
        action: str,
        *,
        evidence_ids: tuple[str, ...] = (),
    ) -> ApprovalDecision:
        """Return an explicit advisory approval decision; this never executes."""
        return self._approvals.evaluate(
            action_id,
            action,
            records=self._approval_records,
            evidence_ids=evidence_ids,
            scope=self._approval_scope,
        )

    def require_approval(self, decision: ApprovalDecision) -> None:
        """Fail closed when an action is pending, rejected, or forbidden."""
        self._approvals.require_approval(decision)


__all__ = ["REMEDIATION_PLANNING", "IncidentIntelligenceEngine"]

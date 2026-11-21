"""Deterministic JSON and Markdown incident report rendering."""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from devobs.incident_intelligence.models import Evidence
from scripts.ci_failure_intelligence import redact_secrets

from .models import (
    APPROVAL_NOT_REQUIRED,
    SCHEMA_VERSION,
    SUPPORTED_APPROVAL_STATES,
    SUPPORTED_CATEGORIES,
    SUPPORTED_SEVERITIES,
    AdvisoryRecommendation,
    ClassificationResult,
    EngineReport,
    IncidentRecord,
    InvestigationReport,
    SchemaValidationError,
)
from .approval import PROHIBITED_ACTIONS

_TOP_LEVEL = frozenset({
    "schema_version", "incident_ids", "duplicate_incident_ids", "severity",
    "classifications", "investigation", "recommendations", "evidence",
    "verification_instructions", "warnings", "ai_provider_status",
})
_CLASSIFICATION_FIELDS = frozenset({
    "incident_id", "category", "confidence", "evidence_ids", "missing_information",
    "diagnostic_step", "rationale", "signature_ids",
})
_INVESTIGATION_FIELDS = frozenset({
    "incident_ids", "findings", "repeated_signatures", "correlations",
    "probable_cause_category", "probable_cause_confidence", "symptom_categories",
    "insufficient_evidence", "timeline",
})
_REPEATED_FIELDS = frozenset({"signature_id", "count", "incident_ids"})
_CORRELATION_FIELDS = frozenset({
    "from_incident_id", "to_incident_id", "relationship", "evidence_ids", "rationale",
})
_TIMELINE_FIELDS = frozenset({"timestamp", "incident_id", "event", "detail"})
_RECOMMENDATION_FIELDS = frozenset({
    "id", "incident_id", "category", "action", "verification", "evidence_ids", "approval",
})
_APPROVAL_FIELDS = frozenset({
    "action_id", "action", "state", "requires_human", "rationale", "evidence_ids",
})
_EVIDENCE_FIELDS = frozenset({"id", "source", "excerpt", "confidence"})
_CONFIDENCES = frozenset({"HIGH", "MEDIUM", "LOW"})
_SEVERITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

VERIFICATION_INSTRUCTIONS = (
    "Re-run the offline analyzer against the same redacted fixture and compare the report digest.",
    "Confirm signature IDs, evidence references and approval states before any human action.",
    "Do not execute remediation; obtain separate owner approval for any production change.",
)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise SchemaValidationError(code)


def _is_string_list(value: Any) -> bool:
    return type(value) is list and all(type(item) is str for item in value)


def _overall_severity(records: Sequence[IncidentRecord]) -> str:
    if not records:
        return "LOW"
    return max((record.severity for record in records), key=lambda value: _SEVERITY_RANK[value])


def _provider_status(records: Sequence[IncidentRecord]) -> str:
    statuses = [record.provider_status for record in records if record.provider_status != "disabled"]
    if not statuses:
        return "disabled"
    return statuses[0] if len(set(statuses)) == 1 else "mixed"


def build_engine_report(
    records: Sequence[IncidentRecord],
    findings: Sequence[ClassificationResult],
    investigation: InvestigationReport,
    recommendations: Sequence[AdvisoryRecommendation],
    *,
    duplicate_incident_ids: Sequence[str] = (),
    warnings: Sequence[str] = (),
) -> EngineReport:
    """Assemble a deterministic report from already validated components."""
    evidence: dict[str, Evidence] = {}
    combined_warnings: list[str] = list(warnings)
    for record in records:
        combined_warnings.extend(record.warnings)
        for item in record.evidence:
            evidence.setdefault(item.id, item)
    return EngineReport(
        schema_version=SCHEMA_VERSION,
        incident_ids=tuple(investigation.incident_ids),
        duplicate_incident_ids=tuple(duplicate_incident_ids),
        severity=_overall_severity(records),
        classifications=tuple(findings),
        investigation=investigation,
        recommendations=tuple(recommendations),
        evidence=tuple(evidence[item_id] for item_id in sorted(evidence)),
        verification_instructions=VERIFICATION_INSTRUCTIONS,
        warnings=tuple(dict.fromkeys(combined_warnings)),
        ai_provider_status=_provider_status(records),
    )


def render_engine_json(report: EngineReport) -> str:
    """Render compact, sorted JSON suitable for deterministic comparison."""
    payload = report.to_dict()
    validate_engine_report_json(payload)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _markdown_lines(report: EngineReport) -> list[str]:
    lines = [
        "# Incident Intelligence Engine Report",
        "",
        f"- Schema: `{report.schema_version}`",
        f"- Incident IDs: `{', '.join(report.incident_ids) or 'none'}`",
        f"- Severity: `{report.severity}`",
        f"- Probable cause: `{report.investigation.probable_cause_category}` "
        f"({report.investigation.probable_cause_confidence} confidence)",
        "",
        "## Timeline",
        "",
    ]
    for event in report.investigation.timeline:
        lines.append(f"- `{event.timestamp}` `{event.incident_id}` {event.event}: {redact_secrets(event.detail)}")
    lines.extend(["", "## Evidence", ""])
    for item in report.evidence:
        lines.append(
            f"- `{item.id}` [{item.confidence}] {redact_secrets(item.source)}: "
            f"{redact_secrets(item.excerpt)}"
        )
    lines.extend(["", "## Classifications", ""])
    for finding in report.classifications:
        lines.append(
            f"- `{finding.incident_id}` {finding.category} ({finding.confidence} confidence); "
            f"evidence: {', '.join(finding.evidence_ids) or 'none'}"
        )
        lines.append(f"  - Missing: {' '.join(finding.missing_information)}")
        lines.append(f"  - Next diagnostic step: {redact_secrets(finding.diagnostic_step)}")
    lines.extend(["", "## Correlation", ""])
    for item in report.investigation.repeated_signatures:
        lines.append(f"- Repeated signature `{item.signature_id}` x{item.count}: {', '.join(item.incident_ids)}")
    for link in report.investigation.correlations:
        lines.append(f"- `{link.from_incident_id}` -> `{link.to_incident_id}`: {link.relationship}")
    for item in report.investigation.insufficient_evidence:
        lines.append(f"- Insufficient evidence: `{item}`")
    lines.extend(["", "## Recommended actions (advisory only)", ""])
    for item in report.recommendations:
        lines.append(
            f"- `{item.id}` {redact_secrets(item.action)} "
            f"[approval: {item.approval.state}; human required: {item.approval.requires_human}]"
        )
        lines.append(f"  - Verify: {redact_secrets(item.verification)}")
    lines.extend(["", "## Verification instructions", ""])
    lines.extend(f"- {redact_secrets(item)}" for item in report.verification_instructions)
    if report.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {redact_secrets(item)}" for item in report.warnings)
    lines.extend(["", "AI provider status: `" + report.ai_provider_status + "`", ""])
    return lines


def render_engine_markdown(report: EngineReport) -> str:
    """Render a human-readable report without changing the structured data."""
    return "\n".join(_markdown_lines(report))


def validate_engine_report_json(payload: Any) -> bool:
    """Validate structure, closed vocabularies and internal references."""
    _require(isinstance(payload, Mapping) and set(payload) == _TOP_LEVEL, "invalid_report_fields")
    _require(payload["schema_version"] == SCHEMA_VERSION, "unsupported_schema_version")
    _require(_is_string_list(payload["incident_ids"]), "invalid_incident_ids")
    _require(_is_string_list(payload["duplicate_incident_ids"]), "invalid_duplicate_ids")
    _require(payload["severity"] in SUPPORTED_SEVERITIES, "invalid_severity")
    _require(_is_string_list(payload["verification_instructions"]), "invalid_verification")
    _require(_is_string_list(payload["warnings"]), "invalid_warnings")
    _require(type(payload["ai_provider_status"]) is str, "invalid_provider_status")

    evidence = payload["evidence"]
    _require(type(evidence) is list and bool(evidence), "invalid_evidence")
    evidence_ids: set[str] = set()
    for item in evidence:
        _require(isinstance(item, Mapping) and set(item) == _EVIDENCE_FIELDS, "invalid_evidence_fields")
        _require(type(item["id"]) is str and bool(item["id"]), "invalid_evidence_id")
        _require(item["id"] not in evidence_ids, "duplicate_evidence_id")
        evidence_ids.add(item["id"])

    findings = payload["classifications"]
    _require(type(findings) is list, "invalid_classifications")
    for item in findings:
        _require(isinstance(item, Mapping) and set(item) == _CLASSIFICATION_FIELDS, "invalid_classification_fields")
        _require(item["category"] in SUPPORTED_CATEGORIES, "invalid_category")
        _require(item["confidence"] in _CONFIDENCES, "invalid_confidence")
        _require(_is_string_list(item["evidence_ids"]), "invalid_evidence_references")
        _require(set(item["evidence_ids"]).issubset(evidence_ids), "dangling_evidence_reference")
        _require(_is_string_list(item["missing_information"]), "invalid_missing_information")
        _require(type(item["diagnostic_step"]) is str, "invalid_diagnostic_step")

    investigation = payload["investigation"]
    _require(isinstance(investigation, Mapping) and set(investigation) == _INVESTIGATION_FIELDS,
             "invalid_investigation_fields")
    _require(_is_string_list(investigation["incident_ids"]), "invalid_investigation_incident_ids")
    _require(investigation["probable_cause_category"] in SUPPORTED_CATEGORIES, "invalid_probable_cause")
    _require(investigation["probable_cause_confidence"] in _CONFIDENCES, "invalid_probable_confidence")
    for field in ("symptom_categories", "insufficient_evidence"):
        _require(_is_string_list(investigation[field]), f"invalid_{field}")
    for item in investigation["repeated_signatures"]:
        _require(isinstance(item, Mapping) and set(item) == _REPEATED_FIELDS, "invalid_repeated_fields")
    for item in investigation["correlations"]:
        _require(isinstance(item, Mapping) and set(item) == _CORRELATION_FIELDS, "invalid_correlation_fields")
    for item in investigation["timeline"]:
        _require(isinstance(item, Mapping) and set(item) == _TIMELINE_FIELDS, "invalid_timeline_fields")

    recommendations = payload["recommendations"]
    _require(type(recommendations) is list, "invalid_recommendations")
    for item in recommendations:
        _require(isinstance(item, Mapping) and set(item) == _RECOMMENDATION_FIELDS,
                 "invalid_recommendation_fields")
        _require(item["category"] in SUPPORTED_CATEGORIES, "invalid_recommendation_category")
        _require(_is_string_list(item["evidence_ids"]), "invalid_recommendation_evidence")
        approval = item["approval"]
        _require(isinstance(approval, Mapping) and set(approval) == _APPROVAL_FIELDS, "invalid_approval_fields")
        _require(approval["state"] in SUPPORTED_APPROVAL_STATES, "invalid_approval_state")
        _require(type(approval["requires_human"]) is bool, "invalid_approval_requirement")
        _require(item["action"] not in PROHIBITED_ACTIONS, "prohibited_action_in_report")
        _require(approval["action"] not in PROHIBITED_ACTIONS, "prohibited_action_in_report")
        if approval["state"] == APPROVAL_NOT_REQUIRED:
            _require(approval["requires_human"] is False, "diagnostic_requires_human")
        else:
            _require(approval["requires_human"] is True, "approval_without_human")
    return True


__all__ = [
    "VERIFICATION_INSTRUCTIONS",
    "build_engine_report",
    "render_engine_json",
    "render_engine_markdown",
    "validate_engine_report_json",
]

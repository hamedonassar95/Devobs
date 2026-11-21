"""Rule-based correlation and root-cause baseline for sanitized incidents."""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from devobs.incident_intelligence.rules import CONFIDENCE_HIGH, CONFIDENCE_LOW, CONFIDENCE_MEDIUM
from scripts.ci_failure_intelligence import detect_repeated_signatures

from .classification import classify_records
from .models import (
    CATEGORY_AUTHENTICATION_CONFIGURATION,
    CATEGORY_CI_CONFIGURATION_FAILURE,
    CATEGORY_CONTAINER_BUILD_FAILURE,
    CATEGORY_DEPENDENCY_FAILURE,
    CATEGORY_INFRASTRUCTURE_CONFIGURATION,
    CATEGORY_SERVICE_HEALTH_FAILURE,
    CATEGORY_TEST_FAILURE,
    CATEGORY_UNKNOWN_FAILURE,
    ClassificationResult,
    CorrelationLink,
    IncidentRecord,
    InvestigationReport,
    RepeatedSignature,
    TimelineEvent,
)

_SYMPTOMS = frozenset({
    CATEGORY_CI_CONFIGURATION_FAILURE,
    CATEGORY_TEST_FAILURE,
    CATEGORY_CONTAINER_BUILD_FAILURE,
    CATEGORY_SERVICE_HEALTH_FAILURE,
})
_CAUSES = frozenset({
    CATEGORY_DEPENDENCY_FAILURE,
    CATEGORY_AUTHENTICATION_CONFIGURATION,
    CATEGORY_INFRASTRUCTURE_CONFIGURATION,
})
_CONFIDENCE_RANK = {CONFIDENCE_HIGH: 3, CONFIDENCE_MEDIUM: 2, CONFIDENCE_LOW: 1}
_MAX_CORRELATIONS = 100


def _signature_inputs(records: tuple[IncidentRecord, ...]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for record in records:
        evidence_ref = record.evidence[0].id if record.evidence else "ev-none"
        for signature_id in record.signature_ids:
            findings.append({
                "signature_id": signature_id,
                "signature": signature_id,
                "job": record.metadata.get("job", ""),
                "step": record.metadata.get("step", ""),
                "evidence_ref": evidence_ref,
            })
    return findings


def _repeated_signatures(records: tuple[IncidentRecord, ...]) -> tuple[RepeatedSignature, ...]:
    signature_to_ids: dict[str, set[str]] = defaultdict(set)
    for record in records:
        for value in record.signature_ids:
            signature_to_ids[value].add(record.incident_id)
    grouped = detect_repeated_signatures(_signature_inputs(records))
    result: list[RepeatedSignature] = []
    for entry in grouped:
        signature = str(entry.get("signature_id", ""))
        if not signature:
            continue
        result.append(RepeatedSignature(
            signature_id=signature,
            count=int(entry.get("count", 0)),
            incident_ids=tuple(sorted(signature_to_ids.get(signature, ()))),
        ))
    return tuple(result)


def _link(
    source: str,
    target: str,
    relationship: str,
    rationale: str,
    evidence_ids: tuple[str, ...],
) -> CorrelationLink:
    return CorrelationLink(
        from_incident_id=source,
        to_incident_id=target,
        relationship=relationship,
        evidence_ids=evidence_ids,
        rationale=rationale,
    )


def _correlations(
    records: tuple[IncidentRecord, ...],
    findings: tuple[ClassificationResult, ...],
    repeated: tuple[RepeatedSignature, ...],
) -> tuple[CorrelationLink, ...]:
    by_id = {record.incident_id: record for record in records}
    finding_by_id = {item.incident_id: item for item in findings}
    links: list[CorrelationLink] = []

    for item in repeated:
        ids = item.incident_ids
        for source, target in combinations(ids, 2):
            if len(links) >= _MAX_CORRELATIONS:
                return tuple(links)
            evidence = by_id[source].evidence[:1] + by_id[target].evidence[:1]
            links.append(_link(
                source, target, "repeated_signature",
                "The same redacted error signature appears in both incidents.",
                tuple(item.id for item in evidence),
            ))

    by_category: dict[str, set[str]] = defaultdict(set)
    for finding in findings:
        by_category[finding.category].add(finding.incident_id)
    for category, ids in sorted(by_category.items()):
        if category == CATEGORY_UNKNOWN_FAILURE or len(ids) < 2:
            continue
        source, *targets = sorted(ids)
        for target in targets:
            if len(links) >= _MAX_CORRELATIONS:
                return tuple(links)
            evidence = finding_by_id[source].evidence_ids[:1] + finding_by_id[target].evidence_ids[:1]
            links.append(_link(
                source, target, "recurring_category",
                "The same bounded incident category recurs across distinct incidents.",
                evidence,
            ))

    symptom_ids = [item.incident_id for item in findings if item.category in _SYMPTOMS]
    cause_ids = [
        item.incident_id for item in findings
        if item.category in _CAUSES and item.confidence in (CONFIDENCE_HIGH, CONFIDENCE_MEDIUM)
    ]
    for symptom in symptom_ids:
        for cause in cause_ids:
            if symptom == cause:
                continue
            if len(links) >= _MAX_CORRELATIONS:
                return tuple(links)
            evidence = finding_by_id[symptom].evidence_ids[:1] + finding_by_id[cause].evidence_ids[:1]
            links.append(_link(
                symptom, cause, "symptom_of",
                "A cause-category finding co-occurs with a symptom-category finding; "
                "this is a heuristic link, not causal proof.",
                evidence,
            ))
    return tuple(links)


def _probable_cause(
    records: tuple[IncidentRecord, ...],
    findings: tuple[ClassificationResult, ...],
) -> tuple[str, str, tuple[str, ...], tuple[str, ...]]:
    insufficient: list[str] = []
    for finding in findings:
        if finding.confidence == CONFIDENCE_LOW:
            insufficient.append(f"{finding.incident_id}:LOW_CONFIDENCE")
        if finding.missing_information:
            insufficient.append(f"{finding.incident_id}:MISSING_INFORMATION")

    candidates = [
        item for item in findings
        if item.category in _CAUSES and item.confidence in (CONFIDENCE_HIGH, CONFIDENCE_MEDIUM)
    ]
    if not candidates:
        insufficient.append("NO_CAUSE_CATEGORY_EVIDENCE")
        return CATEGORY_UNKNOWN_FAILURE, CONFIDENCE_LOW, (), tuple(sorted(set(insufficient)))

    distinct = sorted({item.category for item in candidates})
    if len(distinct) > 1:
        insufficient.append("MULTIPLE_CAUSE_CATEGORIES")
    best = sorted(candidates, key=lambda item: (-_CONFIDENCE_RANK[item.confidence], item.category, item.incident_id))[0]
    confidence = CONFIDENCE_MEDIUM if len(distinct) > 1 else best.confidence
    symptoms = tuple(sorted({item.category for item in findings if item.category in _SYMPTOMS}))
    return best.category, confidence, symptoms, tuple(sorted(set(insufficient)))


def _timeline(records: tuple[IncidentRecord, ...], findings: tuple[ClassificationResult, ...]) -> tuple[TimelineEvent, ...]:
    category_by_id = {item.incident_id: item.category for item in findings}
    ordered = sorted(records, key=lambda record: (record.timestamp, record.incident_id))
    return tuple(
        TimelineEvent(
            timestamp=record.timestamp,
            incident_id=record.incident_id,
            event="incident_received",
            detail=f"{record.kind}:{category_by_id.get(record.incident_id, CATEGORY_UNKNOWN_FAILURE)}",
        )
        for record in ordered
    )


def correlate_incidents(
    records: tuple[IncidentRecord, ...],
    findings: tuple[ClassificationResult, ...] | None = None,
) -> InvestigationReport:
    """Correlate bounded findings without claiming causal proof."""
    findings = findings if findings is not None else classify_records(records)
    repeated = _repeated_signatures(records)
    correlations = _correlations(records, findings, repeated)
    cause, confidence, symptoms, insufficient = _probable_cause(records, findings)
    return InvestigationReport(
        incident_ids=tuple(sorted(record.incident_id for record in records)),
        findings=findings,
        repeated_signatures=repeated,
        correlations=correlations,
        probable_cause_category=cause,
        probable_cause_confidence=confidence,
        symptom_categories=symptoms,
        insufficient_evidence=insufficient,
        timeline=_timeline(records, findings),
    )


__all__ = ["correlate_incidents"]

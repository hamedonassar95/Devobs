"""Offline-first incident analysis orchestration.

The analyzer is deterministic by default. It never applies a fix, reruns a
workflow, merges, deploys, or calls an external provider unless a caller
explicitly injects an advisory provider object.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Protocol

from scripts.ci_failure_intelligence import analyze_run, redact_secrets
from scripts.devobs_intelligence.adviser import propose
from scripts.devobs_intelligence.contracts import parse_event

from .models import (
    SCHEMA_VERSION,
    AIProviderReport,
    Evidence,
    Hypothesis,
    IncidentInput,
    IncidentReport,
    Recommendation,
)
from .rules import (
    CATEGORY_UNKNOWN,
    CONFIDENCE_LOW,
    EVIDENCE_INFERRED,
    EVIDENCE_UNVERIFIED,
    Classification,
    classify_adviser_signal,
    classify_failure,
    hypothesis_statement,
    recommendation_for,
)


class AIProvider(Protocol):
    """Advisory provider boundary. No provider is constructed or called by default."""

    def diagnose(self, prompt: str) -> str: ...


class DisabledAIProvider:
    """Explicit no-op provider used when AI is not enabled."""

    def diagnose(self, prompt: str) -> str:
        return "AI provider disabled; deterministic evidence only."


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return redact_secrets(str(value)).strip()


def _normalize_input(value: Any) -> IncidentInput:
    if isinstance(value, IncidentInput):
        safe_logs = [_safe_text(log) for log in value.logs]
        return IncidentInput(
            title=_safe_text(value.title),
            job=_safe_text(value.job),
            step=_safe_text(value.step),
            logs=tuple(log for log in safe_logs if log),
            metadata={str(k): _safe_text(v) for k, v in value.metadata.items()},
            warnings=tuple(_safe_text(warning) for warning in value.warnings),
        )

    warnings: list[str] = []
    if not isinstance(value, Mapping):
        warnings.append("Input was not a mapping; analyzed as empty evidence.")
        return IncidentInput(warnings=tuple(warnings))

    raw_logs = value.get("logs", ())
    logs: list[str] = []
    if isinstance(raw_logs, str):
        if raw_logs.strip():
            logs.append(_safe_text(raw_logs))
    elif isinstance(raw_logs, (list, tuple)):
        for item in raw_logs:
            if isinstance(item, str) and item.strip():
                logs.append(_safe_text(item))
            else:
                warnings.append("Non-string log entries were ignored.")
    else:
        warnings.append("Logs were missing or not a string/list; analyzed as empty evidence.")

    raw_metadata = value.get("metadata", {})
    if isinstance(raw_metadata, Mapping):
        metadata = {str(key): _safe_text(item) for key, item in raw_metadata.items()}
    else:
        metadata = {}
        if raw_metadata is not None:
            warnings.append("Metadata was not a mapping; it was ignored.")

    raw_warnings = value.get("warnings", ())
    if isinstance(raw_warnings, (list, tuple)):
        warnings.extend(_safe_text(item) for item in raw_warnings if isinstance(item, str))

    return IncidentInput(
        title=_safe_text(value.get("title") or ""),
        job=_safe_text(value.get("job") or ""),
        step=_safe_text(value.get("step") or ""),
        logs=tuple(log for log in logs if log),
        metadata=metadata,
        warnings=tuple(warning for warning in warnings if warning),
    )


def _build_evidence(
    incident: IncidentInput,
    classification: Any,
    source_label: str,
) -> tuple[Evidence, ...]:
    evidence: list[Evidence] = []
    for log in incident.logs:
        excerpt = redact_secrets(log)[:240]
        digest = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
        evidence.append(
            Evidence(
                id=f"ev-{digest[:12]}",
                source=source_label,
                excerpt=excerpt,
                confidence=classification.evidence_confidence,
            )
        )

    if not evidence:
        metadata_text = " / ".join(part for part in (incident.job, incident.step) if part)
        excerpt = _safe_text(metadata_text)[:240]
        if not excerpt:
            excerpt = "No sanitized log or metadata evidence supplied."
        digest = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
        confidence = classification.evidence_confidence if metadata_text else EVIDENCE_UNVERIFIED
        evidence.append(
            Evidence(
                id=f"ev-{digest[:12]}",
                source=source_label,
                excerpt=excerpt,
                confidence=confidence,
            )
        )
    return tuple(evidence)


def _provider_report(
    provider: AIProvider,
    incident: IncidentInput,
    classification: Any,
    evidence: tuple[Evidence, ...],
) -> AIProviderReport:
    prompt = redact_secrets(
        json.dumps(
            {
                "classification": classification.category,
                "signal": classification.signal,
                "logs": incident.logs[:10],
                "evidence": [
                    {"source": item.source, "excerpt": item.excerpt}
                    for item in evidence[:10]
                ],
            },
            sort_keys=True,
        )
    )
    try:
        result = provider.diagnose(prompt)
        if not isinstance(result, str) or not result.strip():
            raise ValueError("empty_provider_response")
        summary = redact_secrets(result).strip()[:1200]
        status = "disabled" if isinstance(provider, DisabledAIProvider) else "available"
    except Exception as exc:  # fail closed; deterministic evidence remains intact
        status = "error"
        summary = (
            f"AI provider unavailable: {redact_secrets(type(exc).__name__)}. "
            "Deterministic evidence retained."
        )
    return AIProviderReport(status=status, summary=summary)


def _summary(
    category: str,
    confidence: str,
    statement: str,
    evidence: tuple[Evidence, ...],
    recommendation: Recommendation,
    warnings: tuple[str, ...],
) -> str:
    if category == CATEGORY_UNKNOWN or confidence == CONFIDENCE_LOW:
        prefix = "Insufficient trusted evidence" if warnings else "Unverified evidence"
        lead = f"{prefix}: the incident is classified as unknown and remains unverified."
    else:
        lead = f"Leading hypothesis ({confidence} confidence): {statement}"
    sources = ", ".join(dict.fromkeys(item.source.split(":")[0] for item in evidence[:3]))
    return (
        f"{lead} Evidence: {len(evidence)} redacted item(s) from {sources or 'input'}. "
        f"Recommended safe next step: {recommendation.action} "
        "Human approval is required before any remediation."
    )


def _build_report(
    normalized: IncidentInput,
    classification: Classification,
    *,
    source: str,
    evidence_source: str,
    ai_provider: AIProvider | None,
    evidence: tuple[Evidence, ...] | None = None,
) -> IncidentReport:
    """Assemble a report from deterministic classification and safe evidence."""
    evidence = (
        evidence
        if evidence is not None
        else _build_evidence(normalized, classification, evidence_source)
    )

    hypothesis = Hypothesis(
        id="H1",
        category=classification.category,
        statement=hypothesis_statement(classification.category),
        confidence=classification.confidence,
        evidence_ids=tuple(item.id for item in evidence),
        rationale=classification.rationale,
    )
    action, rationale = recommendation_for(classification.category)
    recommendation = Recommendation(
        id="R1",
        action=action,
        rationale=rationale,
        hypothesis_id=hypothesis.id,
    )
    summary = _summary(
        classification.category,
        classification.confidence,
        hypothesis.statement,
        evidence,
        recommendation,
        normalized.warnings,
    )
    provider = ai_provider if ai_provider is not None else DisabledAIProvider()
    return IncidentReport(
        schema_version=SCHEMA_VERSION,
        source=source,
        category=classification.category,
        signal=classification.signal,
        confidence=classification.confidence,
        summary=summary,
        evidence=evidence,
        hypotheses=(hypothesis,),
        recommendations=(recommendation,),
        warnings=normalized.warnings,
        ai_provider=_provider_report(provider, normalized, classification, evidence),
        guardrails={
            "read_only": True,
            "modifies_code": False,
            "reruns_workflows": False,
            "merges_prs": False,
            "deploys": False,
            "automatic_fixes": False,
            "external_api_calls_by_default": False,
            "human_approval_required": True,
        },
    )


def analyze_incident(
    incident: Any,
    *,
    source: str = "provided_evidence",
    evidence_source: str = "provided_evidence",
    ai_provider: AIProvider | None = None,
) -> IncidentReport:
    """Produce a deterministic, evidence-linked incident report."""
    normalized = _normalize_input(incident)
    classification = classify_failure(normalized.logs, normalized.job, normalized.step)
    return _build_report(
        normalized,
        classification,
        source=source,
        evidence_source=evidence_source,
        ai_provider=ai_provider,
    )


def _signal_evidence(proposal: Any) -> tuple[Evidence, ...]:
    """Derive evidence from the adviser output without copying raw identifiers."""
    evidence: list[Evidence] = []
    adviser_excerpt = _safe_text(
        "offline adviser classification: "
        f"signal={proposal.hypothesis}; status={proposal.status}; "
        f"runbook_ids={','.join(proposal.runbook_ids) or 'none'}; "
        f"suggested_tests={'; '.join(proposal.recommended_tests) or 'none'}; "
        f"proposal_digest={proposal.proposal_digest}"
    )
    evidence.append(
        Evidence(
            id=f"ev-adviser-{proposal.proposal_digest}",
            source="devobs_intelligence",
            excerpt=adviser_excerpt,
            confidence=EVIDENCE_INFERRED,
        )
    )
    for digest in proposal.evidence_digests:
        safe_digest = _safe_text(digest)
        if not safe_digest:
            continue
        evidence.append(
            Evidence(
                id=f"ev-envelope-{safe_digest}",
                source="devobs_intelligence",
                excerpt=f"Validated evidence envelope digest: {safe_digest}",
                confidence=EVIDENCE_INFERRED,
            )
        )
    return tuple(evidence)


def _signal_failure_report(
    warnings: tuple[str, ...],
    *,
    ai_provider: AIProvider | None,
) -> IncidentReport:
    """Fail closed when the strict envelope or aggregate signals are invalid."""
    classification = Classification(
        category=CATEGORY_UNKNOWN,
        confidence=CONFIDENCE_LOW,
        signal="unknown",
        excerpt="No validated aggregate signals were supplied.",
        evidence_confidence=EVIDENCE_UNVERIFIED,
        rationale="Evidence envelope or aggregate signals failed validation; fail closed.",
    )
    evidence = (
        Evidence(
            id="ev-invalid-aggregate-signals",
            source="devobs_intelligence",
            excerpt="No validated aggregate signals were supplied.",
            confidence=EVIDENCE_UNVERIFIED,
        ),
    )
    return _build_report(
        IncidentInput(warnings=warnings),
        classification,
        source="devobs_intelligence",
        evidence_source="devobs_intelligence",
        ai_provider=ai_provider,
        evidence=evidence,
    )


def analyze_signals(
    event: Any,
    signal_values: Any,
    *,
    ai_provider: AIProvider | None = None,
) -> IncidentReport:
    """Classify bounded aggregate signals via the existing offline adviser.

    The strict evidence envelope hashes raw project identifiers. This wrapper
    returns only deterministic classifications, derived digests, and advisory
    recommendations; it never returns the project reference or source SHA.
    """
    try:
        parsed_event = parse_event(event)
    except Exception:  # fixed warning; validation errors are never echoed
        return _signal_failure_report(
            ("Evidence envelope was rejected by the strict contract.",),
            ai_provider=ai_provider,
        )

    try:
        proposal = propose(parsed_event, signal_values)
    except Exception:  # fixed warning; raw signal values are never echoed
        return _signal_failure_report(
            ("Aggregate signals were rejected by the offline adviser.",),
            ai_provider=ai_provider,
        )

    category, confidence = classify_adviser_signal(proposal.hypothesis)
    classification = Classification(
        category=category,
        confidence=confidence,
        signal=proposal.hypothesis,
        excerpt=_safe_text(f"offline adviser signal: {proposal.hypothesis}"),
        evidence_confidence=EVIDENCE_INFERRED,
        rationale="Existing offline adviser classified bounded aggregate signals from a valid envelope.",
    )
    return _build_report(
        IncidentInput(),
        classification,
        source="devobs_intelligence",
        evidence_source="devobs_intelligence",
        ai_provider=ai_provider,
        evidence=_signal_evidence(proposal),
    )


def analyze_workflow_run(
    run_metadata: Any,
    jobs_data: Any,
    *,
    ai_provider: AIProvider | None = None,
) -> IncidentReport:
    """Convert PR #734's GitHub Actions report into an incident intelligence report."""
    warnings: list[str] = []
    try:
        ci_report = analyze_run(run_metadata, jobs_data)
    except Exception as exc:  # fail closed with deterministic empty evidence
        warnings.append(
            "CI Failure Intelligence analyzer failed closed: "
            f"{redact_secrets(type(exc).__name__)}."
        )
        ci_report = {
            "run": {},
            "top_findings": [],
            "repeated_signatures": [],
            "overall_category": CATEGORY_UNKNOWN,
        }

    findings = ci_report.get("top_findings")
    if not isinstance(findings, list):
        findings = []
        warnings.append("CI Failure Intelligence findings were missing or invalid.")
    logs: list[str] = []
    job = ""
    step = ""
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            warnings.append(f"CI finding {index} was not a mapping and was ignored.")
            continue
        if not job and isinstance(finding.get("job"), str):
            job = finding["job"]
        if not step and isinstance(finding.get("step"), str):
            step = finding["step"]
        for key in ("detail", "message"):
            value = finding.get(key)
            if isinstance(value, str) and value.strip():
                logs.append(value)

    raw_run = ci_report.get("run")
    run = raw_run if isinstance(raw_run, Mapping) else {}
    metadata = {str(key): _safe_text(value) for key, value in run.items()}
    metadata["ci_overall_category"] = _safe_text(ci_report.get("overall_category"))
    repeated = ci_report.get("repeated_signatures")
    metadata["repeated_signature_count"] = str(len(repeated) if isinstance(repeated, list) else 0)
    if not logs:
        warnings.append("CI Failure Intelligence returned no usable finding text.")

    return analyze_incident(
        {
            "title": "github_actions_failure",
            "job": job,
            "step": step,
            "logs": logs,
            "metadata": metadata,
            "warnings": warnings,
        },
        source="github_actions",
        evidence_source="ci_failure_intelligence",
        ai_provider=ai_provider,
    )


def render_summary(report: IncidentReport) -> str:
    """Render a human-readable Markdown summary without changing the report."""
    lines = [
        "# Incident Intelligence Report",
        "",
        redact_secrets(report.summary),
        "",
        f"- Source: `{redact_secrets(report.source)}`",
        f"- Category: `{redact_secrets(report.category)}`",
        f"- Signal: `{redact_secrets(report.signal)}`",
        f"- Confidence: `{redact_secrets(report.confidence)}`",
        "",
        "## Evidence",
        "",
    ]
    for item in report.evidence:
        lines.append(
            f"- `{item.id}` [{item.confidence}] {redact_secrets(item.source)}: "
            f"{redact_secrets(item.excerpt)}"
        )
    lines.extend(["", "## Advisory recommendations", ""])
    for item in report.recommendations:
        lines.append(
            f"- {redact_secrets(item.action)} "
            f"(human approval required: {item.requires_human_approval})"
        )
    if report.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {redact_secrets(warning)}" for warning in report.warnings)
    lines.extend(["", f"AI provider status: `{report.ai_provider.status}`", ""])
    return "\n".join(lines)

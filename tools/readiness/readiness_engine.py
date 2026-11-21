"""Offline production-readiness intelligence engine."""

from __future__ import annotations

from typing import Any, Mapping

from scripts.ci_failure_intelligence import redact_secrets

from .checks import (
    check_cicd,
    check_dependencies,
    check_deployment,
    check_duplicate_tasks,
    check_observability,
    check_ownership,
    check_pr_risk,
    check_secrets,
)
from .models import BLOCKED, DEGRADED, Finding, READY, SCHEMA_VERSION, SEV_RANK, UNKNOWN, clip, now_iso


class ReadinessInputError(ValueError):
    pass


def _add(findings: list[Finding], *args: Any, **kwargs: Any) -> None:
    if len(findings) < 500:
        findings.append(Finding(*args, **kwargs))


def _optional_ai(snapshot: Mapping[str, Any], findings: list[Finding]) -> dict[str, Any]:
    ai = snapshot.get("ai_analysis")
    if not isinstance(ai, Mapping):
        return {"enabled": False, "mode": "disabled"}
    enabled = ai.get("enabled") is True
    provider = str(ai.get("provider", "")).strip()
    authorized = ai.get("authorized") is True
    if not enabled:
        return {"enabled": False, "mode": "disabled"}
    if not provider or not authorized:
        _add(findings, "AI_ANALYSIS_UNAUTHORIZED", "HIGH", "ai", "AI analysis requested but provider is not authorized/configured", remediation="Keep AI disabled or provide explicit authorized local/provider config; AI remains advisory only.")
        return {"enabled": False, "mode": "blocked", "provider": redact_secrets(provider)}
    # read-only advisory summary only; never authoritative
    summary = clip(redact_secrets(str(ai.get("summary", ""))), 500)
    return {"enabled": True, "mode": "advisory_read_only", "provider": redact_secrets(provider), "summary": summary, "authoritative": False}


def evaluate_production_readiness(snapshot: Any) -> dict[str, Any]:
    findings: list[Finding] = []
    if not isinstance(snapshot, Mapping):
        _add(findings, "INVALID_INPUT", "CRITICAL", "input", "Snapshot must be a JSON object", remediation="Provide a valid JSON object snapshot.")
        snapshot = {}
    repo = str(snapshot.get("repository", ""))
    sections = {}
    try:
        sections["cicd"] = check_cicd(snapshot, findings)
        sections["dependencies"] = check_dependencies(snapshot, findings)
        sections["security"] = check_secrets(snapshot, findings)
        sections["ownership"] = check_ownership(snapshot, findings)
        sections["pr_risk"] = check_pr_risk(snapshot, findings)
        sections["deployment"] = check_deployment(snapshot, findings)
        sections["observability"] = check_observability(snapshot, findings)
        sections["tasks"] = check_duplicate_tasks(snapshot, findings)
    except Exception as exc:  # noqa: BLE001
        _add(findings, "INVALID_INPUT", "CRITICAL", "input", f"Invalid snapshot: {type(exc).__name__}: {clip(exc,200)}", remediation="Fix input schema/types/bounds.")
    ai = _optional_ai(snapshot, findings)

    codes = {f.code for f in findings}
    sev_counts = {s: 0 for s in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]}
    for f in findings:
        sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1

    if "INVALID_INPUT" in codes:
        status = UNKNOWN
    elif sev_counts["CRITICAL"] > 0 or any(c in codes for c in {"CI_CHECK_FAILED", "AGENT_OWNERSHIP_CONFLICT", "DEPENDENCY_CYCLE", "SECRET_EXPOSURE_RISK", "SECRET_PATTERN_DETECTED", "UNSAFE_DEPLOYMENT_CONFIG"}):
        status = BLOCKED
    elif sev_counts["HIGH"] > 0 or sev_counts["MEDIUM"] > 0:
        status = UNKNOWN if any("UNKNOWN" in c or "MISSING" in c for c in codes) and sev_counts["HIGH"] > 0 else DEGRADED
        if sev_counts["HIGH"] > 0:
            status = UNKNOWN
    else:
        status = READY

    if status != BLOCKED and any(c in codes for c in {"MISSING_REQUIRED_CI_CHECK", "CI_CHECK_PENDING", "MISSING_APPROVAL_GATE", "CI_REQUIRED_CHECKS_UNKNOWN", "AI_ANALYSIS_UNAUTHORIZED"}):
        status = UNKNOWN

    findings_sorted = sorted(findings, key=lambda f: (SEV_RANK.get(f.severity, 9), f.category, f.code, f.component, f.message))
    recommendations = []
    seen = set()
    for f in findings_sorted:
        if f.remediation and f.remediation not in seen:
            seen.add(f.remediation)
            recommendations.append({"priority": f.severity, "action": f.remediation, "code": f.code})
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "repository": repo,
        "status": status,
        "advisory_only": True,
        "human_approval_required": True,
        "no_destructive_actions": True,
        "ai_analysis": ai,
        "summary": {"severity_counts": sev_counts, "finding_count": len(findings_sorted)},
        "checks": sections,
        "findings": [f.as_dict() for f in findings_sorted],
        "recommendations": recommendations[:100],
        "risk_matrix": sev_counts,
    }

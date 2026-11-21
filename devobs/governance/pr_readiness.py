"""Deterministic, fail-closed PR readiness and security evidence engine.

This module evaluates pre-collected evidence. It does not fetch network resources,
does not approve PRs, and does not merge PRs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .evidence_validator import (
    EvidenceValidationError,
    NormalizedEvidence,
    ValidationIssue,
    READINESS_STATES,
    redact_sensitive,
    validate_evidence,
)

SUCCESS_CONCLUSIONS = {"success", "passed", "pass"}
FAIL_CONCLUSIONS = {"failure", "failed", "fail", "cancelled", "timed_out", "action_required"}
PENDING_CONCLUSIONS = {"pending", "queued", "in_progress", ""}
SECURITY_PASS = {"pass", "passed", "success"}
SECURITY_FAIL = {"fail", "failed"}
SECURITY_PENDING = {"pending", "missing", "unknown"}


class ReadinessState:
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
    PENDING = "PENDING"
    BLOCKED = "BLOCKED"
    UNVERIFIED = "UNVERIFIED"

    ALL = READINESS_STATES


@dataclass(frozen=True)
class Decision:
    state: str
    reasons: list[dict[str, str]]
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return {"state": self.state, "reasons": self.reasons, "summary": self.summary}


def _reason(code: str, message: str, source: str, severity: str) -> dict[str, str]:
    return {"code": code, "message": message, "source": source, "severity": severity}


def _issue_to_reason(issue: ValidationIssue) -> dict[str, str]:
    return _reason(issue.code, issue.message, issue.source, issue.severity)


def _dedupe_reasons(reasons: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str, str]] = set()
    out: list[dict[str, str]] = []
    for r in reasons:
        key = (r.get("code", ""), r.get("message", ""), r.get("source", ""), r.get("severity", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _evaluate_checks(ev: NormalizedEvidence, reasons: list[dict[str, str]]) -> dict[str, Any]:
    checks = ev.checks
    required = ev.required_checks
    by_name: dict[str, list[dict[str, Any]]] = {}
    for c in checks:
        by_name.setdefault(c["name"].lower(), []).append(c)

    missing_required = []
    failing = []
    pending = []
    unknown = []
    passing_required = []

    for req in required:
        matches = by_name.get(req.lower(), [])
        if not matches:
            missing_required.append(req)
            reasons.append(_reason("MISSING_REQUIRED_CHECK", f"required check missing: {req}", "checks", "BLOCKED"))
            continue
        # latest by completed_at string if present, else last
        selected = sorted(matches, key=lambda x: x.get("completed_at") or "")[-1]
        status = selected.get("status", "")
        conclusion = selected.get("conclusion", "")
        if selected.get("stale"):
            reasons.append(_reason("STALE_REQUIRED_CHECK", f"required check is stale for head SHA: {req}", "checks", "BLOCKED"))
            missing_required.append(req)
            continue
        if conclusion in FAIL_CONCLUSIONS or status in {"failure"}:
            failing.append(req)
            reasons.append(_reason("FAILING_REQUIRED_CHECK", f"required check failed: {req}", "checks", "BLOCKED"))
        elif conclusion in SUCCESS_CONCLUSIONS or status == "success":
            passing_required.append(req)
        elif status in {"queued", "in_progress", "pending"} or conclusion in PENDING_CONCLUSIONS:
            pending.append(req)
            reasons.append(_reason("PENDING_REQUIRED_CHECK", f"required check pending: {req}", "checks", "PENDING"))
        else:
            unknown.append(req)
            reasons.append(_reason("UNKNOWN_REQUIRED_CHECK", f"required check has unknown state: {req}", "checks", "UNVERIFIED"))

    # any failing/pending observed check (even non-required) is informative
    for c in checks:
        conclusion = c.get("conclusion", "")
        status = c.get("status", "")
        name = c["name"]
        if c.get("stale"):
            continue
        if conclusion in FAIL_CONCLUSIONS or status == "failure":
            reasons.append(_reason("FAILING_CHECK", f"check failed: {name}", "checks", "BLOCKED"))
        elif status in {"queued", "in_progress", "pending"} or (status == "completed" and conclusion in PENDING_CONCLUSIONS):
            reasons.append(_reason("PENDING_CHECK", f"check pending: {name}", "checks", "PENDING"))
        elif status == "completed" and conclusion and conclusion not in SUCCESS_CONCLUSIONS and conclusion not in FAIL_CONCLUSIONS and conclusion not in {"skipped", "neutral"}:
            reasons.append(_reason("UNKNOWN_CHECK_STATE", f"check has unknown conclusion: {name}", "checks", "UNVERIFIED"))

    return {
        "total": len(checks),
        "required_total": len(required),
        "missing_required": sorted(set(missing_required)),
        "failing_required": sorted(set(failing)),
        "pending_required": sorted(set(pending)),
        "unknown_required": sorted(set(unknown)),
        "passing_required": sorted(set(passing_required)),
    }


def _evaluate_security(ev: NormalizedEvidence, reasons: list[dict[str, str]]) -> dict[str, Any]:
    evidence = ev.security_evidence
    if not evidence:
        reasons.append(_reason("MISSING_SECURITY_EVIDENCE", "no security scan evidence provided", "security_evidence", "UNVERIFIED"))
        return {"present": False, "passing": [], "failing": [], "pending": [], "unknown": []}
    passing, failing, pending, unknown = [], [], [], []
    for item in evidence:
        name = item["name"]
        status = item.get("status", "")
        if item.get("stale"):
            reasons.append(_reason("STALE_SECURITY_EVIDENCE", f"security evidence stale for head SHA: {name}", "security_evidence", "BLOCKED"))
            failing.append(name)
            continue
        if status in SECURITY_FAIL:
            failing.append(name)
            reasons.append(_reason("SECURITY_SCAN_FAILED", f"security evidence failed: {name}", "security_evidence", "BLOCKED"))
        elif status in SECURITY_PASS:
            passing.append(name)
        elif status in SECURITY_PENDING:
            pending.append(name)
            reasons.append(_reason("SECURITY_EVIDENCE_PENDING", f"security evidence missing/pending: {name}", "security_evidence", "UNVERIFIED"))
        else:
            unknown.append(name)
            reasons.append(_reason("SECURITY_EVIDENCE_UNKNOWN", f"security evidence unknown: {name}", "security_evidence", "UNVERIFIED"))
    return {
        "present": True,
        "passing": sorted(set(passing)),
        "failing": sorted(set(failing)),
        "pending": sorted(set(pending)),
        "unknown": sorted(set(unknown)),
    }


def _evaluate_approvals(ev: NormalizedEvidence, reasons: list[dict[str, str]]) -> dict[str, Any]:
    required = ev.required_approvals
    approvals = ev.approvals
    authoritative = []
    stale = []
    untrusted = []
    for a in approvals:
        actor = a["actor"]
        if a.get("stale"):
            stale.append(actor)
            continue
        if a.get("state") != "approved":
            continue
        if a.get("verified") is True and a.get("source_type") not in {"self", "self_reported", "self-reported", "comment", "pr_body", "author"}:
            authoritative.append(actor)
        else:
            untrusted.append(actor)
            reasons.append(_reason("UNTRUSTED_APPROVAL", f"approval is not authoritative: {actor}", "approvals", "UNVERIFIED"))

    if required > 0 and len(authoritative) < required:
        if stale:
            reasons.append(_reason("STALE_APPROVAL_EVIDENCE", "approval evidence is stale for head SHA", "approvals", "BLOCKED"))
        reasons.append(_reason("MISSING_APPROVAL_EVIDENCE", f"authoritative approvals {len(authoritative)}/{required}", "approvals", "UNVERIFIED"))
    return {
        "required": required,
        "authoritative_count": len(authoritative),
        "authoritative_actors": sorted(set(authoritative)),
        "stale_actors": sorted(set(stale)),
        "untrusted_actors": sorted(set(untrusted)),
    }


def evaluate_pr_readiness(evidence: Mapping[str, Any] | str | bytes) -> dict[str, Any]:
    """Evaluate evidence and return a stable JSON-ready readiness report.

    Never returns READY_FOR_HUMAN_REVIEW when required evidence is missing or unverified.
    """
    try:
        ev = validate_evidence(evidence)
    except EvidenceValidationError as exc:
        report = {
            "schema_version": 1,
            "engine": "devobs.governance.pr_readiness",
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "state": ReadinessState.UNVERIFIED,
            "summary": "Evidence could not be validated; readiness is UNVERIFIED.",
            "reasons": [_reason("MALFORMED_EVIDENCE", redact_sensitive(str(exc)), "evidence", "UNVERIFIED")],
            "evidence": {},
        }
        return report

    reasons: list[dict[str, str]] = [_issue_to_reason(i) for i in ev.issues]

    # explicit checks for required inputs / evidence absence
    if not ev.head_sha:
        reasons.append(_reason("MISSING_HEAD_SHA", "PR head SHA is missing", "pr", "UNVERIFIED"))
    if not ev.pr.get("branch"):
        reasons.append(_reason("MISSING_BRANCH", "PR branch is missing", "pr", "UNVERIFIED"))
    if not ev.checks and ev.required_checks:
        reasons.append(_reason("MISSING_CHECK_EVIDENCE", "required checks configured but no check evidence provided", "checks", "UNVERIFIED"))
    if ev.required_checks == []:
        # absence of required-check policy is not success; fail closed as unverified unless caller explicitly provides empty policy with checks? keep unverified.
        reasons.append(_reason("MISSING_REQUIRED_CHECK_POLICY", "required check policy evidence is missing", "policy", "UNVERIFIED"))

    checks_summary = _evaluate_checks(ev, reasons)
    security_summary = _evaluate_security(ev, reasons)
    approvals_summary = _evaluate_approvals(ev, reasons)

    # conflicting evidence: same check name+sha with different conclusions/statuses
    seen_outcomes: dict[tuple[str, str], set[str]] = {}
    for c in ev.checks:
        key = (c["name"].lower(), c.get("head_sha") or "")
        outcome = f"{c.get('status','')}:{c.get('conclusion','')}"
        seen_outcomes.setdefault(key, set()).add(outcome)
    for (name, sha), outcomes in sorted(seen_outcomes.items()):
        if len(outcomes) > 1:
            reasons.append(_reason("CONFLICTING_CHECK_EVIDENCE", f"conflicting outcomes for {name}", "checks", "BLOCKED"))

    reasons = _dedupe_reasons(reasons)
    severities = {r["severity"] for r in reasons}

    if ReadinessState.BLOCKED in severities:
        state = ReadinessState.BLOCKED
        summary = "Readiness blocked by failed, stale, conflicting, or policy-invalid evidence."
    elif ReadinessState.UNVERIFIED in severities:
        state = ReadinessState.UNVERIFIED
        summary = "Readiness cannot be verified; missing or unverified evidence."
    elif ReadinessState.PENDING in severities:
        state = ReadinessState.PENDING
        summary = "Readiness pending: required evidence is incomplete but not failed."
    else:
        # only allow READY_FOR_HUMAN_REVIEW when all required evidence is present and passing
        has_required_checks = bool(ev.required_checks) and not checks_summary["missing_required"] and not checks_summary["failing_required"] and not checks_summary["pending_required"] and not checks_summary["unknown_required"]
        security_ok = security_summary["present"] and not security_summary["failing"] and not security_summary["pending"] and not security_summary["unknown"]
        approvals_ok = approvals_summary["authoritative_count"] >= ev.required_approvals
        if has_required_checks and security_ok and approvals_ok and ev.head_sha and ev.pr.get("branch"):
            state = ReadinessState.READY_FOR_HUMAN_REVIEW
            summary = "Evidence satisfies deterministic checks; human review required before merge."
        else:
            state = ReadinessState.UNVERIFIED
            summary = "Required evidence incomplete; readiness is UNVERIFIED."
            reasons.append(_reason("INSUFFICIENT_VERIFIED_EVIDENCE", "Not all required evidence is verified", "evaluation", "UNVERIFIED"))
            reasons = _dedupe_reasons(reasons)

    report = {
        "schema_version": 1,
        "engine": "devobs.governance.pr_readiness",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "state": state,
        "summary": summary,
        "pr": ev.pr,
        "policy": {
            "required_checks": sorted(ev.required_checks),
            "required_approvals": ev.required_approvals,
            "protected_branch": ev.protected_branch,
        },
        "checks": checks_summary,
        "security": security_summary,
        "approvals": approvals_summary,
        "reasons": sorted(reasons, key=lambda r: (r["severity"], r["code"], r["source"], r["message"])),
    }
    return redact_sensitive(report)


def render_markdown_report(report: Mapping[str, Any]) -> str:
    """Render a human-readable Markdown summary. No approval/merge actions."""
    r = json.loads(json.dumps(report))
    lines = [
        f"# PR Readiness Report",
        "",
        f"- **State:** `{r.get('state', 'UNVERIFIED')}`",
        f"- **Generated:** {r.get('generated_at', '')}",
        f"- **Summary:** {r.get('summary', '')}",
        "",
        "## Pull Request",
    ]
    pr = r.get("pr", {}) if isinstance(r.get("pr"), dict) else {}
    lines += [
        f"- Branch: `{pr.get('branch', '')}`",
        f"- Base: `{pr.get('base', '')}`",
        f"- Head SHA: `{pr.get('head_sha', '')}`",
        "",
        "## Evidence",
    ]
    checks = r.get("checks", {}) if isinstance(r.get("checks"), dict) else {}
    sec = r.get("security", {}) if isinstance(r.get("security"), dict) else {}
    appr = r.get("approvals", {}) if isinstance(r.get("approvals"), dict) else {}
    lines += [
        f"- Required checks passing: {len(checks.get('passing_required', []))}/{checks.get('required_total', 0)}",
        f"- Missing required checks: {', '.join(checks.get('missing_required', [])) or 'none'}",
        f"- Failing required checks: {', '.join(checks.get('failing_required', [])) or 'none'}",
        f"- Pending required checks: {', '.join(checks.get('pending_required', [])) or 'none'}",
        f"- Security evidence present: {sec.get('present', False)}; failing: {', '.join(sec.get('failing', [])) or 'none'}",
        f"- Authoritative approvals: {appr.get('authoritative_count', 0)}/{appr.get('required', 0)}",
        "",
        "## Reasons",
    ]
    reasons = r.get("reasons", []) if isinstance(r.get("reasons"), list) else []
    if not reasons:
        lines.append("- None")
    else:
        for reason in reasons:
            if not isinstance(reason, dict):
                continue
            lines.append(
                f"- [{reason.get('severity','')}] `{reason.get('code','')}` ({reason.get('source','')}): {reason.get('message','')}"
            )
    lines += [
        "",
        "> Deterministic, read-only evidence report. Human approval is required before merge/production changes.",
    ]
    return "\n".join(lines) + "\n"

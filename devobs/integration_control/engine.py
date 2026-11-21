"""Deterministic integration decision engine."""

from __future__ import annotations

from typing import Any

from .advisory import build_advisory
from .coordination import evaluate_coordination
from .evidence_registry import build_registry
from .models import BLOCKED, NEEDS_EVIDENCE, POLICY_VIOLATION, READY_FOR_HUMAN_REVIEW, Finding, MAX_FINDINGS, utc_now_iso
from .validation import ValidationError, normalize_input, redact

SUCCESS = {"success", "passed", "pass", "completed/success"}
FAIL = {"failure", "failed", "cancelled", "timed_out", "action_required", "error"}
PENDING = {"pending", "queued", "in_progress", "waiting", "requested", ""}
SEC_FAIL = {"high", "critical"}


def _add(findings: list[Finding], code: str, severity: str, category: str, message: str, evidence: dict | None = None) -> None:
    if len(findings) < MAX_FINDINGS:
        findings.append(Finding(code, severity, category, message, redact(evidence or {})))


def build_failure_report(
    code: str,
    message: str,
    *,
    category: str = "validation",
    advisory_provider: Any | None = None,
) -> dict[str, Any]:
    """Build a fail-closed report when evidence cannot be collected or parsed."""

    report = {
        "schema_version": 1,
        "engine": "devobs.integration_control",
        "generated_at": utc_now_iso(),
        "decision": NEEDS_EVIDENCE,
        "human_review_required": True,
        "summary": "Integration evidence unavailable; fail closed.",
        "findings": [Finding(code, "error", category, message).as_dict()],
        "evidence_registry": [],
        "recommended_next_action": "Collect verified evidence and rerun the integration check.",
    }
    report["advisory"] = build_advisory(report, advisory_provider)
    return redact(report)


def evaluate_integration(raw: Any, advisory_provider: Any | None = None) -> dict[str, Any]:
    findings: list[Finding] = []
    try:
        ev = normalize_input(raw)
    except ValidationError as exc:
        return build_failure_report("MALFORMED_INPUT", str(exc), advisory_provider=advisory_provider)

    repo, base, head = ev.get("repository"), ev.get("base_branch"), ev.get("head_branch")
    head_sha, reviewed_sha = ev.get("head_sha"), ev.get("reviewed_head_sha")
    if not repo: _add(findings, "MISSING_REPOSITORY", "error", "identity", "Repository identity missing.")
    if not ev.get("pr_number"): _add(findings, "MISSING_PR_NUMBER", "error", "identity", "PR number missing.")
    if not base: _add(findings, "MISSING_BASE_BRANCH", "error", "identity", "Base branch missing.")
    if not head: _add(findings, "MISSING_HEAD_BRANCH", "error", "identity", "Head branch missing.")
    if head in {"main", "master"}: _add(findings, "POLICY_VIOLATION", "error", "policy", "Protected branch cannot be head.")
    if not head_sha: _add(findings, "MISSING_HEAD_SHA", "error", "identity", "Head SHA missing.")
    if not reviewed_sha: _add(findings, "MISSING_REVIEWED_HEAD_SHA", "error", "identity", "Reviewed SHA missing.")
    if head_sha and reviewed_sha and head_sha != reviewed_sha:
        _add(findings, "STALE_HEAD_SHA", "error", "identity", "Reviewed SHA differs from current head SHA.", {"head_sha": head_sha, "reviewed_head_sha": reviewed_sha})

    mergeable, merge_state = ev.get("mergeable"), ev.get("merge_state")
    if mergeable is None or merge_state in {None, "", "unknown"}:
        _add(findings, "MERGE_EVIDENCE_UNAVAILABLE", "error", "pr", "Mergeability evidence unavailable.")
    elif mergeable is False or merge_state in {"dirty", "blocked"}:
        _add(findings, "MERGE_CONFLICT", "error", "pr", "Merge conflict / blocked merge state.", {"merge_state": merge_state})

    required = ev.get("required_checks", [])
    checks = ev.get("checks", [])
    by_name = {str(c.get("name", "")).lower(): c for c in checks}
    if not required:
        _add(findings, "MISSING_REQUIRED_CHECKS_POLICY", "error", "ci", "Required checks policy unavailable.")
    if not checks:
        _add(findings, "CI_EVIDENCE_UNAVAILABLE", "error", "ci", "CI evidence unavailable.")
    for req in required:
        c = by_name.get(req.lower())
        if not c:
            _add(findings, "MISSING_REQUIRED_CHECK", "error", "ci", f"Missing required check: {req}", {"check": req})
            continue
        if c.get("head_sha") and head_sha and c["head_sha"] != head_sha:
            _add(findings, "STALE_HEAD_SHA", "error", "ci", f"Check evidence stale for {req}", {"check": req})
            continue
        status, conclusion = c.get("status", ""), c.get("conclusion", "")
        if status in FAIL or conclusion in FAIL:
            _add(findings, "FAILED_CI", "error", "ci", f"Required check failed: {req}", {"check": req})
        elif status in PENDING or conclusion in PENDING:
            _add(findings, "PENDING_CI", "error", "ci", f"Required check pending: {req}", {"check": req})
        elif conclusion in SUCCESS or status in SUCCESS:
            pass
        else:
            _add(findings, "CI_EVIDENCE_UNAVAILABLE", "error", "ci", f"Unknown check state: {req}", {"check": req, "status": status, "conclusion": conclusion})

    sec = ev.get("security_findings", [])
    if not sec:
        _add(findings, "SECURITY_EVIDENCE_MISSING", "error", "security", "Security scan evidence missing.")
    for s in sec:
        if s.get("head_sha") and head_sha and s["head_sha"] != head_sha:
            _add(findings, "STALE_HEAD_SHA", "error", "security", f"Security evidence stale: {s.get('tool')}")
        st, sev = s.get("status", "unknown"), s.get("severity", "unknown")
        if st in FAIL or sev in SEC_FAIL:
            _add(findings, "SECURITY_POLICY_VIOLATION", "error", "security", f"Security violation: {s.get('tool')}", s)
        elif st not in {"pass", "passed", "success"}:
            _add(findings, "SECURITY_EVIDENCE_MISSING", "error", "security", f"Security evidence unavailable: {s.get('tool')}", s)

    deps = ev.get("dependency_results", [])
    if not deps:
        _add(findings, "DEPENDENCY_EVIDENCE_MISSING", "error", "dependency", "Dependency evidence missing.")
    for d in deps if isinstance(deps, list) else []:
        if isinstance(d, dict):
            st = str(d.get("status", "unknown")).lower()
            if st in FAIL:
                _add(findings, "DEPENDENCY_POLICY_VIOLATION", "error", "dependency", "Dependency check failed.", d)
            elif st not in {"pass", "passed", "success", "ok", "up_to_date"}:
                _add(findings, "DEPENDENCY_EVIDENCE_MISSING", "error", "dependency", "Dependency evidence unavailable.", d)

    reviews = ev.get("reviews", {})
    if not reviews.get("human_approval") and not reviews.get("approved") and (reviews.get("approvals_count") or 0) < (reviews.get("required_approvals") or 1):
        _add(findings, "MISSING_HUMAN_APPROVAL", "error", "reviews", "Required human approval evidence missing.")



    pr_text = ev.get("untrusted_pr_text") or ""
    if pr_text:
        # treat as untrusted; do not execute. flag suspicious patterns as advisory-only finding.
        if any(x in pr_text.lower() for x in ["curl ", "wget ", "powershell", "bash -c", "rm -rf", "invoke-expression"]):
            _add(findings, "UNTRUSTED_PR_TEXT", "warning", "security", "Untrusted PR text contains command-like patterns; ignored and never executed.")

    coordination = evaluate_coordination(ev, findings)
    registry = build_registry(ev, findings)

    codes = {f.code for f in findings}
    policy_codes = {"POLICY_VIOLATION", "SECURITY_POLICY_VIOLATION", "DEPENDENCY_POLICY_VIOLATION", "STALE_HEAD_SHA", "CONCURRENT_FILE_OWNERSHIP", "CONFLICTING_BRANCH_OWNERSHIP", "INVALID_DEPENDENCY_GRAPH", "BLOCKED_TASK_OWNERSHIP_CONFLICT", "STALE_WORKSPACE_EVIDENCE", "CONTRADICTORY_EVIDENCE", "DUPLICATE_EVIDENCE", "UNVERIFIABLE_EVIDENCE"}
    blocked_codes = {"FAILED_CI", "PENDING_CI", "MERGE_CONFLICT"}
    needs_codes = {"MISSING_REPOSITORY", "MISSING_PR_NUMBER", "MISSING_BASE_BRANCH", "MISSING_HEAD_BRANCH", "MISSING_HEAD_SHA", "MISSING_REVIEWED_HEAD_SHA", "MERGE_EVIDENCE_UNAVAILABLE", "MISSING_REQUIRED_CHECKS_POLICY", "MISSING_REQUIRED_CHECK", "CI_EVIDENCE_UNAVAILABLE", "SECURITY_EVIDENCE_MISSING", "DEPENDENCY_EVIDENCE_MISSING", "MISSING_HUMAN_APPROVAL", "MALFORMED_EVIDENCE_RECORD"}

    if codes & policy_codes:
        decision = POLICY_VIOLATION
        next_action = "Resolve policy/security/ownership/evidence violations and recollect fresh evidence for current head SHA."
    elif codes & blocked_codes:
        decision = BLOCKED
        next_action = "Resolve failing/pending CI or merge conflicts before requesting human review."
    elif codes & needs_codes or findings:
        decision = NEEDS_EVIDENCE
        next_action = "Collect missing verified evidence; do not infer success."
    else:
        decision = READY_FOR_HUMAN_REVIEW
        next_action = "Ready for human review only; human approval required before merge."

    report = {
        "schema_version": 1,
        "engine": "devobs.integration_control",
        "generated_at": utc_now_iso(),
        "repository": {"name": repo, "pr_number": ev.get("pr_number"), "base_branch": base, "head_branch": head, "head_sha": head_sha, "reviewed_head_sha": reviewed_sha},
        "decision": decision,
        "human_review_required": True,
        "summary": f"Deterministic decision={decision}; findings={len(findings)}.",
        "findings": [f.as_dict() for f in findings],
        "evidence_registry": registry,
        "coordination": coordination,
        "recommended_next_action": next_action,
        "untrusted_pr_text_handling": {"accepted": ev.get("untrusted_pr_text") is not None, "executed": False, "redacted": True},
    }
    report["advisory"] = build_advisory(report, advisory_provider)
    return redact(report)

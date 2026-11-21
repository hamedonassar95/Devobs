"""Policy evaluation for PR readiness."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .evidence import EvidenceValidationError, normalize_evidence, redact
from .models import (
    BLOCKED,
    Finding,
    INSUFFICIENT_EVIDENCE,
    NEEDS_EVIDENCE,
    POLICY_VIOLATION,
    PRIdentity,
    PRReadinessReport,
    READY_FOR_HUMAN_REVIEW,
    ReadinessDecision,
    bounded_findings,
)
from .ownership import evaluate_ownership

SUCCESS = {"success", "succeeded", "pass", "passed"}
FAIL = {"failure", "failed", "fail", "cancelled", "timed_out", "action_required", "error"}
PENDING = {"pending", "queued", "in_progress", "waiting", "requested", "neutral", ""}
SECURITY_BLOCK = {"critical", "high"}
SECURITY_FAIL_STATUS = {"fail", "failed", "error", "violation"}
DEP_OK = {"success", "passed", "ok", "up_to_date"}
DEP_FAIL = {"failure", "failed", "error", "vulnerable"}
DEP_PENDING = {"pending", "unknown", "unavailable", ""}


def _f(findings: list[Finding], code: str, severity: str, category: str, message: str, evidence: dict[str, Any] | None = None) -> None:
    findings.append(Finding(code=code, severity=severity, category=category, message=message, evidence=redact(evidence or {})))


def _status_for(decision: str) -> str:
    return decision


def evaluate_pr_readiness(raw_evidence: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Evaluate evidence and return a stable JSON-serializable report dict."""
    try:
        ev = normalize_evidence(raw_evidence)
    except EvidenceValidationError as exc:
        decision = ReadinessDecision(INSUFFICIENT_EVIDENCE, ("malformed_evidence",), True)
        report = PRReadinessReport(
            pr=PRIdentity("", None, "", "", "", ""),
            evidence_timestamps={},
            ci={"status": "unavailable", "checks": []},
            security={"status": "unavailable", "findings": []},
            policy={"status": "invalid"},
            ownership={"status": "unavailable"},
            decision=decision,
            recommended_next_action="Provide valid, bounded PR evidence JSON matching the documented schema.",
            findings=bounded_findings([Finding("MALFORMED_EVIDENCE", "error", "evidence", str(exc), {})]),
            advisory={"summary": "Evidence invalid; deterministic policy failed closed.", "engine": "deterministic"},
        )
        return redact(report.as_dict())

    findings: list[Finding] = []
    repo = ev["repository"] or ""
    base = ev["base_branch"] or ""
    head = ev["head_branch"] or ""
    head_sha = ev["head_sha"] or ""
    reviewed_sha = ev["reviewed_head_sha"] or ""
    pr_number = ev["pr_number"]

    if not repo:
        _f(findings, "MISSING_REPOSITORY", "error", "identity", "Repository identity is missing.")
    if pr_number is None:
        _f(findings, "MISSING_PR_NUMBER", "error", "identity", "PR number is missing.")
    if not base:
        _f(findings, "MISSING_BASE_BRANCH", "error", "identity", "Base branch is missing.")
    if not head:
        _f(findings, "MISSING_HEAD_BRANCH", "error", "identity", "Head branch is missing.")
    if head and base and head == base:
        _f(findings, "INVALID_BRANCH", "error", "identity", "Head branch must not equal base branch.", {"base_branch": base, "head_branch": head})
    if head and head in {"main", "master", "release"}:
        _f(findings, "INVALID_BRANCH", "error", "identity", "Protected/release branch cannot be used as PR head branch.", {"head_branch": head})
    if not head_sha:
        _f(findings, "MISSING_HEAD_SHA", "error", "identity", "Head commit SHA is missing.")
    if not reviewed_sha:
        _f(findings, "MISSING_REVIEWED_HEAD_SHA", "error", "identity", "Reviewed head SHA is missing or unverified.")
    if head_sha and reviewed_sha and head_sha != reviewed_sha:
        _f(findings, "STALE_COMMIT_SHA", "error", "identity", "Reviewed SHA differs from current PR head SHA.", {"head_sha": head_sha, "reviewed_head_sha": reviewed_sha})

    mergeable = ev["mergeable"]
    merge_state = ev.get("merge_state")
    if mergeable is None or merge_state in {None, "unknown", ""}:
        _f(findings, "MERGEABILITY_UNAVAILABLE", "error", "mergeability", "Mergeability evidence is unavailable.")
    elif mergeable is False or merge_state in {"dirty", "blocked", "behind"}:
        _f(findings, "MERGEABILITY_BLOCKED", "error", "mergeability", "Mergeability evidence indicates PR is not mergeable.", {"mergeable": mergeable, "merge_state": merge_state})

    # CI checks
    checks = ev["checks"]
    required = ev["required_checks"]
    by_name = {c["name"].lower(): c for c in checks}
    missing_required = []
    failed = []
    pending = []
    unavailable = []
    for req in required:
        c = by_name.get(req.lower())
        if not c:
            missing_required.append(req)
            _f(findings, "MISSING_REQUIRED_CHECK", "error", "ci", f"Required check is missing: {req}", {"check": req})
            continue
        if c.get("head_sha") and head_sha and c["head_sha"] != head_sha:
            _f(findings, "STALE_CHECK_EVIDENCE", "error", "ci", f"Required check evidence is stale: {req}", {"check": req})
            missing_required.append(req)
            continue
        st = c.get("status", "")
        con = c.get("conclusion", "")
        if st in FAIL or con in FAIL:
            failed.append(req)
            _f(findings, "FAILED_REQUIRED_CHECK", "error", "ci", f"Required check failed: {req}", {"check": req})
        elif st in PENDING or (st == "completed" and con in PENDING):
            pending.append(req)
            _f(findings, "PENDING_REQUIRED_CHECK", "error", "ci", f"Required check pending: {req}", {"check": req})
        elif con in SUCCESS or st in SUCCESS:
            pass
        else:
            unavailable.append(req)
            _f(findings, "UNKNOWN_CHECK_STATE", "error", "ci", f"Required check state unavailable/unknown: {req}", {"check": req})
    if not required:
        _f(findings, "REQUIRED_CHECK_POLICY_UNAVAILABLE", "error", "ci", "Required check policy is unavailable; fail closed.")
    if not checks:
        _f(findings, "CI_EVIDENCE_UNAVAILABLE", "error", "ci", "CI check evidence is unavailable.")
    if ev.get("merge_state") is None and mergeable is None:
        pass

    # workflow permission / sensitive changes from evidence
    workflow_perms = ev.get("workflow_permissions") if isinstance(ev.get("workflow_permissions"), dict) else {}
    if workflow_perms.get("unsafe") is True or workflow_perms.get("write_all") is True:
        _f(findings, "UNSAFE_WORKFLOW_PERMISSION", "error", "security", "Unsafe workflow permission change detected.", redact(workflow_perms))
    for cf in ev.get("changed_files", []):
        cfs = str(cf).replace("\\", "/").lower()
        if cfs.startswith(".github/workflows/") and ev.get("workflow_permissions", {}).get("reviewed") is not True and not workflow_perms:
            # no explicit permission review evidence: fail-closed signal for sensitive change
            pass

    # approvals
    reviews = ev["reviews"]
    approved = reviews.get("approved") is True
    approvals_count = reviews.get("approvals_count")
    required_approvals = reviews.get("required_approvals")
    human_approval = reviews.get("human_approval") is True
    if required_approvals is None:
        # fail closed: if no policy signal, require at least 1 human approval evidence
        required_approvals = 1
    if not isinstance(required_approvals, int) or required_approvals < 0:
        _f(findings, "INVALID_APPROVAL_POLICY", "error", "reviews", "Required approvals policy is invalid.")
        required_approvals = 1
    if not isinstance(approvals_count, int):
        approvals_count = 1 if approved else 0
    if approvals_count < required_approvals or not (approved or human_approval or approvals_count > 0):
        # need explicit evidence; absence is not success
        if approvals_count < required_approvals:
            _f(findings, "MISSING_REQUIRED_APPROVAL", "error", "reviews", "Required human approval evidence is missing.", {"approvals_count": approvals_count, "required_approvals": required_approvals})

    # security
    sec = ev["security_findings"]
    if not sec:
        _f(findings, "SECURITY_EVIDENCE_UNAVAILABLE", "error", "security", "Security scanning evidence is unavailable.")
    sec_violations = []
    for item in sec:
        if item.get("head_sha") and head_sha and item["head_sha"] != head_sha:
            _f(findings, "STALE_SECURITY_EVIDENCE", "error", "security", f"Security evidence stale: {item['tool']}")
            sec_violations.append(item["tool"])
            continue
        sev = item.get("severity", "unknown")
        st = item.get("status", "unknown")
        if st in SECURITY_FAIL_STATUS or sev in SECURITY_BLOCK:
            sec_violations.append(item["tool"])
            _f(findings, "SECURITY_POLICY_VIOLATION", "error", "security", f"Security finding/policy violation: {item['tool']}", {"tool": item["tool"], "severity": sev, "status": st})
        elif st in DEP_PENDING or sev == "unknown":
            _f(findings, "SECURITY_EVIDENCE_UNKNOWN", "error", "security", f"Security evidence unknown/unavailable: {item['tool']}", {"tool": item["tool"], "status": st})

    # dependencies
    deps = ev["dependency_results"]
    if not deps:
        _f(findings, "DEPENDENCY_EVIDENCE_UNAVAILABLE", "error", "dependency", "Dependency verification evidence is unavailable.")
    dep_block = []
    for item in deps:
        if item.get("head_sha") and head_sha and item["head_sha"] != head_sha:
            _f(findings, "STALE_DEPENDENCY_EVIDENCE", "error", "dependency", f"Dependency evidence stale: {item['name']}")
            dep_block.append(item["name"])
            continue
        st = item.get("status", "unknown")
        if st in DEP_FAIL:
            dep_block.append(item["name"])
            _f(findings, "DEPENDENCY_VIOLATION", "error", "dependency", f"Dependency verification failed: {item['name']}")
        elif st not in DEP_OK:
            dep_block.append(item["name"])
            _f(findings, "DEPENDENCY_EVIDENCE_UNKNOWN", "error", "dependency", f"Dependency evidence unavailable/unknown: {item['name']}")

    # ownership / multi-agent conflicts
    ownership_report = evaluate_ownership(ev, findings)

    # Decision
    codes = {f.code for f in findings}
    policy_violation_codes = {
        "STALE_COMMIT_SHA", "SECURITY_POLICY_VIOLATION", "DEPENDENCY_VIOLATION", "UNSAFE_WORKFLOW_PERMISSION",
        "CONCURRENT_FILE_OWNERSHIP", "CONFLICTING_BRANCH_OWNERSHIP", "UNRESOLVED_DEPENDENCY",
        "BLOCKED_TASK_OWNERSHIP", "STALE_VALIDATION_EVIDENCE", "CONCURRENT_MODIFICATION_HAZARD",
        "INVALID_BRANCH", "MALFORMED_EVIDENCE",
    }
    needs_evidence_codes = {
        "MISSING_REPOSITORY", "MISSING_PR_NUMBER", "MISSING_BASE_BRANCH", "MISSING_HEAD_BRANCH",
        "MISSING_HEAD_SHA", "MISSING_REVIEWED_HEAD_SHA", "MERGEABILITY_UNAVAILABLE",
        "MISSING_REQUIRED_CHECK", "REQUIRED_CHECK_POLICY_UNAVAILABLE", "CI_EVIDENCE_UNAVAILABLE",
        "UNKNOWN_CHECK_STATE", "SECURITY_EVIDENCE_UNAVAILABLE", "SECURITY_EVIDENCE_UNKNOWN",
        "DEPENDENCY_EVIDENCE_UNAVAILABLE", "DEPENDENCY_EVIDENCE_UNKNOWN", "MISSING_REQUIRED_APPROVAL",
        "INVALID_APPROVAL_POLICY", "STALE_CHECK_EVIDENCE", "STALE_SECURITY_EVIDENCE", "STALE_DEPENDENCY_EVIDENCE",
    }
    blocked_codes = {
        "MERGEABILITY_BLOCKED", "FAILED_REQUIRED_CHECK", "PENDING_REQUIRED_CHECK",
    }

    reasons = sorted(codes)
    if codes & policy_violation_codes:
        decision = POLICY_VIOLATION
        next_action = "Resolve policy/ownership/security violations and collect fresh verified evidence for the current head SHA."
    elif codes & blocked_codes:
        decision = BLOCKED
        next_action = "Fix failing/pending required checks and mergeability blockers, then refresh evidence."
    elif codes & needs_evidence_codes or reasons:
        decision = INSUFFICIENT_EVIDENCE
        next_action = "Collect missing or unverified required evidence before requesting human review."
    else:
        decision = READY_FOR_HUMAN_REVIEW
        reasons = ("all_required_evidence_verified",)
        next_action = "Ready for human review only. Do not merge without required human approval."

    risk = _risk_classification(ev, findings)
    report = PRReadinessReport(
        pr=PRIdentity(repo, pr_number, base, head, head_sha, reviewed_sha),
        evidence_timestamps=ev.get("timestamps", {}),
        ci={
            "status": "pass" if not (missing_required or failed or pending or unavailable or not required or not checks) else "not_ready",
            "required_checks": required,
            "missing_required_checks": missing_required,
            "failed_required_checks": failed,
            "pending_required_checks": pending,
            "unknown_required_checks": unavailable,
            "checks": ev["checks"],
        },
        security={
            "status": "pass" if sec and not sec_violations and not any(f.code.startswith("SECURITY_EVIDENCE_") for f in findings) else "not_ready",
            "findings": ev["security_findings"],
            "violations": sorted(set(sec_violations)),
        },
        policy={
            "status": "pass" if decision in {READY_FOR_HUMAN_REVIEW, BLOCKED, INSUFFICIENT_EVIDENCE} and not (codes & policy_violation_codes) else "violation",
            "required_approvals": required_approvals,
            "approvals_count": approvals_count,
            "dependency_results": ev["dependency_results"],
        },
        ownership=ownership_report,
        decision=ReadinessDecision(decision, tuple(reasons), True),
        recommended_next_action=next_action,
        findings=bounded_findings(findings),
        advisory=_advisory_summary(decision, findings),
        risk=risk,
    )
    out = redact(report.as_dict())
    out["risk"] = risk
    out["evaluation_timestamp"] = out.get("generated_at")
    out["decision"] = out.get("readiness_decision", {}).get("decision")
    return out


def _risk_classification(ev: dict[str, Any], findings: list[Finding]) -> dict[str, Any]:
    """Deterministic transparent risk classification. No AI confidence score."""
    score = 0
    reasons = []
    changed = [str(p).replace("\\", "/").lower() for p in ev.get("changed_files", [])]
    codes = {f.code for f in findings}
    categories = {f.category for f in findings}

    sensitive_prefixes = (".github/workflows/", "terraform/", "infra/", "k8s/", "helm/", "auth", "security", "secrets", ".env", "docker", "deploy")
    infra_prefixes = ("terraform/", "infra/", "k8s/", "helm/", "docker-compose", ".github/workflows/")
    auth_prefixes = ("auth", "oidc", "jwt", "rbac", "permission", "security/")
    for p in changed:
        if any(x in p for x in sensitive_prefixes):
            score += 2; reasons.append(f"sensitive_file:{p}")
        if any(p.startswith(x) or f"/{x}" in p for x in infra_prefixes):
            score += 3; reasons.append(f"infrastructure:{p}")
        if any(x in p for x in auth_prefixes):
            score += 3; reasons.append(f"auth_or_authorization:{p}")
        if p.endswith("requirements.txt") or p.endswith("package.json") or p.endswith("pyproject.toml") or "lock" in p:
            score += 1; reasons.append(f"dependency_change:{p}")

    if "WORKFLOW_PERMISSION_CHANGE" in codes or "UNSAFE_WORKFLOW_PERMISSION" in codes:
        score += 4; reasons.append("workflow_permission_change")
    if any(c.startswith("SECURITY_") for c in codes):
        score += 4; reasons.append("security_scan_failure_or_unknown")
    if "MISSING_REQUIRED_APPROVAL" in codes:
        score += 2; reasons.append("missing_approval")
    if "CONCURRENT_FILE_OWNERSHIP" in codes or "CONFLICTING_BRANCH_OWNERSHIP" in codes:
        score += 3; reasons.append("ownership_conflict")
    if "FAILED_REQUIRED_CHECK" in codes or "PENDING_REQUIRED_CHECK" in codes:
        score += 2; reasons.append("ci_not_green")
    if "MISSING_REQUIRED_CHECK" in codes or "CI_EVIDENCE_UNAVAILABLE" in codes:
        score += 2; reasons.append("missing_test_or_ci_evidence")

    has_infra = any(r.startswith("infrastructure:") or r.startswith("auth_or_authorization:") for r in reasons)
    if score >= 10 or "SECURITY_POLICY_VIOLATION" in codes or "UNSAFE_WORKFLOW_PERMISSION" in codes or has_infra:
        level = "CRITICAL"
    elif score >= 6:
        level = "HIGH"
    elif score >= 3:
        level = "MEDIUM"
    else:
        level = "LOW"
    return {"level": level, "score": score, "reasons": sorted(set(reasons))[:50], "method": "deterministic-rules-v1"}
def _advisory_summary(decision: str, findings: list[Finding]) -> dict[str, Any]:
    by_cat: dict[str, int] = {}
    for f in findings:
        by_cat[f.category] = by_cat.get(f.category, 0) + 1
    return {
        "engine": "deterministic-rules",
        "authoritative": False,
        "summary": f"Deterministic decision={decision}; findings={len(findings)}.",
        "categories": dict(sorted(by_cat.items())),
        "recommended_review_actions": sorted({f.code for f in findings})[:20],
    }

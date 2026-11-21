"""Deterministic offline portfolio health evaluator. Fail-closed, advisory only."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from scripts.ci_failure_intelligence import classify_failure

from .collector import CollectionError, collect_snapshot, redact_obj
from .models import (
    BLOCKED,
    DEGRADED,
    FRESH,
    Finding,
    MISSING,
    POLICY_VERSION,
    READY,
    SCHEMA_VERSION,
    SEVERITY_RANK,
    STALE,
    UNKNOWN,
    clip,
    iso_now,
)


def _f(findings: list[Finding], *args: Any, **kwargs: Any) -> None:
    if len(findings) < 500:
        findings.append(Finding(*args, **kwargs))


def _score(findings: list[Finding]) -> dict[str, Any]:
    penalties = {"CRITICAL": 35, "HIGH": 20, "MEDIUM": 10, "LOW": 3, "INFO": 0}
    score = 100
    for item in findings:
        score -= penalties.get(item.severity, 10)
    score = max(0, min(100, score))
    return {"score": score, "scale": "0-100", "method": "deterministic_penalty_v1"}


def _evidence_index(evidence: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(e.get("evidence_id")): e for e in evidence}


def _eval_evidence(snapshot: dict[str, Any], findings: list[Finding]) -> dict[str, Any]:
    evidence = snapshot["evidence"]
    counts = {FRESH: 0, STALE: 0, MISSING: 0, UNKNOWN: 0}
    for e in evidence:
        st = str(e.get("freshness", UNKNOWN))
        counts[st] = counts.get(st, 0) + 1
        if st == STALE:
            _f(findings, "STALE_EVIDENCE", "HIGH", "evidence", f"Evidence {e['evidence_id']} is stale", evidence_ids=(e["evidence_id"],), remediation="Refresh evidence from authoritative source and re-run evaluation.")
        elif st == UNKNOWN:
            _f(findings, "UNKNOWN_EVIDENCE_FRESHNESS", "MEDIUM", "evidence", f"Evidence {e['evidence_id']} freshness unknown", evidence_ids=(e["evidence_id"],), remediation="Provide ISO-8601 observed_at and source for evidence.")
    if not evidence:
        _f(findings, "MISSING_EVIDENCE", "HIGH", "evidence", "No evidence records provided", remediation="Collect read-only evidence artifacts before making readiness claims.")
    return {"total": len(evidence), "counts": counts}


def _eval_ci(snapshot: dict[str, Any], findings: list[Finding]) -> dict[str, Any]:
    checks = snapshot["ci_checks"]
    failed = pending = missing = 0
    classifications = []
    for c in checks:
        status = str(c.get("status", UNKNOWN)).upper()
        name = str(c.get("name", "unknown"))
        if status in {"FAIL", "FAILED", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED"}:
            failed += 1
            cls = classify_failure(str(c.get("log_excerpt", "")), job_name=name)
            classifications.append({"check": name, "status": status, "classification": cls["category"], "confidence": cls["confidence"], "signature": cls["signature_name"]})
            sev = "CRITICAL" if c.get("required") else "HIGH"
            _f(findings, "CI_CHECK_FAILED", sev, "ci", f"CI check failed: {name}", remediation="Inspect verified CI logs/evidence; fix root cause before human review.")
        elif status in {"PENDING", "QUEUED", "IN_PROGRESS", "WAITING", "REQUESTED"}:
            pending += 1
            _f(findings, "CI_CHECK_PENDING", "HIGH" if c.get("required") else "MEDIUM", "ci", f"CI check pending: {name}", remediation="Wait for authoritative CI completion evidence.")
        elif status in {UNKNOWN, "", "MISSING"}:
            missing += 1
            _f(findings, "CI_CHECK_UNKNOWN", "HIGH" if c.get("required") else "MEDIUM", "ci", f"CI check status unknown: {name}", remediation="Collect CI status evidence; unknown is not passing.")
        elif status in {"PASS", "PASSED", "SUCCESS", "SKIPPED", "NEUTRAL"}:
            pass
        else:
            missing += 1
            _f(findings, "CI_CHECK_INVALID_STATUS", "MEDIUM", "ci", f"CI check has invalid status: {name}={status}", remediation="Normalize CI status from authoritative source.")
    if not checks:
        _f(findings, "CI_EVIDENCE_MISSING", "HIGH", "ci", "No CI checks provided", remediation="Provide CI evidence; absence of CI evidence fails closed.")
    return {"total": len(checks), "failed": failed, "pending": pending, "unknown": missing, "classifications": classifications}


def _eval_prs(snapshot: dict[str, Any], findings: list[Finding]) -> dict[str, Any]:
    prs = snapshot["pull_requests"]
    blocked = 0
    for pr in prs:
        num = pr.get("number", "?")
        blockers = [b for b in pr.get("blockers", []) if str(b).strip()]
        approval = str(pr.get("approval_state", UNKNOWN)).upper()
        mergeable = str(pr.get("mergeable", UNKNOWN)).upper()
        status = str(pr.get("status", UNKNOWN)).upper()
        if status in {"CLOSED", "MERGED"}:
            continue
        if pr.get("draft"):
            blockers.append("draft_pr")
        if approval in {"CHANGES_REQUESTED", "REVIEW_REQUIRED", "MISSING", UNKNOWN}:
            blockers.append(f"approval_{approval.lower()}")
        if mergeable in {"CONFLICTING", "CONFLICT", "DIRTY"}:
            blockers.append("merge_conflict")
        elif mergeable in {UNKNOWN, ""}:
            blockers.append("mergeability_unknown")
        for b in blockers:
            _f(findings, "PR_MERGE_BLOCKER", "HIGH", "pull_request", f"PR {num} blocked: {b}", component=f"PR#{num}", remediation="Resolve blocker with verified evidence and human review; do not bypass.")
        if blockers:
            blocked += 1
        if approval in {"APPROVED"} and status not in {"APPROVED", "READY"}:
            # approval alone not enough; CI/evidence still required - no finding if other evidence present, but note advisory
            pass
    if not prs:
        _f(findings, "PR_EVIDENCE_MISSING", "MEDIUM", "pull_request", "No pull request evidence provided", remediation="Provide PR metadata/evidence when assessing merge readiness.", inferred=True)
    return {"total": len(prs), "blocked": blocked}


def _eval_ownership(snapshot: dict[str, Any], findings: list[Finding]) -> dict[str, Any]:
    ownership = snapshot["ownership"]
    agents = ownership.get("active_agents", [])
    conflicts = []
    path_map: dict[str, set[str]] = {}
    branch_map: dict[str, set[str]] = {}
    for a in agents:
        agent = str(a.get("agent") or a.get("branch") or "unknown")
        for p in a.get("owned_paths", []):
            norm = str(p).replace("\\", "/").lstrip("./")
            if norm:
                path_map.setdefault(norm, set()).add(agent)
        b = str(a.get("branch", "")).strip()
        if b:
            branch_map.setdefault(b, set()).add(agent)
    for path, owners in sorted(path_map.items()):
        if len(owners) > 1:
            conflicts.append({"type": "path", "path": path, "owners": sorted(owners)})
            _f(findings, "OWNERSHIP_CONFLICT", "CRITICAL", "ownership", f"Concurrent ownership conflict on {path}", evidence_ids=(), remediation="Assign single owner or split paths; do not modify conflicting agent worktrees.")
    for branch, owners in sorted(branch_map.items()):
        if len(owners) > 1:
            conflicts.append({"type": "branch", "branch": branch, "owners": sorted(owners)})
            _f(findings, "OWNERSHIP_CONFLICT", "CRITICAL", "ownership", f"Concurrent branch ownership conflict on {branch}", remediation="Use unique branch/worktree per agent task.")
    manifest = ownership.get("task_manifest")
    if isinstance(manifest, dict):
        try:
            from scripts.check_two_agent_tasks import evaluate as eval_manifest
            result = eval_manifest(manifest)
            for c in result.get("conflicts", []) or []:
                conflicts.append({"type": "manifest_conflict", "detail": redact_obj(c)})
                _f(findings, "OWNERSHIP_CONFLICT", "CRITICAL", "ownership", "Task manifest ownership conflict detected", remediation="Resolve manifest conflict before proceeding.")
            for b in result.get("blocked_tasks", []) or []:
                _f(findings, "BLOCKED_TASK", "HIGH", "ownership", f"Blocked task: {clip(b)}", remediation="Clear task dependency/ownership blocker with verified evidence.")
            if result.get("errors"):
                _f(findings, "OWNERSHIP_MANIFEST_INVALID", "HIGH", "ownership", "Task manifest invalid", remediation="Fix task manifest schema/contract errors.")
        except Exception as exc:
            _f(findings, "OWNERSHIP_MANIFEST_ERROR", "HIGH", "ownership", f"Manifest evaluation failed: {type(exc).__name__}", remediation="Provide valid task manifest or omit it.")
    elif manifest == "INVALID":
        _f(findings, "OWNERSHIP_MANIFEST_INVALID", "HIGH", "ownership", "Task manifest has invalid type", remediation="Provide task manifest as object.")
    elif ownership.get("status") == UNKNOWN and not agents:
        _f(findings, "OWNERSHIP_UNKNOWN", "MEDIUM", "ownership", "Ownership evidence unavailable", remediation="Provide ownership/worktree/task manifest evidence.", inferred=True)
    return {"active_agents": len(agents), "conflicts": conflicts}


def _eval_dependencies(snapshot: dict[str, Any], findings: list[Finding]) -> dict[str, Any]:
    components = snapshot["components"]
    declared = set(snapshot.get("dependencies", []))
    names = {c["name"] for c in components}
    missing = []
    for c in components:
        for dep in c.get("dependencies", []):
            if dep not in names and dep not in declared:
                missing.append({"component": c["name"], "dependency": dep})
                _f(findings, "MISSING_DEPENDENCY", "HIGH", "dependency", f"{c['name']} missing dependency {dep}", component=c["name"], remediation="Provide dependency component or mark as external with verified evidence.")
    # simple cycle detection
    graph = {c["name"]: [d for d in c.get("dependencies", []) if d in names] for c in components}
    cycles = []
    temp, perm = set(), set()
    stack = []

    def visit(n: str) -> None:
        if n in perm:
            return
        if n in temp:
            if n in stack:
                cycles.append(stack[stack.index(n):] + [n])
            return
        temp.add(n); stack.append(n)
        for m in graph.get(n, []):
            visit(m)
        stack.pop(); temp.remove(n); perm.add(n)

    for n in sorted(graph):
        visit(n)
    for cyc in cycles:
        _f(findings, "DEPENDENCY_CYCLE", "CRITICAL", "dependency", f"Dependency cycle: {' -> '.join(cyc)}", remediation="Break dependency cycle; fail closed until resolved.")
    return {"missing": missing, "cycles": cycles}


def _eval_security(snapshot: dict[str, Any], findings: list[Finding]) -> dict[str, Any]:
    secs = snapshot["security_findings"]
    open_high = 0
    for s in secs:
        sev = str(s.get("severity", "HIGH")).upper()
        status = str(s.get("status", "OPEN")).upper()
        if status in {"OPEN", "UNKNOWN", "UNRESOLVED"} and sev in {"CRITICAL", "HIGH"}:
            open_high += 1
            _f(findings, "SECURITY_FINDING_OPEN", "CRITICAL" if sev == "CRITICAL" else "HIGH", "security", f"Open security finding: {s.get('id')} - {s.get('message','')}", component=str(s.get("component","")), remediation="Remediate or obtain human-approved risk acceptance with evidence; do not auto-approve.")
        elif status in {UNKNOWN, ""}:
            _f(findings, "SECURITY_FINDING_UNKNOWN", "HIGH", "security", f"Security finding status unknown: {s.get('id')}", remediation="Obtain verified scanner/evidence status.")
    return {"total": len(secs), "open_high_or_critical": open_high}


def _eval_approval(snapshot: dict[str, Any], findings: list[Finding]) -> dict[str, Any]:
    approval = snapshot.get("approval")
    if not isinstance(approval, dict):
        _f(findings, "APPROVAL_EVIDENCE_MISSING", "HIGH", "approval", "Human approval evidence missing or invalid", remediation="Obtain explicit human approval evidence before merge/deploy decisions.")
        return {"status": "MISSING"}
    status = str(approval.get("status", UNKNOWN)).upper()
    has_human = bool(approval.get("human_approved")) or status in {"APPROVED", "HUMAN_APPROVED"}
    evidence_ids = approval.get("evidence_ids") or []
    if has_human and not evidence_ids and not approval.get("approved_by"):
        _f(findings, "APPROVAL_CLAIM_UNVERIFIED", "HIGH", "approval", "Approval claim lacks verifiable evidence", remediation="Attach approval evidence ID/actor/timestamp; do not accept bare approval claims.")
        return {"status": "UNVERIFIED"}
    if not has_human or status in {UNKNOWN, "PENDING", "MISSING", "REJECTED"}:
        _f(findings, "APPROVAL_NOT_GRANTED", "MEDIUM", "approval", "Human approval not granted", remediation="Require explicit human approval before production/merge.", inferred=False)
        return {"status": status or UNKNOWN}
    return {"status": "PRESENT", "evidence_ids": evidence_ids}


def evaluate_portfolio_health(raw_snapshot: Any, *, now: datetime | None = None, max_age_seconds: int = 86400) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    findings: list[Finding] = []
    try:
        snapshot = collect_snapshot(raw_snapshot, now=now, max_age_seconds=max_age_seconds)
    except CollectionError as exc:
        _f(findings, "INVALID_INPUT", "CRITICAL", "input", f"Invalid snapshot: {clip(exc)}", remediation="Fix input schema/types/bounds and re-run.")
        snapshot = {
            "schema_version": 1, "repository": "", "generated_at": "", "evidence": [], "components": [],
            "ci_checks": [], "pull_requests": [], "ownership": {"status": UNKNOWN, "active_agents": [], "task_manifest": None},
            "security_findings": [], "dependencies": [], "approval": None, "metadata": {},
        }
    except Exception as exc:  # noqa: BLE001
        _f(findings, "EVALUATION_ERROR", "CRITICAL", "input", f"Evaluation failed: {type(exc).__name__}", remediation="Inspect input; fail closed.")
        snapshot = {"schema_version": 1, "repository": "", "generated_at": "", "evidence": [], "components": [], "ci_checks": [], "pull_requests": [], "ownership": {"status": UNKNOWN, "active_agents": [], "task_manifest": None}, "security_findings": [], "dependencies": [], "approval": None, "metadata": {}}

    evidence_summary = _eval_evidence(snapshot, findings)
    ci_summary = _eval_ci(snapshot, findings)
    pr_summary = _eval_prs(snapshot, findings)
    ownership_summary = _eval_ownership(snapshot, findings)
    dep_summary = _eval_dependencies(snapshot, findings)
    security_summary = _eval_security(snapshot, findings)
    approval_summary = _eval_approval(snapshot, findings)

    # readiness decision - fail closed
    codes = {f.code for f in findings}
    has_critical = any(f.severity == "CRITICAL" for f in findings)
    has_high = any(f.severity == "HIGH" for f in findings)
    has_unknown = any(f.severity in {"HIGH", "MEDIUM"} and ("UNKNOWN" in f.code or "MISSING" in f.code) for f in findings)
    if "INVALID_INPUT" in codes or "EVALUATION_ERROR" in codes:
        readiness = UNKNOWN
    elif has_critical or any(c in codes for c in {"OWNERSHIP_CONFLICT", "DEPENDENCY_CYCLE", "SECURITY_FINDING_OPEN", "CI_CHECK_FAILED", "PR_MERGE_BLOCKER", "BLOCKED_TASK", "MISSING_DEPENDENCY"}):
        readiness = BLOCKED
    elif has_high or has_unknown:
        readiness = DEGRADED if not has_high else UNKNOWN
        # be fail-closed: high/unknown evidence means not ready
        if has_high:
            readiness = UNKNOWN
    else:
        readiness = READY

    # More explicit fail-closed: any unknown evidence freshness, missing evidence, unknown CI/approval -> UNKNOWN unless blocked
    if readiness != BLOCKED:
        if any(x in codes for x in {"MISSING_EVIDENCE", "CI_EVIDENCE_MISSING", "UNKNOWN_EVIDENCE_FRESHNESS", "CI_CHECK_UNKNOWN", "APPROVAL_EVIDENCE_MISSING", "APPROVAL_CLAIM_UNVERIFIED", "OWNERSHIP_UNKNOWN"}):
            readiness = UNKNOWN
        if any(f.severity == "HIGH" for f in findings) and readiness == READY:
            readiness = UNKNOWN

    score = _score(findings)
    findings_sorted = sorted(findings, key=lambda f: (SEVERITY_RANK.get(f.severity, 9), f.category, f.code, f.component, f.message))
    remediation = []
    seen_actions = set()
    for f in findings_sorted:
        if f.remediation and f.remediation not in seen_actions:
            seen_actions.add(f.remediation)
            remediation.append({"priority": f.severity, "action": f.remediation, "code": f.code, "component": f.component})

    return {
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "generated_at": iso_now(),
        "repository": snapshot.get("repository", ""),
        "readiness": readiness,
        "advisory_only": True,
        "human_review_required": True,
        "no_merge_no_deploy": True,
        "score": score,
        "summary": {
            "evidence": evidence_summary,
            "ci": ci_summary,
            "pull_requests": pr_summary,
            "ownership": ownership_summary,
            "dependencies": dep_summary,
            "security": security_summary,
            "approval": approval_summary,
        },
        "findings": [f.as_dict() for f in findings_sorted],
        "recommended_remediations": remediation[:100],
        "inputs": {
            "component_count": len(snapshot.get("components", [])),
            "evidence_count": len(snapshot.get("evidence", [])),
            "ci_check_count": len(snapshot.get("ci_checks", [])),
            "pr_count": len(snapshot.get("pull_requests", [])),
            "security_finding_count": len(snapshot.get("security_findings", [])),
        },
    }
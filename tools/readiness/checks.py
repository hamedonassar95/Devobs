"""Deterministic production readiness checks. Offline, fail-closed."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from scripts.ci_failure_intelligence import redact_secrets

from .models import Finding, MAX_ITEMS, MAX_STR, clip

SENSITIVE_RE = re.compile(r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
SAFE_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _add(findings: list[Finding], *args: Any, **kwargs: Any) -> None:
    if len(findings) < 500:
        findings.append(Finding(*args, **kwargs))


def _map(raw: Any, name: str) -> Mapping[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ValueError(f"{name} must be an object")
    return raw


def _list(raw: Any, name: str) -> list[Any]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"{name} must be a list")
    if len(raw) > MAX_ITEMS:
        raise ValueError(f"{name} exceeds limit")
    return raw


def check_cicd(snapshot: Mapping[str, Any], findings: list[Finding]) -> dict[str, Any]:
    cicd = _map(snapshot.get("cicd"), "cicd")
    required = [str(x) for x in _list(cicd.get("required_checks"), "cicd.required_checks")]
    observed = _map(cicd.get("observed_checks"), "cicd.observed_checks")
    missing = []
    for name in required:
        state = str(observed.get(name, "MISSING")).upper()
        if state in {"MISSING", "UNKNOWN", ""}:
            missing.append(name)
            _add(findings, "MISSING_REQUIRED_CI_CHECK", "HIGH", "cicd", f"Required CI check missing/unknown: {name}", remediation="Provide verified CI evidence for required check before human review.")
        elif state in {"FAIL", "FAILED", "ERROR", "CANCELLED", "TIMED_OUT"}:
            _add(findings, "CI_CHECK_FAILED", "CRITICAL", "cicd", f"Required CI check failed: {name}", remediation="Fix failing CI check and collect fresh verified evidence.")
        elif state in {"PENDING", "QUEUED", "IN_PROGRESS"}:
            _add(findings, "CI_CHECK_PENDING", "HIGH", "cicd", f"Required CI check pending: {name}", remediation="Wait for CI completion; pending is not ready.")
    if not required:
        _add(findings, "CI_REQUIRED_CHECKS_UNKNOWN", "MEDIUM", "cicd", "No required CI checks declared", remediation="Declare required CI checks from branch protection/policy evidence.", evidence={"inferred": True})
    return {"required": required, "missing_or_unknown": missing}


def check_dependencies(snapshot: Mapping[str, Any], findings: list[Finding]) -> dict[str, Any]:
    deps = _map(snapshot.get("dependencies"), "dependencies")
    components = _list(deps.get("components"), "dependencies.components")
    names = set()
    graph = {}
    for c in components:
        if not isinstance(c, Mapping):
            raise ValueError("dependencies.components item must be object")
        name = str(c.get("name", "")).strip()
        if not name:
            raise ValueError("component.name required")
        if name in names:
            _add(findings, "DUPLICATE_COMPONENT", "HIGH", "dependencies", f"Duplicate component: {name}", remediation="Remove duplicate component records.")
        names.add(name)
        reqs = [str(x) for x in _list(c.get("depends_on"), "component.depends_on")]
        graph[name] = reqs
        for r in reqs:
            if r not in names and r not in {str(x.get("name", "")) for x in components}:
                pass
    # missing deps
    missing = []
    for n, reqs in graph.items():
        for r in reqs:
            if r not in names:
                missing.append({"component": n, "dependency": r})
                _add(findings, "INCOMPLETE_DEPENDENCY_GRAPH", "HIGH", "dependencies", f"Missing dependency {r} for {n}", component=n, remediation="Declare dependency or mark external with verified evidence.")
    # cycles
    cycles = []
    temp, perm, stack = set(), set(), []

    def visit(n: str) -> None:
        if n in perm: return
        if n in temp:
            if n in stack: cycles.append(stack[stack.index(n):] + [n])
            return
        temp.add(n); stack.append(n)
        for m in graph.get(n, []):
            if m in graph: visit(m)
        stack.pop(); temp.remove(n); perm.add(n)
    for n in sorted(graph): visit(n)
    for c in cycles:
        _add(findings, "DEPENDENCY_CYCLE", "CRITICAL", "dependencies", f"Dependency cycle: {' -> '.join(c)}", remediation="Break dependency cycle before readiness.")

    vulns = _list(deps.get("vulnerabilities"), "dependencies.vulnerabilities")
    for v in vulns:
        if not isinstance(v, Mapping):
            raise ValueError("vulnerability must be object")
        sev = str(v.get("severity", "HIGH")).upper()
        if sev in {"CRITICAL", "HIGH"}:
            _add(findings, "SUPPLY_CHAIN_VULNERABILITY", "CRITICAL" if sev == "CRITICAL" else "HIGH", "dependencies", f"Dependency vulnerability: {clip(v.get('id','unknown'),80)}", remediation="Remediate or document approved risk with human approval and evidence.")
    return {"components": len(components), "missing_dependencies": missing, "cycles": cycles, "vulnerabilities": len(vulns)}


def check_secrets(snapshot: Mapping[str, Any], findings: list[Finding]) -> dict[str, Any]:
    sec = _map(snapshot.get("security"), "security")
    exposures = _list(sec.get("secret_findings"), "security.secret_findings")
    count = 0
    for e in exposures:
        if not isinstance(e, Mapping):
            raise ValueError("secret finding must be object")
        count += 1
        _add(findings, "SECRET_EXPOSURE_RISK", "CRITICAL", "security", f"Secret exposure signal: {clip(e.get('id','unknown'),80)}", remediation="Rotate/revoke secret outside repo, remove from history/artifacts as approved process, add prevention checks.")
    # scan provided text fields for obvious secret patterns
    blobs = []
    for k in ("notes", "config_text"):
        v = snapshot.get(k)
        if isinstance(v, str):
            blobs.append(v)
    for t in blobs:
        if SENSITIVE_RE.search(t):
            _add(findings, "SECRET_PATTERN_DETECTED", "CRITICAL", "security", "Potential secret pattern detected in snapshot text", remediation="Remove secret material; provide redacted evidence only.")
            count += 1
    return {"secret_signals": count}


def check_ownership(snapshot: Mapping[str, Any], findings: list[Finding]) -> dict[str, Any]:
    own = _map(snapshot.get("ownership"), "ownership")
    agents = _list(own.get("active_agents"), "ownership.active_agents")
    path_owners: dict[str, set[str]] = {}
    for a in agents:
        if not isinstance(a, Mapping):
            raise ValueError("active agent must be object")
        agent = str(a.get("agent") or a.get("id") or "unknown")
        for p in _list(a.get("owned_paths"), "owned_paths"):
            norm = str(p).replace("\\", "/").lstrip("./")
            if norm:
                path_owners.setdefault(norm, set()).add(agent)
    conflicts = []
    for p, owners in sorted(path_owners.items()):
        if len(owners) > 1:
            conflicts.append({"path": p, "owners": sorted(owners)})
            _add(findings, "AGENT_OWNERSHIP_CONFLICT", "CRITICAL", "ownership", f"Ownership conflict on {p}", evidence={"owners": sorted(owners)}, remediation="Assign single owner or split paths; do not edit conflicting files.")
    return {"active_agents": len(agents), "conflicts": conflicts}


def check_pr_risk(snapshot: Mapping[str, Any], findings: list[Finding]) -> dict[str, Any]:
    prs = _list(snapshot.get("pull_requests"), "pull_requests")
    high_risk = 0
    for pr in prs:
        if not isinstance(pr, Mapping):
            raise ValueError("pull request must be object")
        num = pr.get("number", "?")
        files = [str(x) for x in _list(pr.get("changed_files"), "changed_files")]
        risk = "LOW"
        reasons = []
        if any(f.startswith(".github/workflows/") for f in files):
            risk = "HIGH"; reasons.append("workflow_change")
        if any(f.startswith("infra/") or f.startswith("deploy/") or f.endswith(".tf") for f in files):
            risk = "HIGH"; reasons.append("deployment_infra_change")
        if any("secret" in f.lower() or "auth" in f.lower() for f in files):
            risk = "CRITICAL"; reasons.append("security_sensitive_change")
        if any(f.startswith("devobs/") or f.startswith("scripts/") for f in files) and risk == "LOW":
            risk = "MEDIUM"; reasons.append("core_logic_change")
        if pr.get("missing_tests") is True:
            if risk in {"LOW", "MEDIUM"}: risk = "HIGH"
            reasons.append("missing_tests")
        if pr.get("unverified", False):
            _add(findings, "PR_RISK_UNVERIFIED", "MEDIUM", "pr_risk", f"PR {num} has unverified risk inputs", remediation="Provide changed files, tests, CI, and review evidence.")
        if risk in {"HIGH", "CRITICAL"}:
            high_risk += 1
            _add(findings, "PR_HIGH_RISK", "HIGH" if risk == "HIGH" else "CRITICAL", "pr_risk", f"PR {num} classified {risk}", evidence={"reasons": reasons, "files": files[:20]}, remediation="Require human review, targeted tests, and verified CI before merge.")
    return {"pull_requests": len(prs), "high_risk": high_risk}


def check_deployment(snapshot: Mapping[str, Any], findings: list[Finding]) -> dict[str, Any]:
    dep = _map(snapshot.get("deployment"), "deployment")
    configs = _list(dep.get("configs"), "deployment.configs")
    unsafe = 0
    for cfg in configs:
        if not isinstance(cfg, Mapping):
            raise ValueError("deployment config must be object")
        name = str(cfg.get("name", "unknown"))
        if cfg.get("allow_unauthenticated") is True:
            unsafe += 1
            _add(findings, "UNSAFE_DEPLOYMENT_CONFIG", "CRITICAL", "deployment", f"Unauthenticated deployment exposure: {name}", remediation="Require authentication and explicit human-approved exposure review.")
        if cfg.get("debug") is True:
            unsafe += 1
            _add(findings, "UNSAFE_DEPLOYMENT_CONFIG", "HIGH", "deployment", f"Debug enabled in deployment config: {name}", remediation="Disable debug in production-bound configs.")
        if cfg.get("mutable_image_tag") is True:
            unsafe += 1
            _add(findings, "UNSAFE_DEPLOYMENT_CONFIG", "HIGH", "deployment", f"Mutable image tag in deployment config: {name}", remediation="Pin immutable image digests.")
        if cfg.get("missing_healthcheck") is True:
            _add(findings, "DEPLOYMENT_HEALTHCHECK_MISSING", "MEDIUM", "deployment", f"Healthcheck missing: {name}", remediation="Add health/readiness checks before deployment.")
    if dep.get("approval_gate") is not True:
        _add(findings, "MISSING_APPROVAL_GATE", "HIGH", "deployment", "Deployment approval gate missing/unverified", remediation="Require explicit human approval gate before deployment.")
    return {"configs": len(configs), "unsafe_signals": unsafe}


def check_observability(snapshot: Mapping[str, Any], findings: list[Finding]) -> dict[str, Any]:
    obs = _map(snapshot.get("observability"), "observability")
    signals = ["logs", "metrics", "traces", "alerts"]
    missing = []
    for s in signals:
        v = obs.get(s)
        if v is not True:
            missing.append(s)
            _add(findings, "OBSERVABILITY_GAP", "MEDIUM" if s != "alerts" else "HIGH", "observability", f"Observability signal missing/unverified: {s}", remediation=f"Provide verified {s} configuration/evidence.")
    return {"missing": missing}


def check_duplicate_tasks(snapshot: Mapping[str, Any], findings: list[Finding]) -> dict[str, Any]:
    tasks = _list(snapshot.get("tasks"), "tasks")
    seen = {}
    dups = []
    for t in tasks:
        if not isinstance(t, Mapping):
            raise ValueError("task must be object")
        tid = str(t.get("id", "")).strip()
        fingerprint = str(t.get("fingerprint", "")).strip() or tid
        if not fingerprint:
            _add(findings, "INVALID_TASK_RECORD", "MEDIUM", "tasks", "Task missing id/fingerprint", remediation="Provide stable task id/fingerprint.")
            continue
        owner = str(t.get("owner", ""))
        key = fingerprint
        if key in seen and seen[key] != owner:
            dups.append({"fingerprint": key, "owners": sorted({seen[key], owner})})
            _add(findings, "DUPLICATE_TASK_EXECUTION", "HIGH", "tasks", f"Duplicate task execution/fingerprint: {key}", evidence={"owners": sorted({seen[key], owner})}, remediation="Deduplicate task assignment and enforce single owner.")
        else:
            seen[key] = owner
    return {"tasks": len(tasks), "duplicates": dups}

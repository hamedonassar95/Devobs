"""Deterministic integration verification hub evaluator."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .contracts import ValidationError, as_mapping, redact, validate_approval, validate_component_contracts, validate_evidence
from .inventory import build_inventory
from .models import (
    BLOCKED,
    CAPABILITY_BLOCKED,
    Finding,
    INSUFFICIENT_EVIDENCE,
    MAX_FINDINGS,
    POLICY_VIOLATION,
    READY_FOR_HUMAN_REVIEW,
    SCHEMA_VERSION,
    utc_now_iso,
)
from .ownership import evaluate_ownership


def _add(findings: list[Finding], *args, **kwargs) -> None:
    if len(findings) < MAX_FINDINGS:
        findings.append(Finding(*args, **kwargs))


def _dep_graph(components: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {str(c.get("name")): [str(d) for d in c.get("integration_dependencies", []) if str(d)] for c in components if c.get("name")}


def _detect_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    # iterative DFS with path tracking; bounded by node count in tests/real usage
    cycles = []
    visited = set()
    stack = []
    for node in graph:
        if node in visited:
            continue
        # explicit stack frames: (node, iterator, in_stack_index)
        path = []
        path_set = set()
        frames = [(node, iter(graph.get(node, [])))]
        path.append(node); path_set.add(node)
        while frames:
            cur, it = frames[-1]
            try:
                nxt = next(it)
            except StopIteration:
                frames.pop()
                popped = path.pop()
                path_set.discard(popped)
                visited.add(popped)
                continue
            if nxt not in graph:
                continue
            if nxt in path_set:
                idx = path.index(nxt)
                cyc = path[idx:] + [nxt]
                if cyc not in cycles:
                    cycles.append(cyc)
                continue
            if nxt in visited:
                continue
            frames.append((nxt, iter(graph.get(nxt, []))))
            path.append(nxt); path_set.add(nxt)
    return cycles


def _dependency_findings(components: list[dict[str, Any]], findings: list[Finding]) -> dict[str, Any]:
    graph = _dep_graph(components)
    names = set(graph)
    missing = []
    for name, deps in graph.items():
        for dep in deps:
            if dep not in names:
                missing.append({"component": name, "dependency": dep})
                _add(findings, "MISSING_DEPENDENCY", "CRITICAL", "dependency", f"Component {name} missing dependency {dep}", component=name, evidence={"dependency": dep})
    cycles = _detect_cycles(graph)
    for cyc in cycles:
        _add(findings, "CYCLIC_DEPENDENCY", "CRITICAL", "dependency", "Cyclic dependency detected", evidence={"cycle": cyc})
    status_by_name = {str(c.get("name")): str(c.get("verification_status")) for c in components}
    blocked = []
    for name, deps in graph.items():
        for dep in deps:
            st = status_by_name.get(dep)
            if st in {BLOCKED, CAPABILITY_BLOCKED, "ABSENT", "INSUFFICIENT_EVIDENCE", "IMPLEMENTED_UNVERIFIED", "PARTIALLY_IMPLEMENTED", "DOCUMENTATION_ONLY"}:
                blocked.append({"component": name, "dependency": dep, "dependency_status": st})
    for b in blocked:
        sev = "HIGH" if b["dependency_status"] in {BLOCKED, CAPABILITY_BLOCKED, "ABSENT"} else "MEDIUM"
        _add(findings, "BLOCKED_DEPENDENCY", sev, "dependency", "Dependency not verified/ready", component=b["component"], evidence=b)
    return {"graph": graph, "missing_dependencies": missing, "cycles": cycles, "blocked_dependencies": blocked}


def _decision(findings: list[Finding], *, has_components: bool) -> str:
    codes = {f.code for f in findings}
    severities = {f.severity for f in findings}
    policy_codes = {"POLICY_VIOLATION","CONCURRENT_FILE_OWNERSHIP","CONCURRENT_BRANCH_OWNERSHIP","OWNERSHIP_MANIFEST_INVALID","INVALID_SCHEMA_VERSION","CONTRADICTORY_EVIDENCE","UNSAFE_INPUT"}
    blocking_codes = {"CYCLIC_DEPENDENCY","MISSING_DEPENDENCY","BLOCKED_DEPENDENCY","BLOCKED_TASK_RETAINS_OWNERSHIP","UNRESOLVED_DEPENDENCY","OWNERSHIP_VALIDATOR_UNAVAILABLE"}
    evidence_codes = {"MISSING_APPROVAL_EVIDENCE","MISSING_EVIDENCE_FIELDS","MISSING_OWNERSHIP_EVIDENCE","MISSING_TASK_MANIFEST","MISSING_CI_EVIDENCE","MALFORMED_EVIDENCE","MALFORMED_OWNERSHIP_EVIDENCE","MALFORMED_INPUT","MISSING_COMPONENTS"}
    if codes & policy_codes:
        return POLICY_VIOLATION
    if codes & blocking_codes or CAPABILITY_BLOCKED in {f.code for f in findings}:
        return BLOCKED
    if not has_components:
        return INSUFFICIENT_EVIDENCE
    if codes & evidence_codes or any(f.severity in {"CRITICAL","HIGH"} for f in findings):
        # high-severity unknowns fail closed as insufficient evidence unless policy/blocked
        if any(c in codes for c in evidence_codes):
            return INSUFFICIENT_EVIDENCE
        return BLOCKED
    return READY_FOR_HUMAN_REVIEW


def evaluate_hub(raw: Any, *, repo_root: str | Path | None = None) -> dict[str, Any]:
    findings: list[Finding] = []
    repo_root_path = Path(repo_root) if repo_root else Path.cwd()
    try:
        payload = as_mapping(raw, "input")
    except ValidationError as exc:
        return {
            "schema_version": SCHEMA_VERSION,
            "engine": "devobs.integration_verification",
            "generated_at": utc_now_iso(),
            "repository": "",
            "head_sha": "",
            "decision": INSUFFICIENT_EVIDENCE,
            "human_review_required": True,
            "findings": [Finding("MALFORMED_INPUT", "HIGH", "input", str(exc)).as_dict()],
            "component_inventory": [],
            "dependency_matrix": {},
            "conflicts": [],
            "evidence_summary": {"count": 0},
            "remediation_backlog": [{"priority": "HIGH", "action": "Provide valid JSON object input", "component": ""}],
        }

    repository = str(payload.get("repository") or "")
    head_sha = str(payload.get("head_sha") or "")
    components_input = payload.get("components")
    if components_input is None:
        inventory = build_inventory(repo_root_path, ownership_by_component=payload.get("ownership_by_component") if isinstance(payload.get("ownership_by_component"), Mapping) else None)
        components = inventory
        _add(findings, "INVENTORY_DISCOVERED", "LOW", "inventory", "Components discovered from repository scan", inferred=True, evidence={"count": len(components)})
    else:
        try:
            components = validate_component_contracts(components_input, findings)
        except ValidationError as exc:
            components = []
            _add(findings, "MALFORMED_COMPONENTS", "HIGH", "contract", str(exc))

    if not components:
        _add(findings, "MISSING_COMPONENTS", "HIGH", "inventory", "No components available for verification")

    ownership = evaluate_ownership(payload.get("ownership"), findings)
    evidence = []
    try:
        evidence = validate_evidence(payload.get("evidence"), findings)
    except ValidationError as exc:
        _add(findings, "MALFORMED_EVIDENCE", "HIGH", "evidence", str(exc))
    approval = validate_approval(payload.get("approval"), findings)

    dep = _dependency_findings(components, findings)

    # evidence expectations
    for c in components:
        status = str(c.get("verification_status"))
        name = str(c.get("name"))
        if status == "DOCUMENTATION_ONLY":
            _add(findings, "DOCUMENTATION_ONLY_COMPONENT", "MEDIUM", "evidence", "Component is documentation-only; no runtime verification claim", component=name, inferred=True)
        if status in {"IMPLEMENTED_UNVERIFIED", "PARTIALLY_IMPLEMENTED"}:
            _add(findings, "UNVERIFIED_COMPONENT", "HIGH", "evidence", "Component present but not independently verified", component=name)
        if status == "ABSENT":
            _add(findings, "ABSENT_COMPONENT", "HIGH", "inventory", "Required component absent", component=name)
    if not any(str(e.get("result", "")).upper() == "PASS" and "ci" in str(e.get("verification_method","" )).lower() for e in evidence):
        _add(findings, "MISSING_CI_EVIDENCE", "HIGH", "evidence", "No independently verified CI evidence present")

    decision = _decision(findings, has_components=bool(components))
    # compute remediation backlog
    backlog = []
    for f in findings:
        if f.severity in {"CRITICAL","HIGH","MEDIUM"}:
            backlog.append({"priority": f.severity, "component": f.component, "action": f.message, "code": f.code})
    # deterministic ordering
    sev_rank = {"CRITICAL":0,"HIGH":1,"MEDIUM":2,"LOW":3}
    backlog.sort(key=lambda x: (sev_rank.get(x["priority"],9), x.get("component",""), x.get("code","")))

    report = {
        "schema_version": SCHEMA_VERSION,
        "engine": "devobs.integration_verification",
        "generated_at": utc_now_iso(),
        "repository": repository,
        "head_sha": head_sha,
        "decision": decision,
        "human_review_required": True,
        "component_inventory": components,
        "dependency_matrix": dep,
        "ownership": ownership,
        "evidence": evidence,
        "approval": approval,
        "evidence_summary": {
            "count": len(evidence),
            "pass": sum(1 for e in evidence if str(e.get("result","" )).upper()=="PASS"),
            "fail": sum(1 for e in evidence if str(e.get("result","" )).upper()=="FAIL"),
            "unknown": sum(1 for e in evidence if str(e.get("result","" )).upper() in {"UNKNOWN","UNVERIFIED"}),
        },
        "conflicts": ownership.get("conflicts", []) if isinstance(ownership, dict) else [],
        "findings": [f.as_dict() for f in findings[:MAX_FINDINGS]],
        "remediation_backlog": backlog[:200],
        "missing_capability_register": [c for c in components if c.get("verification_status") in {"ABSENT","PARTIALLY_IMPLEMENTED","DOCUMENTATION_ONLY","BLOCKED"}],
    }
    return redact(report)

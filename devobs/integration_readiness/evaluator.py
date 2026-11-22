"""Deterministic, offline evaluation of versioned integration readiness catalogs."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .catalog import normalize_catalog
from .compatibility import parse_version, satisfies
from .models import (
    BLOCKED,
    CATALOG_SCHEMA_VERSION,
    GUARDRAILS,
    MAX_FINDINGS,
    NEEDS_APPROVAL,
    NEEDS_EVIDENCE,
    POLICY_VIOLATION,
    PRIORITY_RANK,
    READY_FOR_HUMAN_REVIEW,
    REPORT_SCHEMA,
    REPORT_SCHEMA_VERSION,
    CatalogError,
    CompatibilityError,
    Finding,
)
from .security import (
    classify_license,
    config_secret_keys,
    redact_text,
    safe_relative_path,
    unsafe_config_keys,
    validate_approval,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_APPROVAL_CODES = frozenset({
    "APPROVAL_DATE_INVALID",
    "APPROVAL_IDENTITY_MISSING",
    "APPROVAL_NOT_HUMAN",
    "APPROVAL_SCOPE_INVALID",
    "APPROVAL_SCOPE_STALE",
    "MISSING_HUMAN_APPROVAL",
})
_DIAGNOSTICS = (
    "offline-fixture-only",
    "no-network-access",
    "no-package-installation",
    "no-service-restart",
    "no-merge-or-deploy",
    "ai-recommendations-non-authoritative",
)


def _finding(
    code: str,
    priority: str,
    category: str,
    integration_id: str,
    message: str,
    remediation: str,
    evidence: tuple[str, ...] = (),
) -> Finding:
    return Finding(
        code=code,
        priority=priority,
        category=category,
        integration_id=integration_id,
        message=redact_text(message, 512),
        remediation=redact_text(remediation, 512),
        evidence=tuple(redact_text(item, 256) for item in evidence),
    )


def _report(catalog: dict[str, Any], findings: list[Finding]) -> dict[str, Any]:
    ordered = sorted(
        findings[:MAX_FINDINGS],
        key=lambda item: (PRIORITY_RANK[item.priority], item.code, item.integration_id, item.message),
    )
    rendered = [item.as_dict(index) for index, item in enumerate(ordered, 1)]
    by_priority = {priority: 0 for priority in PRIORITY_RANK}
    for item in ordered:
        by_priority[item.priority] += 1
    if by_priority["P0"]:
        decision = NEEDS_APPROVAL if all(item.code in _APPROVAL_CODES for item in ordered) else POLICY_VIOLATION
    elif by_priority["P1"]:
        decision = BLOCKED
    elif by_priority["P2"]:
        decision = NEEDS_EVIDENCE
    else:
        decision = READY_FOR_HUMAN_REVIEW
    inventory = [
        {
            "id": item["id"],
            "name": redact_text(item["name"], 256),
            "category": item["category"],
            "status": item["status"],
            "version": redact_text(item["version"], 128),
            "license": redact_text(item["license"] or "UNSPECIFIED", 128),
            "owner": redact_text(item["owner"], 128),
            "owned_paths": list(item["owned_paths"]),
            "required_config": list(item["required_config"]),
            "config_keys": sorted(str(key) for key in item["config"]),
            "requirements": len(item["requirements"]),
            "dependencies": len(item["dependencies"]),
            "security_requirements": len(item["security_requirements"]),
            "required_tools": list(item["required_tools"]),
            "evidence_records": len(item["evidence"]),
            "deprecated": bool(item["deprecated"]),
            "support_until": item["support_until"],
            "human_approval": (
                "not_required" if not item["requires_human_approval"]
                else "approved" if validate_approval(item["approval"], catalog["scope_sha"])[0]
                else "missing"
            ),
        }
        for item in catalog["integrations"]
    ]
    remediation_plan = [
        {
            "rank": rank,
            "priority": item["priority"],
            "finding_id": item["id"],
            "integration_id": item["integration_id"],
            "action": item["remediation"],
        }
        for rank, item in enumerate(rendered, 1)
    ]
    payload = {
        "decision": decision,
        "findings": rendered,
        "inventory": inventory,
        "profile": catalog["profile"],
        "scope_sha": catalog["scope_sha"],
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_schema": REPORT_SCHEMA,
        "profile": catalog["profile"],
        "scope_sha": catalog["scope_sha"],
        "evaluation_date": catalog["evaluation_date"],
        "decision": decision,
        "human_review_required": True,
        "summary": (
            f"Decision={decision}; integrations={len(inventory)}; "
            f"findings={len(rendered)}; P0={by_priority['P0']}; P1={by_priority['P1']}"
        ),
        "counts": {
            "integrations": len(inventory),
            "findings": len(rendered),
            "by_priority": by_priority,
            "errors": sum(1 for item in rendered if item["severity"] == "error"),
            "warnings": sum(1 for item in rendered if item["severity"] == "warning"),
        },
        "findings": rendered,
        "remediation_plan": remediation_plan,
        "integration_inventory": inventory,
        "guardrails": dict(GUARDRAILS),
        "diagnostics": list(_DIAGNOSTICS),
        "report_digest": digest,
    }


def _fail_closed(code: str, detail: str) -> dict[str, Any]:
    catalog = {
        "profile": "unavailable",
        "scope_sha": "0" * 40,
        "evaluation_date": "1970-01-01",
        "integrations": [],
    }
    finding = _finding(
        code,
        "P0",
        "input",
        "",
        f"Catalog evaluation failed closed: {detail}",
        "Provide a schema-valid, bounded, local catalog fixture and rerun the read-only check.",
        (code,),
    )
    return _report(catalog, [finding])


def _check_versions(
    integration: dict[str, Any], catalog: dict[str, Any], findings: list[Finding]
) -> None:
    identifier = integration["id"]
    for requirement in integration["requirements"]:
        name = str(requirement.get("name", "")).strip()
        spec = requirement.get("spec")
        if not name:
            findings.append(_finding(
                "MISSING_REQUIREMENT_NAME", "P1", "version", identifier,
                "Compatibility requirement has no component name.",
                "Add a component name to every compatibility requirement.",
            ))
            continue
        if name not in catalog["component_versions"]:
            findings.append(_finding(
                "MISSING_COMPONENT_VERSION", "P2", "version", identifier,
                "No verified component version is available for a requirement.",
                "Add a pinned component version to the offline catalog.",
                (name,),
            ))
            continue
        try:
            if not satisfies(catalog["component_versions"][name], spec):
                findings.append(_finding(
                    "INCOMPATIBLE_VERSION", "P1", "version", identifier,
                    "Component version does not satisfy an explicit compatibility range.",
                    "Pin a compatible component version or update the requirement with evidence.",
                    (name,),
                ))
        except CompatibilityError:
            findings.append(_finding(
                "INVALID_VERSION_SPEC", "P1", "version", identifier,
                "Compatibility requirement uses an unsupported version specification.",
                "Use bounded numeric clauses such as >=3.10,<4.",
                (name,),
            ))


def _check_dependencies(
    integrations: list[dict[str, Any]], integration: dict[str, Any], findings: list[Finding]
) -> None:
    identifier = integration["id"]
    known = {item["id"]: item for item in integrations}
    for dependency in integration["dependencies"]:
        dependency_id = str(dependency.get("id", "")).strip()
        if not dependency_id or dependency_id not in known:
            findings.append(_finding(
                "MISSING_DEPENDENCY", "P1", "dependency", identifier,
                "Dependency is not present in the integration catalog.",
                "Add the dependency with verified metadata or remove the stale reference.",
                (dependency_id or "unknown",),
            ))
            continue
        try:
            if not satisfies(known[dependency_id]["version"], dependency.get("spec")):
                findings.append(_finding(
                    "UNSUPPORTED_DEPENDENCY", "P1", "dependency", identifier,
                    "Dependency version is outside the supported range.",
                    "Pin a supported dependency version or update the range with evidence.",
                    (dependency_id,),
                ))
        except CompatibilityError:
            findings.append(_finding(
                "INVALID_VERSION_SPEC", "P1", "dependency", identifier,
                "Dependency version range is malformed.",
                "Use bounded numeric clauses such as >=1.0,<2.",
                (dependency_id,),
            ))
        if dependency.get("artifact") is True:
            integrity = dependency.get("integrity")
            expected = integrity.get("expected") if isinstance(integrity, dict) else None
            algorithm = integrity.get("algorithm") if isinstance(integrity, dict) else None
            if not isinstance(expected, str) or not _SHA256_RE.fullmatch(expected.lower()):
                findings.append(_finding(
                    "MISSING_INTEGRITY_METADATA", "P1", "dependency", identifier,
                    "Artifact dependency has no usable SHA-256 integrity value.",
                    "Record a verified SHA-256 value in the offline catalog.",
                    (dependency_id,),
                ))
            elif algorithm != "sha256":
                findings.append(_finding(
                    "INVALID_INTEGRITY_METADATA", "P1", "dependency", identifier,
                    "Artifact integrity metadata declares an unsupported algorithm.",
                    "Use the sha256 algorithm for offline artifact integrity records.",
                    (dependency_id,),
                ))


def _check_paths(integration: dict[str, Any], findings: list[Finding]) -> None:
    identifier = integration["id"]
    for path in integration["owned_paths"]:
        try:
            safe_relative_path(path, "owned_path")
        except CatalogError:
            findings.append(_finding(
                "UNSAFE_PATH", "P1", "ownership", identifier,
                "Owned path is absolute, contains traversal, or uses an unsafe character.",
                "Replace the path with a normalized repository-relative path.",
                ("owned_paths",),
            ))
    for record in integration["evidence"]:
        reference = record.get("reference")
        try:
            safe_relative_path(reference, "evidence_reference")
        except CatalogError:
            findings.append(_finding(
                "UNSAFE_PATH", "P2", "evidence", identifier,
                "Evidence reference is not a safe repository-relative path.",
                "Replace the reference with a normalized repository-relative path.",
                ("evidence",),
            ))
        if not str(record.get("kind", "")).strip():
            findings.append(_finding(
                "MISSING_EVIDENCE_KIND", "P2", "evidence", identifier,
                "Evidence record has no kind.",
                "Set an evidence kind such as file, workflow, or fixture.",
            ))


def _check_security_and_approval(
    integration: dict[str, Any], catalog: dict[str, Any], findings: list[Finding]
) -> None:
    identifier = integration["id"]
    license_status = classify_license(integration["license"])
    if license_status != "approved":
        priority = "P0" if license_status == "restricted" else "P1"
        findings.append(_finding(
            "UNSUPPORTED_LICENSE", priority, "license", identifier,
            "Component license is restricted or not recognized by the offline policy.",
            "Record an approved SPDX license or obtain explicit owner approval.",
            (str(integration["license"] or "UNSPECIFIED"),),
        ))
    secret_keys = config_secret_keys(integration["config"])
    if secret_keys:
        findings.append(_finding(
            "SECRET_EXPOSURE", "P0", "security", identifier,
            "Configuration contains secret-like keys; values were redacted.",
            "Remove secret material from the catalog and reference a secure provider instead.",
            tuple(f"{key}=[REDACTED]" for key in sorted(secret_keys)[:5]),
        ))
    command_keys = unsafe_config_keys(integration["config"])
    if command_keys:
        findings.append(_finding(
            "UNTRUSTED_CONFIG_FIELD", "P0", "security", identifier,
            "Configuration contains command-like fields that are never executed.",
            "Remove command fields from untrusted integration configuration.",
            tuple(command_keys),
        ))
    for requirement in integration["security_requirements"]:
        status = str(requirement.get("status", "")).strip().lower()
        if status == "fail":
            findings.append(_finding(
                "SECURITY_REQUIREMENT_FAILED", "P0", "security", identifier,
                "A required security control reported a failed status.",
                "Resolve the security finding and provide refreshed offline evidence.",
                (str(requirement.get("id", "unnamed")),),
            ))
        elif status not in {"pass", "passed", "success"}:
            findings.append(_finding(
                "SECURITY_EVIDENCE_MISSING", "P1", "security", identifier,
                "Security requirement has no passing evidence.",
                "Attach verified pass status and evidence for the control.",
                (str(requirement.get("id", "unnamed")),),
            ))
    if integration["requires_human_approval"]:
        accepted, reason = validate_approval(integration["approval"], catalog["scope_sha"])
        if not accepted:
            findings.append(_finding(
                reason.upper(), "P0", "approval", identifier,
                "Human approval is required and the current record is not acceptable.",
                "Obtain owner approval tied to the exact reviewed SHA before release.",
                (reason,),
            ))
    for tool in integration["required_tools"]:
        if not catalog["tool_availability"].get(tool, False):
            findings.append(_finding(
                "EXTERNAL_TOOL_UNAVAILABLE", "P2", "tool", identifier,
                "A required external tool is unavailable in the offline profile.",
                "Record the tool as available with evidence or mark the integration blocked.",
                (tool,),
            ))


def _check_ownership(integrations: list[dict[str, Any]], findings: list[Finding]) -> None:
    seen: dict[str, tuple[str, str]] = {}
    for integration in integrations:
        for raw_path in integration["owned_paths"]:
            try:
                path = safe_relative_path(raw_path, "owned_path")
            except CatalogError:
                continue
            previous = seen.get(path)
            if previous and previous[1] != integration["owner"]:
                findings.append(_finding(
                    "OWNERSHIP_CONFLICT", "P0", "ownership", integration["id"],
                    "Two integrations claim the same path with different owners.",
                    "Assign one owner for the path and update the catalog.",
                    (path, previous[0]),
                ))
            else:
                seen[path] = (integration["id"], integration["owner"])


def _find_cycle(integrations: list[dict[str, Any]]) -> tuple[str, ...]:
    known = {item["id"] for item in integrations}
    edges: dict[str, list[str]] = {
        item["id"]: [
            str(dep.get("id", ""))
            for dep in item["dependencies"]
            if str(dep.get("id", "")) in known
        ]
        for item in integrations
    }
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> tuple[str, ...]:
        state[node] = 1
        stack.append(node)
        for child in edges.get(node, []):
            if state.get(child) == 1:
                start = stack.index(child)
                return tuple(stack[start:] + [child])
            if state.get(child, 0) == 0:
                cycle = visit(child)
                if cycle:
                    return cycle
        stack.pop()
        state[node] = 2
        return ()

    for node in sorted(edges):
        if state.get(node, 0) == 0:
            cycle = visit(node)
            if cycle:
                return cycle
    return ()


def evaluate_catalog(raw: Any) -> dict[str, Any]:
    """Evaluate a normalized-ready catalog and return a stable redacted report."""
    try:
        catalog = normalize_catalog(raw)
    except CatalogError as exc:
        return _fail_closed("MALFORMED_CATALOG", exc.code)
    if catalog["schema_version"] != CATALOG_SCHEMA_VERSION:
        return _fail_closed("INCOMPATIBLE_SCHEMA", f"catalog_schema_{catalog['schema_version']}")
    findings: list[Finding] = []
    integrations = catalog["integrations"]
    if not integrations:
        findings.append(_finding(
            "EMPTY_CATALOG", "P2", "input", "",
            "Integration catalog contains no records.",
            "Add verified integration metadata before declaring readiness.",
        ))
    for field in catalog["unrecognized_top_level"]:
        findings.append(_finding(
            "UNRECOGNIZED_CATALOG_FIELD", "P3", "input", "",
            "Catalog contains an unrecognized top-level field.",
            "Remove the field or update the versioned schema.",
            (field,),
        ))
    for integration in integrations:
        identifier = integration["id"]
        try:
            parse_version(integration["version"])
        except CompatibilityError:
            findings.append(_finding(
                "INVALID_VERSION_SPEC", "P1", "version", identifier,
                "Integration version is not a bounded numeric version.",
                "Use a dotted numeric version such as 1.2.3.",
            ))
        if integration["status"] == "blocked":
            findings.append(_finding(
                "INTEGRATION_BLOCKED", "P1", "status", identifier,
                "Integration is explicitly blocked.",
                "Resolve the blocking condition and refresh the catalog.",
            ))
        if integration["deprecated"] or (
            integration["support_until"] and integration["support_until"] <= catalog["evaluation_date"]
        ):
            findings.append(_finding(
                "DEPRECATED_INTEGRATION", "P1", "status", identifier,
                "Integration is deprecated or outside its support window.",
                "Migrate to a supported integration or record an approved exception.",
                (str(integration["support_until"] or "deprecated"),),
            ))
        missing_config = [
            key for key in integration["required_config"]
            if key not in integration["config"]
        ]
        if missing_config:
            findings.append(_finding(
                "MISSING_CONFIGURATION", "P1", "config", identifier,
                "Required configuration keys are absent; no values are inferred.",
                "Add non-sensitive configuration keys or mark the integration incomplete.",
                tuple(sorted(missing_config)[:5]),
            ))
        _check_versions(integration, catalog, findings)
        _check_dependencies(integrations, integration, findings)
        _check_paths(integration, findings)
        _check_security_and_approval(integration, catalog, findings)
    _check_ownership(integrations, findings)
    cycle = _find_cycle(integrations)
    if cycle:
        findings.append(_finding(
            "DEPENDENCY_CYCLE", "P1", "dependency", cycle[0],
            "Integration dependency graph contains a cycle.",
            "Break the cycle and rerun the offline evaluation.",
            cycle,
        ))
    return _report(catalog, findings)


__all__ = ["evaluate_catalog"]

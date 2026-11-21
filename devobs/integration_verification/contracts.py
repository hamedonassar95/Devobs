"""Contract/evidence validation and safe parsing helpers."""

from __future__ import annotations

import re
from typing import Any, Mapping

from .models import Finding, MAX_EVIDENCE, MAX_LIST, MAX_STRING, clip

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SCHEMA_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
SENSITIVE_KEY_RE = re.compile(r"(token|secret|password|authorization|api[_-]?key|credential|private_key)", re.I)
SENSITIVE_VALUE_RE = re.compile(r"(gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,}|AKIA[0-9A-Z]{16}|Bearer\s+[A-Za-z0-9._\-]+)")


class ValidationError(ValueError):
    pass


def redact(value: Any, key_hint: str | None = None) -> Any:
    if key_hint and SENSITIVE_KEY_RE.search(key_hint):
        return "[REDACTED]"
    if isinstance(value, str):
        out = SENSITIVE_VALUE_RE.sub("[REDACTED]", value)
        return clip(out)
    if isinstance(value, Mapping):
        return {str(k): redact(v, str(k)) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, list):
        return [redact(v) for v in value[:MAX_LIST]]
    if isinstance(value, tuple):
        return [redact(v) for v in value[:MAX_LIST]]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return clip(value)


def as_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{name} must be an object")
    return value


def as_list(value: Any, name: str, limit: int = MAX_LIST) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError(f"{name} must be a list")
    if len(value) > limit:
        raise ValidationError(f"{name} exceeds limit {limit}")
    return value


def validate_component_contracts(raw_components: Any, findings: list[Finding]) -> list[dict[str, Any]]:
    components = []
    seen = set()
    for i, raw in enumerate(as_list(raw_components, "components", 500)):
        if not isinstance(raw, Mapping):
            findings.append(Finding("INVALID_COMPONENT", "HIGH", "contract", f"components[{i}] must be object", inferred=False))
            continue
        name = str(raw.get("name", "")).strip()
        if not name:
            findings.append(Finding("MISSING_COMPONENT_NAME", "HIGH", "contract", f"components[{i}] missing name"))
            continue
        if name in seen:
            findings.append(Finding("DUPLICATE_COMPONENT", "HIGH", "contract", f"Duplicate component {name}", component=name))
        seen.add(name)
        schema_version = raw.get("schema_version", 1)
        if schema_version != 1:
            findings.append(Finding("INVALID_SCHEMA_VERSION", "HIGH", "contract", f"Component {name} has unsupported schema_version", component=name, evidence={"schema_version": redact(schema_version)}))
        status = str(raw.get("verification_status", "INSUFFICIENT_EVIDENCE"))
        if status not in {"IMPLEMENTED_AND_TESTED","IMPLEMENTED_UNVERIFIED","PARTIALLY_IMPLEMENTED","DOCUMENTATION_ONLY","ABSENT","BLOCKED"}:
            findings.append(Finding("INVALID_COMPONENT_STATUS", "HIGH", "contract", f"Component {name} has invalid status", component=name, evidence={"status": status}))
        deps = raw.get("integration_dependencies", [])
        if not isinstance(deps, list):
            findings.append(Finding("INVALID_DEPENDENCIES", "HIGH", "contract", f"Component {name} dependencies must be list", component=name))
            deps = []
        comp = {str(k): redact(v, str(k)) for k, v in raw.items()}
        comp["name"] = name
        comp["integration_dependencies"] = [str(d) for d in deps][:MAX_LIST]
        comp["verification_status"] = status
        components.append(comp)
    return components


def validate_evidence(raw_evidence: Any, findings: list[Finding]) -> list[dict[str, Any]]:
    evidence = []
    seen_ids = set()
    for i, raw in enumerate(as_list(raw_evidence, "evidence", MAX_EVIDENCE)):
        if not isinstance(raw, Mapping):
            findings.append(Finding("MALFORMED_EVIDENCE", "HIGH", "evidence", f"evidence[{i}] must be object"))
            continue
        item = {str(k): redact(v, str(k)) for k, v in raw.items()}
        missing = [k for k in ("source","evidence_id","verification_method","verification_timestamp","result") if not str(item.get(k, "")).strip()]
        if missing:
            findings.append(Finding("MISSING_EVIDENCE_FIELDS", "HIGH", "evidence", f"evidence[{i}] missing required fields", evidence={"missing": missing}))
            continue
        eid = str(item["evidence_id"])
        if eid in seen_ids:
            findings.append(Finding("CONTRADICTORY_EVIDENCE", "HIGH", "evidence", f"Duplicate evidence_id {eid}", evidence={"evidence_id": eid}))
        seen_ids.add(eid)
        sha = item.get("commit_sha")
        if sha is not None and sha != "":
            if not isinstance(sha, str) or not SHA_RE.fullmatch(sha.lower()):
                findings.append(Finding("INVALID_EVIDENCE_SHA", "HIGH", "evidence", f"Invalid commit SHA for evidence {eid}", evidence={"evidence_id": eid}))
            else:
                item["commit_sha"] = sha.lower()
        result = str(item.get("result", "")).upper()
        if result not in {"PASS","FAIL","UNKNOWN","UNVERIFIED"}:
            findings.append(Finding("INVALID_EVIDENCE_RESULT", "MEDIUM", "evidence", f"Invalid evidence result for {eid}", evidence={"result": item.get("result")}))
        evidence.append(item)
    # contradictory results for same component+method
    by_key = {}
    for e in evidence:
        comp = str(e.get("component", ""))
        method = str(e.get("verification_method", ""))
        result = str(e.get("result", "")).upper()
        key = (comp, method)
        if comp and method:
            by_key.setdefault(key, set()).add(result)
    for (comp, method), results in by_key.items():
        if "PASS" in results and "FAIL" in results:
            findings.append(Finding("CONTRADICTORY_EVIDENCE", "CRITICAL", "evidence", "Contradictory PASS/FAIL evidence for same component/method", component=comp, evidence={"method": method, "results": sorted(results)}))
    return evidence


def validate_approval(raw: Any, findings: list[Finding]) -> dict[str, Any]:
    if raw is None:
        findings.append(Finding("MISSING_APPROVAL_EVIDENCE", "HIGH", "approval", "Human approval evidence missing"))
        return {"status": "missing"}
    if not isinstance(raw, Mapping):
        findings.append(Finding("MALFORMED_APPROVAL_EVIDENCE", "HIGH", "approval", "Approval evidence must be object"))
        return {"status": "invalid"}
    approval = {str(k): redact(v, str(k)) for k, v in raw.items()}
    approved = approval.get("human_approved") is True
    evidence_id = str(approval.get("evidence_id", "")).strip()
    if not approved:
        findings.append(Finding("MISSING_APPROVAL_EVIDENCE", "HIGH", "approval", "Human approval not granted"))
    if not evidence_id:
        findings.append(Finding("MISSING_APPROVAL_EVIDENCE", "HIGH", "approval", "Approval evidence_id missing"))
    return approval

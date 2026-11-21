"""Input validation, redaction, and bounded normalization."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .models import Finding, MAX_CHANGED_FILES, MAX_CHECKS, MAX_FINDINGS, _clip

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]{1,200}$")
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9:._/\-\s]{1,200}$")
SENSITIVE_KEY_RE = re.compile(r"(token|secret|password|authorization|api[_-]?key|credential|cookie)", re.I)
SENSITIVE_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{16,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.I),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)([?&])(token|secret|password|api_key|apikey|access_token|refresh_token)=([^&\s]+)"),
)


class EvidenceValidationError(ValueError):
    """Raised for malformed or unsafe evidence structures."""


def redact(value: Any, key_hint: str | None = None) -> Any:
    if key_hint and SENSITIVE_KEY_RE.search(key_hint):
        return "[REDACTED]"
    if isinstance(value, str):
        out = value
        for pat in SENSITIVE_PATTERNS:
            if pat.pattern.startswith("(?i)([?&])"):
                out = pat.sub(lambda m: f"{m.group(1)}{m.group(2)}=[REDACTED]", out)
            else:
                out = pat.sub("[REDACTED]", out)
        return _clip(out)
    if isinstance(value, Mapping):
        return {str(k): redact(v, str(k)) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return redact(str(value))


def as_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EvidenceValidationError(f"{name} must be an object")
    return value


def as_list(value: Any, name: str, limit: int) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise EvidenceValidationError(f"{name} must be a list")
    if len(value) > limit:
        raise EvidenceValidationError(f"{name} exceeds limit {limit}")
    return value


def norm_sha(value: Any, name: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise EvidenceValidationError(f"{name} must be a string SHA")
    candidate = value.strip().lower()
    if not SHA_RE.fullmatch(candidate):
        raise EvidenceValidationError(f"{name} must be a 40-char lowercase hex SHA")
    return candidate


def norm_repo(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise EvidenceValidationError("repository must be a string")
    candidate = value.strip()
    if not REPO_RE.fullmatch(candidate):
        raise EvidenceValidationError("repository must be OWNER/REPO")
    return candidate


def norm_branch(value: Any, name: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise EvidenceValidationError(f"{name} must be a string")
    candidate = value.strip()
    if not BRANCH_RE.fullmatch(candidate) or ".." in candidate or candidate.startswith("/"):
        raise EvidenceValidationError(f"{name} contains invalid characters")
    return candidate


def norm_text(value: Any, name: str, limit: int = 500) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise EvidenceValidationError(f"{name} must be a string")
    text = value.strip()
    if len(text) > limit:
        raise EvidenceValidationError(f"{name} exceeds limit {limit}")
    return text


def norm_status(value: Any, name: str) -> str | None:
    text = norm_text(value, name, 80)
    return text.lower() if text else None


def normalize_check(raw: Any, idx: int) -> dict[str, Any]:
    item = as_mapping(raw, f"checks[{idx}]")
    name = norm_text(item.get("name") or item.get("context"), f"checks[{idx}].name", 200)
    if not name or not SAFE_NAME_RE.fullmatch(name):
        raise EvidenceValidationError(f"checks[{idx}].name is invalid")
    status = norm_status(item.get("status") or item.get("state"), f"checks[{idx}].status") or "unknown"
    conclusion = norm_status(item.get("conclusion"), f"checks[{idx}].conclusion") or ""
    head_sha = norm_sha(item.get("head_sha") or item.get("sha"), f"checks[{idx}].head_sha") if (item.get("head_sha") or item.get("sha")) else None
    required = item.get("required")
    if required is not None and not isinstance(required, bool):
        raise EvidenceValidationError(f"checks[{idx}].required must be boolean")
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "head_sha": head_sha,
        "required": bool(required) if required is not None else None,
        "url": redact(item.get("url")) if isinstance(item.get("url"), str) else None,
        "timestamp": norm_text(item.get("completed_at") or item.get("timestamp"), f"checks[{idx}].timestamp", 80),
    }


def normalize_security(raw: Any, idx: int) -> dict[str, Any]:
    item = as_mapping(raw, f"security_findings[{idx}]")
    tool = norm_text(item.get("tool") or item.get("scanner"), f"security_findings[{idx}].tool", 120)
    status = norm_status(item.get("status") or item.get("state"), f"security_findings[{idx}].status") or "unknown"
    severity = norm_status(item.get("severity"), f"security_findings[{idx}].severity") or "unknown"
    if not tool:
        raise EvidenceValidationError(f"security_findings[{idx}].tool is required")
    return {
        "tool": tool,
        "status": status,
        "severity": severity,
        "head_sha": norm_sha(item.get("head_sha") or item.get("sha"), f"security_findings[{idx}].head_sha") if (item.get("head_sha") or item.get("sha")) else None,
        "summary": redact(item.get("summary")) if item.get("summary") is not None else None,
    }


def normalize_dependency(raw: Any, idx: int) -> dict[str, Any]:
    item = as_mapping(raw, f"dependency_results[{idx}]")
    name = norm_text(item.get("name") or item.get("manager"), f"dependency_results[{idx}].name", 120)
    status = norm_status(item.get("status") or item.get("state"), f"dependency_results[{idx}].status") or "unknown"
    if not name:
        raise EvidenceValidationError(f"dependency_results[{idx}].name is required")
    return {
        "name": name,
        "status": status,
        "head_sha": norm_sha(item.get("head_sha") or item.get("sha"), f"dependency_results[{idx}].head_sha") if (item.get("head_sha") or item.get("sha")) else None,
        "summary": redact(item.get("summary")) if item.get("summary") is not None else None,
    }


def normalize_changed_file(raw: Any, idx: int) -> str:
    if not isinstance(raw, str):
        raise EvidenceValidationError(f"changed_files[{idx}] must be a string")
    value = raw.replace("\\", "/").strip()
    if not value or value.startswith("/") or re.match(r"^[A-Za-z]:", value) or ".." in value.split("/"):
        raise EvidenceValidationError(f"changed_files[{idx}] is not a safe repo-relative path")
    if len(value) > 500:
        raise EvidenceValidationError(f"changed_files[{idx}] exceeds limit")
    return "/".join(p for p in value.split("/") if p not in ("", "."))




def normalize_evidence(raw: Mapping[str, Any] | Any) -> dict[str, Any]:
    evidence = as_mapping(raw, "evidence")
    pr = as_mapping(evidence.get("pr", evidence), "pr")
    checks = [normalize_check(x, i) for i, x in enumerate(as_list(evidence.get("checks") or evidence.get("ci_checks"), "checks", MAX_CHECKS))]
    security = [normalize_security(x, i) for i, x in enumerate(as_list(evidence.get("security_findings"), "security_findings", MAX_FINDINGS))]
    deps = [normalize_dependency(x, i) for i, x in enumerate(as_list(evidence.get("dependency_results"), "dependency_results", MAX_FINDINGS))]
    changed = [normalize_changed_file(x, i) for i, x in enumerate(as_list(evidence.get("changed_files"), "changed_files", MAX_CHANGED_FILES))]
    reviews = as_mapping(evidence.get("reviews", {}), "reviews") if evidence.get("reviews") is not None else {}
    ownership = as_mapping(evidence.get("ownership", {}), "ownership") if evidence.get("ownership") is not None else {}
    timestamps = as_mapping(evidence.get("timestamps", {}), "timestamps") if evidence.get("timestamps") is not None else {}

    required_checks = as_list(evidence.get("required_checks"), "required_checks", MAX_CHECKS)
    req_norm = []
    for i, item in enumerate(required_checks):
        name = norm_text(item, f"required_checks[{i}]", 200)
        if not name or not SAFE_NAME_RE.fullmatch(name):
            raise EvidenceValidationError(f"required_checks[{i}] is invalid")
        req_norm.append(name)

    wf = as_mapping(evidence.get("workflow_permissions", {}), "workflow_permissions") if evidence.get("workflow_permissions") is not None else {}
    wf_norm = {}
    if isinstance(wf, Mapping):
        for k in ("unsafe", "write_all", "reviewed", "contents", "actions", "pull_requests", "id_token"):
            if k in wf:
                wf_norm[k] = bool(wf.get(k)) if isinstance(wf.get(k), bool) else redact(wf.get(k))
    return {
        "repository": norm_repo(pr.get("repository") or evidence.get("repository")),
        "pr_number": pr.get("pr_number") if isinstance(pr.get("pr_number"), int) and not isinstance(pr.get("pr_number"), bool) else None,
        "base_branch": norm_branch(pr.get("base_branch") or pr.get("base"), "base_branch"),
        "head_branch": norm_branch(pr.get("head_branch") or pr.get("head"), "head_branch"),
        "head_sha": norm_sha(pr.get("head_sha") or evidence.get("head_sha"), "head_sha"),
        "reviewed_head_sha": norm_sha(pr.get("reviewed_head_sha") or evidence.get("reviewed_head_sha"), "reviewed_head_sha"),
        "mergeable": pr.get("mergeable"),
        "merge_state": norm_status(pr.get("merge_state") or pr.get("merge_state_status"), "merge_state"),
        "required_checks": req_norm,
        "checks": checks,
        "security_findings": security,
        "dependency_results": deps,
        "changed_files": sorted(set(changed)),
        "reviews": {
            "state": norm_status(reviews.get("state") or reviews.get("review_decision"), "reviews.state"),
            "approved": reviews.get("approved"),
            "approvals_count": reviews.get("approvals_count"),
            "required_approvals": reviews.get("required_approvals"),
            "human_approval": reviews.get("human_approval"),
            "reviewers": redact(reviews.get("reviewers", [])),
        },
        "ownership": {
            "owner": norm_text(ownership.get("owner"), "ownership.owner", 120),
            "active_agents": redact(ownership.get("active_agents", [])),
            "file_owners": redact(ownership.get("file_owners", {})),
            "task_manifest": ownership.get("task_manifest"),
            "stale_evidence": ownership.get("stale_evidence"),
        },
        "timestamps": {str(k): norm_text(v, f"timestamps.{k}", 80) for k, v in timestamps.items()},
        "policy": redact(as_mapping(evidence.get("policy", {}), "policy")) if evidence.get("policy") is not None else {},
        "workflow_permissions": wf_norm,
    }

"""Validation, redaction, and bounded parsing for integration evidence."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .models import MAX_FILES, MAX_LIST, MAX_STRING, clip

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]{1,200}$")
SENSITIVE_KEY_RE = re.compile(r"(token|secret|password|authorization|api[_-]?key|credential|cookie)", re.I)
SENSITIVE_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{16,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.I),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)([?&])(token|secret|password|api_key|apikey|access_token|refresh_token)=([^&\s]+)"),
)


class ValidationError(ValueError):
    pass


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
        return clip(out)
    if isinstance(value, Mapping):
        return {str(k): redact(v, str(k)) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return redact(str(value))


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


def norm_sha(value: Any, name: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be string")
    v = value.strip().lower()
    if not SHA_RE.fullmatch(v):
        raise ValidationError(f"{name} must be 40-char hex sha")
    return v


def norm_repo(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not REPO_RE.fullmatch(value.strip()):
        raise ValidationError("repository must be OWNER/REPO")
    return value.strip()


def norm_branch(value: Any, name: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be string")
    v = value.strip()
    if not BRANCH_RE.fullmatch(v) or ".." in v or v.startswith("/") or "\\" in v:
        raise ValidationError(f"{name} invalid")
    return v


def norm_text(value: Any, name: str, limit: int = MAX_STRING) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be string")
    v = value.strip()
    if len(v) > limit:
        raise ValidationError(f"{name} exceeds limit")
    return v


def safe_path(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be string")
    v = value.replace("\\", "/").strip()
    if not v or v.startswith("/") or re.match(r"^[A-Za-z]:", v) or ".." in v.split("/"):
        raise ValidationError(f"{name} invalid")
    parts = [p for p in v.split("/") if p not in ("", ".")]
    if not parts:
        raise ValidationError(f"{name} invalid")
    out = "/".join(parts)
    if len(out) > 500:
        raise ValidationError(f"{name} too long")
    return out


def normalize_input(raw: Any) -> dict[str, Any]:
    root = as_mapping(raw, "input")
    pr = as_mapping(root.get("pr", root), "pr")
    checks = []
    for i, item in enumerate(as_list(root.get("checks") or root.get("ci_checks"), "checks", MAX_LIST)):
        m = as_mapping(item, f"checks[{i}]")
        checks.append({
            "name": norm_text(m.get("name") or m.get("context"), f"checks[{i}].name", 200),
            "status": (norm_text(m.get("status") or m.get("state"), f"checks[{i}].status", 80) or "unknown").lower(),
            "conclusion": (norm_text(m.get("conclusion"), f"checks[{i}].conclusion", 80) or "").lower(),
            "required": m.get("required") is True,
            "head_sha": norm_sha(m.get("head_sha") or m.get("sha"), f"checks[{i}].head_sha") if (m.get("head_sha") or m.get("sha")) else None,
            "url": redact(m.get("url")) if isinstance(m.get("url"), str) else None,
        })
    required_checks = []
    for i, item in enumerate(as_list(root.get("required_checks"), "required_checks", MAX_LIST)):
        name = norm_text(item, f"required_checks[{i}]", 200)
        if not name:
            raise ValidationError("required_checks item invalid")
        required_checks.append(name)
    security = []
    for i, item in enumerate(as_list(root.get("security_findings"), "security_findings", MAX_LIST)):
        m = as_mapping(item, f"security_findings[{i}]")
        security.append({
            "tool": norm_text(m.get("tool"), f"security_findings[{i}].tool", 120) or "unknown",
            "status": (norm_text(m.get("status"), f"security_findings[{i}].status", 80) or "unknown").lower(),
            "severity": (norm_text(m.get("severity"), f"security_findings[{i}].severity", 80) or "unknown").lower(),
            "head_sha": norm_sha(m.get("head_sha") or m.get("sha"), f"security_findings[{i}].head_sha") if (m.get("head_sha") or m.get("sha")) else None,
            "summary": redact(m.get("summary")) if m.get("summary") is not None else None,
        })
    changed_files = [safe_path(x, f"changed_files[{i}]") for i, x in enumerate(as_list(root.get("changed_files"), "changed_files", MAX_FILES))]
    reviews = as_mapping(root.get("reviews", {}), "reviews") if root.get("reviews") is not None else {}
    ownership = as_mapping(root.get("ownership", {}), "ownership") if root.get("ownership") is not None else {}
    evidence_records = as_list(root.get("evidence"), "evidence", MAX_LIST)
    task_manifest = ownership.get("task_manifest") if isinstance(ownership.get("task_manifest"), dict) else None
    return {
        "repository": norm_repo(pr.get("repository") or root.get("repository")),
        "pr_number": pr.get("pr_number") if isinstance(pr.get("pr_number"), int) and not isinstance(pr.get("pr_number"), bool) else None,
        "base_branch": norm_branch(pr.get("base_branch") or pr.get("base"), "base_branch"),
        "head_branch": norm_branch(pr.get("head_branch") or pr.get("head"), "head_branch"),
        "head_sha": norm_sha(pr.get("head_sha") or root.get("head_sha"), "head_sha"),
        "reviewed_head_sha": norm_sha(pr.get("reviewed_head_sha") or root.get("reviewed_head_sha"), "reviewed_head_sha"),
        "mergeable": pr.get("mergeable"),
        "merge_state": (norm_text(pr.get("merge_state") or pr.get("merge_state_status"), "merge_state", 80) or "").lower() or None,
        "required_checks": required_checks,
        "checks": checks,
        "security_findings": security,
        "dependency_results": redact(as_list(root.get("dependency_results"), "dependency_results", MAX_LIST)),
        "changed_files": sorted(set(changed_files)),
        "reviews": {
            "approved": reviews.get("approved") is True,
            "approvals_count": reviews.get("approvals_count") if isinstance(reviews.get("approvals_count"), int) else None,
            "required_approvals": reviews.get("required_approvals") if isinstance(reviews.get("required_approvals"), int) else 1,
            "human_approval": reviews.get("human_approval") is True,
        },
        "ownership": {
            "file_owners": redact(ownership.get("file_owners", {})),
            "active_agents": redact(ownership.get("active_agents", [])),
            "task_manifest": task_manifest,
            "stale_evidence": ownership.get("stale_evidence") is True,
        },
        "evidence": redact(evidence_records),
        "timestamps": redact(as_mapping(root.get("timestamps", {}), "timestamps")) if root.get("timestamps") is not None else {},
        "untrusted_pr_text": norm_text(root.get("untrusted_pr_text") or pr.get("body"), "untrusted_pr_text", 4000),
    }

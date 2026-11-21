"""Evidence validation and normalization for PR readiness evaluation.

This module is deterministic and read-only. It validates external evidence inputs,
rejects malformed structures fail-closed, detects stale/conflicting evidence, and
redacts sensitive values from report-safe outputs.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
BRANCH_RE = re.compile(
    r"^(?:feature|fix|bugfix|hotfix|chore|docs|test|refactor|release|ci|build|perf)/[A-Za-z0-9._/-]+$"
)
SENSITIVE_KEY_RE = re.compile(r"(token|secret|password|authorization|api[_-]?key|credential)", re.I)
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{16,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.I),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)([?&])(token|secret|password|api_key|apikey|access_token|refresh_token)=([^&\s]+)"),
)

READINESS_STATES = (
    "READY_FOR_HUMAN_REVIEW",
    "PENDING",
    "BLOCKED",
    "UNVERIFIED",
)


class EvidenceValidationError(ValueError):
    """Raised when evidence cannot be safely parsed."""


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    source: str
    severity: str = "UNVERIFIED"  # UNVERIFIED | BLOCKED

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "source": self.source,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class NormalizedEvidence:
    pr: dict[str, Any]
    head_sha: str
    checks: list[dict[str, Any]]
    required_checks: list[str]
    security_evidence: list[dict[str, Any]]
    approvals: list[dict[str, Any]]
    required_approvals: int
    protected_branch: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "pr": self.pr,
            "head_sha": self.head_sha,
            "checks": self.checks,
            "required_checks": self.required_checks,
            "security_evidence": self.security_evidence,
            "approvals": self.approvals,
            "required_approvals": self.required_approvals,
            "protected_branch": self.protected_branch,
            "issues": [i.as_dict() for i in self.issues],
        }


def _redact_string(value: str) -> str:
    redacted = value
    for pattern in SENSITIVE_VALUE_PATTERNS:
        if pattern.pattern.startswith("(?i)([?&])"):
            redacted = pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}=[REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def redact_sensitive(value: Any, key_hint: str | None = None) -> Any:
    """Recursively redact sensitive values from report-safe structures."""
    if key_hint and SENSITIVE_KEY_RE.search(key_hint):
        return "[REDACTED]"
    if isinstance(value, str):
        return _redact_string(value)
    if isinstance(value, Mapping):
        return {str(k): redact_sensitive(v, str(k)) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [redact_sensitive(v) for v in value]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _redact_string(str(value))


def _parse_time(value: Any, *, field_name: str, issues: list[ValidationIssue], source: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        issues.append(ValidationIssue("MALFORMED_TIMESTAMP", f"{field_name} must be an ISO-8601 string", source))
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        issues.append(ValidationIssue("MALFORMED_TIMESTAMP", f"{field_name} is not a valid timestamp", source))
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_sha(value: Any, *, field_name: str, issues: list[ValidationIssue], source: str, required: bool) -> str:
    if value is None or value == "":
        if required:
            issues.append(ValidationIssue("MISSING_SHA", f"{field_name} is required", source))
        return ""
    if not isinstance(value, str):
        issues.append(ValidationIssue("MALFORMED_SHA", f"{field_name} must be a string", source))
        return ""
    candidate = value.strip().lower()
    if not SHA_RE.fullmatch(candidate):
        issues.append(ValidationIssue("MALFORMED_SHA", f"{field_name} must be a 40-char lowercase/hex SHA", source))
        return ""
    return candidate


def _as_mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EvidenceValidationError(f"{name} must be an object")
    return value


def _as_list(value: Any, *, name: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise EvidenceValidationError(f"{name} must be a list")
    return value


def _normalize_check(raw: Any, index: int, issues: list[ValidationIssue], head_sha: str) -> dict[str, Any] | None:
    source = f"checks[{index}]"
    if not isinstance(raw, Mapping):
        issues.append(ValidationIssue("MALFORMED_CHECK", "check entry must be an object", source))
        return None
    name = raw.get("name")
    status = raw.get("status")
    conclusion = raw.get("conclusion")
    sha = _normalize_sha(raw.get("head_sha") or raw.get("sha"), field_name="head_sha", issues=issues, source=source, required=False)
    completed_at = _parse_time(raw.get("completed_at"), field_name="completed_at", issues=issues, source=source)
    if not isinstance(name, str) or not name.strip():
        issues.append(ValidationIssue("MALFORMED_CHECK", "check name is required", source))
        return None
    if not isinstance(status, str) or not status.strip():
        issues.append(ValidationIssue("MALFORMED_CHECK", "check status is required", source))
        return None
    status_norm = status.strip().lower()
    conclusion_norm = conclusion.strip().lower() if isinstance(conclusion, str) and conclusion.strip() else ""
    allowed_status = {"queued", "in_progress", "completed", "pending", "success", "failure"}
    allowed_conclusion = {"", "success", "failure", "cancelled", "timed_out", "action_required", "neutral", "skipped", "stale", "pending"}
    if status_norm not in allowed_status:
        issues.append(ValidationIssue("UNKNOWN_CHECK_STATUS", f"unknown check status: {redact_sensitive(status_norm)}", source, severity="UNVERIFIED"))
    if conclusion_norm not in allowed_conclusion:
        issues.append(ValidationIssue("UNKNOWN_CHECK_CONCLUSION", f"unknown check conclusion: {redact_sensitive(conclusion_norm)}", source, severity="UNVERIFIED"))
    stale = bool(head_sha and sha and sha != head_sha)
    if stale:
        issues.append(ValidationIssue("STALE_CHECK_EVIDENCE", f"check {name.strip()} SHA does not match PR head", source, severity="BLOCKED"))
    return {
        "name": name.strip(),
        "status": status_norm,
        "conclusion": conclusion_norm,
        "head_sha": sha,
        "completed_at": completed_at.isoformat() if completed_at else None,
        "url": redact_sensitive(raw.get("url")) if isinstance(raw.get("url"), str) else None,
        "stale": stale,
    }


def _normalize_security(raw: Any, index: int, issues: list[ValidationIssue], head_sha: str) -> dict[str, Any] | None:
    source = f"security_evidence[{index}]"
    if not isinstance(raw, Mapping):
        issues.append(ValidationIssue("MALFORMED_SECURITY_EVIDENCE", "security evidence entry must be an object", source))
        return None
    name = raw.get("name")
    status = raw.get("status")
    sha = _normalize_sha(raw.get("head_sha") or raw.get("sha"), field_name="head_sha", issues=issues, source=source, required=False)
    if not isinstance(name, str) or not name.strip():
        issues.append(ValidationIssue("MALFORMED_SECURITY_EVIDENCE", "security evidence name is required", source))
        return None
    if not isinstance(status, str) or not status.strip():
        issues.append(ValidationIssue("MALFORMED_SECURITY_EVIDENCE", "security evidence status is required", source))
        return None
    status_norm = status.strip().lower()
    if status_norm not in {"pass", "passed", "success", "fail", "failed", "pending", "missing", "unknown"}:
        issues.append(ValidationIssue("UNKNOWN_SECURITY_STATUS", f"unknown security status: {redact_sensitive(status_norm)}", source, severity="BLOCKED"))
    stale = bool(head_sha and sha and sha != head_sha)
    if stale:
        issues.append(ValidationIssue("STALE_SECURITY_EVIDENCE", f"security evidence {name.strip()} SHA does not match PR head", source, severity="BLOCKED"))
    return {
        "name": name.strip(),
        "status": status_norm,
        "head_sha": sha,
        "details": redact_sensitive(raw.get("details")) if raw.get("details") is not None else None,
        "stale": stale,
    }


def _normalize_approval(raw: Any, index: int, issues: list[ValidationIssue], head_sha: str) -> dict[str, Any] | None:
    source = f"approvals[{index}]"
    if not isinstance(raw, Mapping):
        issues.append(ValidationIssue("MALFORMED_APPROVAL", "approval entry must be an object", source))
        return None
    actor = raw.get("actor") or raw.get("user")
    state = raw.get("state")
    sha = _normalize_sha(raw.get("head_sha") or raw.get("sha"), field_name="head_sha", issues=issues, source=source, required=False)
    source_type = raw.get("source_type") or raw.get("source") or "unknown"
    verified = raw.get("verified")
    if not isinstance(actor, str) or not actor.strip():
        issues.append(ValidationIssue("MALFORMED_APPROVAL", "approval actor is required", source))
        return None
    if not isinstance(state, str) or not state.strip():
        issues.append(ValidationIssue("MALFORMED_APPROVAL", "approval state is required", source))
        return None
    state_norm = state.strip().lower()
    if state_norm not in {"approved", "changes_requested", "commented", "dismissed", "pending"}:
        issues.append(ValidationIssue("UNKNOWN_APPROVAL_STATE", f"unknown approval state: {redact_sensitive(state_norm)}", source, severity="BLOCKED"))
    source_norm = str(source_type).strip().lower()
    verified_bool = verified is True
    stale = bool(head_sha and sha and sha != head_sha)
    if stale:
        issues.append(ValidationIssue("STALE_APPROVAL_EVIDENCE", f"approval by {actor.strip()} SHA does not match PR head", source, severity="BLOCKED"))
    self_reported = source_norm in {"self", "self_reported", "self-reported", "comment", "pr_body", "author"}
    if state_norm == "approved" and (self_reported or not verified_bool):
        issues.append(ValidationIssue("UNTRUSTED_APPROVAL", f"approval by {actor.strip()} is not authoritative verified evidence", source))
    return {
        "actor": actor.strip(),
        "state": state_norm,
        "head_sha": sha,
        "source_type": source_norm,
        "verified": verified_bool,
        "stale": stale,
    }


def validate_evidence(evidence: Mapping[str, Any] | str | bytes) -> NormalizedEvidence:
    """Validate and normalize evidence. Fail closed on malformed structures."""
    if isinstance(evidence, (str, bytes)):
        try:
            parsed = json.loads(evidence)
        except Exception as exc:  # noqa: BLE001
            raise EvidenceValidationError(f"malformed JSON evidence: {exc.__class__.__name__}") from exc
    else:
        parsed = evidence
    root = _as_mapping(parsed, name="evidence")
    issues: list[ValidationIssue] = []

    pr = _as_mapping(root.get("pr", {}), name="pr")
    head_sha = _normalize_sha(pr.get("head_sha"), field_name="pr.head_sha", issues=issues, source="pr", required=True)
    branch = pr.get("branch")
    base = pr.get("base")
    title = pr.get("title")
    if not isinstance(branch, str) or not branch.strip():
        issues.append(ValidationIssue("MISSING_BRANCH", "pr.branch is required", "pr"))
        branch_norm = ""
    else:
        branch_norm = branch.strip()
        if not BRANCH_RE.fullmatch(branch_norm):
            issues.append(ValidationIssue("INVALID_BRANCH_NAME", f"branch name does not match policy: {redact_sensitive(branch_norm)}", "pr", severity="BLOCKED"))
    if base is not None and (not isinstance(base, str) or not base.strip()):
        issues.append(ValidationIssue("MALFORMED_PR", "pr.base must be a non-empty string when provided", "pr"))
        base_norm = ""
    else:
        base_norm = base.strip() if isinstance(base, str) else ""
    if title is not None and not isinstance(title, str):
        issues.append(ValidationIssue("MALFORMED_PR", "pr.title must be a string when provided", "pr"))
        title_norm = ""
    else:
        title_norm = redact_sensitive(title.strip()) if isinstance(title, str) else ""

    checks_raw = _as_list(root.get("checks"), name="checks")
    checks = [c for c in (_normalize_check(item, i, issues, head_sha) for i, item in enumerate(checks_raw)) if c is not None]
    # detect duplicate check names for same SHA
    seen: dict[tuple[str, str], int] = {}
    for c in checks:
        k = (c["name"].lower(), c.get("head_sha") or "")
        seen[k] = seen.get(k, 0) + 1
    for (name, sha), count in sorted(seen.items()):
        if count > 1:
            issues.append(ValidationIssue("DUPLICATE_CHECK", f"duplicate check evidence for {name}", "checks", severity="BLOCKED"))

    required_checks_raw = root.get("required_checks", [])
    if required_checks_raw is None:
        required_checks_raw = []
    if not isinstance(required_checks_raw, list) or not all(isinstance(x, str) and x.strip() for x in required_checks_raw):
        raise EvidenceValidationError("required_checks must be a list of non-empty strings")
    required_checks = [x.strip() for x in required_checks_raw]

    security_raw = _as_list(root.get("security_evidence"), name="security_evidence")
    security_evidence = [s for s in (_normalize_security(item, i, issues, head_sha) for i, item in enumerate(security_raw)) if s is not None]

    approvals_raw = _as_list(root.get("approvals"), name="approvals")
    approvals = [a for a in (_normalize_approval(item, i, issues, head_sha) for i, item in enumerate(approvals_raw)) if a is not None]

    required_approvals = root.get("required_approvals", 1)
    if not isinstance(required_approvals, int) or isinstance(required_approvals, bool) or required_approvals < 0:
        raise EvidenceValidationError("required_approvals must be a non-negative integer")

    protected_branch = root.get("protected_branch", True)
    if not isinstance(protected_branch, bool):
        raise EvidenceValidationError("protected_branch must be a boolean")

    normalized_pr = {
        "branch": branch_norm,
        "base": base_norm,
        "head_sha": head_sha,
        "title": title_norm,
        "url": redact_sensitive(pr.get("url")) if isinstance(pr.get("url"), str) else None,
    }
    return NormalizedEvidence(
        pr=normalized_pr,
        head_sha=head_sha,
        checks=checks,
        required_checks=required_checks,
        security_evidence=security_evidence,
        approvals=approvals,
        required_approvals=required_approvals,
        protected_branch=protected_branch,
        issues=issues,
    )

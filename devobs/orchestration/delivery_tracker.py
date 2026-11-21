"""Read-only GitHub delivery evidence tracker.

All input is supplied by the caller. This module never calls GitHub, starts a
process, changes Git state, merges, deploys, or grants approval. Statuses are
advisory classifications of supplied evidence, not runtime proof.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import pathlib
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Mapping

_ROOT = pathlib.Path(__file__).resolve().parents[2]
for _folder in ("scripts", "tools"):
    _path = str(_ROOT / _folder)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from agent_task_status_report import sanitize_display  # noqa: E402
from check_two_agent_tasks import BRANCH_RE, PR_RE, SHA_RE  # noqa: E402
from human_approval_gate import evaluate as evaluate_approval  # noqa: E402

from .task_registry import OrchestrationError  # noqa: E402

DELIVERED = "DELIVERED"
BLOCKED = "BLOCKED"
UNVERIFIED = "UNVERIFIED"
PARTIAL = "PARTIAL"
KNOWN_STATUSES = frozenset((DELIVERED, BLOCKED, UNVERIFIED))
FAILURE_CONCLUSIONS = frozenset(("FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED"))
PROTECTED_BRANCHES = frozenset(("main", "master"))
REDACTED = "[REDACTED]"
_TOKEN_PATTERNS = (
    re.compile(r"github_pat_[A-Za-z0-9_]{16,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
)


def redact_secrets(value: str) -> str:
    """Replace common credential shapes before a value is logged or exported."""
    for pattern in _TOKEN_PATTERNS:
        value = pattern.sub(REDACTED, value)
    return value


@dataclass(frozen=True)
class DeliveryEvidence:
    """Caller-supplied, read-only evidence about one task's GitHub delivery."""

    task_id: str
    pr_reference: str | None = None
    pr_state: str | None = None
    head_sha: str | None = None
    expected_sha: str | None = None
    branch: str | None = None
    base_branch: str | None = None
    required_checks: tuple[str, ...] = ()
    checks: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    approval: Mapping[str, Any] | None = None
    approved_sha: str | None = None
    api_error: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class CheckSummary:
    """A sanitized classification of one required status check."""

    name: str
    state: str
    reason: str = ""


@dataclass(frozen=True)
class DeliveryUpdate:
    """The advisory classification of one evidence snapshot."""

    task_id: str
    status: str
    reasons: tuple[str, ...]
    checks: tuple[CheckSummary, ...]
    pr_reference: str | None
    head_sha: str | None
    approval_status: str
    evidence_digest: str
    evidence_excerpt: str


@dataclass(frozen=True)
class DeliveryReport:
    """Aggregate view of all recorded delivery classifications."""

    status: str
    updates: tuple[DeliveryUpdate, ...]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "updates": [
                {
                    "task_id": update.task_id,
                    "status": update.status,
                    "reasons": list(update.reasons),
                    "checks": [
                        dataclasses.asdict(check) for check in update.checks
                    ],
                    "pr_reference": update.pr_reference,
                    "head_sha": update.head_sha,
                    "approval_status": update.approval_status,
                    "evidence_digest": update.evidence_digest,
                    "evidence_excerpt": update.evidence_excerpt,
                }
                for update in self.updates
            ],
            "summary": copy.deepcopy(self.summary),
        }


_EVIDENCE_FIELDS = frozenset(item.name for item in dataclasses.fields(DeliveryEvidence))


def _coerce_evidence(evidence: DeliveryEvidence | Mapping[str, Any]) -> DeliveryEvidence:
    if isinstance(evidence, DeliveryEvidence):
        return copy.deepcopy(evidence)
    if not isinstance(evidence, Mapping):
        raise OrchestrationError("evidence must be a DeliveryEvidence or mapping")
    values = dict(evidence)
    unknown = set(values) - _EVIDENCE_FIELDS
    if unknown:
        raise OrchestrationError(f"unknown evidence fields: {', '.join(sorted(unknown))}")
    return DeliveryEvidence(
        **{key: copy.deepcopy(value) for key, value in values.items()}
    )


def _digest(evidence: DeliveryEvidence) -> str:
    payload = dataclasses.asdict(evidence)
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _safe_text(value: Any, limit: int = 200) -> str | None:
    if value is None:
        return None
    return sanitize_display(value, limit=limit)


def _check_status(name: str, check: Any) -> CheckSummary:
    safe_name = sanitize_display(name, limit=100)
    if not isinstance(check, Mapping):
        return CheckSummary(safe_name, UNVERIFIED, f"invalid_ci_evidence:{safe_name}")
    state = str(check.get("status", "")).upper()
    conclusion = str(check.get("conclusion", "")).upper()
    if state == "COMPLETED" and conclusion == "SUCCESS":
        return CheckSummary(safe_name, "SUCCESS")
    if conclusion in FAILURE_CONCLUSIONS or state in FAILURE_CONCLUSIONS:
        return CheckSummary(safe_name, BLOCKED, f"ci_failed:{safe_name}")
    return CheckSummary(safe_name, UNVERIFIED, f"ci_pending:{safe_name}")


def classify(evidence: DeliveryEvidence | Mapping[str, Any]) -> DeliveryUpdate:
    """Classify supplied evidence without any I/O."""
    try:
        item = _coerce_evidence(evidence)
    except Exception as exc:
        raw_id = evidence.get("task_id") if isinstance(evidence, Mapping) else "UNKNOWN"
        return DeliveryUpdate(
            sanitize_display(raw_id, limit=80), BLOCKED, ("invalid_evidence",), (),
            None, None, "INVALID", "0" * 64, f"evidence rejected: {type(exc).__name__}",
        )

    digest = _digest(item)
    task_id = sanitize_display(item.task_id, limit=80)
    block_reasons: list[str] = []
    pending_reasons: list[str] = []
    checks: list[CheckSummary] = []

    if item.api_error is not None and str(item.api_error).strip():
        block_reasons.append("github_api_failure")

    pr_reference = _safe_text(item.pr_reference, 200)
    if pr_reference is None:
        pending_reasons.append("missing_pr_reference")
    elif not PR_RE.fullmatch(pr_reference):
        block_reasons.append("invalid_pr_reference")

    if item.pr_state is None:
        pending_reasons.append("missing_pr_state")
    elif str(item.pr_state).lower() != "open":
        block_reasons.append("pr_not_open")

    branch = _safe_text(item.branch, 200)
    if branch is None:
        pending_reasons.append("missing_branch")
    elif not BRANCH_RE.fullmatch(branch):
        block_reasons.append("invalid_branch")

    base_branch = _safe_text(item.base_branch, 200)
    if base_branch is None:
        pending_reasons.append("missing_base_branch")
    elif base_branch.lower() in PROTECTED_BRANCHES:
        block_reasons.append("protected_branch")

    head_sha = _safe_text(item.head_sha, 40)
    if head_sha is None:
        pending_reasons.append("missing_head_sha")
    elif not SHA_RE.fullmatch(head_sha):
        block_reasons.append("invalid_head_sha")

    expected_sha = _safe_text(item.expected_sha, 40)
    if expected_sha is None:
        pending_reasons.append("missing_expected_sha")
    elif head_sha is not None and expected_sha != head_sha:
        block_reasons.append("sha_mismatch")

    required = tuple(sanitize_display(name, limit=100) for name in item.required_checks)
    if not required:
        pending_reasons.append("missing_required_checks")
    else:
        check_map = item.checks if isinstance(item.checks, Mapping) else {}
        for name in required:
            if name not in check_map:
                summary = CheckSummary(name, UNVERIFIED, f"missing_ci_check:{name}")
            else:
                summary = _check_status(name, check_map[name])
            checks.append(summary)
            if summary.state == BLOCKED:
                block_reasons.append(summary.reason)
            elif summary.state != "SUCCESS":
                pending_reasons.append(summary.reason)

    approval_status = "MISSING"
    if item.approval is None:
        block_reasons.append("missing_approval")
    else:
        try:
            approval_result = evaluate_approval(dict(item.approval))
        except Exception as exc:
            approval_status = "INVALID"
            block_reasons.append(f"approval_evaluation_failure:{type(exc).__name__}")
        else:
            approval_status = sanitize_display(approval_result.status, limit=80)
            if approval_result.status != "HUMAN_APPROVED":
                block_reasons.append(f"approval_{approval_result.status.lower()}")

        approved_sha = _safe_text(item.approved_sha, 40)
        if approved_sha is None:
            pending_reasons.append("missing_approved_sha")
        elif head_sha is not None and approved_sha != head_sha:
            block_reasons.append("stale_approval")

    reasons = tuple(dict.fromkeys(block_reasons + pending_reasons))
    if block_reasons:
        status = BLOCKED
    elif pending_reasons:
        status = UNVERIFIED
    else:
        status = DELIVERED

    return DeliveryUpdate(
        task_id=task_id,
        status=status,
        reasons=reasons,
        checks=tuple(checks),
        pr_reference=pr_reference,
        head_sha=head_sha,
        approval_status=approval_status,
        evidence_digest=digest,
        evidence_excerpt=redact_secrets(sanitize_display(item.notes, limit=300)),
    )


class DeliveryTracker:
    """Stores idempotent classifications of caller-supplied evidence."""

    def __init__(self) -> None:
        self._updates: dict[str, DeliveryUpdate] = {}
        self._history: dict[str, list[DeliveryUpdate]] = {}
        self._digests: dict[str, dict[str, DeliveryUpdate]] = {}

    def record(self, evidence: DeliveryEvidence | Mapping[str, Any]) -> DeliveryUpdate:
        update = classify(evidence)
        digests = self._digests.setdefault(update.task_id, {})
        existing = digests.get(update.evidence_digest)
        if existing is not None:
            return existing
        digests[update.evidence_digest] = update
        self._updates[update.task_id] = update
        self._history.setdefault(update.task_id, []).append(update)
        return update

    def record_all(self, items: list[DeliveryEvidence | Mapping[str, Any]]) -> tuple[DeliveryUpdate, ...]:
        return tuple(self.record(item) for item in items)

    def get(self, task_id: str) -> DeliveryUpdate:
        try:
            return self._updates[task_id]
        except (KeyError, TypeError) as exc:
            raise OrchestrationError("unknown delivery task") from exc

    def history(self, task_id: str) -> tuple[DeliveryUpdate, ...]:
        return tuple(self._history.get(task_id, ()))

    def evidence_count(self, task_id: str) -> int:
        return len(self._history.get(task_id, ()))

    def report(self) -> DeliveryReport:
        updates = tuple(self._updates.values())
        counts = {status: 0 for status in KNOWN_STATUSES}
        for update in updates:
            if update.status in counts:
                counts[update.status] += 1
        if not updates:
            status = UNVERIFIED
        elif counts[BLOCKED] and counts[DELIVERED]:
            status = PARTIAL
        elif counts[BLOCKED]:
            status = BLOCKED
        elif counts[DELIVERED]:
            status = DELIVERED
        else:
            status = UNVERIFIED
        summary = {
            "total": len(updates),
            "delivered": counts[DELIVERED],
            "blocked": counts[BLOCKED],
            "unverified": counts[UNVERIFIED],
        }
        return DeliveryReport(status, updates, summary)


__all__ = [
    "BLOCKED",
    "DELIVERED",
    "PARTIAL",
    "UNVERIFIED",
    "CheckSummary",
    "DeliveryEvidence",
    "DeliveryReport",
    "DeliveryTracker",
    "DeliveryUpdate",
    "REDACTED",
    "classify",
    "redact_secrets",
]

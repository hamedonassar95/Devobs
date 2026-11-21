"""Evidence verification primitives.

Deterministic, fail-closed verification for integration evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .validation import SHA_RE, norm_sha, redact

VERIFIED = "VERIFIED"
UNVERIFIED = "UNVERIFIED"
STALE = "STALE"
CONFLICTED = "CONFLICTED"
BLOCKED = "BLOCKED"
UNKNOWN = "UNKNOWN"
STATES = {VERIFIED, UNVERIFIED, STALE, CONFLICTED, BLOCKED, UNKNOWN}


@dataclass(frozen=True)
class EvidenceCheck:
    name: str
    state: str
    message: str
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "state": self.state, "message": self.message, "details": redact(self.details)}


def _state(ok: bool, missing: bool = False, stale: bool = False, conflicted: bool = False, blocked: bool = False) -> str:
    if conflicted:
        return CONFLICTED
    if blocked:
        return BLOCKED
    if stale:
        return STALE
    if missing:
        return UNVERIFIED
    return VERIFIED if ok else UNKNOWN


def verify_commit_sha(value: Any) -> EvidenceCheck:
    if not value:
        return EvidenceCheck("commit_sha", UNVERIFIED, "Commit SHA missing.", {"value": value})
    try:
        sha = norm_sha(value, "commit_sha")
    except Exception:
        return EvidenceCheck("commit_sha", BLOCKED, "Commit SHA invalid.", {"value": redact(value)})
    return EvidenceCheck("commit_sha", VERIFIED, "Commit SHA format verified.", {"sha": sha})


def verify_sha_pair(name: str, expected: Any, actual: Any) -> EvidenceCheck:
    if not expected or not actual:
        return EvidenceCheck(name, UNVERIFIED, f"{name} missing.", {"expected": redact(expected), "actual": redact(actual)})
    try:
        e = norm_sha(expected, f"{name}.expected")
        a = norm_sha(actual, f"{name}.actual")
    except Exception:
        return EvidenceCheck(name, BLOCKED, f"{name} has invalid SHA.", {"expected": redact(expected), "actual": redact(actual)})
    if e != a:
        return EvidenceCheck(name, CONFLICTED, f"{name} mismatch.", {"expected": e, "actual": a})
    return EvidenceCheck(name, VERIFIED, f"{name} matches.", {"sha": e})


def verify_ci_checks(checks: list[dict[str, Any]], required: list[str], head_sha: str | None) -> EvidenceCheck:
    if not required:
        return EvidenceCheck("ci_required_checks", UNVERIFIED, "Required checks policy missing.", {})
    if not checks:
        return EvidenceCheck("ci_required_checks", UNVERIFIED, "CI check evidence missing.", {"required": required})
    by_name = {str(c.get("name", "")).lower(): c for c in checks if isinstance(c, dict)}
    missing, pending, failed, stale, unknown = [], [], [], [], []
    for req in required:
        c = by_name.get(req.lower())
        if not c:
            missing.append(req); continue
        if head_sha and c.get("head_sha") and c.get("head_sha") != head_sha:
            stale.append(req); continue
        status = str(c.get("status", "")).lower()
        conclusion = str(c.get("conclusion", "")).lower()
        if status in {"failure", "failed"} or conclusion in {"failure", "failed", "cancelled", "timed_out", "action_required", "error"}:
            failed.append(req)
        elif status in {"pending", "queued", "in_progress", "waiting", "requested"} or (status == "completed" and conclusion == ""):
            pending.append(req)
        elif status in {"success", "passed"} or conclusion in {"success", "passed"}:
            pass
        else:
            unknown.append(req)
    if stale:
        return EvidenceCheck("ci_required_checks", STALE, "Required check evidence stale.", {"stale": stale})
    if missing or unknown:
        return EvidenceCheck("ci_required_checks", UNVERIFIED, "Required check evidence missing/unknown.", {"missing": missing, "unknown": unknown})
    if failed or pending:
        return EvidenceCheck("ci_required_checks", BLOCKED, "Required checks failed/pending.", {"failed": failed, "pending": pending})
    return EvidenceCheck("ci_required_checks", VERIFIED, "Required checks verified.", {"required": required})


def verify_human_approval(reviews: Mapping[str, Any]) -> EvidenceCheck:
    approved = bool(reviews.get("approved")) or bool(reviews.get("human_approval"))
    count = reviews.get("approvals_count")
    required = reviews.get("required_approvals", 1)
    if not isinstance(count, int):
        count = 1 if approved else 0
    if not isinstance(required, int):
        required = 1
    if count >= max(required, 0) and approved:
        return EvidenceCheck("human_approval", VERIFIED, "Human approval evidence verified.", {"approvals_count": count, "required_approvals": required})
    return EvidenceCheck("human_approval", UNVERIFIED, "Human approval missing.", {"approvals_count": count, "required_approvals": required})


def verify_evidence_record(record: Mapping[str, Any], head_sha: str | None) -> EvidenceCheck:
    source = record.get("source")
    kind = record.get("kind")
    ref = record.get("ref")
    if not isinstance(source, str) or not source.strip() or not isinstance(kind, str) or not kind.strip() or not isinstance(ref, str) or not ref.strip():
        return EvidenceCheck("evidence_record", UNVERIFIED, "Evidence record missing source/kind/ref.", redact(dict(record)))
    sha = record.get("sha")
    if sha is not None:
        if not isinstance(sha, str) or not SHA_RE.fullmatch(sha.strip().lower()):
            return EvidenceCheck("evidence_record", BLOCKED, "Evidence record SHA invalid.", redact(dict(record)))
        if head_sha and sha.strip().lower() != head_sha:
            return EvidenceCheck("evidence_record", STALE, "Evidence record SHA does not match head SHA.", redact(dict(record)))
    ts = record.get("timestamp")
    if ts is not None and not isinstance(ts, str):
        return EvidenceCheck("evidence_record", BLOCKED, "Evidence timestamp invalid.", redact(dict(record)))
    return EvidenceCheck("evidence_record", VERIFIED, "Evidence record verified.", {"source": source, "kind": kind, "ref": ref})


def summarize_states(checks: list[EvidenceCheck]) -> str:
    states = {c.state for c in checks}
    if CONFLICTED in states:
        return CONFLICTED
    if BLOCKED in states:
        return BLOCKED
    if STALE in states:
        return STALE
    if UNVERIFIED in states or UNKNOWN in states:
        return UNVERIFIED
    return VERIFIED

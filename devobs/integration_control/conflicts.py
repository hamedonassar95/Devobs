"""Conflict detection for multi-agent integration evidence."""

from __future__ import annotations

from typing import Any

from .coordination import evaluate_coordination
from .evidence import BLOCKED, CONFLICTED, STALE, UNVERIFIED, VERIFIED, EvidenceCheck
from .validation import redact


def detect_conflicts(normalized: dict[str, Any]) -> dict[str, Any]:
    findings = []
    coordination = evaluate_coordination(normalized, findings)
    checks: list[EvidenceCheck] = []

    owners = normalized.get("ownership", {}).get("file_owners", {})
    seen_files = {}
    for path, agents in (owners.items() if isinstance(owners, dict) else []):
        if isinstance(agents, list) and len({str(a) for a in agents if str(a).strip()}) > 1:
            seen_files[path] = sorted({str(a) for a in agents})
    if seen_files:
        checks.append(EvidenceCheck("file_ownership", CONFLICTED, "Multiple agents modify same files.", {"files": seen_files}))
    else:
        checks.append(EvidenceCheck("file_ownership", VERIFIED, "No concurrent file ownership conflict detected.", {}))

    manifest = normalized.get("ownership", {}).get("task_manifest")
    if isinstance(manifest, dict):
        task_ids = [t.get("id") for t in manifest.get("tasks", []) if isinstance(t, dict)]
        dups = sorted({tid for tid in task_ids if isinstance(tid, str) and task_ids.count(tid) > 1})
        if dups:
            checks.append(EvidenceCheck("duplicate_task_ids", CONFLICTED, "Duplicate task identifiers detected.", {"task_ids": dups}))
        else:
            checks.append(EvidenceCheck("duplicate_task_ids", VERIFIED, "No duplicate task IDs detected.", {}))
    else:
        checks.append(EvidenceCheck("duplicate_task_ids", UNVERIFIED, "Task manifest unavailable for duplicate ID check.", {}))

    codes = {f.code for f in findings}
    if "CONFLICTING_BRANCH_OWNERSHIP" in codes:
        checks.append(EvidenceCheck("branch_ownership", CONFLICTED, "Conflicting branch ownership detected.", {}))
    elif isinstance(manifest, dict):
        checks.append(EvidenceCheck("branch_ownership", VERIFIED, "No branch ownership conflict detected.", {}))
    else:
        checks.append(EvidenceCheck("branch_ownership", UNVERIFIED, "Task manifest unavailable for branch ownership check.", {}))

    if "STALE_WORKSPACE_EVIDENCE" in codes or any(f.code == "STALE_HEAD_SHA" for f in findings):
        checks.append(EvidenceCheck("stale_evidence", STALE, "Stale integration evidence detected.", {}))
    else:
        checks.append(EvidenceCheck("stale_evidence", VERIFIED, "No stale evidence flag detected.", {}))

    if "INVALID_DEPENDENCY_GRAPH" in codes:
        checks.append(EvidenceCheck("dependencies", BLOCKED, "Invalid or unresolved dependencies detected.", {}))
    elif isinstance(manifest, dict):
        checks.append(EvidenceCheck("dependencies", VERIFIED, "Dependency graph has no blocking errors detected.", {}))
    else:
        checks.append(EvidenceCheck("dependencies", UNVERIFIED, "Task manifest unavailable for dependency check.", {}))

    if "BLOCKED_TASK_OWNERSHIP_CONFLICT" in codes:
        checks.append(EvidenceCheck("blocked_task_ownership", BLOCKED, "Blocked task retains ownership.", {}))
    elif isinstance(manifest, dict):
        checks.append(EvidenceCheck("blocked_task_ownership", VERIFIED, "No blocked-task ownership conflict detected.", {}))
    else:
        checks.append(EvidenceCheck("blocked_task_ownership", UNVERIFIED, "Task manifest unavailable for blocked-task check.", {}))

    if "CONTRADICTORY_EVIDENCE" in codes or "DUPLICATE_EVIDENCE" in codes:
        checks.append(EvidenceCheck("evidence_consistency", CONFLICTED, "Duplicate or contradictory evidence detected.", {}))
    else:
        checks.append(EvidenceCheck("evidence_consistency", VERIFIED, "No duplicate/conflicting evidence record detected.", {}))

    recommendations = []
    for c in checks:
        if c.state in {CONFLICTED, BLOCKED, STALE, UNVERIFIED}:
            recommendations.append(f"Remediate {c.name}: {c.message}")
    if not recommendations:
        recommendations.append("No conflict remediation required; continue human review process.")

    return {
        "checks": [c.as_dict() for c in checks],
        "findings": [f.as_dict() for f in findings],
        "coordination": redact(coordination),
        "recommendations": recommendations,
    }

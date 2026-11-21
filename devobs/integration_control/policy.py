"""Deterministic approval and branch-change policy."""

from __future__ import annotations

from typing import Any

from .models import (
    BLOCKER,
    UNVERIFIED_SEVERITY,
    ComponentResult,
    Finding,
    RESTRICTED_ACTIONS,
)
from .security import digest_payload


def assess_approvals(approval: Any) -> ComponentResult:
    if not isinstance(approval, dict):
        return ComponentResult(
            name="approval",
            status="BLOCKED",
            findings=(Finding("HUMAN_APPROVAL_MISSING", BLOCKER, "approval"),),
            check_failed="approval",
            details={"missing": list(RESTRICTED_ACTIONS)},
        )

    findings: list[Finding] = []
    missing: list[str] = []
    for action in RESTRICTED_ACTIONS:
        value = approval.get(action)
        if value is None:
            missing.append(action)
            findings.append(Finding("HUMAN_APPROVAL_MISSING", BLOCKER, f"approval:{action}"))
        elif value != "pending_human":
            findings.append(Finding(
                "SECURITY_POLICY_VIOLATION", BLOCKER, f"approval:{action}",
            ))
    if findings:
        status, passed, failed = "BLOCKED", None, "approval"
    else:
        status, passed, failed = "PASS", "approval", None

    return ComponentResult(
        name="approval",
        status=status,
        findings=tuple(findings),
        check_passed=passed,
        check_failed=failed,
        details={"missing": sorted(missing)},
    )


def assess_branches(observations: list[dict[str, Any]]) -> ComponentResult:
    if not observations:
        return ComponentResult(
            name="branch_observations",
            status="UNVERIFIED",
            findings=(Finding("BRANCH_EVIDENCE_MISSING", UNVERIFIED_SEVERITY,
                              "branch_observations"),),
            check_failed="branch_observations",
            details={"branches": []},
        )

    branches: dict[str, set[str]] = {}
    for item in observations:
        branches.setdefault(item["branch"], set()).add(item["sha"])
    changed = sorted(branch for branch, shas in branches.items() if len(shas) > 1)
    findings = tuple(
        Finding("CONCURRENT_BRANCH_CHANGE", BLOCKER, f"branch:{branch}")
        for branch in changed
    )
    digest = digest_payload(observations)
    evidence_records = ({
        "id": f"BRANCH_{digest[:12].upper()}",
        "kind": "branch_observation",
        "source": "component:branch_observations",
        "excerpt": f"branches={len(branches)} changed={len(changed)}",
    },)
    if findings:
        status, passed, failed = "BLOCKED", None, "branch_observations"
    else:
        status, passed, failed = "PASS", "branch_observations", None
    return ComponentResult(
        name="branch_observations",
        status=status,
        findings=findings,
        evidence_ids=tuple(item["id"] for item in evidence_records),
        check_passed=passed,
        check_failed=failed,
        details={"branches": sorted(branches), "evidence_records": evidence_records},
    )

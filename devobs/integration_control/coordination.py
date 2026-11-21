"""Adapter over the existing offline two-agent coordination validator."""

from __future__ import annotations

import copy
from typing import Any

from scripts.check_two_agent_tasks import evaluate as evaluate_manifest

from .models import BLOCKER, UNVERIFIED_SEVERITY, ComponentResult, Finding
from .security import digest_payload

CONFLICT_CODES = {
    "concurrent_file_ownership": "CONCURRENT_FILE_OWNERSHIP",
    "concurrent_branch_ownership": "CONCURRENT_BRANCH_OWNERSHIP",
}
BLOCKED_CODES = {
    "task_blocked": "BLOCKED_TASK_RETAINS_OWNERSHIP",
    "unresolved_dependency": "UNRESOLVED_DEPENDENCY",
    "agent_not_enabled": "AGENT_NOT_ENABLED",
}


def _map_error(error: str) -> str:
    lowered = error.lower()
    if "separate human approval" in lowered or "approval must" in lowered:
        return "SECURITY_POLICY_VIOLATION"
    if "depend" in lowered:
        return "INVALID_DEPENDENCY_GRAPH"
    return "COORDINATION_MANIFEST_INVALID"


def assess_coordination(manifest: dict[str, Any] | None) -> ComponentResult:
    if not isinstance(manifest, dict):
        return ComponentResult(
            name="coordination",
            status="UNVERIFIED",
            findings=(Finding("COORDINATION_EVIDENCE_MISSING", UNVERIFIED_SEVERITY,
                              "task_manifest"),),
            check_failed="coordination",
            details={"decision": "NOT_EVALUATED", "conflicts": [], "blocked_tasks": []},
        )

    result = evaluate_manifest(copy.deepcopy(manifest))
    findings: list[Finding] = []
    for error in result.get("errors", []):
        findings.append(Finding(_map_error(error), BLOCKER, "task_manifest"))
    for item in result.get("blocked_tasks", []):
        reason = item.get("reason") if isinstance(item, dict) else "unknown"
        findings.append(Finding(
            BLOCKED_CODES.get(str(reason), "COORDINATION_BLOCKED"),
            BLOCKER,
            "task_manifest",
        ))
    for item in result.get("conflicts", []):
        reason = item.get("reason") if isinstance(item, dict) else "unknown"
        findings.append(Finding(
            CONFLICT_CODES.get(str(reason), "COORDINATION_CONFLICT"),
            BLOCKER,
            "task_manifest",
        ))

    decision = result.get("decision", "FAIL")
    if decision == "PASS" and not findings:
        status, passed, failed = "PASS", "coordination", None
    elif decision == "BLOCKED" or findings:
        status, passed, failed = "BLOCKED", None, "coordination"
    else:
        status, passed, failed = "UNVERIFIED", None, "coordination"

    digest = digest_payload(copy.deepcopy(manifest))
    evidence_records = ({
        "id": f"COORD_{digest[:12].upper()}",
        "kind": "coordination",
        "source": "component:coordination",
        "excerpt": f"decision={decision}",
    },)
    return ComponentResult(
        name="coordination",
        status=status,
        findings=tuple(findings),
        evidence_ids=tuple(item["id"] for item in evidence_records),
        check_passed=passed,
        check_failed=failed,
        details={
            "decision": decision,
            "conflicts": [str(item.get("reason", "unknown"))
                          for item in result.get("conflicts", [])
                          if isinstance(item, dict)],
            "blocked_tasks": [str(item.get("reason", "unknown"))
                              for item in result.get("blocked_tasks", [])
                              if isinstance(item, dict)],
            "evidence_records": evidence_records,
        },
    )

"""Read-only adapter over the existing PR readiness gate."""

from __future__ import annotations

from typing import Any

from scripts.pr_readiness_gate import (
    CommandResult,
    evaluate as evaluate_pr,
)

from .models import BLOCKER, UNVERIFIED_SEVERITY, ComponentResult, Finding
from .security import strict_json_loads

BLOCKER_CODES = {
    "CI_FAILED": "CI_FAILED",
    "CI_PENDING": "CI_PENDING",
    "PR_NOT_READY": "PR_NOT_READY",
    "MERGE_CONFLICT": "MERGE_CONFLICT",
    "PR_MERGE_STATE": "PR_MERGE_STATE",
    "OUTDATED_BRANCH": "OUTDATED_BRANCH",
    "REVIEW_REQUESTED": "REVIEW_REQUESTED",
    "CHANGES_REQUESTED": "CHANGES_REQUESTED",
    "APPROVAL_MISSING": "PR_APPROVAL_MISSING",
    "APPROVAL_STALE": "PR_APPROVAL_STALE",
}
UNVERIFIED_CODES = {
    "REQUIRED_CHECK_MISSING": "REQUIRED_CHECK_MISSING",
    "CHECK_STALE": "CHECK_STALE",
    "CI_EVIDENCE_MISSING": "CI_EVIDENCE_UNVERIFIED",
    "PR_METADATA_UNVERIFIED": "PR_METADATA_UNVERIFIED",
    "CHECKS_UNVERIFIED": "CHECKS_UNVERIFIED",
    "REVIEWS_UNVERIFIED": "REVIEWS_UNVERIFIED",
    "REVIEW_REQUESTS_UNVERIFIED": "REVIEW_REQUESTS_UNVERIFIED",
    "BRANCH_PROTECTION_UNVERIFIED": "BRANCH_PROTECTION_UNVERIFIED",
    "MERGEABILITY_UNVERIFIED": "MERGEABILITY_UNVERIFIED",
    "COMMIT_EVIDENCE_UNVERIFIED": "COMMIT_EVIDENCE_UNVERIFIED",
    "INVALID_INPUT": "INPUT_INVALID",
}


def _kind(argv: list[str]) -> str:
    joined = " ".join(argv)
    if argv[:3] == ["gh", "pr", "view"]:
        return "pr"
    if argv[:3] == ["gh", "pr", "checks"]:
        return "checks"
    if "/branches/" in joined and "/protection" in joined:
        return "protection"
    if "/commits/" in joined and "--jq" in argv:
        return "commit"
    if "/requested_reviewers" in joined:
        return "requested"
    if "/reviews" in joined:
        return "reviews"
    return "unknown"


def _json_shape(kind: str, payload: Any) -> bool:
    expected = {
        "pr": dict,
        "checks": list,
        "protection": dict,
        "requested": dict,
        "reviews": list,
    }.get(kind)
    return expected is not None and isinstance(payload, expected)


def preflight(responses: list[dict[str, Any]]) -> tuple[Finding, ...]:
    """Detect unavailable or malformed snapshots before gate evaluation."""
    found: dict[str, str] = {}
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for record in responses:
        by_kind.setdefault(_kind(record["argv"]), []).append(record)

    for kind in ("pr", "commit", "protection", "checks", "reviews", "requested"):
        records = by_kind.get(kind, [])
        if not records:
            found[kind] = "GITHUB_API_UNAVAILABLE"
            continue
        record = records[0]
        if record["returncode"] != 0:
            if kind == "protection" and record["returncode"] == 404:
                continue
            found[kind] = "GITHUB_API_UNAVAILABLE"
            continue
        if kind == "commit":
            if not record["stdout"].strip():
                found[kind] = "MALFORMED_GITHUB_RESPONSE"
            continue
        try:
            payload = strict_json_loads(record["stdout"])
        except Exception:  # noqa: BLE001 - fixed validation must fail closed.
            found[kind] = "MALFORMED_GITHUB_RESPONSE"
            continue
        if not _json_shape(kind, payload):
            found[kind] = "MALFORMED_GITHUB_RESPONSE"

    codes = sorted(set(found.values()))
    return tuple(Finding(code, UNVERIFIED_SEVERITY, "github_api") for code in codes)


def _fixture_runner(responses: list[dict[str, Any]]):
    by_argv = {tuple(record["argv"]): record for record in responses}

    def runner(argv: list[str]) -> CommandResult:
        record = by_argv.get(tuple(argv))
        if record is None:
            raise RuntimeError("fixture_response_missing")
        return CommandResult(
            record["returncode"], record["stdout"], record["stderr"],
        )

    return runner


def assess_pr(snapshot: dict[str, Any], expected_sha: str | None) -> ComponentResult:
    preflight_findings = preflight(snapshot["responses"])
    if preflight_findings:
        return ComponentResult(
            name="pr_readiness",
            status="UNVERIFIED",
            findings=preflight_findings,
            check_failed="pr_readiness",
            details={"gate_status": "NOT_EVALUATED"},
        )

    report = evaluate_pr(
        snapshot["repository"], snapshot["pr_ref"],
        _fixture_runner(snapshot["responses"]),
    )
    status = report["status"]
    findings: list[Finding] = []
    for item in report["blockers"]:
        code = BLOCKER_CODES.get(item["code"], "PR_READINESS_BLOCKED")
        findings.append(Finding(code, BLOCKER, item["source"] or "github"))
    for item in report["unverified"]:
        code = UNVERIFIED_CODES.get(item["code"], "PR_EVIDENCE_UNVERIFIED")
        findings.append(Finding(code, UNVERIFIED_SEVERITY, item["source"] or "github"))

    evidence = report.get("evidence", {})
    head = evidence.get("head_commit", {})
    observed_sha = head.get("sha") if isinstance(head, dict) else None
    if expected_sha and isinstance(observed_sha, str) and observed_sha != expected_sha:
        findings.append(Finding("STALE_HEAD_SHA", BLOCKER, "snapshot"))
    elif expected_sha and not isinstance(observed_sha, str):
        findings.append(Finding("HEAD_SHA_UNVERIFIED", UNVERIFIED_SEVERITY, "github"))

    blockers = any(item.severity == BLOCKER for item in findings)
    unverified = any(item.severity == UNVERIFIED_SEVERITY for item in findings)
    if status == "VERIFIED_READY" and not findings:
        component_status, passed, failed = "PASS", "pr_readiness", None
    elif blockers:
        component_status, passed, failed = "BLOCKED", None, "pr_readiness"
    else:
        component_status, passed, failed = "UNVERIFIED", None, "pr_readiness"

    number = report.get("pr", {}).get("number") if isinstance(report.get("pr"), dict) else None
    suffix = str(number) if isinstance(number, int) else snapshot["pr_ref"]
    evidence_records = (
        {
            "id": f"GH_PR_{suffix}",
            "kind": "pr_readiness",
            "source": "component:pr_readiness",
            "excerpt": f"status={status} head={observed_sha or 'unverified'}",
        },
        {
            "id": f"GH_CHECKS_{suffix}",
            "kind": "ci_evidence",
            "source": "component:pr_readiness",
            "excerpt": "checks=" + ",".join(sorted(
                str(item.get("name", "")) for item in evidence.get("ci", {}).get("checks", [])
                if isinstance(item, dict)
            ))[:512],
        },
    )
    return ComponentResult(
        name="pr_readiness",
        status=component_status,
        findings=tuple(findings),
        evidence_ids=tuple(item["id"] for item in evidence_records),
        check_passed=passed,
        check_failed=failed,
        details={"gate_status": status, "evidence_records": evidence_records},
    )

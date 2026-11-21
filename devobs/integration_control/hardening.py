"""Additive, offline hardening diagnostics for integration-control reports.

This module never executes a task, authorizes an action, changes Git state, or
calls a network service. It reuses the existing two-agent validator as the
authoritative coordination rule source and adds bounded diagnostics for:

* explicit, caller-supplied approval-evidence records;
* unauthorized restricted/destructive action requests;
* deterministic unsafe-retry detection;
* a stable manifest digest for traceability.

Every emitted finding is advisory or fail-closed. Even valid human-approval
evidence is recorded as non-authoritative; ``merge_authorized`` remains false.
"""

from __future__ import annotations

import copy
from typing import Any, Iterable

from scripts.human_approval_gate import evaluate as evaluate_approval_record

from .models import (
    ADVISORY,
    BLOCKED,
    BLOCKER,
    PENDING_HUMAN,
    PROCEED,
    RESTRICTED_ACTIONS,
    SCHEMA_VERSION,
    UNVERIFIED,
    UNVERIFIED_SEVERITY,
    Finding,
)
from .report import finalize_report
from .security import ID_RE, TIMESTAMP_RE, digest_payload

HARDENING_POLICY_VERSION = "integration-control-hardening-v1"
HARDENING_SOURCE = "task_hardening"

DESTRUCTIVE_ACTIONS = frozenset({
    "bypass_branch_protection",
    "delete",
    "destroy",
    "disable_checks",
    "drop_database",
    "force_push",
    "publish_release",
    "reset_hard",
    "terraform_apply",
})
APPROVAL_STATES = frozenset({"APPROVE", "REJECT", "PENDING"})
VERIFICATION_STATES = frozenset({"VERIFIED", "PENDING"})
APPROVAL_RECORD_KEYS = frozenset({
    "action",
    "approval",
    "verification_status",
    "pr_open",
    "pr_merged",
    "approver_is_human",
    "approver_has_write",
    "evidence_ids",
    "recorded_at",
})
MAX_APPROVAL_RECORDS = 20
MAX_EVIDENCE_IDS = 20
MAX_RETRY_PRIORS = 50
MAX_IDENTICAL_RETRIES = 1


class HardeningError(ValueError):
    """Fixed, non-sensitive diagnostic code."""


def _deep_copy(value: Any) -> Any:
    return copy.deepcopy(value)


def _manifest_from(document: Any) -> dict[str, Any] | None:
    if not isinstance(document, dict):
        return None
    manifest = document.get("coordination")
    return manifest if isinstance(manifest, dict) else None


def _finding_record(finding: Finding) -> tuple[str, str, str, str]:
    record = finding.to_record()
    return (record["code"], record["severity"], record["source"], record["message"])


def _add_findings(report: dict[str, Any], findings: Iterable[Finding]) -> None:
    existing = {_finding_record(Finding(**item)) for item in report["findings"]}
    for finding in findings:
        key = _finding_record(finding)
        if key in existing:
            continue
        existing.add(key)
        report["findings"].append(finding.to_record())


def _add_evidence(report: dict[str, Any], prefix: str, payload: Any) -> None:
    digest = digest_payload(payload)
    evidence_id = f"{prefix}_{digest[:12].upper()}"
    accepted = report["components"]["evidence"]["accepted_ids"]
    if evidence_id not in accepted:
        accepted.append(evidence_id)
        accepted.sort()


def _move_check(report: dict[str, Any], name: str, *, failed: bool) -> None:
    checks = report["checks"]
    if failed:
        if name in checks["passed"]:
            checks["passed"].remove(name)
        if name not in checks["failed"]:
            checks["failed"].append(name)
    else:
        if name in checks["failed"]:
            checks["failed"].remove(name)
        if name not in checks["passed"]:
            checks["passed"].append(name)
    for key in ("passed", "failed", "skipped"):
        checks[key].sort()


def _recompute_decision(report: dict[str, Any]) -> None:
    if report["decision"] == "INVALID":
        return
    severities = {item["severity"] for item in report["findings"]}
    if report["decision"] == BLOCKED or BLOCKER in severities:
        report["decision"] = BLOCKED
    elif report["decision"] == UNVERIFIED or UNVERIFIED_SEVERITY in severities:
        report["decision"] = UNVERIFIED
    else:
        report["decision"] = PROCEED


def _validate_approval_record(record: Any) -> bool:
    if not isinstance(record, dict) or set(record) != APPROVAL_RECORD_KEYS:
        return False
    if record["action"] not in RESTRICTED_ACTIONS:
        return False
    if record["approval"] not in APPROVAL_STATES:
        return False
    if record["verification_status"] not in VERIFICATION_STATES:
        return False
    for key in ("pr_open", "pr_merged", "approver_is_human", "approver_has_write"):
        if type(record[key]) is not bool:
            return False
    evidence_ids = record["evidence_ids"]
    if (not isinstance(evidence_ids, list) or not 1 <= len(evidence_ids) <= MAX_EVIDENCE_IDS
            or any(not isinstance(item, str) or not ID_RE.fullmatch(item)
                   for item in evidence_ids)):
        return False
    recorded_at = record["recorded_at"]
    return isinstance(recorded_at, str) and bool(TIMESTAMP_RE.fullmatch(recorded_at))


def _approval_findings(
    records: Any,
    manifest_digest: str,
) -> tuple[list[Finding], bool]:
    """Return findings and whether any coordination check must fail."""
    if records is None:
        return [], False

    if not isinstance(records, (list, tuple)):
        return [Finding("APPROVAL_EVIDENCE_INVALID", BLOCKER, HARDENING_SOURCE,
                        "approval evidence must be a bounded list")], True
    if len(records) > MAX_APPROVAL_RECORDS:
        return [Finding("APPROVAL_EVIDENCE_INVALID", BLOCKER, HARDENING_SOURCE,
                        "approval evidence exceeds record limit")], True

    findings: list[Finding] = []
    represented: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for record in records:
        if not _validate_approval_record(record):
            findings.append(Finding(
                "APPROVAL_EVIDENCE_INVALID", BLOCKER, HARDENING_SOURCE,
                "approval evidence record failed closed validation",
            ))
            continue
        action = str(record["action"])
        represented.add(action)
        normalized.append(_deep_copy(record))
        decision = evaluate_approval_record({
            "verification_status": record["verification_status"],
            "approval": record["approval"],
            "approver_is_human": record["approver_is_human"],
            "approver_has_write": record["approver_has_write"],
            "pr_open": record["pr_open"],
            "pr_merged": record["pr_merged"],
        })
        if decision.status == "HUMAN_APPROVED":
            findings.append(Finding(
                "APPROVAL_EVIDENCE_PRESENT", ADVISORY, HARDENING_SOURCE,
                "caller-supplied approval evidence is advisory and not authoritative",
            ))
        elif decision.status == "REJECTED":
            findings.append(Finding(
                "APPROVAL_EVIDENCE_REJECTED", BLOCKER, HARDENING_SOURCE,
                "caller-supplied approval evidence records human rejection",
            ))
        elif decision.status == "PENDING":
            findings.append(Finding(
                "APPROVAL_EVIDENCE_PENDING", UNVERIFIED_SEVERITY, HARDENING_SOURCE,
                "caller-supplied approval evidence is still pending",
            ))
        else:
            findings.append(Finding(
                "APPROVAL_EVIDENCE_INVALID", BLOCKER, HARDENING_SOURCE,
                "approval evidence failed the canonical human gate semantics",
            ))

    for action in RESTRICTED_ACTIONS:
        if action not in represented:
            findings.append(Finding(
                "APPROVAL_EVIDENCE_MISSING", UNVERIFIED_SEVERITY, HARDENING_SOURCE,
                f"no caller-supplied evidence record for {action}",
            ))

    if findings:
        payload = {"manifest_digest": manifest_digest, "records": normalized}
        return findings, any(item.severity != ADVISORY for item in findings)
    return findings, False


def _action_findings(manifest: dict[str, Any]) -> tuple[list[Finding], list[str]]:
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list):
        return [], []
    flagged: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict):
            continue
        actions = task.get("requested_actions")
        if not isinstance(actions, list):
            continue
        for action in actions:
            if not isinstance(action, str):
                continue
            normalized = action.strip().lower()
            if normalized in RESTRICTED_ACTIONS or normalized in DESTRUCTIVE_ACTIONS:
                flagged.add(normalized)
    if not flagged:
        return [], []
    finding = Finding(
        "UNAUTHORIZED_ACTION_REQUESTED", BLOCKER, HARDENING_SOURCE,
        "task contract requested a restricted or destructive action",
    )
    return [finding], sorted(flagged)


def _validate_retry_policy(policy: Any) -> dict[str, Any]:
    if policy is None:
        return {"max_identical_retries": MAX_IDENTICAL_RETRIES, "prior_attempt_digests": ()}
    allowed = {"max_identical_retries", "prior_attempt_digests"}
    if not isinstance(policy, dict) or set(policy) - allowed:
        raise HardeningError("RETRY_POLICY_INVALID")
    maximum = policy.get("max_identical_retries", MAX_IDENTICAL_RETRIES)
    if type(maximum) is not int or not 1 <= maximum <= 10:
        raise HardeningError("RETRY_POLICY_INVALID")
    priors = policy.get("prior_attempt_digests", ())
    if not isinstance(priors, (list, tuple)) or len(priors) > MAX_RETRY_PRIORS:
        raise HardeningError("RETRY_POLICY_INVALID")
    if any(not isinstance(item, str) or len(item) != 64
           or any(char not in "0123456789abcdef" for char in item) for item in priors):
        raise HardeningError("RETRY_POLICY_INVALID")
    return {"max_identical_retries": maximum, "prior_attempt_digests": tuple(priors)}


def _retry_findings(
    manifest: dict[str, Any],
    manifest_digest: str,
    policy: Any,
) -> tuple[list[Finding], list[str]]:
    try:
        validated = _validate_retry_policy(policy)
    except HardeningError:
        return [Finding("RETRY_POLICY_INVALID", BLOCKER, HARDENING_SOURCE)], []

    reasons: list[str] = []
    if manifest_digest in validated["prior_attempt_digests"]:
        reasons.append("prior_attempt_digest_repeated")

    keys: dict[str, list[str]] = {}
    tasks = manifest.get("tasks")
    if isinstance(tasks, list):
        for task in tasks:
            if not isinstance(task, dict) or task.get("status") == "complete":
                continue
            verification = task.get("verification")
            if not isinstance(verification, dict):
                continue
            commands = verification.get("commands")
            evidence = verification.get("evidence")
            if (not isinstance(commands, list)
                    or any(not isinstance(item, str) for item in commands)
                    or not isinstance(evidence, str)):
                continue
            key = digest_payload({
                "repository": task.get("repository"),
                "commands": commands,
                "evidence": evidence,
            })
            keys.setdefault(key, []).append(str(task.get("id", "unknown")))
    if any(len(task_ids) > validated["max_identical_retries"]
           for task_ids in keys.values()):
        reasons.append("identical_retry_claims")

    if not reasons:
        return [], []
    finding = Finding(
        "UNSAFE_RETRY_LOOP", BLOCKER, HARDENING_SOURCE,
        "unsafe retry pattern detected in task contract",
    )
    return [finding], sorted(reasons)


def harden_report(
    report: dict[str, Any],
    document: Any,
    *,
    approval_evidence: Any = None,
    retry_policy: Any = None,
) -> dict[str, Any]:
    """Return a schema-valid report with additive hardening diagnostics."""
    result = _deep_copy(report)
    if not isinstance(result, dict) or "findings" not in result or "checks" not in result:
        return result

    try:
        manifest = _manifest_from(document)
        if manifest is None:
            return result
        digest = digest_payload(_deep_copy(manifest))

        findings: list[Finding] = []
        coordination_failed = False
        approval_failed = False

        findings.append(Finding(
            "HARDENING_MANIFEST_DIGEST", ADVISORY, HARDENING_SOURCE,
            f"manifest_digest={digest[:12]}",
        ))

        approval_findings, approval_failed = _approval_findings(approval_evidence, digest)
        findings.extend(approval_findings)

        action_findings, action_reasons = _action_findings(manifest)
        findings.extend(action_findings)

        retry_findings, retry_reasons = _retry_findings(manifest, digest, retry_policy)
        findings.extend(retry_findings)
        coordination_failed = bool(action_findings or retry_findings)

        if not findings:
            return result

        _add_findings(result, findings)
        _add_evidence(result, "HARDEN", {"manifest_digest": digest})
        if any(item.code.startswith("APPROVAL_EVIDENCE_") for item in findings):
            record_count = len(approval_evidence) if isinstance(approval_evidence, (list, tuple)) else 0
            _add_evidence(result, "APPR", {
                "manifest_digest": digest,
                "record_count": record_count,
            })
        if action_reasons:
            _add_evidence(result, "ACTION", {"reasons": action_reasons})
        if retry_reasons:
            _add_evidence(result, "RETRY", {
                "manifest_digest": digest,
                "reasons": retry_reasons,
            })

        if coordination_failed:
            _move_check(result, "coordination", failed=True)
        if approval_failed:
            _move_check(result, "approval", failed=True)
        _recompute_decision(result)

        if HARDENING_POLICY_VERSION not in result["warnings"]:
            result["warnings"].append(HARDENING_POLICY_VERSION)
        return finalize_report(result)
    except Exception:  # noqa: BLE001 - hardening failures must fail closed.
        sha = result.get("source_sha") if isinstance(result, dict) else None
        expected = result.get("expected_head_sha") if isinstance(result, dict) else None
        run_id = result.get("run_id") if isinstance(result, dict) else None
        fallback: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id if isinstance(run_id, str) and run_id else "unverified",
            "decision": BLOCKED,
            "merge_authorized": False,
            "human_approval": PENDING_HUMAN,
            "offline": True,
            "source_sha": sha if isinstance(sha, str) else None,
            "expected_head_sha": expected if isinstance(expected, str) else None,
            "findings": [Finding(
                "HARDENING_INTERNAL_ERROR", BLOCKER, HARDENING_SOURCE,
                "hardening diagnostic failed closed",
            ).to_record()],
            "checks": {"passed": [], "failed": ["coordination"], "skipped": []},
            "components": {
                "pr_readiness": {"status": "NOT_EVALUATED", "gate_status": "NOT_EVALUATED",
                                 "evidence_ids": []},
                "coordination": {"status": "BLOCKED", "decision": "NOT_EVALUATED",
                                 "conflicts": [], "blocked_tasks": []},
                "evidence": {"accepted_ids": [], "rejected": 0},
                "security": {"secret_redactions": 0, "unsafe_sources": 0},  # nosec B105 - integer counters, not credentials
            },
            "advisory": {
                "provider": "disabled", "status": "disabled",
                "notes": ["Deterministic policy only."], "influenced_decision": False,
            },
            "warnings": [HARDENING_POLICY_VERSION],
        }
        try:
            return finalize_report(fallback)
        except Exception:  # noqa: BLE001 - return the original schema-valid report.
            return result


def evaluate_hardened(
    document: Any,
    *,
    advisory_provider: Any = None,
    approval_evidence: Any = None,
    retry_policy: Any = None,
) -> dict[str, Any]:
    """Evaluate ``document`` and apply additive hardening diagnostics."""
    from .engine import IntegrationControlPlane

    base_report = IntegrationControlPlane(advisory_provider=advisory_provider).evaluate(document)
    return harden_report(
        base_report,
        document,
        approval_evidence=approval_evidence,
        retry_policy=retry_policy,
    )


__all__ = [
    "DESTRUCTIVE_ACTIONS",
    "HARDENING_POLICY_VERSION",
    "HardeningError",
    "evaluate_hardened",
    "harden_report",
]

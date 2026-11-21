"""Bounded, closed result schema for the advisory AI quality gate.

The schema intentionally forbids authorization fields from asserting authority:
``merge_authorized`` is always false, human approval is always pending, the mode
is always ``DRY_RUN`` and the advisory block can never influence the verdict.
"""

from __future__ import annotations

from typing import Any

from devobs.integration_control.models import RESTRICTED_ACTIONS
from devobs.integration_control.security import canonical_json, digest_payload

GATE_SCHEMA = "ai-quality-gate/1.0"
GATE_POLICY_VERSION = "ai-quality-gate-policy-v1"
MODE_DRY_RUN = "DRY_RUN"

PASS = "PASS"  # nosec B105 - public decision enum, not a password
BLOCKED = "BLOCKED"
UNVERIFIED = "UNVERIFIED"
INVALID = "INVALID"
DECISIONS = frozenset({PASS, BLOCKED, UNVERIFIED, INVALID})

BLOCKER = "BLOCKER"
UNVERIFIED_SEVERITY = "UNVERIFIED"
ADVISORY = "ADVISORY"
SEVERITIES = frozenset({BLOCKER, UNVERIFIED_SEVERITY, ADVISORY})

PENDING_HUMAN = "PENDING_HUMAN"
NOT_EVALUATED = "NOT_EVALUATED"

TOP_KEYS = frozenset({
    "schema_version", "mode", "decision", "merge_authorized", "human_approval",
    "offline", "source_sha", "findings", "checks", "coordination", "evidence_ids",
    "ci_failures", "advisory", "audit_events", "consequential_actions", "warnings",
    "gate_digest",
})
FINDING_KEYS = frozenset({"code", "severity", "source", "message"})
CHECK_KEYS = frozenset({"passed", "failed", "skipped"})
COORD_KEYS = frozenset({"decision", "conflicts", "blocked_tasks"})
CI_KEYS = frozenset({"overall_category", "findings", "repeated_count"})
CI_FINDING_KEYS = frozenset({
    "job", "step", "category", "confidence", "signature", "signature_id",
})
ADVISORY_KEYS = frozenset({"provider", "status", "notes", "influenced_decision"})
EVENT_KEYS = frozenset({
    "event", "incident_id", "category", "confidence", "status", "counts",
    "warnings", "report_digest", "detail",
})
ACTION_KEYS = frozenset({"action", "status"})

MAX_FINDINGS = 100
MAX_CI_FINDINGS = 20
MAX_EVENTS = 20
MAX_NOTES = 20
MAX_WARNINGS = 20
MAX_EVIDENCE_IDS = 100
MAX_STRING = 512


class GateValidationError(ValueError):
    """Fixed, non-sensitive schema validation diagnostic."""


def _strings(value: Any, limit: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) <= limit
        and all(
            isinstance(item, str) and 0 < len(item) <= MAX_STRING
            for item in value
        )
    )


def compute_digest(payload: dict[str, Any]) -> str:
    """Return the deterministic digest of a result without its own digest."""
    unsigned = {
        key: value for key, value in payload.items() if key != "gate_digest"
    }
    return digest_payload(unsigned)


def finalize_result(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach the digest and validate the closed result schema."""
    result = dict(payload)
    result["gate_digest"] = compute_digest(result)
    validate_result(result)
    return result


def validate_result(payload: Any) -> bool:
    """Validate a gate result; raise ``GateValidationError`` on any deviation."""
    if not isinstance(payload, dict) or set(payload) != TOP_KEYS:
        raise GateValidationError("invalid_gate_fields")
    if payload["schema_version"] != GATE_SCHEMA:
        raise GateValidationError("unsupported_gate_schema")
    if payload["mode"] != MODE_DRY_RUN:
        raise GateValidationError("dry_run_contract_violated")
    if payload["decision"] not in DECISIONS:
        raise GateValidationError("invalid_decision")
    if payload["merge_authorized"] is not False:
        raise GateValidationError("merge_authorization_asserted")
    if payload["human_approval"] != PENDING_HUMAN:
        raise GateValidationError("invalid_human_approval_state")
    if payload["offline"] is not True:
        raise GateValidationError("offline_contract_violated")
    source_sha = payload["source_sha"]
    if source_sha is not None and (
        not isinstance(source_sha, str) or len(source_sha) != 40
    ):
        raise GateValidationError("invalid_source_sha")

    findings = payload["findings"]
    if not isinstance(findings, list) or len(findings) > MAX_FINDINGS:
        raise GateValidationError("invalid_findings")
    for item in findings:
        if (
            not isinstance(item, dict)
            or set(item) != FINDING_KEYS
            or not all(
                isinstance(item[key], str) and item[key]
                for key in FINDING_KEYS
            )
            or item["severity"] not in SEVERITIES
            or len(item["message"]) > MAX_STRING
        ):
            raise GateValidationError("invalid_finding")

    checks = payload["checks"]
    if (
        not isinstance(checks, dict)
        or set(checks) != CHECK_KEYS
        or not all(_strings(checks[key], MAX_FINDINGS) for key in CHECK_KEYS)
    ):
        raise GateValidationError("invalid_checks")

    coordination = payload["coordination"]
    if (
        not isinstance(coordination, dict)
        or set(coordination) != COORD_KEYS
        or not isinstance(coordination["decision"], str)
        or not _strings(coordination["conflicts"], MAX_FINDINGS)
        or not _strings(coordination["blocked_tasks"], MAX_FINDINGS)
    ):
        raise GateValidationError("invalid_coordination")
    if not _strings(payload["evidence_ids"], MAX_EVIDENCE_IDS):
        raise GateValidationError("invalid_evidence_ids")

    ci = payload["ci_failures"]
    if (
        not isinstance(ci, dict)
        or set(ci) != CI_KEYS
        or not isinstance(ci["overall_category"], str)
        or type(ci["repeated_count"]) is not int
        or ci["repeated_count"] < 0
        or not isinstance(ci["findings"], list)
        or len(ci["findings"]) > MAX_CI_FINDINGS
    ):
        raise GateValidationError("invalid_ci_failures")
    for item in ci["findings"]:
        if (
            not isinstance(item, dict)
            or set(item) != CI_FINDING_KEYS
            or not all(
                isinstance(item[key], str) and len(item[key]) <= MAX_STRING
                for key in CI_FINDING_KEYS
            )
        ):
            raise GateValidationError("invalid_ci_finding")

    advisory = payload["advisory"]
    if (
        not isinstance(advisory, dict)
        or set(advisory) != ADVISORY_KEYS
        or not isinstance(advisory["provider"], str)
        or not isinstance(advisory["status"], str)
        or not _strings(advisory["notes"], MAX_NOTES)
        or advisory["influenced_decision"] is not False
    ):
        raise GateValidationError("invalid_advisory")

    events = payload["audit_events"]
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        raise GateValidationError("invalid_audit_events")
    for event in events:
        if not isinstance(event, dict) or set(event) - EVENT_KEYS:
            raise GateValidationError("invalid_audit_event")
        if not all(
            isinstance(value, (str, int, float, bool, dict, list))
            for value in event.values()
        ):
            raise GateValidationError("invalid_audit_event_value")

    actions = payload["consequential_actions"]
    if not isinstance(actions, list) or len(actions) != len(RESTRICTED_ACTIONS):
        raise GateValidationError("invalid_consequential_actions")
    seen: set[str] = set()
    for item in actions:
        if (
            not isinstance(item, dict)
            or set(item) != ACTION_KEYS
            or item["action"] not in RESTRICTED_ACTIONS
            or item["status"] != PENDING_HUMAN
            or item["action"] in seen
        ):
            raise GateValidationError("invalid_consequential_action")
        seen.add(item["action"])
    if seen != set(RESTRICTED_ACTIONS):
        raise GateValidationError("incomplete_consequential_actions")

    if not _strings(payload["warnings"], MAX_WARNINGS):
        raise GateValidationError("invalid_warnings")

    digest = payload["gate_digest"]
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(char not in "0123456789abcdef" for char in digest)
        or compute_digest(payload) != digest
    ):
        raise GateValidationError("gate_digest_mismatch")
    return True


def render_gate_json(result: dict[str, Any]) -> str:
    """Serialize a validated result as deterministic canonical JSON."""
    validate_result(result)
    return canonical_json(result)

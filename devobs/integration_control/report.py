"""Schema-validated, deterministic integration-control reports."""

from __future__ import annotations

from typing import Any

from .models import DECISIONS, SCHEMA_VERSION
from .security import canonical_json, digest_payload

TOP_KEYS = {
    "schema_version", "run_id", "decision", "merge_authorized", "human_approval",
    "offline", "source_sha", "expected_head_sha", "findings", "checks",
    "components", "advisory", "warnings", "report_digest",
}
FINDING_KEYS = {"code", "severity", "source", "message"}
CHECK_KEYS = {"passed", "failed", "skipped"}
COMPONENT_KEYS = {"pr_readiness", "coordination", "evidence", "security"}
PR_KEYS = {"status", "gate_status", "evidence_ids"}
COORD_KEYS = {"status", "decision", "conflicts", "blocked_tasks"}
EVIDENCE_KEYS = {"accepted_ids", "rejected"}
SECURITY_KEYS = {"secret_redactions", "unsafe_sources"}
ADVISORY_KEYS = {"provider", "status", "notes", "influenced_decision"}


class ReportError(ValueError):
    """Fixed non-sensitive validation code."""


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def compute_digest(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "report_digest"}
    return digest_payload(unsigned)


def finalize_report(payload: dict[str, Any]) -> dict[str, Any]:
    report = dict(payload)
    report["report_digest"] = compute_digest(report)
    validate_report(report)
    return report


def validate_report(payload: Any) -> bool:
    if not isinstance(payload, dict) or set(payload) != TOP_KEYS:
        raise ReportError("invalid_report_fields")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ReportError("unsupported_report_schema")
    if payload["decision"] not in DECISIONS:
        raise ReportError("invalid_decision")
    if payload["merge_authorized"] is not False:
        raise ReportError("merge_authorization_asserted")
    if payload["human_approval"] != "PENDING_HUMAN":
        raise ReportError("invalid_human_approval_state")
    if payload["offline"] is not True:
        raise ReportError("offline_contract_violated")
    for key in ("run_id", "source_sha", "expected_head_sha"):
        if payload[key] is not None and not isinstance(payload[key], str):
            raise ReportError(f"invalid_{key}")
    findings = payload["findings"]
    if not isinstance(findings, list):
        raise ReportError("invalid_findings")
    for item in findings:
        if not isinstance(item, dict) or set(item) != FINDING_KEYS:
            raise ReportError("invalid_finding_fields")
        if not all(isinstance(item[key], str) and item[key] for key in FINDING_KEYS):
            raise ReportError("invalid_finding_value")

    checks = payload["checks"]
    if not isinstance(checks, dict) or set(checks) != CHECK_KEYS:
        raise ReportError("invalid_checks")
    if not all(_is_string_list(checks[key]) for key in CHECK_KEYS):
        raise ReportError("invalid_check_lists")

    components = payload["components"]
    if not isinstance(components, dict) or set(components) != COMPONENT_KEYS:
        raise ReportError("invalid_components")
    pr = components["pr_readiness"]
    if not isinstance(pr, dict) or set(pr) != PR_KEYS or not _is_string_list(pr["evidence_ids"]):
        raise ReportError("invalid_pr_component")
    coordination = components["coordination"]
    if (not isinstance(coordination, dict) or set(coordination) != COORD_KEYS
            or not _is_string_list(coordination["conflicts"])
            or not _is_string_list(coordination["blocked_tasks"])):
        raise ReportError("invalid_coordination_component")
    evidence = components["evidence"]
    if (not isinstance(evidence, dict) or set(evidence) != EVIDENCE_KEYS
            or not _is_string_list(evidence["accepted_ids"])
            or not isinstance(evidence["rejected"], int)):
        raise ReportError("invalid_evidence_component")
    security = components["security"]
    if (not isinstance(security, dict) or set(security) != SECURITY_KEYS
            or not isinstance(security["secret_redactions"], int)
            or not isinstance(security["unsafe_sources"], int)):
        raise ReportError("invalid_security_component")

    advisory = payload["advisory"]
    if (not isinstance(advisory, dict) or set(advisory) != ADVISORY_KEYS
            or not _is_string_list(advisory["notes"])
            or advisory["influenced_decision"] is not False):
        raise ReportError("invalid_advisory")
    if not _is_string_list(payload["warnings"]):
        raise ReportError("invalid_warnings")
    digest = payload["report_digest"]
    if not isinstance(digest, str) or len(digest) != 64:
        raise ReportError("invalid_report_digest")
    if compute_digest(payload) != digest:
        raise ReportError("report_digest_mismatch")
    return True


def render_report_json(report: dict[str, Any]) -> str:
    validate_report(report)
    return canonical_json(report)


def render_report_markdown(report: dict[str, Any]) -> str:
    validate_report(report)
    checks = report["checks"]
    lines = [
        "# Integration control decision",
        "",
        f"- Decision: `{report['decision']}`",
        "- Merge authorized: `false`",
        f"- Human approval: `{report['human_approval']}`",
        f"- Offline: `{str(report['offline']).lower()}`",
        f"- Report digest: `{report['report_digest']}`",
        "",
        "## Checks",
        "",
        f"- Passed: {', '.join(checks['passed']) or 'none'}",
        f"- Failed: {', '.join(checks['failed']) or 'none'}",
        f"- Skipped: {', '.join(checks['skipped']) or 'none'}",
        "",
        "## Findings",
        "",
    ]
    if report["findings"]:
        for item in report["findings"]:
            lines.append(f"- `{item['severity']}` `{item['code']}` ({item['source']})")
    else:
        lines.append("- None")
    lines.extend(["", "## Advisory", "",
                  f"- Provider: `{report['advisory']['provider']}`",
                  "- Influenced deterministic decision: `false`"])
    return "\n".join(lines) + "\n"

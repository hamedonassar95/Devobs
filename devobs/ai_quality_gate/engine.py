"""Compose existing offline controls into one advisory ``DRY_RUN`` gate.

This module is deliberately additive. The authoritative rules stay in
``scripts/check_two_agent_tasks.py``, ``devobs/integration_control`` and
``scripts/ci_failure_intelligence.py``. The gate only normalizes their results
into one bounded schema, appends audit events, and enforces that no advisory or
CI observation can create an authorization.
"""

from __future__ import annotations

from typing import Any

from devobs.integration_control.advisory import assess_advisory
from devobs.integration_control.control_events import (
    APPROVAL_REQUIRED,
    REPORT_GENERATED,
    VALIDATION_COMPLETED,
    sanitize_event,
)
from devobs.integration_control.hardening import evaluate_hardened
from devobs.integration_control.models import (
    BLOCKER,
    INVALID,
    RESTRICTED_ACTIONS,
    UNVERIFIED_SEVERITY,
    Finding,
)
from scripts.ci_failure_intelligence import analyze_run

from .models import (
    BLOCKED,
    CHECK_KEYS,
    GATE_POLICY_VERSION,
    MODE_DRY_RUN,
    NOT_EVALUATED,
    PASS,
    PENDING_HUMAN,
    UNVERIFIED,
    finalize_result,
)

GATE_CHECK = "ai_quality_gate"
CI_CHECK = "ci_failures"
MAX_FINDINGS = 100
MAX_CI_FINDINGS = 20

CI_CODES = {
    "code": "CI_FAILURE_CODE",
    "infrastructure": "CI_FAILURE_UNVERIFIED",
    "flaky-or-external": "CI_FAILURE_FLAKY_OR_EXTERNAL",
    "ambiguous": "CI_FAILURE_AMBIGUOUS",
}
CI_SEVERITIES = {
    "code": BLOCKER,
    "infrastructure": UNVERIFIED_SEVERITY,
    "flaky-or-external": UNVERIFIED_SEVERITY,
    "ambiguous": UNVERIFIED_SEVERITY,
}


def _dedupe(records: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, ...]] = set()
    result: list[dict[str, str]] = []
    for item in records:
        key = (
            str(item.get("code", "")),
            str(item.get("severity", "")),
            str(item.get("source", "")),
            str(item.get("message", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(dict(item))
    return result[:MAX_FINDINGS]


def _ci_analysis(
    run: Any,
    jobs: Any,
) -> tuple[dict[str, Any], list[Finding]]:
    """Return bounded CI diagnostics derived only from offline fixtures."""
    empty = {
        "overall_category": NOT_EVALUATED,
        "findings": [],
        "repeated_count": 0,
    }
    if not isinstance(run, dict) or not isinstance(jobs, dict):
        return empty, []

    try:
        report = analyze_run(run, jobs)
    except Exception:  # noqa: BLE001 - diagnostics never become authority.
        return empty, [Finding(
            "CI_ANALYSIS_ERROR", UNVERIFIED_SEVERITY, "ci_failure_intelligence",
            "CI failure analysis failed closed",
        )]

    findings: list[dict[str, str]] = []
    gate_findings: list[Finding] = []
    for item in report.get("top_findings", [])[:MAX_CI_FINDINGS]:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category") or "ambiguous")[:32]
        signature = str(item.get("signature") or "unknown-failure")[:64]
        signature_id = str(item.get("signature_id") or "")[:32]
        findings.append({
            "job": str(item.get("job") or "unknown")[:80],
            "step": str(item.get("step") or "unknown")[:80],
            "category": category,
            "confidence": str(item.get("confidence") or "UNVERIFIED")[:16],
            "signature": signature,
            "signature_id": signature_id,
        })
        gate_findings.append(Finding(
            CI_CODES.get(category, "CI_FAILURE_AMBIGUOUS"),
            CI_SEVERITIES.get(category, UNVERIFIED_SEVERITY),
            "ci_failure_intelligence",
            f"ci failure signature={signature_id or 'unverified'}",
        ))

    repeated = report.get("repeated_signatures", [])
    category = str(report.get("overall_category") or "ambiguous")[:32]
    summary = {
        "overall_category": category if findings else "NO_FAILURES",
        "findings": findings,
        "repeated_count": len(repeated) if isinstance(repeated, list) else 0,
    }
    return summary, gate_findings


def _audit_events(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return bounded local audit events for every gate decision."""
    common = {
        "incident_id": str(result.get("source_sha") or "unverified")[:64],
        "category": "ai_quality_gate",
        "counts": {
            "findings": len(result["findings"]),
            "failed_checks": len(result["checks"]["failed"]),
            "evidence_ids": len(result["evidence_ids"]),
        },
        "warnings": [str(item)[:128] for item in result["warnings"]][:20],
    }
    decision = str(result["decision"])
    candidates = [
        {
            "event": VALIDATION_COMPLETED,
            **common,
            "status": decision,
            "detail": f"decision={decision}",
        },
        {
            "event": APPROVAL_REQUIRED,
            **common,
            "status": PENDING_HUMAN,
            "detail": "human approval remains pending",
        },
        {
            "event": REPORT_GENERATED,
            **common,
            "status": decision,
            "detail": "schema-valid gate result generated",
        },
    ]
    return [sanitize_event(item) for item in candidates]


def _finalize(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach redacted audit events, then digest and validate the result."""
    payload["audit_events"] = _audit_events(payload)
    return finalize_result(payload)


class AIQualityGate:
    """Read-only advisory gate over existing deterministic controls."""

    def __init__(self, *, advisory_provider: Any = None) -> None:
        self._advisory_provider = advisory_provider

    @staticmethod
    def _failure_result(code: str) -> dict[str, Any]:
        finding = Finding(code, BLOCKER, "ai_quality_gate", "gate failed closed")
        return _finalize({
            "schema_version": "ai-quality-gate/1.0",
            "mode": MODE_DRY_RUN,
            "decision": INVALID,
            "merge_authorized": False,
            "human_approval": PENDING_HUMAN,
            "offline": True,
            "source_sha": None,
            "findings": [finding.to_record()],
            "checks": {
                "passed": [],
                "failed": [],
                "skipped": [GATE_CHECK, CI_CHECK],
            },
            "coordination": {
                "decision": NOT_EVALUATED,
                "conflicts": [],
                "blocked_tasks": [],
            },
            "evidence_ids": [],
            "ci_failures": {
                "overall_category": NOT_EVALUATED,
                "findings": [],
                "repeated_count": 0,
            },
            "advisory": {
                "provider": "disabled",
                "status": "disabled",
                "notes": ["Deterministic policy only."],
                "influenced_decision": False,
            },
            "consequential_actions": [
                {"action": action, "status": PENDING_HUMAN}
                for action in RESTRICTED_ACTIONS
            ],
            "warnings": [GATE_POLICY_VERSION],
        })

    def evaluate(
        self,
        snapshot: Any,
        *,
        ci_run: Any = None,
        ci_jobs: Any = None,
        approval_evidence: Any = None,
        retry_policy: Any = None,
    ) -> dict[str, Any]:
        """Return one schema-valid, advisory, fail-closed gate result."""
        try:
            return self._evaluate(
                snapshot,
                ci_run=ci_run,
                ci_jobs=ci_jobs,
                approval_evidence=approval_evidence,
                retry_policy=retry_policy,
            )
        except Exception:  # noqa: BLE001 - unexpected failures never pass.
            return self._failure_result("GATE_INTERNAL_ERROR")

    def _evaluate(
        self,
        snapshot: Any,
        *,
        ci_run: Any,
        ci_jobs: Any,
        approval_evidence: Any,
        retry_policy: Any,
    ) -> dict[str, Any]:
        base = evaluate_hardened(
            snapshot,
            advisory_provider=None,
            approval_evidence=approval_evidence,
            retry_policy=retry_policy,
        )
        ci_summary, ci_findings = _ci_analysis(ci_run, ci_jobs)

        records = [dict(item) for item in base.get("findings", [])]
        records.extend(item.to_record() for item in ci_findings)
        records = _dedupe(records)
        severities = {item["severity"] for item in records}
        base_decision = str(base.get("decision", INVALID))

        if base_decision == INVALID:
            decision = INVALID
        elif BLOCKER in severities:
            decision = BLOCKED
        elif UNVERIFIED_SEVERITY in severities:
            decision = UNVERIFIED
        else:
            decision = PASS

        checks = {
            key: sorted(set(str(item) for item in base["checks"].get(key, [])))
            for key in CHECK_KEYS
        }
        if ci_run is None and ci_jobs is None:
            checks["skipped"].append(CI_CHECK)
        elif ci_findings:
            checks["failed"].append(CI_CHECK)
        else:
            checks["passed"].append(CI_CHECK)
        if decision != INVALID:
            checks["passed"].append(GATE_CHECK)
        for key in CHECK_KEYS:
            checks[key] = sorted(set(checks[key]))

        coordination = dict(base["components"]["coordination"])
        evidence_ids = sorted(
            str(item) for item in base["components"]["evidence"]["accepted_ids"]
        )
        untrusted_present = (
            bool(str(snapshot.get("untrusted_text", "")).strip())
            if isinstance(snapshot, dict)
            else False
        )
        codes = tuple(
            sorted({
                str(item.get("code", "")) for item in records
                if isinstance(item, dict) and item.get("code")
            })
        )[:50]
        ci_codes = tuple(sorted({
            str(item["signature"]).replace("-", "_").upper()
            for item in ci_summary["findings"]
        }))[:20]
        advisory = assess_advisory(
            self._advisory_provider,
            untrusted_text_present=untrusted_present,
            finding_codes=codes + ci_codes,
            source_sha=base.get("source_sha"),
        )
        advisory = dict(advisory)
        advisory["status"] = str(advisory.get("status", "disabled"))

        warnings = sorted(set(
            [str(item) for item in base.get("warnings", [])]
            + [GATE_POLICY_VERSION]
        ))

        return _finalize({
            "schema_version": "ai-quality-gate/1.0",
            "mode": MODE_DRY_RUN,
            "decision": decision,
            "merge_authorized": False,
            "human_approval": PENDING_HUMAN,
            "offline": True,
            "source_sha": base.get("source_sha"),
            "findings": records,
            "checks": checks,
            "coordination": {
                "decision": str(coordination.get("decision", NOT_EVALUATED)),
                "conflicts": [str(item) for item in coordination.get("conflicts", [])],
                "blocked_tasks": [
                    str(item) for item in coordination.get("blocked_tasks", [])
                ],
            },
            "evidence_ids": evidence_ids,
            "ci_failures": ci_summary,
            "advisory": advisory,
            "consequential_actions": [
                {"action": action, "status": PENDING_HUMAN}
                for action in RESTRICTED_ACTIONS
            ],
            "warnings": warnings,
        })


__all__ = ["AIQualityGate"]

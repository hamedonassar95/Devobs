"""Readiness evaluation over evidence and conflict checks."""

from __future__ import annotations

from typing import Any

from .conflicts import detect_conflicts
from .evidence import (
    BLOCKED as E_BLOCKED,
    CONFLICTED as E_CONFLICTED,
    STALE as E_STALE,
    UNVERIFIED as E_UNVERIFIED,
    VERIFIED as E_VERIFIED,
    verify_ci_checks,
    verify_commit_sha,
    verify_evidence_record,
    verify_human_approval,
    verify_sha_pair,
)
from .engine import evaluate_integration
from .validation import ValidationError, normalize_input, redact

READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
BLOCKED = "BLOCKED"
UNKNOWN = "UNKNOWN"


def evaluate_readiness(raw: Any) -> dict[str, Any]:
    try:
        ev = normalize_input(raw)
    except ValidationError as exc:
        return {
            "schema_version": 1,
            "decision": UNKNOWN,
            "human_review_required": True,
            "summary": "Input invalid; readiness unknown.",
            "evidence_checks": [{"name": "input", "state": E_BLOCKED, "message": str(exc), "details": {}}],
            "conflicts": {"checks": [], "recommendations": ["Fix input schema and re-run."]},
            "recommended_next_action": "Provide valid, bounded evidence input.",
        }

    checks = []
    checks.append(verify_commit_sha(ev.get("head_sha")))
    checks.append(verify_sha_pair("remote_branch_sha", ev.get("head_sha"), ev.get("reviewed_head_sha")))
    checks.append(verify_sha_pair("pr_head_sha", ev.get("head_sha"), ev.get("reviewed_head_sha")))
    checks.append(verify_ci_checks(ev.get("checks", []), ev.get("required_checks", []), ev.get("head_sha")))
    checks.append(verify_human_approval(ev.get("reviews", {})))

    for rec in ev.get("evidence", []) if isinstance(ev.get("evidence"), list) else []:
        if isinstance(rec, dict):
            checks.append(verify_evidence_record(rec, ev.get("head_sha")))

    # dependency/file ownership/agent/task identity/timestamps/provenance basic checks
    deps = ev.get("dependency_results", [])
    if not isinstance(deps, list) or not deps:
        checks.append({"name": "dependency_completion", "state": E_UNVERIFIED, "message": "Dependency evidence missing.", "details": {}})
    else:
        bad = [d for d in deps if isinstance(d, dict) and str(d.get("status", "")).lower() not in {"pass", "passed", "success", "ok", "up_to_date"}]
        checks.append({"name": "dependency_completion", "state": E_VERIFIED if not bad else E_BLOCKED, "message": "Dependency evidence verified." if not bad else "Dependency evidence blocked/missing.", "details": {"items": len(deps)}})

    ownership = ev.get("ownership", {})
    if not ownership.get("file_owners"):
        checks.append({"name": "file_ownership", "state": E_UNVERIFIED, "message": "File ownership evidence missing.", "details": {}})
    else:
        checks.append({"name": "file_ownership", "state": E_VERIFIED, "message": "File ownership evidence present.", "details": {"files": len(ownership.get("file_owners", {}))}})

    manifest = ownership.get("task_manifest")
    if not isinstance(manifest, dict):
        checks.append({"name": "agent_task_identity", "state": E_UNVERIFIED, "message": "Task/agent identity manifest missing.", "details": {}})
    else:
        checks.append({"name": "agent_task_identity", "state": E_VERIFIED, "message": "Task/agent identity manifest present.", "details": {"tasks": len(manifest.get("tasks", []))}})

    ts = ev.get("timestamps", {})
    if not isinstance(ts, dict) or not ts:
        checks.append({"name": "timestamps_provenance", "state": E_UNVERIFIED, "message": "Evidence timestamps/provenance missing.", "details": {}})
    else:
        checks.append({"name": "timestamps_provenance", "state": E_VERIFIED, "message": "Evidence timestamps present.", "details": {"keys": sorted(ts.keys())}})

    norm_checks = []
    for c in checks:
        norm_checks.append(c.as_dict() if hasattr(c, "as_dict") else c)

    conflict_report = detect_conflicts(ev)
    conflict_states = {c.get("state") for c in conflict_report.get("checks", []) if isinstance(c, dict)}
    evidence_states = {c.get("state") for c in norm_checks}

    engine_report = evaluate_integration(raw)

    if E_CONFLICTED in evidence_states or E_CONFLICTED in conflict_states or E_STALE in evidence_states or E_STALE in conflict_states or E_BLOCKED in evidence_states or E_BLOCKED in conflict_states or engine_report.get("decision") in {"BLOCKED", "POLICY_VIOLATION"}:
        decision = BLOCKED
        next_action = "Resolve blocking/conflicting/stale evidence before human review."
    elif E_UNVERIFIED in evidence_states or E_UNVERIFIED in conflict_states or engine_report.get("decision") == "NEEDS_EVIDENCE":
        decision = UNKNOWN
        next_action = "Collect missing verified evidence and re-run readiness check."
    else:
        decision = READY_FOR_HUMAN_REVIEW
        next_action = "Ready for human review only. No auto-merge."

    return redact({
        "schema_version": 1,
        "decision": decision,
        "human_review_required": True,
        "summary": f"Readiness decision={decision}",
        "evidence_checks": norm_checks,
        "conflicts": conflict_report,
        "engine_decision": engine_report.get("decision"),
        "recommended_next_action": next_action,
    })

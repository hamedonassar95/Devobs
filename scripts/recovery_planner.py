#!/usr/bin/env python3
"""Deterministic, fail-closed eligibility planner for Devobs recovery preparation."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

ALLOWED_CONCLUSIONS = {"failure", "timed_out"}
BLOCKED_TERMS = {
    "migration", "database migration", "production data", "credential", "credentials",
    "secret", "secrets", "branch protection", "access control", "permission",
    "billing", "destructive", "rollback",
}


@dataclass(frozen=True)
class RecoveryPlan:
    eligible: bool
    status: str
    reason: str
    risk: str
    final_state: str = "PENDING HUMAN APPROVAL"


def evaluate(record: dict) -> RecoveryPlan:
    required = ("trusted_incident", "incident_open", "conclusion", "investigation_count",
                "decision", "confidence", "reversible", "repository_scoped",
                "existing_recovery_pr", "proposed_change")
    missing = [key for key in required if key not in record]
    if missing:
        return RecoveryPlan(False, "NOT_ELIGIBLE", f"missing required evidence: {', '.join(missing)}", "unknown")

    if record["trusted_incident"] is not True:
        return RecoveryPlan(False, "NOT_ELIGIBLE", "incident trust gate failed", "high")
    if record["incident_open"] is not True:
        return RecoveryPlan(False, "NOT_ELIGIBLE", "incident is not open", "low")
    if record["conclusion"] not in ALLOWED_CONCLUSIONS:
        return RecoveryPlan(False, "NOT_ELIGIBLE", "workflow conclusion is not eligible", "low")
    if record["investigation_count"] != 1:
        return RecoveryPlan(False, "NOT_ELIGIBLE", "exactly one trusted investigation is required", "medium")
    if record["decision"] != "FIX_FORWARD":
        return RecoveryPlan(False, "NOT_ELIGIBLE", "investigation did not select FIX_FORWARD", "medium")
    try:
        confidence = float(record["confidence"])
    except (TypeError, ValueError):
        return RecoveryPlan(False, "NOT_ELIGIBLE", "confidence is invalid", "unknown")
    if not 0.0 <= confidence <= 1.0 or confidence < 0.80:
        return RecoveryPlan(False, "NOT_ELIGIBLE", "confidence is below the 0.80 threshold", "medium")
    if record["reversible"] is not True or record["repository_scoped"] is not True:
        return RecoveryPlan(False, "NOT_ELIGIBLE", "change is not proven reversible and repository-scoped", "high")
    if record["existing_recovery_pr"] is not False:
        return RecoveryPlan(False, "NOT_ELIGIBLE", "a recovery PR already exists or status is unknown", "medium")

    proposed = str(record["proposed_change"]).lower()
    blocked = sorted(term for term in BLOCKED_TERMS if re.search(rf"\b{re.escape(term)}\b", proposed))
    if blocked:
        return RecoveryPlan(False, "NOT_ELIGIBLE", f"blocked recovery scope: {', '.join(blocked)}", "high")

    return RecoveryPlan(True, "ELIGIBLE", "all deterministic recovery gates passed", "low")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    try:
        record = json.loads(args.record.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps(asdict(RecoveryPlan(False, "NOT_ELIGIBLE", f"invalid input: {exc}", "unknown"))))
        return 0
    print(json.dumps(asdict(evaluate(record)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

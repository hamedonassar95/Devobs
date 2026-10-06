#!/usr/bin/env python3
"""Deterministic Phase 8C verification controller for guarded recovery PRs."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass

REQUIRED_CHECKS = {
    "validate",
    "CodeQL",
    "Analyze (actions)",
    "Analyze (python)",
    "Analyze (javascript-typescript)",
}
RECOVERY_BRANCH_RE = re.compile(r"^recovery/incident-[1-9][0-9]*-[a-z0-9][a-z0-9-]{0,47}$")
SUCCESS = "success"


@dataclass(frozen=True)
class Verification:
    verified: bool
    status: str
    reason: str
    final_state: str = "PENDING HUMAN APPROVAL"


def evaluate(record: dict) -> Verification:
    required = ("planner_status", "patch_guard_status", "pr_state", "draft",
                "merged", "base_branch", "head_branch", "checks")
    missing = [key for key in required if key not in record]
    if missing:
        return Verification(False, "BLOCKED", f"missing evidence: {', '.join(missing)}")

    if record["planner_status"] != "ELIGIBLE":
        return Verification(False, "BLOCKED", "Phase 8A planner is not ELIGIBLE")
    if record["patch_guard_status"] != "ALLOW":
        return Verification(False, "BLOCKED", "Phase 8B patch guard is not ALLOW")
    if record["pr_state"] != "open" or record["merged"] is not False:
        return Verification(False, "BLOCKED", "recovery PR must be open and unmerged")
    if record["draft"] is not False:
        return Verification(False, "BLOCKED", "recovery PR must be ready for human review")
    if record["base_branch"] != "main":
        return Verification(False, "BLOCKED", "recovery PR must target main")
    head = record["head_branch"]
    if not isinstance(head, str) or not RECOVERY_BRANCH_RE.fullmatch(head):
        return Verification(False, "BLOCKED", "head branch is not an approved recovery branch")

    checks = record["checks"]
    if not isinstance(checks, list) or not checks:
        return Verification(False, "BLOCKED", "check evidence is missing")

    conclusions: dict[str, list[str]] = {}
    for item in checks:
        if not isinstance(item, dict):
            return Verification(False, "BLOCKED", "malformed check evidence")
        name = item.get("name")
        status = item.get("status")
        conclusion = item.get("conclusion")
        if not all(isinstance(value, str) for value in (name, status, conclusion)):
            return Verification(False, "BLOCKED", "malformed check fields")
        conclusions.setdefault(name, []).append(f"{status}:{conclusion}")

    missing_checks = sorted(REQUIRED_CHECKS - conclusions.keys())
    if missing_checks:
        return Verification(False, "BLOCKED", f"required checks missing: {', '.join(missing_checks)}")

    for name in sorted(REQUIRED_CHECKS):
        values = conclusions[name]
        if len(values) != 1:
            return Verification(False, "BLOCKED", f"ambiguous duplicate check: {name}")
        if values[0] != f"completed:{SUCCESS}":
            return Verification(False, "BLOCKED", f"required check not successful: {name}")

    return Verification(True, "VERIFIED", "all guarded recovery verification gates passed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record")
    args = parser.parse_args()
    try:
        with open(args.record, encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        result = Verification(False, "BLOCKED", f"invalid input: {exc}")
    else:
        result = evaluate(record)
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

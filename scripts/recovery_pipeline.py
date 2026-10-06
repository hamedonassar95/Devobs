#!/usr/bin/env python3
"""Phase 8 deterministic end-to-end recovery decision pipeline.

This composes the existing 8A-8D policy engines. It performs no GitHub writes.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from scripts.recovery_planner import evaluate as plan
from scripts.recovery_patch_guard import evaluate as guard_patch
from scripts.recovery_verifier import evaluate as verify
from scripts.human_approval_gate import evaluate as approve


@dataclass(frozen=True)
class PipelineResult:
    status: str
    stage: str
    reason: str
    authorized: bool
    final_state: str


def evaluate(record: dict) -> PipelineResult:
    if not isinstance(record, dict):
        return PipelineResult("BLOCKED", "INPUT", "input must be an object", False, "PENDING HUMAN APPROVAL")

    planner_input = record.get("planner")
    patch_input = record.get("patch")
    verification_input = record.get("verification")
    approval_input = record.get("approval")
    if not all(isinstance(value, dict) for value in (planner_input, patch_input, verification_input, approval_input)):
        return PipelineResult("BLOCKED", "INPUT", "all four stage inputs are required", False, "PENDING HUMAN APPROVAL")

    planner = plan(planner_input)
    if not planner.eligible:
        return PipelineResult("BLOCKED", "8A", planner.reason, False, planner.final_state)

    patch_input = dict(patch_input)
    patch_input["planner_status"] = planner.status
    patch = guard_patch(patch_input)
    if not patch.allowed:
        return PipelineResult("BLOCKED", "8B", patch.reason, False, patch.final_state)

    verification_input = dict(verification_input)
    verification_input["planner_status"] = planner.status
    verification_input["patch_guard_status"] = patch.status
    verification = verify(verification_input)
    if not verification.verified:
        return PipelineResult("BLOCKED", "8C", verification.reason, False, verification.final_state)

    approval_input = dict(approval_input)
    approval_input["verification_status"] = verification.status
    approval = approve(approval_input)
    if not approval.authorized:
        return PipelineResult(approval.status, "8D", approval.reason, False, approval.final_state)

    return PipelineResult("HUMAN_APPROVED", "8D", approval.reason, True, approval.final_state)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record")
    args = parser.parse_args()
    try:
        with open(args.record, encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        result = PipelineResult("BLOCKED", "INPUT", f"invalid input: {exc}", False, "PENDING HUMAN APPROVAL")
    else:
        result = evaluate(record)
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

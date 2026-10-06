#!/usr/bin/env python3
"""Deterministic Phase 8D gate: verification is necessary, human approval is authoritative."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ApprovalDecision:
    authorized: bool
    status: str
    reason: str
    final_state: str


def evaluate(record: dict) -> ApprovalDecision:
    required = ("verification_status", "approval", "approver_is_human",
                "approver_has_write", "pr_open", "pr_merged")
    missing = [key for key in required if key not in record]
    if missing:
        return ApprovalDecision(False, "BLOCKED", f"missing evidence: {', '.join(missing)}", "PENDING HUMAN APPROVAL")

    if record["verification_status"] != "VERIFIED":
        return ApprovalDecision(False, "BLOCKED", "recovery candidate is not VERIFIED", "PENDING HUMAN APPROVAL")
    if record["pr_open"] is not True or record["pr_merged"] is not False:
        return ApprovalDecision(False, "BLOCKED", "PR must be open and unmerged", "PENDING HUMAN APPROVAL")
    if record["approver_is_human"] is not True:
        return ApprovalDecision(False, "BLOCKED", "approval must come from a human", "PENDING HUMAN APPROVAL")
    if record["approver_has_write"] is not True:
        return ApprovalDecision(False, "BLOCKED", "approver lacks repository write authority", "PENDING HUMAN APPROVAL")

    approval = record["approval"]
    if approval == "REJECT":
        return ApprovalDecision(False, "REJECTED", "human rejected recovery", "HUMAN REJECTED")
    if approval != "APPROVE":
        return ApprovalDecision(False, "PENDING", "explicit human approval is required", "PENDING HUMAN APPROVAL")

    return ApprovalDecision(True, "HUMAN_APPROVED", "verified recovery explicitly approved by authorized human", "HUMAN APPROVED")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record")
    args = parser.parse_args()
    try:
        with open(args.record, encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        result = ApprovalDecision(False, "BLOCKED", f"invalid input: {exc}", "PENDING HUMAN APPROVAL")
    else:
        result = evaluate(record)
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

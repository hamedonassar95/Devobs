#!/usr/bin/env python3
"""Offline P01 evidence preflight. A successful read is NEVER an activation GO.

All supplied documents are untrusted assertions. No git, network, provider,
secrets, or billing endpoints are accessed by this program.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from check_p01_evidence import (InvalidEvidence, REQUIRED as REQUIRED_GATES,
                                _unique_pairs as evidence_pairs, assess as assess_evidence)
from check_p01_zero_bill_candidate import (InvalidCandidate,
                                           _unique_pairs as budget_pairs,
                                           assess as assess_budget)

_SHA = re.compile(r"[0-9a-f]{40}\Z")
_MAX_BYTES = 16_384


def read_document(path: Path, pairs):
    """Bound input and reject duplicate keys before interpreting any assertions."""
    raw = path.read_bytes()
    if len(raw) > _MAX_BYTES:
        raise ValueError("input larger than 16384 bytes")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs)


def preflight(evidence: dict, candidate: dict, source_sha: str) -> dict:
    """Return an inspectable rejection matrix. Never returns a GO decision."""
    if not isinstance(source_sha, str) or not _SHA.fullmatch(source_sha):
        raise ValueError("invalid expected source SHA")
    # Reuse canonical validators, not a second looser interpretation of P01.
    e_reviewable, evidence_blockers = assess_evidence(evidence, source_sha)
    b_reviewable, billing_blockers = assess_budget(candidate, source_sha)
    status = {
        "schema_version": 1,
        "gate": "P01",
        "decision": "NO-GO",
        "source_sha": source_sha,
        "repo_checkout_binding": "NOT_VERIFIED_BY_THIS_OFFLINE_TOOL",
        "independent_attestation": False,
        "resource_creation_authorized": False,
        "complete_invoice_ceiling_verified": False,
        "evidence_completeness": "REVIEW_ONLY_UNTRUSTED" if e_reviewable else "BLOCKED",
        "free_only_account_claims": "REVIEW_ONLY_UNTRUSTED" if b_reviewable else "BLOCKED",
        "controls": [],
        "budget_claim_blockers": billing_blockers,
        "remaining_owner_decision": "Select provider and region only after independently verified all-in USD 100/month enforcement; require fresh P01 signoff and live gate evidence before any provisioning",
    }
    for name in REQUIRED_GATES:
        entry = evidence["controls"][name]
        matching = [reason for reason in evidence_blockers if reason.startswith(name + ":")]
        status["controls"].append({
            "name": name,
            "result": "BLOCKED" if entry["state"] != "VERIFIED" or matching or not e_reviewable else "CLAIM_ONLY_UNTRUSTED",
            "reported_state": entry["state"],
            "structural_blockers": matching,
        })
    # Global revision mismatch must remain visible independently of per-control fields.
    status["evidence_global_blockers"] = [
        reason for reason in evidence_blockers
        if not any(reason.startswith(name + ":") for name in REQUIRED_GATES)
    ]
    return status


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", default="docs/p01/evidence.json")
    parser.add_argument("--billing", default="docs/p01/zero_bill_candidate.json")
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args(argv)
    try:
        evidence = read_document(Path(args.evidence), evidence_pairs)
        billing = read_document(Path(args.billing), budget_pairs)
        result = preflight(evidence, billing, args.expected_sha)
    except (OSError, UnicodeError, ValueError, TypeError,
            InvalidEvidence, InvalidCandidate) as exc:
        # Do not include untrusted document values/paths in error output.
        print(json.dumps({"gate": "P01", "decision": "NO-GO", "invalid": True,
                          "reason_class": type(exc).__name__}, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2))
    return 1  # NOT READY even when all untrusted submitted claims are complete.


if __name__ == "__main__":
    raise SystemExit(main())

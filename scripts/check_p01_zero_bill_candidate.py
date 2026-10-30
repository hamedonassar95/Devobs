#!/usr/bin/env python3
"""Pure/offline P01 free-only billing candidate guard; never authorizes a service.

All submitted account assertions are untrusted and require an independent owner
review. No provider APIs, billing data, secrets or external resources are read.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
REQUIRED_PROVIDERS = {
    "web": ("render", "Free"),
    "database": ("supabase", "Free"),
    "identity": ("auth0", "Free"),
}
ACCOUNT_FLAGS = (
    "free_tier_confirmed",
    "payment_method_absent",
    "paid_addons_absent",
    "automatic_paid_upgrade_disabled",
    "no_unpaid_or_pending_charges",
)


class InvalidCandidate(ValueError):
    pass


def _unique_pairs(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise InvalidCandidate("duplicate JSON field")
        data[key] = value
    return data


def assess(document, expected_sha):
    """Return (reviewable, blockers); reviewable is NOT a spending guarantee."""
    if type(expected_sha) is not str or SHA_RE.fullmatch(expected_sha) is None:
        raise InvalidCandidate("invalid expected commit")
    fields = {"schema_version", "decision", "source_sha", "monthly_ceiling_usd", "providers", "external_paid_services_absent"}
    if type(document) is not dict or set(document) != fields:
        raise InvalidCandidate("unexpected candidate document fields")
    if (type(document["schema_version"]) is not int or document["schema_version"] != 1
            or document["decision"] != "NO-GO"):
        raise InvalidCandidate("candidate may never authorize GO")
    if (type(document["monthly_ceiling_usd"]) is not int
            or document["monthly_ceiling_usd"] != 100):
        raise InvalidCandidate("expected all-in USD 100 ceiling")
    if type(document["source_sha"]) is not str or SHA_RE.fullmatch(document["source_sha"]) is None:
        raise InvalidCandidate("invalid candidate source SHA")
    accounts = document["providers"]
    if type(accounts) is not dict or set(accounts) != set(REQUIRED_PROVIDERS):
        raise InvalidCandidate("missing or unexpected provider")
    if type(document["external_paid_services_absent"]) not in (bool, type(None)):
        raise InvalidCandidate("invalid external service attestation")
    blockers = []
    if document["source_sha"] != expected_sha:
        blockers.append("candidate source SHA mismatch")
    if document["external_paid_services_absent"] is not True:
        blockers.append("other billable services not excluded")
    for role, (provider, plan) in REQUIRED_PROVIDERS.items():
        account = accounts[role]
        if type(account) is not dict or set(account) != {"provider", "plan", *ACCOUNT_FLAGS}:
            raise InvalidCandidate(f"{role}: unexpected account fields")
        if account["provider"] != provider or account["plan"] != plan:
            raise InvalidCandidate(f"{role}: paid or unsupported provider/plan")
        for flag in ACCOUNT_FLAGS:
            value = account[flag]
            if type(value) not in (bool, type(None)):
                raise InvalidCandidate(f"{role}: invalid {flag}")
            if value is not True:
                blockers.append(f"{role}: {flag} not independently evidenced")
    return not blockers, blockers


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True)
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args(argv)
    try:
        raw = Path(args.file).read_text(encoding="utf-8")
        if len(raw) > 16384:
            raise InvalidCandidate("candidate file too large")
        document = json.loads(raw, object_pairs_hook=_unique_pairs)
        reviewable, blockers = assess(document, args.expected_sha)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"P01 BUDGET INVALID / NO-GO: {exc}")
        return 2
    if not reviewable:
        print("P01 BUDGET BLOCKED / NO-GO: " + "; ".join(blockers))
        return 1
    print("P01 BUDGET REVIEW_ONLY: free-only account claims structurally complete; NOT independently verified, NOT an all-in spend guarantee, P01 remains NO-GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

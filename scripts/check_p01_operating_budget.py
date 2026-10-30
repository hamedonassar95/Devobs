#!/usr/bin/env python3
"""P01 operating-budget advisory. No provider billing or deployment access.

The owner accepted a $100/month OPERATING TARGET, not a guaranteed invoice cap.
This tool cannot prove invoice coverage or approve provisioning or paid AI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

_SHA = re.compile(r"[0-9a-f]{40}\Z")
_POLICY_KEYS = {
    "schema_version", "policy", "decision", "main_snapshot_sha",
    "monthly_target_usd", "allocation_usd", "alert_percent",
    "new_paid_commitment_review_at_usd", "metered_activity_review_at_usd",
    "spending_authorized", "paid_ai_enabled", "provider_accounts_confirmed",
    "p01_go",
}
_ALLOCATION_KEYS = {"core_services", "metered_services", "reserve"}
_USAGE_KEYS = {
    "schema_version", "period", "reported_cost_cents",
    "pending_unbilled_cents", "forecast_remaining_cents", "tax_and_fees_cents",
    "all_providers_included", "billing_verified",
}
_PERIOD = re.compile(r"(20[0-9]{2})-(0[1-9]|1[0-2])\Z")
_MAX_COST_CENTS = 100_000_000  # bound input; not a budget authorization


class InvalidBudget(ValueError):
    pass


def unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise InvalidBudget("duplicate input field")
        value[key] = item
    return value


def _integer(value, label, maximum=1000):
    if type(value) is not int or value < 0 or value > maximum:
        raise InvalidBudget("invalid " + label)
    return value


def validate_policy(data, expected_main_sha):
    if type(expected_main_sha) is not str or _SHA.fullmatch(expected_main_sha) is None:
        raise InvalidBudget("invalid main reference")
    if type(data) is not dict or set(data) != _POLICY_KEYS:
        raise InvalidBudget("unexpected budget policy fields")
    if (type(data["schema_version"]) is not int or data["schema_version"] != 1
            or data["policy"] != "operating_target_not_guaranteed_cap"
            or data["decision"] != "PREPARE_ONLY"):
        raise InvalidBudget("invalid budget policy mode")
    source = data["main_snapshot_sha"]
    if type(source) is not str or _SHA.fullmatch(source) is None:
        raise InvalidBudget("invalid policy source SHA")
    if source != expected_main_sha:
        raise InvalidBudget("historical main snapshot mismatch; refresh and re-review")
    target = _integer(data["monthly_target_usd"], "target")
    if target != 100:
        raise InvalidBudget("USD 100 monthly owner target cannot drift")
    allocation = data["allocation_usd"]
    if type(allocation) is not dict or set(allocation) != _ALLOCATION_KEYS:
        raise InvalidBudget("invalid allocation categories")
    for name in _ALLOCATION_KEYS:
        _integer(allocation[name], name)
    if sum(allocation.values()) != target or allocation != {
        "core_services": 60, "metered_services": 20, "reserve": 20
    }:
        raise InvalidBudget("budget allocation changed without approval")
    if data["alert_percent"] != [50, 75, 90, 100]:
        raise InvalidBudget("alert ladder must be 50/75/90/100 percent")
    for name, required in (("new_paid_commitment_review_at_usd", 75),
                           ("metered_activity_review_at_usd", 80)):
        if _integer(data[name], name) != required:
            raise InvalidBudget("unexpected operational review threshold")
    for name in ("spending_authorized", "paid_ai_enabled",
                 "provider_accounts_confirmed", "p01_go"):
        if data[name] is not False:
            raise InvalidBudget("external actions or P01 GO are not approved")
    return target * 100


def validate_usage(usage):
    if type(usage) is not dict or set(usage) != _USAGE_KEYS:
        raise InvalidBudget("invalid billing snapshot shape")
    if type(usage["schema_version"]) is not int or usage["schema_version"] != 1:
        raise InvalidBudget("invalid billing snapshot version")
    period = usage["period"]
    if type(period) is not str or _PERIOD.fullmatch(period) is None:
        raise InvalidBudget("invalid billing period")
    for name in ("reported_cost_cents", "pending_unbilled_cents",
                 "forecast_remaining_cents", "tax_and_fees_cents"):
        _integer(usage[name], name, _MAX_COST_CENTS)
    for name in ("all_providers_included", "billing_verified"):
        if type(usage[name]) is not bool:
            raise InvalidBudget("invalid evidence flag")
    return sum(usage[name] for name in
               ("reported_cost_cents", "pending_unbilled_cents",
                "forecast_remaining_cents", "tax_and_fees_cents"))


def assess(policy, expected_main_sha, usage=None):
    target_cents = validate_policy(policy, expected_main_sha)
    projected = None if usage is None else validate_usage(usage)
    coverage = (usage is not None and usage["all_providers_included"]
                and usage["billing_verified"])
    review = projected is None or not coverage
    # Thresholds are advisories only; do not claim to suspend provider billing.
    pause_metered = review or projected >= (
        policy["metered_activity_review_at_usd"] * 100)
    no_new_paid = review or projected >= (
        policy["new_paid_commitment_review_at_usd"] * 100)
    breaches = [] if projected is None else [
        percent for percent in policy["alert_percent"]
        if projected >= target_cents * percent // 100
    ]
    return {
        "decision": "NO-GO",
        "policy": "OPERATING_TARGET_ONLY",
        "target_usd": policy["monthly_target_usd"],
        "planned_allocation_usd": policy["allocation_usd"],
        "projected_total_cents": projected,
        "billing_snapshot_complete_claim": bool(coverage),
        "billing_claims_independently_authenticated": False,
        "thresholds_reached_percent": breaches,
        "recommended_no_new_paid_commitments": no_new_paid,
        "recommended_pause_metered_activity": pause_metered,
        "invoice_cap_guaranteed": False,
        "external_spend_authorized": False,
        "paid_ai_authorized": False,
        "p01_activation_authorized": False,
        "manual_owner_review_required": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default="docs/p01/operating_budget_policy.json")
    parser.add_argument("--expected-main-sha", required=True)
    parser.add_argument("--usage", help="Optional non-sensitive monthly estimate, never live billing")
    args = parser.parse_args(argv)
    try:
        def load(path):
            raw = Path(path).read_bytes()
            if len(raw) > 16384:
                raise InvalidBudget("oversized document")
            return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs)
        policy = load(args.policy)
        usage = load(args.usage) if args.usage else None
        status = assess(policy, args.expected_main_sha, usage)
    except (ValueError, OSError, UnicodeError, TypeError):
        print(json.dumps({"decision": "NO-GO", "invalid": True}, sort_keys=True))
        return 2
    print(json.dumps(status, sort_keys=True, indent=2))
    return 1  # Review only, always nonzero; never a provider cost kill switch.


if __name__ == "__main__":
    raise SystemExit(main())

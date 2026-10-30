#!/usr/bin/env python3
"""Offline commercial-P01 supplier eligibility; NEVER an activation or billing oracle.

No provider API calls, account reads, secrets, provision, or deployment actions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

SHA = re.compile(r"[0-9a-f]{40}\Z")
ROLES = ("web", "database", "identity", "ai")
COSTS = ("web_compute", "database_compute", "identity", "ai_inference",
         "backups_and_storage", "network_and_build", "taxes_and_fees",
         "addons", "other_providers")
LIVE = ("oidc_jwks", "restricted_postgres_rls", "isolated_encrypted_restore",
        "approved_region_and_terms", "commercial_terms", "operations_on_call")
MAX_BYTES = 16_384
PLANS = {
    "web": {"render": {"free", "starter", "standard"},
            "vercel": {"hobby", "pro"}, "cloudflare": {"workers-free", "workers-paid"}},
    "database": {"supabase": {"free", "pro"}, "cloudflare": {"d1-free", "d1-paid"}},
    "identity": {"auth0": {"free", "essentials"}, "supabase": {"free", "pro"}},
    "ai": {"none": {"disabled"}, "openai": {"prepaid", "invoiced"},
           "cloudflare": {"workers-ai-free", "workers-ai-paid"}},
}


class InvalidTarget(ValueError):
    """Incorrect schema; fail closed without exposing supplied content."""


def unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise InvalidTarget("duplicate key")
        out[key] = value
    return out


def assess(data, expected_sha):
    if type(expected_sha) is not str or SHA.fullmatch(expected_sha) is None:
        raise InvalidTarget("invalid requested revision")
    if type(data) is not dict or set(data) != {
        "schema_version", "decision", "source_sha", "scope",
        "monthly_total_ceiling_usd", "providers", "invoice_coverage",
        "live_security", "owner_production_signoff"
    }:
        raise InvalidTarget("invalid target shape")
    if (type(data["schema_version"]) is not int or data["schema_version"] != 1
            or data["decision"] != "NO-GO" or data["scope"] != "commercial_pilot"
            or type(data["monthly_total_ceiling_usd"]) is not int
            or data["monthly_total_ceiling_usd"] != 100):
        raise InvalidTarget("unsupported policy or cost threshold")
    if type(data["source_sha"]) is not str or SHA.fullmatch(data["source_sha"]) is None:
        raise InvalidTarget("invalid source revision")
    if data["owner_production_signoff"] is not False:
        raise InvalidTarget("cannot mark production authorized")
    providers = data["providers"]
    if type(providers) is not dict or set(providers) != set(ROLES):
        raise InvalidTarget("missing provider roles")
    for role in ROLES:
        entry = providers[role]
        if type(entry) is not dict or set(entry) != {"provider", "plan"}:
            raise InvalidTarget("invalid provider profile")
        provider, plan = entry["provider"], entry["plan"]
        if (type(provider) is not str or type(plan) is not str
                or provider not in PLANS[role] or plan not in PLANS[role][provider]):
            raise InvalidTarget("unsupported supplier/plan requires separate review")
    for key, keys in (("invoice_coverage", COSTS), ("live_security", LIVE)):
        values = data[key]
        if type(values) is not dict or set(values) != set(keys):
            raise InvalidTarget("incomplete gate categories")
        if any(type(v) not in (bool, type(None)) for v in values.values()):
            raise InvalidTarget("invalid gate attestation type")
    hard = []
    web, db, ai = providers["web"], providers["database"], providers["ai"]
    if web == {"provider": "render", "plan": "free"}:
        hard.append("Render Free web is explicitly not for production")
    if web == {"provider": "vercel", "plan": "hobby"}:
        hard.append("Vercel Hobby forbids commercial deployments")
    if db == {"provider": "supabase", "plan": "free"}:
        hard.append("Supabase Free has no automatic managed backups")
    if db["provider"] == "cloudflare":
        hard.append("Cloudflare D1 uses SQLite, not required PostgreSQL/RLS")
    if ai == {"provider": "openai", "plan": "prepaid"}:
        hard.append("Prepaid OpenAI API may overrun credits before cutoff")
    if ai == {"provider": "cloudflare", "plan": "workers-ai-free"}:
        hard.append("Workers AI Free quota exhaustion fails inference; no continuity proof")
    costs = sorted(k for k, v in data["invoice_coverage"].items() if v is not True)
    live = sorted(k for k, v in data["live_security"].items() if v is not True)
    revision_match = data["source_sha"] == expected_sha
    return {
        "gate": "P01-to-commercial-pilot",
        "decision": "NO-GO",
        "source_sha": expected_sha,
        "source_revision_matches": revision_match,
        "known_plan_obstacles": hard,
        "unverified_invoice_categories": costs,
        "unverified_live_controls": live,
        "claimed_controls_complete": not (hard or costs or live or not revision_match),
        "independent_provider_invoice_guarantee": False,
        "provisioning_authorized": False,
        "ai_paid_calls_authorized": False,
        "owner_production_signoff": False,
        "review_only": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="docs/p01/commercial_pilot_candidate.json")
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args(argv)
    try:
        raw = Path(args.file).read_bytes()
        if len(raw) > MAX_BYTES:
            raise InvalidTarget("oversized input")
        result = assess(json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs),
                        args.expected_sha)
    except (OSError, UnicodeError, ValueError, TypeError):
        print(json.dumps({"gate": "P01-to-commercial-pilot", "decision": "NO-GO",
                          "invalid": True}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 1  # Contract eligibility requires independent evidence and human signoff.


if __name__ == "__main__":
    raise SystemExit(main())

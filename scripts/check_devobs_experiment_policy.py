#!/usr/bin/env python3
"""Check Devobs control-plane / experiment separation offline.

Passing means a proposed manifest is structurally safe, NOT a live integration,
authorization, or permission to provision any account or resource.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

PATH = Path(__file__).resolve().parents[1] / "docs/architecture/devobs_experiment_policy.json"
IDS = {"phone_repair_assistant_v2", "al_dala_mobile"}
FLOWS = [
    "anonymized_synthetic_test_event_to_devobs",
    "devobs_read_only_diagnostic_recommendation_to_experiment",
]
FORBIDDEN = (
    "cross_project_database_access", "shared_admin_credentials",
    "shared_tenant_identity_without_verification", "copy_customer_data_into_core",
    "experiment_can_trigger_production", "experiment_can_modify_main",
    "unapproved_paid_ai_calls",
)


def check(data):
    errors = []
    if type(data) is not dict or set(data) != {
        "schema_version", "project", "authority_repository", "architecture_status",
        "central_control_plane", "experiments", "integration_policy",
        "allowed_conceptual_flow", "real_external_connections_authorized",
        "spend_authorized", "customer_data_transfer_authorized"
    }:
        return ["invalid architecture manifest keys"]
    if (type(data["schema_version"]) is not int or data["schema_version"] != 1
            or data["project"] != "Devobs AI Intelligence"
            or data["authority_repository"] != "hamedonassar95/Devobs"
            or data["architecture_status"] != "PROPOSED_NOT_DEPLOYED"):
        errors.append("invalid authority or status")
    c = data["central_control_plane"]
    if (type(c) is not dict or set(c) != {
        "role", "environment", "organization_strategy", "organization_name_proposed",
        "organization_created", "organization_plan_proposed", "project_name_proposed",
        "project_created", "region_proposed", "account_quote_verified", "p01_go"
    }):
        errors.append("invalid control plane")
    else:
        for k, v in {"role":"core", "environment":"planned-p01-synthetic",
                     "organization_strategy":"dedicated_new_supabase_organization",
                     "organization_name_proposed":"Devobs AI Intelligence",
                     "organization_plan_proposed":"free",
                     "project_name_proposed":"devobs-p01-staging",
                     "region_proposed":"eu-central-1"}.items():
            if c.get(k) != v:
                errors.append("unexpected control-plane " + k)
        for key in ("organization_created", "project_created", "account_quote_verified", "p01_go"):
            if c.get(key) is not False:
                errors.append("unverified external state: " + key)
    projects = data["experiments"]
    if type(projects) is not list or len(projects) != 2:
        errors.append("incorrect experiment list")
    else:
        seen = set()
        for x in projects:
            if type(x) is not dict or set(x) != {
                "id", "label", "role", "data_boundary", "live_devobs_integration_verified"
            }:
                errors.append("invalid experiment entry")
                continue
            seen.add(x["id"])
            if (x["role"] != "experiment" or x["live_devobs_integration_verified"] is not False
                    or x["data_boundary"] not in ("own_existing_project", "own_independent_resources")):
                errors.append("experiment boundary may not be promoted")
        if seen != IDS:
            errors.append("unexpected/duplicate experiment identities")
    i = data["integration_policy"]
    if type(i) is not dict or set(i) != set(FORBIDDEN) | {"proposal_only", "human_approval_required"}:
        errors.append("invalid integration policy")
    else:
        for k in FORBIDDEN:
            if i[k] is not False:
                errors.append("unsafe integration permission: " + k)
        for k in ("proposal_only", "human_approval_required"):
            if i[k] is not True:
                errors.append("approval or proposal boundary missing")
    if data["allowed_conceptual_flow"] != FLOWS:
        errors.append("unexpected integration flow")
    for key in ("real_external_connections_authorized", "spend_authorized",
                "customer_data_transfer_authorized"):
        if data[key] is not False:
            errors.append("external action not permitted: " + key)
    return errors


def main():
    try:
        raw = PATH.read_bytes()
        if len(raw) > 16000:
            raise ValueError("oversized policy")
        def unique(pairs):
            out = {}
            for k,v in pairs:
                if k in out:
                    raise ValueError("duplicate JSON key")
                out[k]=v
            return out
        policy = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
        violations = check(policy)
    except (OSError, UnicodeError, ValueError, TypeError):
        print("FAIL: Devobs core boundary manifest missing or invalid", file=sys.stderr)
        return 1
    if violations:
        for item in violations:
            print("FAIL: "+item, file=sys.stderr)
        return 1
    print("PASS: Devobs control plane and experiment boundaries validated (proposal only; P01 NO-GO)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Offline, fail-closed check for the public Devobs integration inventory.

No network, provider SDK, credentials, account mutations, deployments, or cost.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

INVENTORY = Path(__file__).resolve().parents[1] / "docs/integrations/service-inventory.json"
EXPECTED_IDS = {"gitbook", "codex", "aictrl", "flyio", "lovable", "openart", "openai-docs-mcp"}
VALID_STATUSES = {"import_confirmed", "github_app_installed", "account_connected_unlinked",
                  "draft_handoff_only", "config_committed_unverified"}
DENIED_POLICY_FLAGS = (
    "default_branch_changes_allowed",
    "production_deploy_allowed",
    "provider_configuration_changes_allowed",
    "paid_operations_allowed",
    "secret_operations_allowed",
)


def validate_catalog(data: Any) -> list[str]:
    """Return actionable errors without ever trusting unknown input as success."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["Catalog must be a JSON object."]

    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        errors.append("schema_version must be exactly 1.")
    try:
        dt.date.fromisoformat(data["review_date"])
    except (TypeError, ValueError, KeyError):
        errors.append("review_date must be an ISO calendar date.")
    if data.get("repository") != "hamedonassar95/Devobs":
        errors.append("repository must refer to hamedonassar95/Devobs.")
    if data.get("classification") != "PUBLIC_REPOSITORY_SAFE_METADATA_ONLY":
        errors.append("classification must state public metadata only.")

    policy = data.get("policy")
    if not isinstance(policy, dict):
        errors.append("policy must be an object.")
    else:
        if policy.get("default_branch") != "main":
            errors.append("policy.default_branch must be main.")
        for flag in DENIED_POLICY_FLAGS:
            if policy.get(flag) is not False:
                errors.append(f"policy.{flag} must explicitly be false.")
        if not isinstance(policy.get("approval_required_for"), str) or not policy["approval_required_for"].strip():
            errors.append("policy.approval_required_for must be nonempty.")

    services = data.get("services")
    if not isinstance(services, list):
        return errors + ["services must be an array."]
    if len(services) != len(EXPECTED_IDS):
        errors.append(f"Expected exactly {len(EXPECTED_IDS)} service records.")

    ids: list[str] = []
    for index, svc in enumerate(services):
        label = f"services[{index}]"
        if not isinstance(svc, dict):
            errors.append(f"{label} must be an object.")
            continue

        identifier = svc.get("id")
        if not isinstance(identifier, str):
            errors.append(f"{label}.id must be a string.")
            continue
        ids.append(identifier)
        label = f"services[{index}] ({identifier})"
        if not isinstance(svc.get("name"), str) or not svc["name"].strip():
            errors.append(f"{label}.name must be nonempty.")
        if svc.get("integration_status") not in VALID_STATUSES:
            errors.append(f"{label}.integration_status is unsupported.")
        if svc.get("provider_writes_authorized") is not False:
            errors.append(f"{label}: provider writes require a separate owner approval.")
        if svc.get("cost_authorized") is not False:
            errors.append(f"{label}: paid operations require a separate owner approval.")
        if type(svc.get("runtime_verified")) is not bool:
            errors.append(f"{label}.runtime_verified must be boolean.")
        if not isinstance(svc.get("verified_capability"), str) or not svc["verified_capability"].strip():
            errors.append(f"{label}.verified_capability must be nonempty.")
        if not isinstance(svc.get("blocker"), str) or not svc["blocker"].strip():
            errors.append(f"{label}.blocker must be nonempty.")
        evidence = svc.get("evidence")
        if not isinstance(evidence, list) or not evidence or any(
            not isinstance(item, str) or not item.strip() for item in evidence
        ):
            errors.append(f"{label}.evidence must contain nonempty textual observations.")
        if identifier == "gitbook":
            if svc.get("integration_status") != "import_confirmed" or svc.get("runtime_verified") is not True:
                errors.append("GitBook is verified only for the observed initial import.")
            if svc.get("observed_branch") != "main" or svc.get("observed_directory") != "docs/gitbook-sync-prep":
                errors.append("GitBook observed source path must match the 2026-10-25 evidence.")
        elif identifier == "openart":
            if svc.get("integration_status") != "draft_handoff_only":
                errors.append("OpenArt has only a draft handoff, not an active generation connector.")
            if svc.get("observed_directory") != ".codex/examples/openart-mcp.toml":
                errors.append("OpenArt source must remain an opt-in example.")
            if svc.get("runtime_verified") is True:
                errors.append("OpenArt live generation is not verified.")
        elif identifier == "openai-docs-mcp":
            if svc.get("integration_status") != "config_committed_unverified":
                errors.append("Docs MCP configuration must not be labeled as runtime verified.")
            if svc.get("observed_directory") != ".codex/config.toml":
                errors.append("Docs MCP configuration source path is not verified.")
            if svc.get("runtime_verified") is True:
                errors.append("Docs MCP runtime handshake is not verified.")
        elif svc.get("runtime_verified") is True:
            errors.append(f"{label}: runtime is not verified for this provider.")

    if len(ids) != len(set(ids)):
        errors.append("Duplicate service ids are forbidden.")
    if set(ids) != EXPECTED_IDS:
        errors.append("Service ids must match the seven explicitly scoped providers.")
    return errors


def main() -> int:
    try:
        if INVENTORY.stat().st_size > 65536:
            print("FAIL: inventory exceeds the 64 KiB review cap.", file=sys.stderr)
            return 1
        payload = json.loads(INVENTORY.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"FAIL: cannot read or parse inventory: {exc}", file=sys.stderr)
        return 1
    errors = validate_catalog(payload)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: seven integration records, evidence and default-deny controls validated locally.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

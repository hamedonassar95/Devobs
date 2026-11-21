#!/usr/bin/env python3
"""Validate a non-secret offline design contract; never authenticate or execute."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

MAX_BYTES = 16_384
AUDIT_FIELDS = {"event_id", "occurred_at", "provider", "source_sha", "mode",
                "auth_state", "approval_state", "decision", "reason_codes"}
FIELDS = {
    "schema_version", "provider", "mode", "read_only", "default_platform", "source_sha",
    "human_approval_required", "authentication_required", "auth_failure_policy",
    "authentication_status", "automatic_production_deployment", "audit_redaction_required",
    "audit_fields",
}


class ReadinessError(ValueError):
    """Fixed, non-sensitive failure category."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ReadinessError(code)


def assess(config: object) -> dict:
    require(type(config) is dict and set(config) == FIELDS, "invalid_fields")
    require(type(config["schema_version"]) is int and config["schema_version"] == 1, "invalid_schema")
    require(type(config["provider"]) is str
            and config["provider"] in {"pulumi_delivery", "azure_catalyst"}, "invalid_provider")
    require(config["mode"] == "DRY_RUN" and config["default_platform"] == "GITHUB_ACTIONS_GCP",
            "unsafe_mode_or_platform")
    for key in ("read_only", "human_approval_required", "authentication_required", "audit_redaction_required"):
        require(config[key] is True, "unsafe_policy")
    require(config["automatic_production_deployment"] is False, "unsafe_policy")
    require(config["auth_failure_policy"] == "DENY"
            and config["authentication_status"] == "NOT_CHECKED", "invalid_auth_policy")
    require(type(config["source_sha"]) is str
            and re.fullmatch(r"[0-9a-f]{40}", config["source_sha"]) is not None, "invalid_revision")
    fields = config["audit_fields"]
    require(type(fields) is list and len(fields) == len(AUDIT_FIELDS)
            and all(type(item) is str for item in fields), "invalid_audit_schema")
    require(set(fields) == AUDIT_FIELDS, "invalid_audit_schema")
    return {
        "schema_version": 1,
        "status": "OFFLINE_DESIGN_VALID_ONLY",
        "provider": config["provider"],
        "source_sha": config["source_sha"],
        "mode": "DRY_RUN",
        "authentication_status": "NOT_CHECKED",
        "human_approval_status": "PENDING",
        "provider_connection_verified": False,
        "execution_authorized": False,
        "production_ready": False,
    }


def unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, "invalid_json")
        result[key] = value
    return result


def reject_constant(_value: str) -> None:
    raise ReadinessError("invalid_json")


def main(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Synthetic, non-secret JSON policy file")
    options = parser.parse_args(args)
    try:
        with options.input.open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
        require(len(raw) <= MAX_BYTES, "input_too_large")
        config = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                            parse_constant=reject_constant)
        result = assess(config)
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        reason = str(error) if isinstance(error, ReadinessError) else "invalid_input"
        print(json.dumps({"schema_version": 1, "status": "INVALID", "reason_codes": [reason],
                          "execution_authorized": False}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Offline, presence-only triage for Devobs P01 staging startup settings.

The inventory accepts configuration *names* and the states ``present``,
``missing`` or ``not_checked``. It never reads the process environment,
interprets configuration values, contacts a provider, or proves readiness.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections.abc import Mapping
from typing import TextIO


SCHEMA_VERSION = 1
MAX_INVENTORY_BYTES = 8192
PRESENCE_STATES = frozenset({"present", "missing", "not_checked"})
REQUIRED_NAMES = (
    "DEVOBS_OIDC_ISSUER",
    "DEVOBS_OIDC_AUDIENCE",
    "DEVOBS_OIDC_CLIENT_ID",
    "DEVOBS_OIDC_METADATA_JSON",
    "DEVOBS_OIDC_JWKS_JSON",
    "DEVOBS_PG_DSN",
)
TLS_CONTEXT_NAMES = (
    "DEVOBS_PG_TLS_MODE",
    "RENDER",
    "RENDER_SERVICE_TYPE",
)
ALLOWED_NAMES = frozenset((*REQUIRED_NAMES, *TLS_CONTEXT_NAMES))


class InventoryError(ValueError):
    """A fixed-code input error that never includes user input."""

    def __init__(self, code: str = "invalid_inventory") -> None:
        super().__init__(code)
        self.code = code


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise InventoryError()
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise InventoryError()


def parse_inventory(raw: bytes) -> dict[str, str]:
    """Parse the narrow JSON presence inventory; reject all value material."""
    if type(raw) is not bytes or len(raw) > MAX_INVENTORY_BYTES:
        raise InventoryError()
    try:
        text = raw.decode("utf-8", errors="strict")
        payload = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError):
        raise InventoryError() from None

    if type(payload) is not dict or set(payload) != {"schema_version", "variables"}:
        raise InventoryError()
    version = payload["schema_version"]
    variables = payload["variables"]
    if type(version) is not int or version != SCHEMA_VERSION or type(variables) is not dict:
        raise InventoryError()

    checked: dict[str, str] = {}
    for name, state in variables.items():
        if type(name) is not str or name not in ALLOWED_NAMES:
            raise InventoryError()
        if type(state) is not str or state not in PRESENCE_STATES:
            raise InventoryError()
        checked[name] = state
    return checked


def _required_status(state: str | None) -> tuple[str, str]:
    if state == "missing":
        return (
            "CONFIRMED_MISSING_CONFIGURATION",
            "The operator inventory explicitly marks this required name missing.",
        )
    if state == "present":
        return (
            "PRESENT_BUT_VALIDITY_UNVERIFIED",
            "Only the name's presence was reported; its value and validity were not inspected.",
        )
    return (
        "INSUFFICIENT_EVIDENCE",
        "The operator inventory did not confirm whether this required name is present.",
    )


def triage(variables: Mapping[str, str]) -> dict[str, object]:
    """Produce a deterministic report from already-validated presence states."""
    requirements = []
    for name in REQUIRED_NAMES:
        status, reason = _required_status(variables.get(name))
        requirements.append({"name": name, "status": status, "reason": reason})

    tls_mode_state = variables.get("DEVOBS_PG_TLS_MODE")
    render_context_present = all(
        variables.get(name) == "present"
        for name in TLS_CONTEXT_NAMES[1:]
    )
    if tls_mode_state == "missing":
        tls_status = "PRESENT_BUT_VALIDITY_UNVERIFIED"
        tls_reason = (
            "The code defaults to verify-full when this name is absent, but the DSN's "
            "sslmode and sslrootcert cannot be checked from presence-only evidence."
        )
    elif tls_mode_state == "present" and render_context_present:
        tls_status = "PRESENT_BUT_VALIDITY_UNVERIFIED"
        tls_reason = (
            "The mode name and conditional Render-context names were inventoried, but their "
            "values and the DSN's sslmode/sslrootcert were intentionally not inspected."
        )
    else:
        tls_status = "INSUFFICIENT_EVIDENCE"
        tls_reason = (
            "The TLS selector or its conditional Render-context names were not fully inventoried; "
            "mode applicability and values remain unknown."
        )

    statuses = [row["status"] for row in requirements]
    if "CONFIRMED_MISSING_CONFIGURATION" in statuses:
        overall = "CONFIRMED_MISSING_CONFIGURATION"
    elif "INSUFFICIENT_EVIDENCE" in statuses or tls_status == "INSUFFICIENT_EVIDENCE":
        overall = "INSUFFICIENT_EVIDENCE"
    else:
        overall = "PRESENT_BUT_VALIDITY_UNVERIFIED"

    render_context = []
    for name in TLS_CONTEXT_NAMES[1:]:
        state = variables.get(name, "not_checked")
        render_context.append({
            "name": name,
            "presence": state,
            "applicability": "conditional_on_render_internal_tls_mode",
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "status": overall,
        "requirements": requirements,
        "tls_assessment": {
            "status": tls_status,
            "mode_name_presence": tls_mode_state or "not_checked",
            "default_mode_when_name_is_absent": "verify-full",
            "conditional_render_mode": "render-internal-require",
            "render_context": render_context,
            "reason": tls_reason,
            "verification_required": [
                "verify-full requires sslmode=verify-full and a valid sslrootcert in DEVOBS_PG_DSN",
                "render-internal-require requires RENDER=true, RENDER_SERVICE_TYPE=web, "
                "and DSN sslmode absent or require",
                "presence-only inventory cannot validate TLS values, certificate identity, "
                "or mode applicability",
            ],
        },
        "readiness_claim": "NOT_ESTABLISHED",
        "limitations": [
            "This tool reads only an operator-supplied JSON inventory of allowed names and presence states.",
            "It does not read environment variables or accept configuration values.",
            "A present name does not prove its value, OIDC metadata, JWKS, database access, TLS, or readiness.",
            "This report is not Render verification, deployment authorization, or P01 approval.",
        ],
    }


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        self.exit(2, "ERROR: invalid_cli_arguments\n")


def _read_inventory(path: pathlib.Path) -> bytes:
    try:
        with path.open("rb") as source:
            raw = source.read(MAX_INVENTORY_BYTES + 1)
    except OSError:
        raise InventoryError("inventory_unavailable") from None
    if len(raw) > MAX_INVENTORY_BYTES:
        raise InventoryError()
    return raw


def main(argv: list[str] | None = None, *, stdout: TextIO | None = None,
         stderr: TextIO | None = None) -> int:
    output = stdout or sys.stdout
    errors = stderr or sys.stderr
    parser = _SafeArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "--inventory",
        required=True,
        type=pathlib.Path,
        metavar="JSON_FILE",
        help="path to a non-sensitive name/presence inventory (never pass values)",
    )
    args = parser.parse_args(argv)
    try:
        variables = parse_inventory(_read_inventory(args.inventory))
    except InventoryError as exc:
        print(f"ERROR: {exc.code}", file=errors)
        return 4
    report = triage(variables)
    serialized = json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    print(serialized, file=output)
    if report["status"] == "CONFIRMED_MISSING_CONFIGURATION":
        return 2
    if report["status"] == "INSUFFICIENT_EVIDENCE":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

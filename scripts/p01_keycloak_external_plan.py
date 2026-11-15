#!/usr/bin/env python3
"""Offline external-route candidate builder; never contacts or deploys to Render.

Inputs contain public outbound CIDRs only, not credentials or provider exports.
Uses only the Python standard library. Output is a review artifact, not evidence
of network ownership, owner approval, TLS or identity readiness.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import sys
import tempfile

TEMPLATE = Path(__file__).resolve().parents[1] / "deploy/keycloak-hosted/render.yaml"
# Drift guard for the reviewed template, not an authenticity or approval proof.
TEMPLATE_SHA256 = "930528ddbac787429c394dd3df9c47bd75b084ecc120a79f4f5bc1aac1fa6ea0"
MAX_BYTES = 8192


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def read_ranges(path: Path) -> list[str]:
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError
    inventory = json.loads(raw, object_pairs_hook=unique_object)
    if (type(inventory) is not dict
            or set(inventory) != {"schema_version", "region", "outbound_cidrs"}
            or type(inventory["schema_version"]) is not int
            or inventory["schema_version"] != 1
            or inventory["region"] != "frankfurt"):
        raise ValueError
    cidrs = inventory["outbound_cidrs"]
    if type(cidrs) is not list or not 1 <= len(cidrs) <= 20:
        raise ValueError
    networks = []
    for cidr in cidrs:
        if type(cidr) is not str or "/" not in cidr:
            raise ValueError
        network = ipaddress.ip_network(cidr, strict=True)
        # Deliberately narrow plan policy: public IPv4 /24 or smaller only.
        # Broader provider ranges need a separate network-policy review.
        if (network.version != 4 or network.prefixlen < 24
                or not network.is_global or network.is_multicast or str(network) != cidr
                or any(network.overlaps(previous) for previous in networks)):
            raise ValueError
        networks.append(network)
    return [str(network) for network in networks]


def build_plan(cidrs: list[str]) -> str:
    raw = TEMPLATE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA256:
        raise ValueError
    template = raw.decode("utf-8")
    marker = "    ipAllowList: []\n"
    if template.count(marker) != 1:
        raise ValueError
    entries = [
        {"source": cidr, "description": "Keycloak outbound candidate; owner review required"}
        for cidr in cidrs
    ]
    # Render Blueprint uses `source`, not the REST API's `cidrBlock` field.
    # https://render.com/docs/blueprint-spec#database-ip-allow-list
    # A JSON flow sequence is valid YAML. Preserve every other template byte:
    # YAML 1.1 parsers would incorrectly coerce Render's `off` enums to false.
    candidate = template.replace(marker, "    ipAllowList: " + json.dumps(entries) + "\n")
    return ("# REVIEW ONLY: no network, billing, TLS or identity approval.\n"
            "# DB host must be its exact Frankfurt external DNS name.\n"
            + candidate)


def main(argv=None) -> int:
    parser = Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    try:
        args = parser.parse_args(argv)
        candidate = build_plan(read_ranges(args.inventory))
        # Finish writing before exclusive publication; failure never exposes a
        # truncated YAML document. A hard link refuses existing paths/symlinks.
        with tempfile.TemporaryDirectory(prefix=".keycloak-plan-", dir=args.output.parent) as directory:
            staged = Path(directory) / "candidate.yaml"
            staged.write_text(candidate, encoding="utf-8")
            os.link(staged, args.output)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        print("EXTERNAL_ROUTE_PLAN_BLOCKED", file=sys.stderr)
        return 2
    print("EXTERNAL_ROUTE_PLAN_ONLY: live_tls_and_identity_unverified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

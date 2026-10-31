#!/usr/bin/env python3
"""Fail-closed offline validator for P01 T07 trust-boundary acceptance matrix.

This is contract integrity only, NOT a staging penetration test or approval.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "docs" / "p01" / "threat-model.json"
ZONES = {"network", "service", "identity", "tenant", "database", "telemetry",
         "connector", "ai", "approval", "provider", "ci", "release"}
BOUNDARIES = {
    "B01": ("network", "service"),
    "B02": ("identity", "service"),
    "B03": ("service", "tenant"),
    "B04": ("tenant", "database"),
    "B05": ("telemetry", "service"),
    "B06": ("connector", "ai"),
    "B07": ("ai", "approval"),
    "B08": ("ci", "release"),
    "B09": ("provider", "service"),
}
CASES = {"AC%02d" % i for i in range(1, 13)}
CASE_BOUNDARIES = {
    "AC01": "B01", "AC02": "B02", "AC03": "B02", "AC04": "B03",
    "AC05": "B04", "AC06": "B04", "AC07": "B05", "AC08": "B06",
    "AC09": "B07", "AC10": "B08", "AC11": "B09", "AC12": "B09",
}


class ThreatModelError(ValueError):
    """Missing, inconsistent or overclaimed safety evidence."""


def exact_fields(obj, expected, name):
    if not isinstance(obj, dict) or set(obj) != set(expected):
        raise ThreatModelError("%s: unexpected or missing fields" % name)


def nonempty(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 300:
        raise ThreatModelError("%s: expected bounded nonempty string" % name)


def validate(data, root=ROOT):
    exact_fields(data, {"schema_version", "repository", "phase", "task",
                        "source_main_sha", "decision", "evidence_scope",
                        "owner_approval_required", "budget", "actions",
                        "zones", "boundaries", "abuse_cases"}, "root")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ThreatModelError("schema_version")
    if (data["repository"], data["phase"], data["task"]) != (
            "hamedonassar95/Devobs", "P01", "T07"):
        raise ThreatModelError("repository or task")
    if not isinstance(data["source_main_sha"], str) or not re.fullmatch(
            r"[0-9a-f]{40}", data["source_main_sha"]):
        raise ThreatModelError("source_main_sha")
    if data["decision"] != "NO-GO" or data["evidence_scope"] != "OFFLINE_THREAT_MODEL_ONLY":
        raise ThreatModelError("unsupported promotion or evidence claim")
    if data["owner_approval_required"] is not True:
        raise ThreatModelError("owner approval must be required")
    exact_fields(data["budget"], {"all_in_monthly_ceiling_usd", "enforcement_verified"}, "budget")
    if type(data["budget"]["all_in_monthly_ceiling_usd"]) is not int or (
            data["budget"]["all_in_monthly_ceiling_usd"] != 100 or
            data["budget"]["enforcement_verified"] is not False):
        raise ThreatModelError("unverified all-in $100 monthly cap")
    required_flags = {"staging_provisioning_authorized", "paid_inference_authorized",
                      "production_release_authorized", "autonomous_changes_authorized"}
    exact_fields(data["actions"], required_flags, "actions")
    if any(data["actions"][flag] is not False for flag in required_flags):
        raise ThreatModelError("unapproved external action")
    zones = data["zones"]
    if not isinstance(zones, list) or len(zones) != len(ZONES):
        raise ThreatModelError("zones: incomplete trust inventory")
    seen = set()
    for zone in zones:
        exact_fields(zone, {"id", "role"}, "zone")
        if zone["id"] not in ZONES or zone["id"] in seen:
            raise ThreatModelError("zone: missing or duplicate identity")
        seen.add(zone["id"])
        nonempty(zone["role"], "zone.role")
    if seen != ZONES:
        raise ThreatModelError("zones: trust coverage gap")
    items = data["boundaries"]
    if not isinstance(items, list) or len(items) != len(BOUNDARIES):
        raise ThreatModelError("boundaries: missing entry")
    seen.clear()
    for item in items:
        exact_fields(item, {"id", "from", "to", "control"}, "boundary")
        name = item["id"]
        if name not in BOUNDARIES or name in seen or (
                item["from"], item["to"]) != BOUNDARIES.get(name):
            raise ThreatModelError("boundary: duplicate or trust-edge drift")
        seen.add(name)
        nonempty(item["control"], "boundary.control")
    if seen != set(BOUNDARIES):
        raise ThreatModelError("boundaries: incomplete")
    rows = data["abuse_cases"]
    if not isinstance(rows, list) or len(rows) != len(CASES):
        raise ThreatModelError("abuse_cases: incomplete test matrix")
    seen.clear()
    for row in rows:
        exact_fields(row, {"id", "boundary", "scenario", "negative_expectation",
                           "test_reference", "status"}, "abuse_case")
        case = row["id"]
        if case not in CASES or case in seen or row["boundary"] != CASE_BOUNDARIES.get(case):
            raise ThreatModelError("abuse_case: missing, duplicate or misbound")
        seen.add(case)
        for field in ("scenario", "negative_expectation"):
            nonempty(row[field], "abuse_case." + field)
        if row["status"] != "NOT_ACCEPTED":
            raise ThreatModelError("abuse_case: unsupported acceptance claim")
        reference = row["test_reference"]
        if not isinstance(reference, str) or not re.fullmatch(
                r"tests/[a-z0-9_]+\.py", reference):
            raise ThreatModelError("abuse_case: invalid local test reference")
        if not (pathlib.Path(root) / reference).is_file():
            raise ThreatModelError("abuse_case: missing candidate test file")
    if seen != CASES:
        raise ThreatModelError("abuse_case: incomplete ID coverage")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=pathlib.Path, default=DEFAULT)
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.file.read_text(encoding="utf-8"))
        validate(data)
    except (OSError, UnicodeError, json.JSONDecodeError, ThreatModelError) as exc:
        print("BLOCKED: P01 T07 model invalid (%s)" % type(exc).__name__, file=sys.stderr)
        return 1
    print("PASS: P01 T07 offline trust matrix (12 cases, 9 boundaries, 12 zones)")
    print("LIMIT: NO-GO; candidate tests are not live proof or release approval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

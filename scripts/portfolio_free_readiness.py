#!/usr/bin/env python3
"""Fail-closed free-capability planning report for separately governed projects."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

from check_free_resource_plan import ROOT, EXPECTED, load_plan, validate_plan, _reject_duplicate_keys

MANIFEST = ROOT / "docs/portfolio/PORTFOLIO_FREE_CANDIDATES.json"
HISTORICAL_SNAPSHOT = Path("docs/portfolio/PORTFOLIO_V1_READINESS.md")
CANDIDATES = {
  "devobs-saas": (
    "ci",
    "cloudevents",
    "otlp-bridge"
  ),
  "phone-repair-assistant-v2": (
    "ci",
    "cloudevents"
  ),
  "al-dala-mobile": (
    "ci",
    "cloudevents"
  ),
  "LiveOps-Integration": (
    "ci",
    "cloudevents"
  ),
  "DevObs-ai-Intelligence-": (
    "ci",
    "cloudevents"
  ),
  "CineForge-AI": (
    "cineforge-triage"
  )
}
DENIED = ("external_network_allowed", "cross_repository_transfer_allowed",
          "paid_activation_allowed", "automatic_merge_allowed", "provider_auth_change_allowed")


def load_candidates(path: Path = MANIFEST) -> Any:
    if not path.is_file() or path.stat().st_size > 16384 or path.is_symlink():
        raise ValueError("missing or oversized candidate manifest")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)


def validate_candidates(data: Any, resource_plan: Any | None = None,
                        root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict) or set(data) != {
        "schema_version", "review_date", "source_repository", "classification", "policy", "projects"
    }:
        return ["invalid manifest fields"]
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        errors.append("invalid schema_version")
    try:
        dt.date.fromisoformat(data["review_date"])
    except (TypeError, ValueError):
        errors.append("invalid review_date")
    if data["source_repository"] != "hamedonassar95/Devobs":
        errors.append("invalid source repository")
    if data["classification"] != "PUBLIC_METADATA_ONLY":
        errors.append("invalid data classification")
    policy = data["policy"]
    if not isinstance(policy, dict) or set(policy) != {*DENIED, "owner_approval_required"}:
        errors.append("invalid policy fields")
    else:
        if policy["owner_approval_required"] is not True:
            errors.append("owner approval is mandatory")
        for field in DENIED:
            if policy[field] is not False:
                errors.append(field + " must remain false")
    try:
        source = load_plan() if resource_plan is None else resource_plan
        upstream_errors = validate_plan(source, root=root)
    except (OSError, UnicodeError, ValueError, TypeError):
        upstream_errors = ["unreadable free-resource plan"]
    if upstream_errors:
        errors.append("free-resource preflight did not pass")
    safe_resources = {
        item["id"] for item in source.get("resources", [])
        if isinstance(source, dict) and isinstance(item, dict) and isinstance(item.get("id"), str)
    } if isinstance(source, dict) else set()
    snapshot = root / HISTORICAL_SNAPSHOT
    if snapshot.is_symlink() or not snapshot.is_file() or not snapshot.resolve().is_relative_to(root.resolve()):
        errors.append("historical portfolio evidence file missing")
    rows = data["projects"]
    if not isinstance(rows, list) or len(rows) != len(CANDIDATES):
        return errors + ["unexpected project count"]
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "id", "candidate_capabilities", "connection_state",
            "runtime_verified", "private_data_processed"
        }:
            errors.append("invalid project fields")
            continue
        name = row["id"]
        if not isinstance(name, str) or name not in CANDIDATES or name in seen:
            errors.append("unknown or duplicate project")
            continue
        seen.add(name)
        caps = row["candidate_capabilities"]
        if not isinstance(caps, list) or any(not isinstance(x, str) for x in caps):
            errors.append("invalid capability list for " + name)
        elif sorted(caps) != sorted(CANDIDATES[name]) or any(x not in EXPECTED or x not in safe_resources for x in caps):
            errors.append("unreviewed capability for " + name)
        if row["connection_state"] != "NOT_CONNECTED" or row["runtime_verified"] is not False:
            errors.append("unsupported active integration claim for " + name)
        if row["private_data_processed"] is not False:
            errors.append("private data is forbidden for " + name)
    if seen != set(CANDIDATES):
        errors.append("missing allowlisted projects")
    return errors


def main(args: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if args is None else args)
    if args not in ([], ["--json"]):
        print("FAIL: only --json is supported", file=sys.stderr)
        return 2
    try:
        data = load_candidates()
        errors = validate_candidates(data)
    except (OSError, UnicodeError, ValueError, TypeError):
        print("FAIL: invalid portfolio candidate manifest", file=sys.stderr)
        return 1
    if errors:
        for err in errors:
            print("FAIL: " + err, file=sys.stderr)
        return 1
    result = {
        "status": "MANIFEST_VALID_ONLY",
        "project_candidates": len(CANDIDATES),
        "local_resource_files_checked": len(EXPECTED),
        "external_repository_access_verified": False,
        "live_integration_verified": False,
        "production_ready": False,
        "paid_operations_authorized": False,
        "projects": [{
            "id": row["id"],
            "candidate_capabilities": row["candidate_capabilities"],
            "state": "NOT_CONNECTED",
        } for row in data["projects"]],
    }
    if args == ["--json"]:
        print(json.dumps(result, sort_keys=True))
    else:
        print("PASS: 6 candidate projects; 12 existing Devobs resource files; "
              "NO external connections or runtime readiness verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

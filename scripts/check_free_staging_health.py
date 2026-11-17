#!/usr/bin/env python3
"""Offline, fail-closed readiness report for Devobs free staging only.

Consumes a small allowlisted, redacted provider snapshot. Never accesses an
external account, grants deployment permission, or declares production GO.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = ROOT / "docs" / "p01" / "free-staging-inventory.json"
FIELDS = {"schema_version", "scope", "observed_on", "render", "supabase"}
RENDER_FIELDS = {
    "web_plan", "web_suspended", "web_auto_deploy", "web_runtime_verified",
    "web_ingress_reviewed", "web_last_deploy_status", "web_last_deploy_commit",
    "database_plan", "database_status", "database_expires_at", "database_backup_verified",
}
SUPABASE_FIELDS = {"project_status", "hosted_isolation_verified"}
# Exact Render REST deploy statuses, including in-progress and failed states.
# See https://api-docs.render.com/reference/retrieve-deploy
RENDER_DEPLOY_STATUSES = {
    "created", "queued", "build_in_progress", "update_in_progress",
    "live", "deactivated", "build_failed", "update_failed", "canceled",
    "pre_deploy_in_progress", "pre_deploy_failed",
}


class InvalidSnapshot(ValueError):
    """The evidence document is malformed or out of its approved scope."""


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidSnapshot("duplicate evidence fields")
        result[key] = value
    return result


def load_snapshot(path: Path) -> dict:
    """Read only an existing small regular file, never a symlink."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
        raise InvalidSnapshot("missing or unsafe snapshot")
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs)
    except (UnicodeError, ValueError, RecursionError):
        raise InvalidSnapshot("invalid JSON evidence") from None


def assess_snapshot(record: dict, now: datetime) -> dict:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise InvalidSnapshot("timezone-aware UTC time required")
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise InvalidSnapshot("unsupported evidence fields")
    if type(record["schema_version"]) is not int or record["schema_version"] != 2:
        raise InvalidSnapshot("unsupported schema")
    if record["scope"] != "devobs-free-staging":
        raise InvalidSnapshot("wrong project scope")
    observed = record["observed_on"]
    if type(observed) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", observed):
        raise InvalidSnapshot("invalid observation date")
    try:
        observed_date = date.fromisoformat(observed)
    except ValueError:
        raise InvalidSnapshot("invalid observation date") from None
    current = now.astimezone(timezone.utc)
    if observed_date > current.date():
        raise InvalidSnapshot("future observation is not evidence")
    render = record["render"]
    supabase = record["supabase"]
    if not isinstance(render, dict) or set(render) != RENDER_FIELDS:
        raise InvalidSnapshot("invalid Render evidence")
    if not isinstance(supabase, dict) or set(supabase) != SUPABASE_FIELDS:
        raise InvalidSnapshot("invalid Supabase evidence")
    if (render["web_plan"] != "free" or render["database_plan"] != "free"
            or type(render["web_suspended"]) is not bool
            or type(render["web_auto_deploy"]) is not bool
            or type(render["web_runtime_verified"]) is not bool
            or type(render["web_ingress_reviewed"]) is not bool
            or type(render["web_last_deploy_status"]) is not str
            or render["web_last_deploy_status"] not in RENDER_DEPLOY_STATUSES
            or type(render["web_last_deploy_commit"]) is not str
            or re.fullmatch(r"[0-9a-f]{40}", render["web_last_deploy_commit"]) is None
            or type(render["database_backup_verified"]) is not bool
            or type(supabase["hosted_isolation_verified"]) is not bool
            or type(render["database_status"]) is not str
            or render["database_status"] not in {"available", "unavailable", "suspended"}
            or type(supabase["project_status"]) is not str
            or supabase["project_status"] not in {"INACTIVE", "ACTIVE_HEALTHY", "UNKNOWN"}):
        raise InvalidSnapshot("invalid free-tier provider states")
    expiry_raw = render["database_expires_at"]
    if type(expiry_raw) is not str or not expiry_raw.endswith("Z"):
        raise InvalidSnapshot("invalid Render expiry")
    try:
        expiry = datetime.fromisoformat(expiry_raw.replace("Z", "+00:00"))
    except ValueError:
        raise InvalidSnapshot("invalid Render expiry") from None
    if expiry.utcoffset() != timedelta(0):
        raise InvalidSnapshot("expiry must be UTC")

    blockers = []
    if (current.date() - observed_date).days > 7:
        blockers.append("STALE_PROVIDER_EVIDENCE")
    if render["web_last_deploy_status"] != "live":
        blockers.append("RENDER_LATEST_DEPLOY_NOT_LIVE")
    if render["web_suspended"]:
        blockers.append("RENDER_WEB_SUSPENDED")
    if render["web_auto_deploy"]:
        blockers.append("UNREVIEWED_AUTO_DEPLOY")
    if not render["web_runtime_verified"]:
        blockers.append("RENDER_RUNTIME_UNVERIFIED")
    if not render["web_ingress_reviewed"]:
        blockers.append("RENDER_PUBLIC_INGRESS_UNREVIEWED")
    if render["database_status"] != "available":
        blockers.append("RENDER_DATABASE_UNAVAILABLE")
    if current >= expiry:
        blockers.append("RENDER_DATABASE_EXPIRED")
    elif expiry - current <= timedelta(days=30):
        blockers.append("RENDER_DATABASE_EXPIRY_REVIEW")
    if not render["database_backup_verified"]:
        blockers.append("RENDER_BACKUP_UNVERIFIED")
    if supabase["project_status"] != "ACTIVE_HEALTHY":
        blockers.append("DEVOBS_SUPABASE_NOT_ACTIVE")
    if not supabase["hosted_isolation_verified"]:
        blockers.append("HOSTED_TENANT_ISOLATION_UNVERIFIED")

    return {
        "status": "REVIEW_REQUIRED",
        "scope": "devobs-free-staging",
        "observed_on": observed,
        "render_database_expires_at": expiry_raw,
        "render_latest_deploy_status": render["web_last_deploy_status"],
        "blockers": blockers,
        "production_ready": False,
        "live_provider_request_performed": False,
        "paid_activation_authorized": False,
        "automatic_merge_authorized": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = assess_snapshot(load_snapshot(args.file), datetime.now(timezone.utc))
    except (OSError, InvalidSnapshot):
        print("INVALID_SNAPSHOT / NO-GO: refresh reviewed provider evidence", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"REVIEW_REQUIRED: {len(result['blockers'])} known blockers; not production evidence")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

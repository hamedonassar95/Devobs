#!/usr/bin/env python3
"""Offline decision-only preflight for a recorded Render Free PostgreSQL expiry.

A sanitized snapshot is not live provider data or authorization to act.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = ROOT / "docs" / "p01" / "render-free-expiry-snapshot.json"
FIELDS = {"plan", "status", "observed_on", "expires_at"}
EXPIRY_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


class InvalidSnapshot(ValueError):
    """Untrusted inventory was malformed or contained unsupported fields."""


def _utc_expiry(value: str) -> datetime:
    if type(value) is not str or not EXPIRY_RE.fullmatch(value):
        raise InvalidSnapshot("invalid UTC expiry")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidSnapshot("invalid UTC expiry") from exc


def assess_expiry(record: dict, now: datetime) -> dict:
    """Check only snapshot validity, freshness and deadline; never return GO."""
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise InvalidSnapshot("unexpected snapshot fields")
    if record["plan"] != "free" or type(record["plan"]) is not str:
        raise InvalidSnapshot("expected Free-only snapshot")
    if type(record["status"]) is not str or record["status"] not in ("available", "unavailable", "suspended"):
        raise InvalidSnapshot("unknown provider status")
    observed = record["observed_on"]
    if type(observed) is not str or not DATE_RE.fullmatch(observed):
        raise InvalidSnapshot("invalid snapshot date")
    try:
        recorded_date = date.fromisoformat(observed)
    except ValueError as exc:
        raise InvalidSnapshot("invalid snapshot date") from exc
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise InvalidSnapshot("current time must be timezone-aware")
    today = now.astimezone(timezone.utc)
    if recorded_date > today.date():
        raise InvalidSnapshot("snapshot date in future")
    expiry = _utc_expiry(record["expires_at"])
    if today >= expiry:
        status = "EXPIRED"
    elif (today.date() - recorded_date).days > 7:
        status = "STALE_INVENTORY"
    elif record["status"] != "available":
        status = "UNAVAILABLE"
    elif expiry - today <= timedelta(days=30):
        status = "REVIEW_REQUIRED"
    else:
        status = "NOT_IMMINENT"
    return {
        "status": status,
        "exit_code": 0 if status == "NOT_IMMINENT" else 1,
        "observed_on": observed,
        "expires_at": record["expires_at"],
        "production_approved": False,
        "paid_activation_authorized": False,
        "provider_access_performed": False,
    }


def _unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise InvalidSnapshot("duplicate keys")
        out[key] = value
    return out


def load_snapshot(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4096:
        raise InvalidSnapshot("missing or unsafe snapshot")
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs)
    except (ValueError, UnicodeError) as exc:
        raise InvalidSnapshot("invalid snapshot") from exc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = assess_expiry(load_snapshot(args.file), datetime.now(timezone.utc))
    except (OSError, InvalidSnapshot):
        print("INVALID_SNAPSHOT / NO-GO: review the sanitized, dated source", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(result["status"] + ": source is an offline snapshot, not live provider evidence; "
              "human retention decision required before expiry; NO production GO")
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())

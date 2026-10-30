#!/usr/bin/env python3
"""Offline, fail-closed P01 evidence *completeness* gate; not an approval oracle.

No remote URLs are fetched and submitted attestations are NOT independently trusted.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

REQUIRED = (
    "owner_approval",
    "provider_region",
    "budget_enforcement",
    "identity_oidc",
    "tenant_isolation",
    "operational_recovery",
    "independent_release_approval",
)
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
MAX_AGE = timedelta(days=30)
FIELDS = {"state", "source_sha", "reviewer", "observed_at", "evidence_url"}


class InvalidEvidence(ValueError):
    pass


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidEvidence("duplicate JSON key")
        result[key] = value
    return result


def _utc_date(value, now):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise InvalidEvidence("observed_at must be a UTC ISO-8601 timestamp")
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidEvidence("invalid observed_at") from exc
    if observed.tzinfo != timezone.utc or not now - MAX_AGE <= observed <= now + timedelta(minutes=5):
        raise InvalidEvidence("expired or future evidence timestamp")


def _safe_reference(value):
    if not isinstance(value, str) or len(value) > 1024 or any(ord(c) < 33 for c in value):
        raise InvalidEvidence("invalid evidence reference")
    parsed = urlsplit(value)
    try:
        bad = (parsed.scheme != "https" or not parsed.hostname or parsed.username or
               parsed.password or parsed.query or parsed.fragment or parsed.port not in (None, 443))
    except ValueError as exc:
        raise InvalidEvidence("invalid evidence reference port") from exc
    if bad:
        raise InvalidEvidence("evidence references must be clean HTTPS URLs")
    if not parsed.path or parsed.path == "/":
        raise InvalidEvidence("evidence reference needs a resource path")


def assess(document, expected_sha, now=None):
    """Return (eligible_for_human_review, messages), never production GO."""
    now = now or datetime.now(timezone.utc)
    if not SHA_RE.fullmatch(expected_sha):
        raise InvalidEvidence("invalid expected SHA")
    if not isinstance(document, dict) or set(document) != {"schema_version", "gate", "decision", "source_sha", "controls"}:
        raise InvalidEvidence("unexpected or missing document keys")
    if document["schema_version"] != 1 or document["gate"] != "P01" or document["decision"] != "NO-GO":
        raise InvalidEvidence("invalid schema, gate, or decision; automatic GO is forbidden")
    if not isinstance(document["source_sha"], str) or not SHA_RE.fullmatch(document["source_sha"]):
        raise InvalidEvidence("invalid source SHA")
    if not isinstance(document["controls"], dict) or set(document["controls"]) != set(REQUIRED):
        raise InvalidEvidence("missing or unknown required controls")
    blockers = []
    if document["source_sha"] != expected_sha:
        blockers.append("source SHA does not match the checked revision")
    for name in REQUIRED:
        entry = document["controls"][name]
        if not isinstance(entry, dict) or set(entry) != FIELDS:
            raise InvalidEvidence(f"{name}: missing or unexpected fields")
        if entry["state"] not in ("VERIFIED", "UNVERIFIED", "FAILED"):
            raise InvalidEvidence(f"{name}: invalid state")
        if entry["state"] != "VERIFIED":
            blockers.append(f"{name}: {entry['state']}")
            continue
        if entry["source_sha"] != expected_sha:
            blockers.append(f"{name}: source revision mismatch")
        if not isinstance(entry["reviewer"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", entry["reviewer"]):
            raise InvalidEvidence(f"{name}: missing reviewer identity")
        _utc_date(entry["observed_at"], now)
        _safe_reference(entry["evidence_url"])
    return not blockers, blockers


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="docs/p01/evidence.json")
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args(argv)
    try:
        with Path(args.file).open("r", encoding="utf-8") as stream:
            data = json.load(stream, object_pairs_hook=_unique_pairs)
        eligible, blockers = assess(data, args.expected_sha)
    except (OSError, UnicodeError, json.JSONDecodeError, InvalidEvidence) as exc:
        print(f"P01 INVALID / NO-GO: {exc}")
        return 2
    if not eligible:
        print("P01 NO-GO / BLOCKED: " + "; ".join(blockers))
        return 1
    print("P01 READY_FOR_HUMAN_REVIEW: claims are structurally complete, NOT independently verified; NO production GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

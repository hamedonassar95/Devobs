#!/usr/bin/env python3
"""Check the canonical Devobs prototype's offline deny-all Firestore policy.

This is deliberately NOT a Firestore rules evaluator or a hosted-rule audit.
Only the reviewed deny-all template may pass; any new policy is unverified.
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = ROOT / "apps/ai-intelligence-console/firestore.rules"

# A narrow, fail-closed structural acceptance rule for this prototype only.
DENY_ALL_BASELINE = (
    "rules_version='2';"
    "servicecloud.firestore{"
    "match/databases/{database}/documents{"
    "match/{document=**}{allowread,write:iffalse;}"
    "}}"
)


def assess_rules(source: str) -> tuple[str, str]:
    """Return (status, reason), never treating unknown grammar as proof of safety."""
    if not source.strip():
        return "BLOCKED", "EMPTY_RULESET"
    # The known baseline contains no string literals with comment markers.
    without_comments = re.sub(r"//[^\n]*", "", source)
    normalized = re.sub(r"\s+", "", without_comments)
    if normalized == DENY_ALL_BASELINE:
        return "PASS", "CANONICAL_DENY_ALL_BASELINE"
    if re.search(r"\|\|\s*true\b|\bif\s+true\s*;", without_comments):
        return "FAIL", "UNCONDITIONAL_ALLOW_CONDITION"
    return "BLOCKED", "RULES_REQUIRE_INDEPENDENT_REVIEW"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rules-file", type=Path, default=DEFAULT_RULES)
    args = parser.parse_args()

    try:
        source = args.rules_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        status, reason = "BLOCKED", "RULES_FILE_UNAVAILABLE"
    else:
        status, reason = assess_rules(source)

    print(json.dumps({"status": status, "reason": reason, "scope": "LOCAL_SOURCE_ONLY"}, sort_keys=True))
    if status == "PASS":
        return 0
    if status == "FAIL":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

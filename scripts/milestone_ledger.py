"""Validate and summarize Devobs's durable, offline GitHub milestone ledger.

This checker validates the integrity of records, NOT GitHub's live truth or any
production readiness claim. It never uses secrets, credentials or the network.
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / "docs" / "MILESTONE_LEDGER.json"
SHA = re.compile(r"^[0-9a-f]{40}$")
IDENT = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
AREAS = {"CI_SECURITY", "AI_GOVERNANCE", "AGENT_OPERATIONS"}
GATE_STATUSES = {"BLOCKED", "OPEN"}
REPO = "hamedonassar95/Devobs"


class InvalidLedger(ValueError):
    pass


def required_string(value, name, limit=512):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise InvalidLedger(f"{name}: expected nonempty string <= {limit} chars")
    if "\\x00" in value:
        raise InvalidLedger(f"{name}: NUL is not permitted")
    return value


def positive_integer(value, name):
    if type(value) is not int or value < 1:
        raise InvalidLedger(f"{name}: expected positive integer")
    return value


def validate(payload):
    if not isinstance(payload, dict):
        raise InvalidLedger("root: expected object")
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        raise InvalidLedger("schema_version: expected 1")
    if payload.get("repository") != REPO:
        raise InvalidLedger("repository: unexpected repository")
    required_string(payload.get("disclaimer"), "disclaimer", 1000)
    milestones, gates = payload.get("milestones"), payload.get("gates")
    if not isinstance(milestones, list) or not milestones:
        raise InvalidLedger("milestones: nonempty array required")
    if not isinstance(gates, list) or not gates:
        raise InvalidLedger("gates: nonempty array required")
    seen_ids, seen_prs, seen_merges = set(), set(), set()
    last_pr = 0
    for i, entry in enumerate(milestones):
        label = f"milestones[{i}]"
        if not isinstance(entry, dict):
            raise InvalidLedger(f"{label}: expected object")
        ident = required_string(entry.get("id"), f"{label}.id", 64)
        if not IDENT.fullmatch(ident) or ident in seen_ids:
            raise InvalidLedger(f"{label}.id: invalid or duplicate")
        seen_ids.add(ident)
        if entry.get("area") not in AREAS:
            raise InvalidLedger(f"{label}.area: unsupported")
        required_string(entry.get("title"), f"{label}.title")
        required_string(entry.get("verification"), f"{label}.verification", 1000)
        required_string(entry.get("limitations"), f"{label}.limitations", 1000)
        pr = positive_integer(entry.get("pr_number"), f"{label}.pr_number")
        if pr <= last_pr or pr in seen_prs:
            raise InvalidLedger(f"{label}.pr_number: not increasing or duplicate")
        seen_prs.add(pr)
        last_pr = pr
        for key in ("pr_head_sha", "merge_sha"):
            if not SHA.fullmatch(required_string(entry.get(key), f"{label}.{key}", 40)):
                raise InvalidLedger(f"{label}.{key}: invalid full SHA")
        if entry["merge_sha"] == entry["pr_head_sha"] or entry["merge_sha"] in seen_merges:
            raise InvalidLedger(f"{label}.merge_sha: duplicate or equals PR head")
        seen_merges.add(entry["merge_sha"])
        positive_integer(entry.get("ci_run_id"), f"{label}.ci_run_id")
    for i, entry in enumerate(gates):
        label = f"gates[{i}]"
        if not isinstance(entry, dict):
            raise InvalidLedger(f"{label}: expected object")
        ident = required_string(entry.get("id"), f"{label}.id", 64)
        if not IDENT.fullmatch(ident) or ident in seen_ids:
            raise InvalidLedger(f"{label}.id: invalid or duplicate")
        seen_ids.add(ident)
        if entry.get("status") not in GATE_STATUSES:
            raise InvalidLedger(f"{label}.status: unsupported; completed gates require a merged milestone")
        source = required_string(entry.get("source"), f"{label}.source")
        if not source.startswith("docs/") or ".." in pathlib.PurePosixPath(source).parts or not source.endswith(".md"):
            raise InvalidLedger(f"{label}.source: expected a repository docs path")
        if not (ROOT / source).is_file():
            raise InvalidLedger(f"{label}.source: file does not exist")
        required_string(entry.get("reason"), f"{label}.reason", 1000)
        required_string(entry.get("next_action"), f"{label}.next_action", 1000)
    return {"repository": REPO, "merged_milestones": len(milestones),
            "open_gates": len(gates), "latest_pr": last_pr,
            "gate_statuses": {e["id"]: e["status"] for e in gates}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=pathlib.Path, default=DEFAULT_LEDGER)
    parser.add_argument("--summary", action="store_true", help="emit machine-readable status")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.file.read_text(encoding="utf-8"))
        summary = validate(data)
    except (OSError, UnicodeError, json.JSONDecodeError, InvalidLedger) as exc:
        print(f"MILESTONE_LEDGER_INVALID: {exc}", file=sys.stderr)
        return 1
    if args.summary:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        print(f"MILESTONE_LEDGER_VALID: {summary['merged_milestones']} recorded merged PRs; {summary['open_gates']} open gates")
        print("Evidence links are offline references; live state is NOT checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

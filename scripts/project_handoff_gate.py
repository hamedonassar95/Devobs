"""Offline advisory preflight for Devobs ecosystem project handoffs.

Never executes a transfer, checks external approval, or proves sanitization.
Default denial is intentional; REVIEW_ONLY is not authorization.
"""
import argparse
import json
import pathlib
import sys

ALLOWED = {
    ("devobs", "devobs-saas", "ci_report"),
    ("devobs", "phone-repair-assistant-v2", "ci_report"),
    ("devobs", "al-dala-mobile", "ci_report"),
    ("phone-repair-assistant-v2", "al-dala-mobile", "knowledge_package"),
}
FIELDS = {
    "source", "destination", "artifact_type", "intent", "classification",
    "contains_customer_data", "contains_secrets", "technical_reviewed",
    "destination_owner_reviewed",
}


def evaluate(request):
    """Return a fail-closed advisory decision; never an execution grant."""
    if not isinstance(request, dict) or set(request) != FIELDS:
        return {"decision": "DENY", "reason": "invalid request fields"}
    bool_fields = ("contains_customer_data", "contains_secrets",
                   "technical_reviewed", "destination_owner_reviewed")
    if any(type(request[k]) is not bool for k in bool_fields):
        return {"decision": "DENY", "reason": "review and data flags must be booleans"}
    str_fields = FIELDS - set(bool_fields)
    if any(not isinstance(request[k], str) or not request[k] or len(request[k]) > 80
           for k in str_fields):
        return {"decision": "DENY", "reason": "invalid text fields"}
    route = (request["source"], request["destination"], request["artifact_type"])
    if route not in ALLOWED:
        return {"decision": "DENY", "reason": "unsupported project handoff"}
    if request["intent"] != "review":
        return {"decision": "DENY", "reason": "no automated publish, merge, or deployment"}
    if request["classification"] != "public_redacted":
        return {"decision": "DENY", "reason": "only declared redacted public metadata"}
    if request["contains_customer_data"] or request["contains_secrets"]:
        return {"decision": "DENY", "reason": "private data or secrets are prohibited"}
    if route[2] == "knowledge_package" and not request["technical_reviewed"]:
        return {"decision": "DENY", "reason": "technical review missing"}
    if not request["destination_owner_reviewed"]:
        return {"decision": "DENY", "reason": "destination owner review missing"}
    return {
        "decision": "REVIEW_ONLY",
        "reason": "self-declared flags require independent human verification; no transfer authorized",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=pathlib.Path,
                        help="Path to a local JSON request (not credentials or customer data)")
    args = parser.parse_args(argv)
    try:
        if args.request.stat().st_size > 4096:
            raise ValueError("request exceeds 4 KiB")
        request = json.loads(args.request.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"decision": "DENY", "reason": f"invalid file: {type(exc).__name__}"}))
        return 2
    result = evaluate(request)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["decision"] == "REVIEW_ONLY" else 1


if __name__ == "__main__":
    sys.exit(main())

"""Offline, read-only task-status report for the Devobs two-worker manifest.

This tool reuses ``scripts/check_two_agent_tasks.py`` contract definitions and
validator, then adds an independent advisory status view. It reads one local
JSON file and prints a sanitized human report plus a machine-readable JSON
summary. It never executes manifest commands, fetches GitHub data, starts an
agent, changes Git state or grants an approval.

``PASS`` in a manifest is only an unverified local claim. This report never
promotes that claim to VERIFIED, runtime acceptance or release approval.
"""
import argparse
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from check_two_agent_tasks import (
        MAX_MANIFEST_BYTES,
        SHA_RE,
        VERIFICATION_RESULTS,
        evaluate,
    )
except ImportError as exc:  # fail closed if the shared contract is unavailable
    IMPORT_ERROR = f"shared validator import failed: {type(exc).__name__}"
else:
    IMPORT_ERROR = None

ADVISORY_LABEL = (
    "ADVISORY LOCAL DATA - offline manifest only; not verification, "
    "runtime acceptance or approval"
)
REPORT_TYPE = "advisory_local_task_status"
VERIFICATION_POLICY = (
    "Manifest PASS is an unverified local claim; fresh commands, exact SHA, "
    "reviewed CI evidence and human approval remain required."
)
UNVERIFIED_CLAIM_STATE = "PASS_CLAIM_UNVERIFIED"
KNOWN_DECISIONS = frozenset(("PASS", "BLOCKED", "FAIL"))
REVIEWED_STATUSES = frozenset(("evidence_ready", "complete"))
EXIT_PASS = 0
EXIT_BLOCKED = 1
EXIT_FAIL = 2

_ANSI_OSC_RE = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_ANSI_CSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_ANSI_ESCAPE_RE = re.compile(r"\x1b[@-Z\\-_]")
_WHITESPACE_RE = re.compile(r"\s+")


def sanitize_display(value, limit=200):
    """Return a bounded single-line string safe for terminal display."""
    if value is None:
        text = "null"
    elif isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, (int, float)):
        text = str(value)
    elif isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)

    text = _ANSI_OSC_RE.sub("[osc removed]", text)
    text = _ANSI_CSI_RE.sub("[ansi removed]", text)
    text = _ANSI_ESCAPE_RE.sub("[escape removed]", text)
    text = "".join(
        " " if unicodedata.category(character) in ("Cc", "Cf") else character
        for character in text
    )
    text = _WHITESPACE_RE.sub(" ", text).strip()
    if len(text) > limit:
        text = text[: limit - 3] + "..."
    return text or "<empty>"


def _json_safe(value):
    """Sanitize every string before JSON encoding; keep output ASCII-only."""
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, str):
        return sanitize_display(value, limit=1000)
    return value


def _failure_report(source_label, errors):
    empty_count = 0
    return {
        "report_type": REPORT_TYPE,
        "advisory": True,
        "source_label": sanitize_display(source_label),
        "validator_decision": "FAIL",
        "effective_decision": "FAIL",
        "verification_policy": VERIFICATION_POLICY,
        "tasks": [],
        "blocked_tasks": [],
        "conflicts": [],
        "errors": [sanitize_display(error, limit=500) for error in errors],
        "summary": {"tasks": empty_count, "blocked_tasks": empty_count,
                    "pass_claims": empty_count},
    }


def _as_list(value):
    return value if isinstance(value, list) else []


def _unresolved_dependencies(task, by_id):
    """Compute unresolved transitive dependencies independently of validator."""
    seen = set()
    unresolved = set()
    pending = list(_as_list(task.get("dependencies")))
    while pending:
        dependency = pending.pop()
        if not isinstance(dependency, str) or not dependency:
            unresolved.add(str(dependency))
            continue
        if dependency in seen:
            continue
        seen.add(dependency)
        other = by_id.get(dependency)
        if other is None or other.get("status") != "complete":
            unresolved.add(dependency)
            if other is not None:
                pending.extend(_as_list(other.get("dependencies")))
    return sorted(unresolved)


def _evidence_state(task):
    """Classify a manifest PASS claim without accepting it as verification."""
    verification = task.get("verification")
    if not isinstance(verification, dict):
        return "INVALID", "verification field is not an object"
    result = verification.get("result")
    if result not in VERIFICATION_RESULTS:
        return "INVALID", "unrecognized verification result"
    if result == "FAIL":
        return "FAIL_CLAIM", "manifest records FAIL; no verification claim accepted"
    if result == "PENDING":
        return "PENDING", "manifest records PENDING; no verification claim accepted"

    if task.get("status") not in REVIEWED_STATUSES:
        return "PASS_CLAIM_INVALID_STATUS", "PASS claim is not valid for this status"
    source_sha = task.get("source_sha")
    if not isinstance(source_sha, str) or not SHA_RE.fullmatch(source_sha):
        return "PASS_CLAIM_MISSING_SHA", "PASS claim lacks an exact 40-character SHA"
    commands = _as_list(verification.get("commands"))
    evidence = verification.get("evidence")
    if not commands or any(not isinstance(item, str) or not item.strip() for item in commands):
        return "PASS_CLAIM_INCOMPLETE", "PASS claim lacks a recorded command"
    if not isinstance(evidence, str) or not evidence.strip():
        return "PASS_CLAIM_INCOMPLETE", "PASS claim lacks recorded evidence"
    return UNVERIFIED_CLAIM_STATE, "PASS is an unverified local claim; human review required"


def _validator_task_reasons(validation, raw_task_id):
    reasons = []
    for item in _as_list(validation.get("blocked_tasks")):
        if isinstance(item, dict) and item.get("task") == raw_task_id:
            reason = sanitize_display(item.get("reason"), limit=80)
            reasons.append(f"validator_blocked:{reason}")
    for item in _as_list(validation.get("conflicts")):
        if isinstance(item, dict) and raw_task_id in _as_list(item.get("tasks")):
            reason = sanitize_display(item.get("reason"), limit=80)
            reasons.append(f"validator_conflict:{reason}")
    return reasons


def _task_row(task, by_id, validation):
    raw_id = task.get("id")
    task_id = sanitize_display(raw_id)
    state, note = _evidence_state(task)
    verification = task.get("verification") if isinstance(task.get("verification"), dict) else {}
    dependencies = [sanitize_display(item) for item in _as_list(task.get("dependencies"))]
    unresolved = _unresolved_dependencies(task, by_id)

    reasons = []
    if task.get("status") == "blocked":
        reasons.append("manifest_status_blocked")
    if unresolved:
        reasons.append("unresolved_dependencies")
    if state in ("FAIL_CLAIM", "PASS_CLAIM_INVALID_STATUS",
                 "PASS_CLAIM_MISSING_SHA", "PASS_CLAIM_INCOMPLETE", "INVALID"):
        reasons.append("evidence_state_" + state.lower())
    if task.get("status") in REVIEWED_STATUSES and state in ("PENDING", "FAIL_CLAIM"):
        reasons.append("reviewed_status_without_pass_claim")
    reasons.extend(_validator_task_reasons(validation, raw_id))

    evidence_excerpt = sanitize_display(verification.get("evidence"), limit=160)
    return {
        "task_id": task_id,
        "assigned_worker": sanitize_display(task.get("assigned_agent")),
        "repository": sanitize_display(task.get("repository")),
        "branch": sanitize_display(task.get("branch")),
        "status": sanitize_display(task.get("status")),
        "dependencies": dependencies,
        "blocked": bool(reasons),
        "blocked_reasons": reasons,
        "unresolved_dependencies": [sanitize_display(item) for item in unresolved],
        "pr_reference": sanitize_display(task.get("pr_reference")),
        "evidence_state": state,
        "evidence_note": sanitize_display(note, limit=300),
        "evidence_excerpt": evidence_excerpt,
        "source_sha": sanitize_display(task.get("source_sha")),
    }


def build_report(manifest, source_label="local JSON manifest"):
    """Return a fail-closed advisory report derived only from local data."""
    if IMPORT_ERROR:
        return _failure_report(source_label, [IMPORT_ERROR])
    try:
        validation = evaluate(manifest)
    except Exception as exc:
        return _failure_report(source_label, [f"validator failure: {type(exc).__name__}"])
    if not isinstance(validation, dict):
        return _failure_report(source_label, ["validator returned an unexpected shape"])

    validator_decision = validation.get("decision")
    if validator_decision not in KNOWN_DECISIONS:
        validator_decision = "FAIL"
    errors = [sanitize_display(item, limit=500)
              for item in _as_list(validation.get("errors"))]
    conflicts = [sanitize_display(item, limit=500)
                 for item in _as_list(validation.get("conflicts"))]

    rows = []
    if validator_decision != "FAIL" and isinstance(manifest, dict):
        tasks = _as_list(manifest.get("tasks"))
        by_id = {
            item.get("id"): item
            for item in tasks
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        rows = [_task_row(item, by_id, validation) for item in tasks if isinstance(item, dict)]

    blocked = [
        {
            "task_id": row["task_id"],
            "status": row["status"],
            "reasons": row["blocked_reasons"],
            "unresolved_dependencies": row["unresolved_dependencies"],
        }
        for row in rows if row["blocked"]
    ]
    if validator_decision == "FAIL":
        effective = "FAIL"
    elif blocked or conflicts or validation.get("blocked_tasks"):
        effective = "BLOCKED"
    else:
        effective = "PASS"

    return {
        "report_type": REPORT_TYPE,
        "advisory": True,
        "source_label": sanitize_display(source_label),
        "validator_decision": validator_decision,
        "effective_decision": effective,
        "verification_policy": VERIFICATION_POLICY,
        "tasks": rows,
        "blocked_tasks": blocked,
        "conflicts": conflicts,
        "errors": errors,
        "summary": {
            "tasks": len(rows),
            "blocked_tasks": len(blocked),
            "pass_claims": sum(1 for row in rows
                               if row["evidence_state"] == UNVERIFIED_CLAIM_STATE),
            "validator_decision": validator_decision,
            "effective_decision": effective,
        },
    }


def render_human(report):
    """Render the sanitized advisory console report."""
    lines = [
        ADVISORY_LABEL,
        "Source: " + sanitize_display(report.get("source_label")),
        "Validator decision: " + sanitize_display(report.get("validator_decision")),
        "Effective advisory status: " + sanitize_display(report.get("effective_decision")),
        "Policy: " + VERIFICATION_POLICY,
        "",
        "Tasks:",
    ]
    if not report.get("tasks"):
        lines.append("  none")
    for row in report.get("tasks", []):
        lines.extend([
            "  - " + sanitize_display(row.get("task_id")),
            "      Worker: " + sanitize_display(row.get("assigned_worker")),
            "      Repository: " + sanitize_display(row.get("repository")),
            "      Branch: " + sanitize_display(row.get("branch")),
            "      Status: " + sanitize_display(row.get("status")),
            "      Dependencies: " + (", ".join(row.get("dependencies", [])) or "none"),
            "      Blocked: " + ("YES" if row.get("blocked") else "no"),
            "      Blocked reasons: " + (", ".join(row.get("blocked_reasons", [])) or "none"),
            "      Unresolved dependencies: "
            + (", ".join(row.get("unresolved_dependencies", [])) or "none"),
            "      PR reference: " + sanitize_display(row.get("pr_reference")),
            "      Verification evidence state: "
            + sanitize_display(row.get("evidence_state")),
            "      Evidence note: " + sanitize_display(row.get("evidence_note"), limit=300),
            "      Evidence excerpt: "
            + sanitize_display(row.get("evidence_excerpt"), limit=160),
        ])

    lines.extend(["", "Blocked tasks:"])
    if not report.get("blocked_tasks"):
        lines.append("  none")
    for item in report.get("blocked_tasks", []):
        lines.append(
            "  - " + sanitize_display(item.get("task_id"))
            + " [" + sanitize_display(item.get("status")) + "]: "
            + ", ".join(item.get("reasons", []))
        )

    lines.extend(["", "Conflicts:"])
    if not report.get("conflicts"):
        lines.append("  none")
    for item in report.get("conflicts", []):
        lines.append("  - " + sanitize_display(item, limit=500))

    if report.get("errors"):
        lines.extend(["", "Contract errors:"])
        for item in report["errors"]:
            lines.append("  - " + sanitize_display(item, limit=500))

    lines.extend([
        "",
        "This advisory report does not verify an agent ran, that evidence is true,",
        "that CI passed, or that merge/deploy/billing/production approval exists.",
    ])
    return "\n".join(lines) + "\n"


def emit(report, json_only=False):
    """Write human output to stdout and JSON to stderr unless json_only is set."""
    payload = json.dumps(_json_safe(report), sort_keys=True,
                         ensure_ascii=True, separators=(",", ":"))
    if json_only:
        print(payload)
        return
    print(render_human(report), end="")
    print(payload, file=sys.stderr)


def exit_code(decision):
    if decision == "PASS":
        return EXIT_PASS
    if decision == "BLOCKED":
        return EXIT_BLOCKED
    return EXIT_FAIL


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--manifest", required=True, type=pathlib.Path,
                        help="Path to a local offline JSON task manifest")
    parser.add_argument("--json-only", action="store_true",
                        help="Print only the machine-readable JSON summary to stdout")
    args = parser.parse_args(argv)

    try:
        if not args.manifest.is_file():
            raise FileNotFoundError("manifest is not a regular file")
        if args.manifest.stat().st_size > MAX_MANIFEST_BYTES:
            raise ValueError("manifest exceeds 512 KiB")
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        report = _failure_report(
            args.manifest.name,
            [f"invalid manifest file: {type(exc).__name__}"],
        )
        emit(report, args.json_only)
        return EXIT_FAIL

    report = build_report(manifest, source_label=args.manifest.name)
    emit(report, args.json_only)
    return exit_code(report["effective_decision"])


if __name__ == "__main__":
    sys.exit(main())

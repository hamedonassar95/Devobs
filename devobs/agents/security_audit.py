"""Offline, read-only security audit for the two-worker task manifest.

The engine reads one local JSON manifest and reports advisory findings before a
human starts any worker. It reuses ``scripts/check_two_agent_tasks.py`` as the
contract source of truth, adds independent safety findings, and never executes
manifest commands, starts agents, changes Git state, calls a network service or
grants an approval.

A PASS result is advisory coordination evidence only. Merge, deploy, billing,
production access and Phase 8 owner approval remain mandatory human gates.
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from check_two_agent_tasks import (
        APPROVAL_VALUE,
        BRANCH_RE,
        MAX_MANIFEST_BYTES,
        OWNED_STATUSES,
        RESTRICTED_ACTIONS,
        SHA_RE,
        TOP_LEVEL_KEYS,
        _normal_path,
        evaluate,
    )
except ImportError as exc:  # fail closed when the shared contract is unavailable
    IMPORT_ERROR = f"shared validator import failed: {type(exc).__name__}"
else:
    IMPORT_ERROR = None

AUDIT_TYPE = "advisory_agent_security_audit"
SCHEMA_VERSION = 1
SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
PROTECTED_BRANCHES = frozenset(("main", "master", "release", "develop"))
REVIEWED_STATUSES = frozenset(("evidence_ready", "complete"))
EXIT_PASS = 0
EXIT_BLOCKED = 1
EXIT_FAIL = 2

RECOMMENDATIONS = {
    "duplicate_task_ownership": "Assign each task ID to exactly one worker.",
    "conflicting_file_assignments": "Separate file ownership or declare a reviewed dependency order.",
    "protected_branch_violation": "Use a valid feature/, fix/, docs/ or chore/ ref; never target a protected branch.",
    "missing_dependency": "Correct or remove references to unknown task IDs.",
    "blocked_dependency": "Wait for upstream work to complete or mark this task blocked.",
    "missing_human_approval": "Keep all approval fields pending_human and remove restricted task actions.",
    "stale_task_assignment": "Refresh the exact SHA, verification commands and sanitized evidence before review.",
    "contract_validation_failure": "Correct the shared-contract errors before any worker starts.",
    "invalid_manifest": "Provide a readable, bounded UTF-8 JSON manifest without duplicate keys.",
    "contract_unavailable": "Restore the shared validator before running the audit.",
}


def _safe(value, limit=200):
    """Return a bounded, printable string safe for machine-readable evidence."""
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)
    text = "".join(character if character.isprintable() else "?" for character in text)
    text = re.sub(r"\s+", " ", text).strip() or "<empty>"
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def _expected_decision(findings, validator_decision):
    if any(item["severity"] == "CRITICAL" for item in findings):
        return "FAIL"
    if validator_decision == "FAIL":
        return "FAIL"
    if findings or validator_decision == "BLOCKED":
        return "BLOCKED"
    if validator_decision == "PASS":
        return "PASS"
    return "FAIL"


def _new_result(source_label):
    return {
        "audit_type": AUDIT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "decision": "FAIL",
        "read_only": True,
        "dispatched": False,
        "source_label": _safe(source_label),
        "findings": [],
        "summary": {"tasks": 0, "findings": 0,
                    "by_severity": {name: 0 for name in SEVERITIES}},
        "validator": {},
        "errors": [],
        "human_approval_actions": [
            "Human must review every finding before starting any worker.",
            "Human must keep merge, deploy, billing and production approvals pending.",
            "Human must complete Phase 8 owner approval; this audit never grants it.",
        ],
    }


def _finding(sequence, category, severity, title, evidence):
    return {
        "id": f"SEC-{sequence:03d}",
        "category": category,
        "severity": severity,
        "title": title,
        "evidence": evidence,
        "recommendation": RECOMMENDATIONS.get(category, "Require human review."),
    }


def _finalize(result, validator_decision):
    findings = result["findings"]
    result["summary"]["findings"] = len(findings)
    for name in SEVERITIES:
        result["summary"]["by_severity"][name] = sum(
            1 for item in findings if item["severity"] == name
        )
    result["decision"] = _expected_decision(findings, validator_decision)
    return result


def _task_list(manifest):
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list):
        return []
    return [task for task in tasks if isinstance(task, dict)]


def _index(tasks):
    by_id = {}
    for task in tasks:
        task_id = task.get("id")
        if isinstance(task_id, str) and task_id not in by_id:
            by_id[task_id] = task
    return by_id


def _depends_on(task_id, target, by_id):
    if not isinstance(task_id, str) or not isinstance(target, str):
        return False
    seen = set()
    pending = _string_list(by_id.get(task_id, {}).get("dependencies"))
    while pending:
        current = pending.pop()
        if current == target:
            return True
        if current in seen or current not in by_id:
            continue
        seen.add(current)
        pending.extend(_string_list(by_id[current].get("dependencies")))
    return False


def _unresolved_dependencies(task_id, by_id):
    if not isinstance(task_id, str):
        return []
    seen = set()
    unresolved = set()
    pending = _string_list(by_id.get(task_id, {}).get("dependencies"))
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        dependency = by_id.get(current)
        if dependency is None:
            continue
        if dependency.get("status") != "complete":
            unresolved.add(current)
            pending.extend(_string_list(dependency.get("dependencies")))
    return sorted(unresolved)


def _string_list(value):
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _normal_paths(task):
    paths = task.get("affected_files")
    if not isinstance(paths, list):
        return []
    result = []
    for value in paths:
        candidate = _normal_path(value)
        if candidate is not None:
            result.append(candidate)
    return result


def _invalid_branch_reason(branch):
    """Return a fail-closed reason string for an unsafe task branch."""
    if not isinstance(branch, str) or not branch:
        return "missing_or_invalid_branch"
    if branch.casefold() in PROTECTED_BRANCHES:
        return "protected_branch_name"
    if not BRANCH_RE.fullmatch(branch):
        return "invalid_or_protected_ref"
    _, _, suffix = branch.partition("/")
    for segment in suffix.split("/"):
        if not segment:
            return "empty_ref_component"
        if segment in (".", "..") or ".." in segment:
            return "git_ref_traversal_or_dot_component"
    return None


def _detect_duplicate_ownership(tasks, add):
    grouped = {}
    for task in tasks:
        task_id = task.get("id")
        if isinstance(task_id, str):
            grouped.setdefault(task_id, []).append(task)
    for task_id in sorted(grouped):
        rows = grouped[task_id]
        if len(rows) < 2:
            continue
        add(
            "duplicate_task_ownership", "HIGH", "Duplicate task ownership",
            {
                "task": _safe(task_id),
                "assignments": len(rows),
                "agents": sorted({_safe(row.get("assigned_agent")) for row in rows}),
                "branches": sorted({_safe(row.get("branch")) for row in rows}),
            },
        )


def _detect_file_conflicts(tasks, add):
    records = []
    for task in tasks:
        if task.get("status") not in OWNED_STATUSES:
            continue
        paths = _normal_paths(task)
        keys = {path.casefold(): path for path in paths}
        records.append((task, keys))
    by_id = _index(tasks)
    for index, (first, first_paths) in enumerate(records):
        for second, second_paths in records[index + 1:]:
            if first.get("repository") != second.get("repository"):
                continue
            shared = sorted(set(first_paths) & set(second_paths))
            if not shared:
                continue
            first_id = first.get("id")
            second_id = second.get("id")
            if (_depends_on(first_id, second_id, by_id)
                    or _depends_on(second_id, first_id, by_id)):
                continue
            add(
                "conflicting_file_assignments", "HIGH",
                "Conflicting file assignments",
                {
                    "tasks": sorted((_safe(first_id), _safe(second_id))),
                    "files": shared,
                    "comparison": "case-insensitive",
                },
            )


def _detect_branch_violations(tasks, add):
    for task in tasks:
        branch = task.get("branch")
        reason = _invalid_branch_reason(branch)
        if reason:
            add(
                "protected_branch_violation", "HIGH",
                "Protected branch or invalid Git ref target",
                {
                    "task": _safe(task.get("id")),
                    "branch": _safe(branch),
                    "reason": reason,
                },
            )


def _detect_dependencies(tasks, add):
    by_id = _index(tasks)
    for task in tasks:
        task_id = _safe(task.get("id"))
        dependencies = task.get("dependencies")
        dependencies = dependencies if isinstance(dependencies, list) else []
        known = [dep for dep in dependencies if isinstance(dep, str)]
        unknown = sorted({dep for dep in known if dep not in by_id})
        if unknown:
            add(
                "missing_dependency", "HIGH", "Missing dependency target",
                {"task": task_id, "dependencies": [_safe(dep) for dep in unknown]},
            )
        unresolved = _unresolved_dependencies(task.get("id"), by_id)
        if unresolved:
            add(
                "blocked_dependency", "MEDIUM", "Unresolved blocked dependency",
                {"task": task_id, "dependencies": [_safe(dep) for dep in unresolved]},
            )


def _detect_human_approval(manifest, tasks, add):
    approval = manifest.get("approval")
    if not isinstance(approval, dict):
        add(
            "missing_human_approval", "CRITICAL", "Human approval object missing",
            {"reason": "approval_object_missing"},
        )
    else:
        missing = sorted(set(RESTRICTED_ACTIONS) - set(approval))
        altered = sorted(
            key for key in RESTRICTED_ACTIONS
            if key in approval and approval[key] != APPROVAL_VALUE
        )
        if missing or altered:
            add(
                "missing_human_approval", "CRITICAL",
                "Human approval fields altered or missing",
                {"missing_fields": missing, "altered_fields": altered},
            )
    for task in tasks:
        actions = task.get("requested_actions")
        actions = actions if isinstance(actions, list) else []
        restricted = sorted({action for action in actions
                             if action in RESTRICTED_ACTIONS})
        if restricted:
            add(
                "missing_human_approval", "CRITICAL",
                "Restricted action requested by a task",
                {
                    "tasks": [_safe(task.get("id"))],
                    "restricted_actions": restricted,
                },
            )


def _detect_stale_assignments(tasks, add):
    for task in tasks:
        if task.get("status") not in REVIEWED_STATUSES:
            continue
        missing = []
        source_sha = task.get("source_sha")
        if not isinstance(source_sha, str) or not SHA_RE.fullmatch(source_sha):
            missing.append("source_sha")
        verification = task.get("verification")
        if not isinstance(verification, dict):
            missing.extend(("verification.commands", "verification.result",
                            "verification.evidence"))
        else:
            commands = verification.get("commands")
            if (not isinstance(commands, list) or not commands
                    or any(not isinstance(item, str) or not item for item in commands)):
                missing.append("verification.commands")
            if verification.get("result") != "PASS":
                missing.append("verification.result")
            evidence = verification.get("evidence")
            if not isinstance(evidence, str) or not evidence.strip():
                missing.append("verification.evidence")
        if missing:
            add(
                "stale_task_assignment", "HIGH", "Reviewed task lacks fresh evidence",
                {
                    "task": _safe(task.get("id")),
                    "status": _safe(task.get("status")),
                    "missing": missing,
                },
            )


def audit_manifest(manifest, source_label="manifest"):
    """Return a fail-closed advisory audit for one parsed manifest object."""
    result = _new_result(source_label)
    if IMPORT_ERROR:
        result["errors"].append(IMPORT_ERROR)
        result["findings"].append(_finding(
            1, "contract_unavailable", "CRITICAL", "Shared validator unavailable",
            {"error": _safe(IMPORT_ERROR)},
        ))
        return _finalize(result, "FAIL")

    if not isinstance(manifest, dict) or set(manifest) != TOP_LEVEL_KEYS:
        unexpected = sorted(str(key) for key in manifest) if isinstance(manifest, dict) else []
        result["errors"].append("invalid top-level manifest fields")
        result["findings"].append(_finding(
            1, "invalid_manifest", "CRITICAL", "Invalid manifest contract",
            {"unexpected_or_missing_fields": [_safe(key) for key in unexpected]},
        ))
        return _finalize(result, "FAIL")

    try:
        validator = evaluate(manifest)
    except Exception as exc:  # fail closed even on unexpected contract errors
        error = f"shared validator error: {type(exc).__name__}"
        result["errors"].append(error)
        result["findings"].append(_finding(
            1, "contract_validation_failure", "CRITICAL",
            "Shared validator raised an unexpected error",
            {"error": _safe(error)},
        ))
        return _finalize(result, "FAIL")
    result["validator"] = validator
    result["errors"] = [_safe(error, limit=500) for error in validator.get("errors", [])]
    tasks = _task_list(manifest)
    result["summary"]["tasks"] = len(tasks)
    sequence = 0

    def add(category, severity, title, evidence):
        nonlocal sequence
        sequence += 1
        result["findings"].append(
            _finding(sequence, category, severity, title, evidence)
        )

    _detect_duplicate_ownership(tasks, add)
    _detect_file_conflicts(tasks, add)
    _detect_branch_violations(tasks, add)
    _detect_dependencies(tasks, add)
    _detect_human_approval(manifest, tasks, add)
    _detect_stale_assignments(tasks, add)
    if validator.get("errors"):
        add(
            "contract_validation_failure", "CRITICAL",
            "Shared contract validation failed",
            {"errors": result["errors"]},
        )
    return _finalize(result, validator.get("decision", "FAIL"))


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _load_manifest(path):
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("manifest exceeds 512 KiB")
    return json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
    )


def exit_code(decision):
    """Map an audit decision to an exact advisory exit code."""
    if decision == "PASS":
        return EXIT_PASS
    if decision == "BLOCKED":
        return EXIT_BLOCKED
    return EXIT_FAIL


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=pathlib.Path,
                        help="Path to a local offline JSON task manifest")
    args = parser.parse_args(argv)
    try:
        manifest = _load_manifest(args.manifest)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        result = _new_result(args.manifest)
        result["errors"].append(f"invalid manifest file: {type(exc).__name__}")
        result["findings"].append(_finding(
            1, "invalid_manifest", "CRITICAL", "Manifest could not be read safely",
            {"error": f"invalid manifest file: {type(exc).__name__}"},
        ))
        print(json.dumps(_finalize(result, "FAIL"), sort_keys=True, ensure_ascii=True))
        return EXIT_FAIL
    result = audit_manifest(manifest, source_label=str(args.manifest))
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return exit_code(result["decision"])


if __name__ == "__main__":
    sys.exit(main())

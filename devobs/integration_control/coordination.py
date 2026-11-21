"""Ownership and task coordination checks, reusing existing task validator."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from .models import Finding
from .validation import redact


def _load_task_validator():
    script = Path(__file__).resolve().parents[2] / "scripts" / "check_two_agent_tasks.py"
    if not script.exists():
        return None
    spec = importlib.util.spec_from_file_location("integration_control_two_agent", script)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def evaluate_coordination(normalized: dict, findings: list[Finding]) -> dict:
    ownership = normalized.get("ownership", {})
    changed = set(normalized.get("changed_files", []))
    file_owners = ownership.get("file_owners", {}) if isinstance(ownership.get("file_owners"), dict) else {}
    active_agents = ownership.get("active_agents", []) if isinstance(ownership.get("active_agents"), list) else []

    for path, owners in sorted(file_owners.items()):
        if not isinstance(path, str) or not isinstance(owners, list):
            continue
        if changed and path not in changed:
            continue
        uniq = sorted({str(o) for o in owners if str(o).strip()})
        if len(uniq) > 1:
            findings.append(Finding("CONCURRENT_FILE_OWNERSHIP", "error", "ownership", f"Concurrent ownership for {path}", {"file": path, "owners": uniq}))

    if len({str(a) for a in active_agents if str(a).strip()}) > 1 and changed and not file_owners:
        findings.append(Finding("CONCURRENT_FILE_OWNERSHIP", "error", "ownership", "Multiple active agents without file owner map; fail closed.", {"active_agents": redact(active_agents)}))

    manifest = ownership.get("task_manifest")
    manifest_result = None
    if isinstance(manifest, dict):
        tasks = manifest.get("tasks")
        if not isinstance(tasks, list) or len(tasks) == 0:
            findings.append(Finding("TASK_MANIFEST_INCOMPLETE", "error", "ownership", "Task manifest missing task entries; identity/dependency evidence unverified.", {"tasks_count": len(tasks) if isinstance(tasks, list) else None}))
        else:
            validator = _load_task_validator()
            if validator is None:
                findings.append(Finding("OWNERSHIP_VALIDATOR_UNAVAILABLE", "error", "ownership", "Task validator unavailable."))
            else:
                try:
                    manifest_result = validator.evaluate(manifest)
                except Exception as exc:  # noqa: BLE001
                    findings.append(Finding("INVALID_DEPENDENCY_GRAPH", "error", "ownership", f"Task manifest evaluation failed: {exc.__class__.__name__}"))
                    manifest_result = {"decision": "FAIL", "errors": [exc.__class__.__name__]}
                decision = manifest_result.get("decision")
                if decision == "FAIL":
                    errs = manifest_result.get("errors", [])
                    code = "INVALID_DEPENDENCY_GRAPH" if any("dependency" in str(e).lower() or "cycle" in str(e).lower() for e in errs) else "POLICY_VIOLATION"
                    findings.append(Finding(code, "error", "ownership", "Task manifest invalid.", {"errors": redact(errs)}))
                for conflict in manifest_result.get("conflicts", []) if isinstance(manifest_result, dict) else []:
                    reason = conflict.get("reason")
                    code = "CONCURRENT_FILE_OWNERSHIP" if reason == "concurrent_file_ownership" else "CONFLICTING_BRANCH_OWNERSHIP"
                    findings.append(Finding(code, "error", "ownership", f"Task conflict: {reason}", redact(conflict)))
                for blocked in manifest_result.get("blocked_tasks", []) if isinstance(manifest_result, dict) else []:
                    reason = blocked.get("reason")
                    if reason == "unresolved_dependency":
                        findings.append(Finding("INVALID_DEPENDENCY_GRAPH", "error", "ownership", "Unresolved dependency in task manifest.", redact(blocked)))
                    else:
                        findings.append(Finding("BLOCKED_TASK_OWNERSHIP_CONFLICT", "error", "ownership", "Blocked task retains ownership and blocks integration.", redact(blocked)))

    stale_workspace = ownership.get("stale_evidence") is True
    if stale_workspace:
        findings.append(Finding("STALE_WORKSPACE_EVIDENCE", "error", "ownership", "Ownership/workspace evidence is stale."))

    return {
        "status": "pass" if not any(f.category == "ownership" for f in findings) else "conflict",
        "manifest_decision": manifest_result.get("decision") if isinstance(manifest_result, dict) else None,
        "active_agents": redact(active_agents),
        "stale_workspace": stale_workspace,
    }

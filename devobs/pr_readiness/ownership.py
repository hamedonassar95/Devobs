"""Multi-agent ownership conflict detection.

Reuses the existing two-agent task validator when possible.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from .models import Finding
from .evidence import redact


def _load_two_agent_validator():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "check_two_agent_tasks.py"
    if not script.exists():
        return None
    spec = importlib.util.spec_from_file_location("devobs_pr_readiness_two_agent", script)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate_ownership(ev: dict[str, Any], findings: list[Finding]) -> dict[str, Any]:
    ownership = ev.get("ownership") or {}
    changed_files = set(ev.get("changed_files") or [])
    stale = ownership.get("stale_evidence") is True
    if stale:
        findings.append(Finding("STALE_VALIDATION_EVIDENCE", "error", "ownership", "Validation evidence marked stale."))

    # Active agent overlap from evidence
    file_owners = ownership.get("file_owners") if isinstance(ownership.get("file_owners"), dict) else {}
    overlaps: list[dict[str, Any]] = []
    for file_path, owners in file_owners.items():
        if not isinstance(file_path, str) or not isinstance(owners, list):
            continue
        norm = file_path.replace("\\", "/")
        if changed_files and norm not in changed_files:
            continue
        owner_set = sorted({str(o) for o in owners if str(o).strip()})
        if len(owner_set) > 1:
            overlaps.append({"file": norm, "owners": owner_set})
            findings.append(Finding("CONCURRENT_FILE_OWNERSHIP", "error", "ownership", f"Concurrent file ownership detected: {norm}", {"file": norm, "owners": owner_set}))

    active_agents = ownership.get("active_agents") if isinstance(ownership.get("active_agents"), list) else []
    if len({str(a) for a in active_agents if str(a).strip()}) > 1 and changed_files and not file_owners:
        findings.append(Finding("CONCURRENT_MODIFICATION_HAZARD", "error", "ownership", "Multiple active agents with changed files but no file ownership map; fail closed.", {"active_agents": redact(active_agents)}))

    manifest_result = None
    task_manifest = ownership.get("task_manifest")
    if isinstance(task_manifest, dict):
        mod = _load_two_agent_validator()
        if mod is None:
            findings.append(Finding("OWNERSHIP_VALIDATOR_UNAVAILABLE", "error", "ownership", "Two-agent task validator unavailable; cannot verify ownership manifest."))
        else:
            try:
                manifest_result = mod.evaluate(task_manifest)
            except Exception as exc:  # noqa: BLE001
                findings.append(Finding("OWNERSHIP_MANIFEST_INVALID", "error", "ownership", f"Task manifest evaluation failed: {exc.__class__.__name__}"))
                manifest_result = {"decision": "FAIL", "errors": [exc.__class__.__name__], "conflicts": [], "blocked_tasks": []}
            if manifest_result.get("decision") == "FAIL":
                findings.append(Finding("OWNERSHIP_MANIFEST_INVALID", "error", "ownership", "Task manifest invalid; ownership cannot be verified.", {"errors": redact(manifest_result.get("errors", []))}))
            for conflict in manifest_result.get("conflicts", []) if isinstance(manifest_result.get("conflicts"), list) else []:
                reason = conflict.get("reason")
                code = "CONCURRENT_FILE_OWNERSHIP" if reason == "concurrent_file_ownership" else "CONFLICTING_BRANCH_OWNERSHIP" if reason == "concurrent_branch_ownership" else "CONCURRENT_MODIFICATION_HAZARD"
                findings.append(Finding(code, "error", "ownership", f"Task manifest conflict: {reason}", redact(conflict)))
            for blocked in manifest_result.get("blocked_tasks", []) if isinstance(manifest_result.get("blocked_tasks"), list) else []:
                reason = blocked.get("reason")
                code = "UNRESOLVED_DEPENDENCY" if reason == "unresolved_dependency" else "BLOCKED_TASK_OWNERSHIP"
                findings.append(Finding(code, "error", "ownership", f"Task manifest blocked: {reason}", redact(blocked)))

    return {
        "status": "pass" if not any(f.category == "ownership" for f in findings) else "conflict_or_unverified",
        "owner": ownership.get("owner"),
        "active_agents": redact(active_agents),
        "overlaps": overlaps,
        "stale_evidence": stale,
        "task_manifest_decision": redact(manifest_result.get("decision")) if isinstance(manifest_result, dict) else None,
    }

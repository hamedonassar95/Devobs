"""Ownership and conflict validation using two-agent manifest contract."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Mapping

from .contracts import redact
from .models import Finding


def _load_two_agent():
    script = Path(__file__).resolve().parents[2] / "scripts" / "check_two_agent_tasks.py"
    if not script.exists():
        return None, script
    spec = importlib.util.spec_from_file_location("ivh_two_agent", script)
    if spec is None or spec.loader is None:
        return None, script
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, script


def evaluate_ownership(raw: Any, findings: list[Finding]) -> dict[str, Any]:
    if raw is None:
        findings.append(Finding("MISSING_OWNERSHIP_EVIDENCE", "HIGH", "ownership", "Ownership evidence missing; fail closed", inferred=False))
        return {"status": "missing"}
    if not isinstance(raw, Mapping):
        findings.append(Finding("MALFORMED_OWNERSHIP_EVIDENCE", "HIGH", "ownership", "Ownership evidence must be object"))
        return {"status": "invalid"}

    ownership = {str(k): redact(v, str(k)) for k, v in raw.items()}
    conflicts = []
    blocked = []
    manifest = ownership.get("task_manifest")
    if isinstance(manifest, Mapping):
        mod, script = _load_two_agent()
        if mod is None:
            findings.append(Finding("OWNERSHIP_VALIDATOR_UNAVAILABLE", "CRITICAL", "ownership", "Two-agent validator unavailable; cannot verify ownership", evidence={"script": str(script)}))
        else:
            try:
                result = mod.evaluate(dict(manifest))
            except Exception as exc:  # noqa: BLE001
                findings.append(Finding("OWNERSHIP_MANIFEST_INVALID", "HIGH", "ownership", f"Manifest evaluation failed: {exc.__class__.__name__}"))
                result = {"decision": "FAIL", "conflicts": [], "blocked_tasks": [], "errors": [exc.__class__.__name__]}
            ownership["manifest_result"] = redact(result)
            for c in result.get("conflicts", []) if isinstance(result, dict) else []:
                reason = str(c.get("reason", "conflict"))
                code = "CONCURRENT_FILE_OWNERSHIP" if reason == "concurrent_file_ownership" else "CONCURRENT_BRANCH_OWNERSHIP"
                conflicts.append(redact(c))
                findings.append(Finding(code, "CRITICAL", "ownership", f"Ownership conflict: {reason}", evidence=redact(c)))
            for b in result.get("blocked_tasks", []) if isinstance(result, dict) else []:
                blocked.append(redact(b))
                reason = str(b.get("reason"))
                if reason == "task_blocked":
                    findings.append(Finding("BLOCKED_TASK_RETAINS_OWNERSHIP", "HIGH", "ownership", "Blocked task retains ownership until explicitly released", evidence=redact(b)))
                elif reason == "unresolved_dependency":
                    findings.append(Finding("UNRESOLVED_DEPENDENCY", "HIGH", "ownership", "Task has unresolved dependency", evidence=redact(b)))
            if result.get("decision") == "FAIL":
                findings.append(Finding("OWNERSHIP_MANIFEST_INVALID", "HIGH", "ownership", "Task manifest invalid", evidence={"errors": redact(result.get("errors", []))}))
    else:
        findings.append(Finding("MISSING_TASK_MANIFEST", "HIGH", "ownership", "Task manifest missing from ownership evidence"))

    # explicit active worktree ownership
    worktrees = ownership.get("active_worktrees")
    if isinstance(worktrees, list):
        by_path = {}
        for wt in worktrees:
            if not isinstance(wt, Mapping):
                continue
            branch = str(wt.get("branch", "")).strip()
            for p in wt.get("owned_paths", []) if isinstance(wt.get("owned_paths"), list) else []:
                norm = str(p).replace("\\", "/")
                by_path.setdefault(norm, set()).add(branch)
        for path, owners in sorted(by_path.items()):
            if len({o for o in owners if o}) > 1:
                conflicts.append({"path": path, "owners": sorted(owners)})
                findings.append(Finding("CONCURRENT_FILE_OWNERSHIP", "CRITICAL", "ownership", f"Active worktree path overlap: {path}", evidence={"path": path, "owners": sorted(owners)}))

    ownership["conflicts"] = conflicts
    ownership["blocked_tasks"] = blocked
    ownership["status"] = "conflict" if conflicts or blocked or any(f.category == "ownership" and f.severity in {"CRITICAL","HIGH"} for f in findings) else "ok"
    return ownership

"""Integration readiness reporting (JSON + Markdown)."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .readiness import evaluate_readiness
from .validation import redact


def build_readiness_report(raw: Any) -> dict[str, Any]:
    readiness = evaluate_readiness(raw)
    raw_map = raw if isinstance(raw, Mapping) else {}
    pr = raw_map.get("pr", raw_map) if isinstance(raw_map.get("pr", raw_map), Mapping) else {}
    report = {
        "schema_version": 1,
        "report_type": "integration_readiness",
        "repository": pr.get("repository") or raw_map.get("repository"),
        "branch": pr.get("head_branch") or pr.get("head"),
        "commit": pr.get("head_sha") or raw_map.get("head_sha"),
        "agent_identifier": raw_map.get("agent_identifier") or raw_map.get("agent"),
        "task_identifier": raw_map.get("task_identifier") or raw_map.get("task_id"),
        "evidence_sources": raw_map.get("evidence", []),
        "verification_results": readiness.get("evidence_checks", []),
        "dependency_status": [c for c in readiness.get("evidence_checks", []) if isinstance(c, dict) and c.get("name") == "dependency_completion"],
        "file_ownership_conflicts": readiness.get("conflicts", {}).get("checks", []),
        "security_findings": [c for c in readiness.get("evidence_checks", []) if isinstance(c, dict) and "security" in c.get("name", "")],
        "ci_verification_results": [c for c in readiness.get("evidence_checks", []) if isinstance(c, dict) and "ci" in c.get("name", "") or c.get("name") == "human_approval"],
        "human_approval_requirements": {"required": True, "state": "PENDING_HUMAN_REVIEW" if readiness.get("decision") == "READY_FOR_HUMAN_REVIEW" else "BLOCKED_OR_UNKNOWN"},
        "recommended_next_action": readiness.get("recommended_next_action"),
        "readiness": readiness.get("decision"),
        "engine_decision": readiness.get("engine_decision"),
    }
    return redact(report)


def render_json(report: Mapping[str, Any]) -> str:
    return json.dumps(redact(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_markdown(report: Mapping[str, Any]) -> str:
    r = redact(report)
    lines = [
        "# Integration Readiness Report",
        "",
        f"- **Readiness:** `{r.get('readiness', 'UNKNOWN')}`",
        f"- **Repository:** `{r.get('repository', '')}`",
        f"- **Branch:** `{r.get('branch', '')}`",
        f"- **Commit:** `{r.get('commit', '')}`",
        f"- **Agent:** `{r.get('agent_identifier', '')}`",
        f"- **Task:** `{r.get('task_identifier', '')}`",
        f"- **Recommended next action:** {r.get('recommended_next_action', '')}",
        "",
        "## Verification results",
    ]
    for item in r.get("verification_results", []) if isinstance(r.get("verification_results"), list) else []:
        if isinstance(item, dict):
            lines.append(f"- `{item.get('state')}` **{item.get('name')}** - {item.get('message')}")
    lines += ["", "## Human approval", "- Human approval is required before merge. No auto-merge is permitted.", ""]
    return "\n".join(lines)

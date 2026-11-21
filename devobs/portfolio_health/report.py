"""Render portfolio health reports as deterministic JSON/Markdown."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .collector import redact_obj


def render_json_report(report: Mapping[str, Any]) -> str:
    return json.dumps(redact_obj(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_markdown_report(report: Mapping[str, Any]) -> str:
    r = redact_obj(report)
    lines = [
        "# Integration Portfolio Health Dashboard",
        "",
        f"- **Readiness:** `{r.get('readiness', 'UNKNOWN')}`",
        f"- **Score:** `{(r.get('score') or {}).get('score', '?')}` / 100 (deterministic, advisory)",
        f"- **Repository:** `{r.get('repository', '')}`",
        f"- **Generated at:** `{r.get('generated_at', '')}`",
        f"- **Advisory only / human review required:** `{r.get('advisory_only')}` / `{r.get('human_review_required')}`",
        "",
        "## Summary",
    ]
    summary = r.get("summary", {}) if isinstance(r.get("summary"), Mapping) else {}
    for k in ["evidence", "ci", "pull_requests", "ownership", "dependencies", "security", "approval"]:
        if k in summary:
            lines.append(f"- **{k}**: `{json.dumps(summary[k], sort_keys=True, ensure_ascii=False)}`")
    lines.extend(["", "## Findings"])
    findings = r.get("findings", []) if isinstance(r.get("findings"), list) else []
    if not findings:
        lines.append("- No findings.")
    for f in findings:
        if not isinstance(f, Mapping):
            continue
        lines.append(f"- **{f.get('severity')} {f.get('code')}** [{f.get('category')}] {f.get('message')} (component={f.get('component','')})")
        if f.get("remediation"):
            lines.append(f"  - Remediation: {f.get('remediation')}")
    lines.extend(["", "## Recommended remediations"])
    rem = r.get("recommended_remediations", []) if isinstance(r.get("recommended_remediations"), list) else []
    if not rem:
        lines.append("- No remediations.")
    for item in rem:
        if isinstance(item, Mapping):
            lines.append(f"- [{item.get('priority')}] {item.get('action')}")
    lines.extend(["", "> Advisory only. No merge, no deployment, no approval override. Missing/unknown evidence fails closed."])
    return "\n".join(lines) + "\n"
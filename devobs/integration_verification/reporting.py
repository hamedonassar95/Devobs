"""JSON and Markdown reporting for integration verification hub."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .contracts import redact


def render_json_report(report: Mapping[str, Any]) -> str:
    return json.dumps(redact(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_markdown_report(report: Mapping[str, Any]) -> str:
    r = redact(report)
    lines = [
        "# Integration Verification Hub Report",
        "",
        f"- **Decision:** `{r.get('decision', 'INSUFFICIENT_EVIDENCE')}`",
        f"- **Repository:** `{r.get('repository', '')}`",
        f"- **HEAD:** `{r.get('head_sha', '')}`",
        f"- **Generated:** `{r.get('generated_at', '')}`",
        f"- **Human review required:** `{r.get('human_review_required', True)}`",
        "",
        "## Component inventory",
    ]
    inv = r.get("component_inventory", [])
    if isinstance(inv, list) and inv:
        for c in inv:
            if isinstance(c, dict):
                lines.append(f"- `{c.get('verification_status')}` **{c.get('name')}** ({c.get('source_path')}) owner={c.get('owning_branch')} tests={c.get('test_coverage')}")
    else:
        lines.append("- No components discovered.")
    lines += ["", "## Findings"]
    findings = r.get("findings", [])
    if isinstance(findings, list) and findings:
        for f in findings:
            if isinstance(f, dict):
                tag = "INFERRED" if f.get("inferred") else "VERIFIED-EVIDENCE"
                lines.append(f"- **{f.get('severity')} {f.get('code')}** [{f.get('category')}] ({tag}) {f.get('message')}")
    else:
        lines.append("- No findings.")
    lines += ["", "## Remediation backlog"]
    for item in r.get("remediation_backlog", []) if isinstance(r.get("remediation_backlog"), list) else []:
        if isinstance(item, dict):
            lines.append(f"- [{item.get('priority')}] {item.get('action')} (component={item.get('component','')})")
    lines += ["", "> Deterministic, fail-closed, advisory only. No merge/deploy/approval performed."]
    return "\n".join(lines) + "\n"

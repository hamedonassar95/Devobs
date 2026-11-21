"""Report renderers."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .validation import redact


def render_json_report(report: Mapping[str, Any]) -> str:
    return json.dumps(redact(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_markdown_report(report: Mapping[str, Any]) -> str:
    r = redact(report)
    repo = r.get("repository", {}) if isinstance(r.get("repository"), dict) else {}
    lines = [
        "# Integration Control Plane Report",
        "",
        f"- **Decision:** `{r.get('decision', 'NEEDS_EVIDENCE')}`",
        f"- **Repository:** `{repo.get('name', '')}` PR `{repo.get('pr_number', '')}`",
        f"- **Head SHA:** `{repo.get('head_sha', '')}`",
        f"- **Reviewed SHA:** `{repo.get('reviewed_head_sha', '')}`",
        f"- **Human review required:** `{r.get('human_review_required', True)}`",
        f"- **Recommended next action:** {r.get('recommended_next_action', '')}",
        "",
        "## Findings",
    ]
    findings = r.get("findings", []) if isinstance(r.get("findings"), list) else []
    if not findings:
        lines.append("- None")
    for f in findings:
        if isinstance(f, dict):
            lines.append(f"- **{f.get('severity','')} {f.get('code','')}** [{f.get('category','')}]: {f.get('message','')}")
    lines += ["", "## Evidence registry", f"- Records: {len(r.get('evidence_registry', []) if isinstance(r.get('evidence_registry'), list) else [])}", "", "> Deterministic policy authoritative. No merge/deploy performed."]
    return "\n".join(lines) + "\n"

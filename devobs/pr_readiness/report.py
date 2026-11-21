"""Report rendering for PR readiness."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .evidence import redact


def render_json_report(report: Mapping[str, Any]) -> str:
    return json.dumps(redact(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_markdown_report(report: Mapping[str, Any]) -> str:
    r = redact(report)
    pr = r.get("pr", {}) if isinstance(r.get("pr"), dict) else {}
    decision = r.get("readiness_decision", {}) if isinstance(r.get("readiness_decision"), dict) else {}
    risk = r.get("risk", {}) if isinstance(r.get("risk"), dict) else {}
    lines = [
        "# PR Readiness Report",
        "",
        f"- **Decision:** `{decision.get('decision', 'INSUFFICIENT_EVIDENCE')}`",
        f"- **Risk:** `{risk.get('level', 'UNKNOWN')}` (deterministic, score={risk.get('score', '')})",
        f"- **Repository:** `{pr.get('repository', '')}`",
        f"- **PR:** `{pr.get('pr_number', '')}`",
        f"- **Base/Head:** `{pr.get('base_branch', '')}` <- `{pr.get('head_branch', '')}`",
        f"- **Head SHA:** `{pr.get('head_sha', '')}`",
        f"- **Reviewed SHA:** `{pr.get('reviewed_head_sha', '')}`",
        f"- **Human review required:** `{r.get('human_review_required', True)}`",
        f"- **Recommended next action:** {r.get('recommended_next_action', '')}",
        "",
        "## Evidence timestamps",
    ]
    ts = r.get("evidence_timestamps", {}) if isinstance(r.get("evidence_timestamps"), dict) else {}
    if ts:
        for k, v in sorted(ts.items()):
            lines.append(f"- `{k}`: {v}")
    else:
        lines.append("- No evidence timestamps provided.")
    lines += ["", "## Findings"]
    findings = r.get("findings", []) if isinstance(r.get("findings"), list) else []
    if not findings:
        lines.append("- No findings.")
    for f in findings:
        if isinstance(f, dict):
            lines.append(f"- **{f.get('severity','')} {f.get('code','')}** [{f.get('category','')}]: {f.get('message','')}")
    lines += [
        "",
        "## Advisory (non-authoritative)",
        f"- {((r.get('advisory') or {}) if isinstance(r.get('advisory'), dict) else {}).get('summary', '')}",
        "",
        "> Deterministic rules are authoritative. AI/advisory output cannot override security policy or required human approval. No merge performed.",
        "",
    ]
    return "\n".join(lines)

"""JSON/Markdown reporting for production readiness."""

from __future__ import annotations

import json
from typing import Any, Mapping

from scripts.ci_failure_intelligence import redact_secrets


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, Mapping):
        return {str(k): _redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    if isinstance(value, tuple):
        return [_redact(v) for v in value]
    return value


def render_json_report(report: Mapping[str, Any]) -> str:
    return json.dumps(_redact(dict(report)), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_markdown_report(report: Mapping[str, Any]) -> str:
    r = _redact(dict(report))
    lines = [
        "# Production Readiness Intelligence Report",
        "",
        f"- **Status:** `{r.get('status','UNKNOWN')}`",
        f"- **Advisory only:** `{r.get('advisory_only', True)}`",
        f"- **Human approval required:** `{r.get('human_approval_required', True)}`",
        f"- **Generated at:** `{r.get('generated_at','')}`",
        f"- **Repository:** `{r.get('repository','')}`",
        "",
        "## Risk Matrix",
        "",
        "| Severity | Count |",
        "|---|---:|",
    ]
    counts = (r.get("summary") or {}).get("severity_counts", {})
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        lines.append(f"| {sev} | {counts.get(sev,0)} |")
    lines += ["", "## Findings", ""]
    findings = r.get("findings", [])
    if not findings:
        lines.append("- No findings.")
    for f in findings:
        lines.append(f"- **{f.get('severity')} {f.get('code')}** [{f.get('category')}] {f.get('message')}")
        if f.get("remediation"):
            lines.append(f"  - Remediation: {f.get('remediation')}")
    lines += ["", "## Recommendations", ""]
    recs = r.get("recommendations", [])
    if not recs:
        lines.append("- No recommendations.")
    for rec in recs:
        lines.append(f"- [{rec.get('priority','')}] {rec.get('action','')}")
    lines += ["", "> Offline deterministic report. No merge, deploy, or destructive action performed."]
    return "\n".join(lines) + "\n"

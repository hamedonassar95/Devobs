"""Deterministic JSON and Markdown renderers for readiness reports."""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .security import redact_text, redact_value

MAX_MARKDOWN_FINDINGS = 100


def render_json_report(report: Mapping[str, Any]) -> str:
    """Serialize a redacted report with stable key ordering."""
    safe = redact_value(dict(report))
    return json.dumps(safe, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_markdown_report(report: Mapping[str, Any]) -> str:
    """Render a bounded Markdown summary from a redacted report."""
    safe = redact_value(dict(report))
    counts = safe.get("counts", {}) if isinstance(safe.get("counts"), Mapping) else {}
    findings = safe.get("findings", []) if isinstance(safe.get("findings"), list) else []
    plan = safe.get("remediation_plan", []) if isinstance(safe.get("remediation_plan"), list) else []
    inventory = safe.get("integration_inventory", []) if isinstance(safe.get("integration_inventory"), list) else []
    guardrails = safe.get("guardrails", {}) if isinstance(safe.get("guardrails"), Mapping) else {}
    lines = [
        "# Open-Source Integration Readiness Report",
        "",
        f"- **Decision:** `{safe.get('decision', 'NEEDS_EVIDENCE')}`",
        f"- **Profile:** {safe.get('profile', '')}",
        f"- **Scope SHA:** `{safe.get('scope_sha', '')}`",
        f"- **Evaluation date:** {safe.get('evaluation_date', '')}",
        f"- **Human review required:** `{safe.get('human_review_required', True)}`",
        f"- **Summary:** {safe.get('summary', '')}",
        f"- **Digest:** `{safe.get('report_digest', '')}`",
        "",
        "## Counts",
        "",
        f"- Integrations: {counts.get('integrations', 0)}",
        f"- Findings: {counts.get('findings', 0)}",
        f"- Errors: {counts.get('errors', 0)}",
        f"- Warnings: {counts.get('warnings', 0)}",
        "",
        "## Findings",
        "",
    ]
    if not findings:
        lines.append("- None")
    for finding in findings[:MAX_MARKDOWN_FINDINGS]:
        if isinstance(finding, Mapping):
            lines.append(
                f"- **{finding.get('id', '')} {finding.get('priority', '')} "
                f"{finding.get('code', '')}** [{finding.get('integration_id') or 'catalog'}]: "
                f"{finding.get('message', '')}"
            )
    lines += ["", "## Remediation plan", ""]
    if not plan:
        lines.append("- None")
    for item in plan[:MAX_MARKDOWN_FINDINGS]:
        if isinstance(item, Mapping):
            lines.append(
                f"{item.get('rank', '')}. **{item.get('priority', '')}** "
                f"{item.get('action', '')} ({item.get('finding_id', '')})"
            )
    lines += ["", "## Integration inventory", ""]
    if not inventory:
        lines.append("- None")
    for item in inventory:
        if isinstance(item, Mapping):
            lines.append(
                f"- `{item.get('id', '')}` {item.get('status', '')} "
                f"v{item.get('version', '')} — {item.get('name', '')} "
                f"(owner: {item.get('owner', '')}, license: {item.get('license', '')})"
            )
    lines += ["", "## Guardrails", ""]
    for key in sorted(guardrails):
        lines.append(f"- `{key}`: `{guardrails[key]}`")
    lines += ["", "## Diagnostics", ""]
    for item in safe.get("diagnostics", []) if isinstance(safe.get("diagnostics"), list) else []:
        lines.append(f"- {redact_text(item, 256)}")
    lines += ["", "> Read-only offline evaluation. No merge, deploy, install, or service restart was performed."]
    return "\n".join(lines) + "\n"


def render_diagnostic(code: str, message: str) -> str:
    """Render a stable, redacted CLI diagnostic without a traceback."""
    payload = {
        "schema_version": 1,
        "report_schema": "devobs.integration_readiness.diagnostic.v1",
        "status": "error",
        "code": redact_text(code, 128),
        "message": redact_text(message, 512),
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


__all__ = ["render_diagnostic", "render_json_report", "render_markdown_report"]

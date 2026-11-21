"""Optional advisory interface. Deterministic rules remain authoritative."""

from __future__ import annotations

from typing import Any, Mapping

from .evidence import redact


def build_advisory(report: Mapping[str, Any]) -> dict[str, Any]:
    findings = report.get("findings", []) if isinstance(report.get("findings"), list) else []
    by_code = [f.get("code") for f in findings if isinstance(f, dict)]
    actions = []
    if any(c in by_code for c in ["FAILED_REQUIRED_CHECK", "PENDING_REQUIRED_CHECK", "MISSING_REQUIRED_CHECK"]):
        actions.append("Resolve required CI checks and refresh evidence for current head SHA.")
    if any(str(c).startswith("SECURITY_") or str(c).startswith("DEPENDENCY_") for c in by_code):
        actions.append("Address security/dependency policy findings; do not override with AI advice.")
    if any("OWNERSHIP" in str(c) or "CONCURRENT" in str(c) or "UNRESOLVED_DEPENDENCY" == c for c in by_code):
        actions.append("Resolve multi-agent ownership/conflict before requesting human review.")
    if not actions:
        actions.append("Request human review; no autonomous merge allowed.")
    return {
        "authoritative": False,
        "engine": "deterministic-advisory",
        "summary": "Advisory summary generated from deterministic findings only.",
        "recommended_review_actions": actions,
        "finding_codes": redact(by_code),
    }

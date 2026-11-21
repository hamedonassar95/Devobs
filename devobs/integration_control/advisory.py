"""Optional, offline advisory boundary.

Advisory output is non-authoritative. The deterministic engine owns the decision,
findings, evidence registry, and human-approval requirement. A caller may inject
a local provider, but the provider receives only a redacted copy of the finished
deterministic report and its response is reduced to bounded, redacted text.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol, runtime_checkable

from .models import MAX_STRING, clip
from .validation import norm_text, redact

MAX_ADVISORY_ITEMS = 20
MAX_ADVISORY_ITEM = 300

OFFLINE_ENGINE = "offline-deterministic"
LOCAL_ENGINE = "local-advisory-provider"
UNAVAILABLE_ENGINE = "advisory-unavailable"

DEFAULT_SUMMARY = "Advisory only; deterministic policy and human approval remain authoritative."
UNAVAILABLE_SUMMARY = "Advisory provider unavailable; deterministic decision unchanged."

_GUIDANCE = {
    "FAILED_CI": "Resolve the failed required check before requesting review.",
    "PENDING_CI": "Wait for required checks to finish and recollect results.",
    "MERGE_CONFLICT": "Resolve the merge conflict and recollect mergeability.",
    "STALE_HEAD_SHA": "Recollect all evidence for the current head SHA.",
    "MISSING_HUMAN_APPROVAL": "Obtain the required human approval.",
    "SECURITY_POLICY_VIOLATION": "Resolve the security finding and rerun the scan.",
    "DEPENDENCY_POLICY_VIOLATION": "Resolve the dependency finding and rerun the check.",
    "CONCURRENT_FILE_OWNERSHIP": "Confirm a single owner for each changed file.",
    "CONFLICTING_BRANCH_OWNERSHIP": "Resolve the conflicting branch ownership in the task manifest.",
    "BLOCKED_TASK_OWNERSHIP_CONFLICT": "Reassign or release ownership of the blocked task.",
    "INVALID_DEPENDENCY_GRAPH": "Repair the task dependency graph.",
    "DUPLICATE_EVIDENCE": "Remove duplicate evidence records.",
    "UNVERIFIABLE_EVIDENCE": "Provide traceable evidence with source, kind, and reference.",
}


@runtime_checkable
class AdvisoryProvider(Protocol):
    """Caller-supplied local advisory contract; return values remain advisory only."""

    def advise(self, report: Mapping[str, Any]) -> Mapping[str, Any]: ...


class DeterministicAdvisoryProvider:
    """Offline provider that maps authoritative finding codes to guidance."""

    def __init__(self, guidance: Mapping[str, str] | None = None) -> None:
        self._guidance = dict(guidance or _GUIDANCE)

    def advise(self, report: Mapping[str, Any]) -> Mapping[str, Any]:
        findings = report.get("findings")
        codes: list[str] = []
        if isinstance(findings, list):
            for item in findings[:MAX_ADVISORY_ITEMS]:
                if not isinstance(item, Mapping):
                    continue
                code = norm_text(item.get("code"), "finding.code", 120)
                if code:
                    codes.append(code)

        recommendations: list[str] = []
        for code in codes[:MAX_ADVISORY_ITEMS]:
            detail = self._guidance.get(code, "Re-collect verified evidence for this finding.")
            recommendations.append(clip(f"{code}: {detail}", MAX_ADVISORY_ITEM))
        decision = norm_text(report.get("decision"), "report.decision", 80) or "unknown"
        return {"summary": f"Offline advisory for {decision}.", "recommendations": recommendations}


def _provider_callable(provider: Any) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    if provider is None or isinstance(provider, (str, bytes, bytearray, Mapping)):
        raise TypeError("provider must be callable or expose advise()")
    advise = getattr(provider, "advise", None)
    if callable(advise):
        return advise
    if callable(provider):
        return provider
    raise TypeError("provider must be callable or expose advise()")


def _bounded_recommendations(values: Any) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise TypeError("advisory.recommendations must be a list")
    recommendations: list[str] = []
    for item in values[:MAX_ADVISORY_ITEMS]:
        text = norm_text(item, "advisory.recommendation", MAX_ADVISORY_ITEM)
        if text:
            recommendations.append(redact(text))
    return recommendations


def build_advisory(report: Mapping[str, Any], provider: Any | None = None) -> dict[str, Any]:
    """Return a bounded advisory block that cannot override authoritative results."""

    local_provider = DeterministicAdvisoryProvider() if provider is None else provider
    try:
        advise = _provider_callable(local_provider)
        result = advise(redact(report))
        if not isinstance(result, Mapping):
            raise TypeError("advisory result must be an object")
        summary = norm_text(result.get("summary"), "advisory.summary", MAX_STRING)
        return {
            "authoritative": False,
            "engine": OFFLINE_ENGINE if isinstance(local_provider, DeterministicAdvisoryProvider) else LOCAL_ENGINE,
            "summary": redact(summary) if summary else DEFAULT_SUMMARY,
            "recommendations": _bounded_recommendations(result.get("recommendations", [])),
        }
    except Exception as exc:  # noqa: BLE001 - advisory failure must never break the decision
        return {
            "authoritative": False,
            "engine": UNAVAILABLE_ENGINE,
            "summary": UNAVAILABLE_SUMMARY,
            "recommendations": [],
            "provider_error": exc.__class__.__name__,
        }

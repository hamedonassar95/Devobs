"""Optional, non-authoritative advisory interface.

The default engine uses only deterministic advisory text. A caller may inject a
local provider, but its output is summarized, redacted, and never used to change
the decision, findings, evidence registry, or human-approval requirement. This
package makes no outbound API call and enables no paid inference by default.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol, runtime_checkable

from .models import MAX_STRING
from .validation import norm_text, redact

MAX_ADVISORY_ITEMS = 20
MAX_ADVISORY_ITEM = 300


@runtime_checkable
class AdvisoryProvider(Protocol):
    """Caller-supplied advisory contract; all return fields are advisory only."""

    def advise(self, report: Mapping[str, Any]) -> Mapping[str, Any]: ...


class StaticAdvisoryProvider:
    """Deterministic local provider for tests and offline operation."""

    def __init__(self, summary: str, recommendations: list[str] | None = None) -> None:
        self._summary = summary
        self._recommendations = recommendations or []

    def advise(self, report: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"summary": self._summary, "recommendations": list(self._recommendations)}


def _default_advisory() -> dict[str, Any]:
    return {
        "authoritative": False,
        "engine": "deterministic-advisory",
        "summary": "Advisory only; deterministic policy and human approval remain authoritative.",
        "recommendations": [],
    }


def _bounded_recommendations(values: Any) -> list[str]:
    if not isinstance(values, list):
        raise ValueError("advisory.recommendations must be a list")
    recommendations = []
    for item in values[:MAX_ADVISORY_ITEMS]:
        text = norm_text(item, "advisory.recommendation", MAX_ADVISORY_ITEM)
        if text:
            recommendations.append(redact(text))
    return recommendations


def build_advisory(
    report: Mapping[str, Any],
    provider: Any | None = None,
    *,
    deterministic_recommendations: list[str] | None = None,
) -> dict[str, Any]:
    """Return a bounded advisory block that cannot override authoritative results."""

    default = _default_advisory()
    if deterministic_recommendations:
        default["recommendations"] = _bounded_recommendations(deterministic_recommendations)
    if provider is None:
        return default

    safe_report = redact(report)
    try:
        if isinstance(provider, Mapping) or isinstance(provider, str):
            raise ValueError("provider must be callable or expose advise()")
        advise = getattr(provider, "advise", None)
        if callable(advise):
            result = advise(safe_report)
        elif callable(provider):
            result = provider(safe_report)
        else:
            raise ValueError("provider must be callable or expose advise()")
        if not isinstance(result, Mapping):
            raise ValueError("advisory result must be an object")

        summary = norm_text(result.get("summary"), "advisory.summary", MAX_STRING)
        recommendations = _bounded_recommendations(result.get("recommendations", []))
        return {
            "authoritative": False,
            "engine": "optional-advisory-provider",
            "summary": redact(summary) if summary else default["summary"],
            "recommendations": recommendations,
        }
    except Exception as exc:  # noqa: BLE001 - advisory failure must never break the decision
        return {
            "authoritative": False,
            "engine": "optional-advisory-provider",
            "summary": "Advisory provider unavailable; deterministic decision unchanged.",
            "recommendations": [],
            "provider_error": exc.__class__.__name__,
        }

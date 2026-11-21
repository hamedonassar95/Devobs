"""Optional advisory interface that cannot alter deterministic policy."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from .models import POLICY_VERSION
from .security import redact


class AdvisoryProvider(Protocol):
    def assess(self, context: Mapping[str, Any]) -> str: ...


class DisabledAdvisoryProvider:
    def assess(self, context: Mapping[str, Any]) -> str:
        return "AI provider disabled; deterministic evidence only."


def assess_advisory(
    provider: AdvisoryProvider | None,
    *,
    untrusted_text_present: bool,
    finding_codes: tuple[str, ...],
    source_sha: str | None,
) -> dict[str, Any]:
    """Collect bounded advisory text without granting it decision authority."""
    if provider is None:
        return {
            "provider": "disabled",
            "status": "disabled",
            "notes": ["Deterministic policy only."],
            "influenced_decision": False,
        }

    context = {
        "policy_version": POLICY_VERSION,
        "untrusted_text_withheld": bool(untrusted_text_present),
        "finding_codes": sorted(set(finding_codes))[:50],
        "source_sha": source_sha or "unverified",
    }
    try:
        response = provider.assess(context)
    except Exception:  # noqa: BLE001 - advisory failure never changes the verdict.
        return {
            "provider": "injected_advisory",
            "status": "error",
            "notes": [],
            "influenced_decision": False,
        }
    if not isinstance(response, str) or not response.strip():
        return {
            "provider": "injected_advisory",
            "status": "empty",
            "notes": [],
            "influenced_decision": False,
        }
    safe, changed = redact(response, limit=600)
    if changed:
        return {
            "provider": "injected_advisory",
            "status": "discarded",
            "notes": [],
            "influenced_decision": False,
        }
    return {
        "provider": "injected_advisory",
        "status": "accepted",
        "notes": [safe],
        "influenced_decision": False,
    }

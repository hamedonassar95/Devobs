"""Collect repository state and evaluate it in one fail-closed boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .collector import CollectionError, collect_repository_state
from .engine import build_failure_report, evaluate_integration


def evaluate_collected_integration(
    provider: Any,
    request: Mapping[str, Any],
    advisory_provider: Any | None = None,
) -> dict[str, Any]:
    """Collect bounded state from a local provider, then evaluate deterministically.

    Collection failures return a `NEEDS_EVIDENCE` report instead of raising so
    callers always receive an explicit, non-authoritative integration decision.
    """

    try:
        state = collect_repository_state(provider, request)
    except CollectionError as exc:
        return build_failure_report(
            "COLLECTION_UNAVAILABLE",
            str(exc),
            category="collection",
            advisory_provider=advisory_provider,
        )
    return evaluate_integration(state, advisory_provider)

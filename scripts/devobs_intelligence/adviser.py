"""Offline-first incident adviser: never grants authority or invokes tools."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Callable

from .contracts import EventEnvelopeV1


class AdvisoryError(ValueError):
    """Fixed errors that do not expose potentially private incident details."""


@dataclass(frozen=True)
class ProposalV1:
    event_id: str
    source_sha: str
    status: str
    hypothesis: str
    confidence: float
    evidence_digests: tuple[str, ...]
    recommended_tests: tuple[str, ...]
    runbook_ids: tuple[str, ...]
    proposal_digest: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))


_CATEGORIES = frozenset({"ci_failure", "high_error_rate", "capacity_pressure", "unknown"})
_RUNBOOKS = {
    "ci_failure": ("RB-CI-01", "Check the failing CI job and compare the pinned source SHA"),
    "high_error_rate": ("RB-SLO-01", "Check recent error-rate changes against approved SLO windows"),
    "capacity_pressure": ("RB-CAP-01", "Review resource saturation and capacity forecasts without changing resources"),
}


def propose(event: EventEnvelopeV1, signals: dict, *, model: Callable | None = None,
            model_enabled: bool = False, kill_switch: bool = False,
            max_model_calls: int = 1) -> ProposalV1:
    """Generate a bounded advisory report from structured aggregate signals only.

    Any model callback must return one allowed category string. No freeform model
    text or tool call is returned. There is no production provider configured.
    """
    if type(event) is not EventEnvelopeV1:
        raise AdvisoryError("invalid_event")
    if type(signals) is not dict or set(signals) != {"failed_checks", "error_rate_pct", "capacity_pct"}:
        raise AdvisoryError("invalid_signals")
    failures, error_rate, capacity = (signals[k] for k in ("failed_checks", "error_rate_pct", "capacity_pct"))
    if type(failures) is not int or not 0 <= failures <= 1000:
        raise AdvisoryError("invalid_signals")
    if any(type(value) not in (float, int) or not 0 <= value <= 100 for value in (error_rate, capacity)):
        raise AdvisoryError("invalid_signals")
    if type(max_model_calls) is not int or max_model_calls != 1:
        raise AdvisoryError("invalid_budget")
    if kill_switch:
        raise AdvisoryError("kill_switch_enabled")
    category = ("ci_failure" if failures else "high_error_rate" if error_rate >= 5
                else "capacity_pressure" if capacity >= 85 else "unknown")
    if model_enabled:
        if not callable(model):
            raise AdvisoryError("model_unavailable")
        # Deliberately no raw logs, source, runbook body, or credentials.
        safe_inputs = {"failed_checks": failures, "error_rate_pct": float(error_rate),
                       "capacity_pct": float(capacity), "allowed_categories": sorted(_CATEGORIES)}
        try:
            response = model(safe_inputs)
        except Exception:
            raise AdvisoryError("model_failed") from None
        if type(response) is not str or response not in _CATEGORIES:
            raise AdvisoryError("invalid_model_output")
        category = response
    runbook_ids = (_RUNBOOKS[category][0],) if category in _RUNBOOKS else ()
    test_plan = (_RUNBOOKS[category][1],) if category in _RUNBOOKS else ("Gather more verified operational evidence",)
    confidence = 0.55 if category != "unknown" else 0.0  # Heuristic, not calibrated accuracy.
    canonical = {"event_id": event.event_id, "source_sha": event.source_sha,
                 "category": category, "evidence_digests": event.evidence_digests,
                 "runbook_ids": runbook_ids, "recommended_tests": test_plan}
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
    return ProposalV1(event.event_id, event.source_sha, "PENDING_HUMAN_APPROVAL",
                      category, confidence, event.evidence_digests, test_plan,
                      runbook_ids, digest)

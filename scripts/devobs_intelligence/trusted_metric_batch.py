"""Bounded offline metric batch for a separately authenticated collection boundary.

Not a network/OTLP listener. Identity and source SHA must come from a trusted
caller, never from metric resources. Reject the entire batch on any bad value.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .context import ContextError, Telemetry
from .telemetry_adapter import from_trusted_metric

_MAX_BATCH = 32
_MAX_AGE_NS = 900 * 1_000_000_000
_MAX_FUTURE_NS = 60 * 1_000_000_000


def from_trusted_metric_batch(
    metrics: list[dict], *, tenant: str, project: str,
    source_sha: str, now_utc: datetime,
) -> tuple[Telemetry, ...]:
    """Map an atomic snapshot into sorted, bounded, provenance-scoped evidence.

    This offline contract is NOT a collector or proof of sender authentication.
    Caller is responsible for verifying tenant/project/SHA and the clock.
    """
    if (type(metrics) is not list or not 1 <= len(metrics) <= _MAX_BATCH
            or type(now_utc) is not datetime or now_utc.tzinfo is None
            or now_utc.utcoffset() is None):
        raise ContextError("invalid_metric_batch")
    now = now_utc.astimezone(timezone.utc)
    now_ns = int(now.timestamp()) * 1_000_000_000 + now.microsecond * 1000
    seen = set()
    result = []
    for item in metrics:
        point = from_trusted_metric(item, tenant=tenant, project=project,
                                    source_sha=source_sha)
        delta_ns = now_ns - item["time_unix_nano"]
        if not -_MAX_FUTURE_NS <= delta_ns <= _MAX_AGE_NS:
            raise ContextError("stale_evidence")
        identity = (point.service, point.metric)
        if identity in seen:
            raise ContextError("duplicate_evidence")
        seen.add(identity)
        result.append(point)
    return tuple(sorted(result, key=lambda p: (p.service, p.metric)))

"""Convert one trusted numeric OTLP-like metric snapshot, not an OTLP receiver.

The authenticated integration supplies tenant, project and SHA separately.
Never accept those from arbitrary resource attributes or log bodies.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone

from .context import ContextError, normalize_telemetry


def from_trusted_metric(metric: dict, *, tenant: str, project: str,
                        source_sha: str):
    if type(metric) is not dict or set(metric)!={"resource","name","value","time_unix_nano"}:
        raise ContextError("invalid_snapshot")
    resource=metric["resource"]
    if type(resource) is not dict or set(resource)!={"service.name"}:
        raise ContextError("invalid_snapshot")
    stamp=metric["time_unix_nano"]
    if type(stamp) is not int or not 1577836800000000000<=stamp<=4102444800000000000:
        raise ContextError("invalid_snapshot")
    try:
        date=datetime.fromtimestamp(stamp/1_000_000_000,timezone.utc)
    except (OverflowError,OSError,ValueError):
        raise ContextError("invalid_snapshot") from None
    scope={"tenant":tenant,"project":project,"service":resource["service.name"],
           "source_sha":source_sha,"observed_at":date.isoformat(timespec="seconds"),
           "metric":metric["name"],"value":metric["value"]}
    try:
        packed=json.dumps(scope,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    except (TypeError,ValueError):
        raise ContextError("invalid_snapshot") from None
    if len(packed)>2048:
        raise ContextError("invalid_snapshot")
    scope["evidence_digest"]=hashlib.sha256(packed).hexdigest()
    return normalize_telemetry(scope)

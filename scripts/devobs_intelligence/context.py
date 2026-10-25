"""Offline, bounded telemetry and service-topology context. No raw log ingestion."""
from __future__ import annotations
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone

_ID=re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_SHA=re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_DIGEST=re.compile(r"[0-9a-f]{64}\Z")
_METRICS={"error_rate_pct","capacity_pct","failed_checks"}


class ContextError(ValueError):
    """Fixed, non-sensitive validation code."""


def _id(v):
    return type(v) is str and _ID.fullmatch(v) is not None


@dataclass(frozen=True)
class Telemetry:
    tenant: str
    project: str
    service: str
    source_sha: str
    observed_at: str
    metric: str
    value: float
    evidence_digest: str


def normalize_telemetry(data: dict) -> Telemetry:
    keys={"tenant","project","service","source_sha","observed_at",
          "metric","value","evidence_digest"}
    if type(data) is not dict or set(data)!=keys:
        raise ContextError("invalid_fields")
    if not all(_id(data[k]) for k in ("tenant","project","service")):
        raise ContextError("invalid_scope")
    if (type(data["source_sha"]) is not str or _SHA.fullmatch(data["source_sha"]) is None
            or type(data["evidence_digest"]) is not str
            or _DIGEST.fullmatch(data["evidence_digest"]) is None):
        raise ContextError("invalid_evidence")
    metric,value=data["metric"],data["value"]
    if type(metric) is not str or metric not in _METRICS:
        raise ContextError("invalid_metric")
    if type(value) not in (int,float) or not math.isfinite(value):
        raise ContextError("invalid_value")
    if metric!="failed_checks" and not 0<=value<=100:
        raise ContextError("invalid_value")
    if metric=="failed_checks" and (type(value) is not int or not 0<=value<=1000):
        raise ContextError("invalid_value")
    stamp=data["observed_at"]
    try:
        if type(stamp) is not str or len(stamp)>35:
            raise ValueError
        dt=datetime.fromisoformat(stamp.replace("Z","+00:00"))
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError
        stamp=dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
    except ValueError:
        raise ContextError("invalid_timestamp") from None
    return Telemetry(data["tenant"],data["project"],data["service"],data["source_sha"],
                     stamp,metric,value if metric=="failed_checks" else float(value),data["evidence_digest"])


class ServiceTopology:
    """(A,B) means A depends on B; cycles are bounded by a visited set."""
    def __init__(self, tenant: str, project: str, services: list[str],
                 edges: list[tuple[str,str]]):
        if (not _id(tenant) or not _id(project) or type(services) is not list
                or not 1<=len(services)<=100 or any(not _id(s) for s in services)
                or len(set(services))!=len(services)
                or type(edges) is not list or len(edges)>500):
            raise ContextError("invalid_topology")
        existing=set()
        for edge in edges:
            if (type(edge) is not tuple or len(edge)!=2 or
                    edge[0] not in services or edge[1] not in services or
                    edge[0]==edge[1] or edge in existing):
                raise ContextError("invalid_edge")
            existing.add(edge)
        self.tenant,self.project=tenant,project
        self.services=frozenset(services)
        self.edges=frozenset(existing)

    def affected_by(self, service: str, depth: int=3) -> tuple[str,...]:
        if (not _id(service) or service not in self.services or
                type(depth) is not int or not 0<=depth<=5):
            raise ContextError("invalid_query")
        affected={service}
        frontier={service}
        for _ in range(depth):
            new={a for a,b in self.edges if b in frontier}-affected
            affected|=new
            frontier=new
        return tuple(sorted(affected))

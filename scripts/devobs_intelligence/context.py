"""Offline, bounded telemetry and service-topology context. No raw log ingestion."""
from __future__ import annotations
import math
import re
import hashlib
import json
from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class ServiceTopologySnapshot:
    """Offline topology bound to a tenant, project, source revision and capture time.

    ``snapshot_digest`` detects content changes; it is not a signature and does not
    authenticate the collector or prove that the graph came from the named source.
    """

    tenant: str
    project: str
    services: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]
    source_sha: str
    captured_at: str
    snapshot_digest: str
    _topology: ServiceTopology = field(repr=False, compare=False)

    def __init__(self, tenant: str, project: str, services: list[str],
                 edges: list[tuple[str, str]], source_sha: str, captured_at: str):
        if (type(source_sha) is not str or _SHA.fullmatch(source_sha) is None):
            raise ContextError("invalid_evidence")
        try:
            if type(captured_at) is not str or len(captured_at) > 35:
                raise ValueError
            instant = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
            if instant.tzinfo is None or instant.utcoffset() is None:
                raise ValueError
            normalized_time = instant.astimezone(timezone.utc).isoformat(
                timespec="microseconds").replace("+00:00", "Z")
        except ValueError:
            raise ContextError("invalid_timestamp") from None

        topology = ServiceTopology(tenant, project, services, edges)
        normalized_services = tuple(sorted(topology.services))
        normalized_edges = tuple(sorted(topology.edges))
        canonical = {
            "schema_version": 1,
            "tenant": tenant,
            "project": project,
            "source_sha": source_sha,
            "captured_at": normalized_time,
            "services": list(normalized_services),
            "edges": [list(edge) for edge in normalized_edges],
        }
        digest = hashlib.sha256(json.dumps(
            canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")).hexdigest()
        object.__setattr__(self, "tenant", tenant)
        object.__setattr__(self, "project", project)
        object.__setattr__(self, "services", normalized_services)
        object.__setattr__(self, "edges", normalized_edges)
        object.__setattr__(self, "source_sha", source_sha)
        object.__setattr__(self, "captured_at", normalized_time)
        object.__setattr__(self, "snapshot_digest", digest)
        object.__setattr__(self, "_topology", topology)

    def to_record(self) -> dict:
        """Return a detached, JSON-compatible versioned snapshot record."""
        return {
            "schema_version": 1,
            "tenant": self.tenant,
            "project": self.project,
            "services": list(self.services),
            "edges": [list(edge) for edge in self.edges],
            "source_sha": self.source_sha,
            "captured_at": self.captured_at,
            "snapshot_digest": self.snapshot_digest,
        }

    @classmethod
    def from_record(cls, record: dict) -> ServiceTopologySnapshot:
        """Parse one strict JSON-compatible record and verify its content digest."""
        fields = {
            "schema_version", "tenant", "project", "services", "edges",
            "source_sha", "captured_at", "snapshot_digest",
        }
        if type(record) is not dict or set(record) != fields:
            raise ContextError("invalid_snapshot_record")
        if type(record["schema_version"]) is not int or record["schema_version"] != 1:
            raise ContextError("unsupported_snapshot_schema")
        if (type(record["services"]) is not list
                or type(record["edges"]) is not list
                or any(type(edge) is not list or len(edge) != 2 for edge in record["edges"])):
            raise ContextError("invalid_snapshot_record")
        try:
            snapshot = cls(
                record["tenant"], record["project"], record["services"],
                [tuple(edge) for edge in record["edges"]],
                record["source_sha"], record["captured_at"],
            )
        except (ContextError, TypeError, ValueError):
            raise ContextError("invalid_snapshot_record") from None
        if (type(record["snapshot_digest"]) is not str
                or snapshot.snapshot_digest != record["snapshot_digest"]):
            raise ContextError("snapshot_digest_mismatch")
        return snapshot

    def validate(self, tenant: str, project: str, *, now: datetime,
                 max_age_seconds: int = 900) -> None:
        """Require an exact scope match and a fresh, timezone-aware snapshot."""
        if (not _id(tenant) or not _id(project)
                or type(now) is not datetime or now.tzinfo is None
                or now.utcoffset() is None or type(max_age_seconds) is not int
                or not 1 <= max_age_seconds <= 86_400):
            raise ContextError("invalid_query")
        if (tenant, project) != (self.tenant, self.project):
            raise ContextError("scope_mismatch")
        age_seconds = (now.astimezone(timezone.utc)
                       - datetime.fromisoformat(self.captured_at.replace("Z", "+00:00")))
        if age_seconds.total_seconds() < 0 or age_seconds.total_seconds() > max_age_seconds:
            raise ContextError("stale_topology")

    def affected_by(self, tenant: str, project: str, service: str, *,
                    now: datetime, max_age_seconds: int = 900,
                    depth: int = 3) -> tuple[str, ...]:
        self.validate(tenant, project, now=now, max_age_seconds=max_age_seconds)
        if not _id(service) or type(depth) is not int or not 0 <= depth <= 5:
            raise ContextError("invalid_query")
        return self._topology.affected_by(service, depth)

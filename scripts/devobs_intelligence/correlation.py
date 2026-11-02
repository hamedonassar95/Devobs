"""Offline incident correlation; bounded numerical evidence and read-only findings."""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from .adviser import propose
from .context import (
    ContextError, ServiceTopology, ServiceTopologySnapshot, Telemetry,
    normalize_telemetry,
)
from .contracts import parse_event
from .incident_memory import IncidentMemory, IncidentMemoryEvidence


@dataclass(frozen=True)
class IncidentFinding:
    status: str
    category: str
    ranked_services: tuple[str, ...]
    impacted_services: tuple[str, ...]
    evidence_digests: tuple[str, ...]
    runbook_ids: tuple[str, ...]
    source_sha: str
    model_used: bool
    calibrated: bool
    topology_snapshot_digest: str | None = None
    topology_captured_at: str | None = None
    memory_provenance: tuple[IncidentMemoryEvidence, ...] = ()


def _revalidate_snapshot(value: ServiceTopologySnapshot) -> ServiceTopologySnapshot:
    """Rebuild from public fields; never trust a dataclass instance's cached graph."""
    try:
        snapshot = ServiceTopologySnapshot(
            value.tenant, value.project, list(value.services), list(value.edges),
            value.source_sha, value.captured_at,
        )
        if (type(value.snapshot_digest) is not str
                or snapshot.snapshot_digest != value.snapshot_digest):
            raise ContextError("invalid_topology_snapshot")
        return snapshot
    except (AttributeError, TypeError, ContextError):
        raise ContextError("invalid_topology_snapshot") from None


def correlate(topology: ServiceTopology | ServiceTopologySnapshot,
              telemetry: list[Telemetry],
              memory: IncidentMemory, now_utc: datetime, *,
              memory_max_age_seconds: int | None = None) -> IncidentFinding:
    """Fail closed on stale, mismatched or ambiguous evidence.

    Rank is a deterministic heuristic; not a causal proof or model confidence.
    """
    snapshot = None
    if type(topology) is ServiceTopologySnapshot:
        snapshot = _revalidate_snapshot(topology)
        topology = snapshot
    if (type(topology) not in (ServiceTopology, ServiceTopologySnapshot)
            or type(memory) is not IncidentMemory
            or type(telemetry) is not list or not 1<=len(telemetry)<=32
            or type(now_utc) is not datetime or now_utc.tzinfo is None
            or now_utc.utcoffset() is None):
        raise ContextError("invalid_incident")
    if (memory_max_age_seconds is not None
            and (type(memory_max_age_seconds) is not int
                 or not 1<=memory_max_age_seconds<=31_536_000)):
        raise ContextError("invalid_query")
    now=now_utc.astimezone(timezone.utc)
    if snapshot is not None:
        snapshot.validate(snapshot.tenant, snapshot.project, now=now)
    sha=None
    seen=set()
    scores={}
    per_service={}
    evidence=set()
    for point in telemetry:
        if type(point) is not Telemetry:
            raise ContextError("invalid_incident_scope")
        # Revalidate dataclass instances too: a direct constructor is NOT an
        # authentication or schema-validation boundary.
        point=normalize_telemetry({
            "tenant":point.tenant,"project":point.project,"service":point.service,
            "source_sha":point.source_sha,"observed_at":point.observed_at,
            "metric":point.metric,"value":point.value,
            "evidence_digest":point.evidence_digest})
        if (
                (point.tenant,point.project)!=(topology.tenant,topology.project)
                or point.service not in topology.services):
            raise ContextError("invalid_incident_scope")
        if sha is not None and sha!=point.source_sha:
            raise ContextError("mixed_source_sha")
        sha=point.source_sha
        timestamp=datetime.fromisoformat(point.observed_at.replace("Z","+00:00"))
        age=(now-timestamp).total_seconds()
        if not -60<=age<=900:
            raise ContextError("stale_evidence")
        key=(point.service,point.metric)
        if key in seen or point.evidence_digest in evidence:
            raise ContextError("duplicate_evidence")
        seen.add(key)
        evidence.add(point.evidence_digest)
        per_service.setdefault(point.service,{})[point.metric]=point.value
    if snapshot is not None and sha != snapshot.source_sha:
        raise ContextError("topology_source_sha_mismatch")
    for service,values in per_service.items():
        scores[service]=(3 if values.get("failed_checks",0)>0 else 0)+(
            2 if values.get("error_rate_pct",0)>=5 else 0)+(
            1 if values.get("capacity_pct",0)>=85 else 0)
    eligible=sorted((s for s in scores if scores[s]>0),key=lambda s:(-scores[s],s))
    if not eligible:
        return IncidentFinding("INSUFFICIENT_EVIDENCE","unknown",(),(),
                               tuple(sorted(evidence)),(),sha,False,False,
                               snapshot.snapshot_digest if snapshot is not None else None,
                               snapshot.captured_at if snapshot is not None else None)
    root=eligible[0]
    values=per_service[root]
    data={"failed_checks":int(values.get("failed_checks",0)),
          "error_rate_pct":float(values.get("error_rate_pct",0)),
          "capacity_pct":float(values.get("capacity_pct",0))}
    digest=hashlib.sha256(json.dumps({"sha":sha,"evidence":sorted(evidence)},
                        sort_keys=True).encode()).hexdigest()
    event=parse_event({"schema_version":1,"event_id":"correlation-"+digest[:32],
                       "provider":"github","project_ref":topology.project,
                       "source_sha":sha,"kind":"incident",
                       "observed_at":now.isoformat(timespec="seconds").replace("+00:00","Z"),
                       "evidence_digests":sorted(evidence)})
    recommendation=propose(event,data,model_enabled=False)
    if snapshot is None:
        safe_memory=memory.retrieve(topology.tenant,topology.project,root,
                                    recommendation.hypothesis)
    elif memory_max_age_seconds is None:
        # Legacy memory records have no source/time provenance; do not use them
        # with provenance-bound topology unless the caller supplies an age policy.
        safe_memory=()
    else:
        safe_memory=memory.retrieve_provenanced(
            topology.tenant,topology.project,root,recommendation.hypothesis,
            now=now,max_age_seconds=memory_max_age_seconds,
            require_approval=True)
    memory_provenance = []
    if snapshot is not None and memory_max_age_seconds is not None:
        for row in safe_memory:
            approval = memory.approval_provenance_for(row)
            memory_provenance.append(IncidentMemoryEvidence(
                row.evidence_digest, row.record_digest, row.source_sha,
                row.recorded_at,
                approval.approval_id if approval is not None else None,
                approval.approver_id if approval is not None else None,
                approval.approval_digest if approval is not None else None,
            ))
    memory_provenance = tuple(memory_provenance)
    impacted=(snapshot.affected_by(topology.tenant, topology.project, root, now=now)
              if snapshot is not None else topology.affected_by(root))
    return IncidentFinding("PENDING_HUMAN_APPROVAL",recommendation.hypothesis,
                           tuple(eligible[:3]),impacted,
                           tuple(sorted(evidence)),
                           tuple(sorted({r.runbook_id for r in safe_memory})),
                           sha,False,False,
                           snapshot.snapshot_digest if snapshot is not None else None,
                           snapshot.captured_at if snapshot is not None else None,
                           memory_provenance)

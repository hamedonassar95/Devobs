"""Offline incident correlation; bounded numerical evidence and read-only findings."""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from .adviser import propose
from .context import ContextError, ServiceTopology, Telemetry
from .contracts import parse_event
from .incident_memory import IncidentMemory


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


def correlate(topology: ServiceTopology, telemetry: list[Telemetry],
              memory: IncidentMemory, now_utc: datetime) -> IncidentFinding:
    """Fail closed on stale, mismatched or ambiguous evidence.

    Rank is a deterministic heuristic; not a causal proof or model confidence.
    """
    if (type(topology) is not ServiceTopology or type(memory) is not IncidentMemory
            or type(telemetry) is not list or not 1<=len(telemetry)<=32
            or type(now_utc) is not datetime or now_utc.tzinfo is None):
        raise ContextError("invalid_incident")
    now=now_utc.astimezone(timezone.utc)
    sha=None
    seen=set()
    scores={}
    per_service={}
    evidence=set()
    for point in telemetry:
        if (type(point) is not Telemetry or
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
    for service,values in per_service.items():
        scores[service]=(3 if values.get("failed_checks",0)>0 else 0)+(
            2 if values.get("error_rate_pct",0)>=5 else 0)+(
            1 if values.get("capacity_pct",0)>=85 else 0)
    eligible=sorted((s for s in scores if scores[s]>0),key=lambda s:(-scores[s],s))
    if not eligible:
        return IncidentFinding("INSUFFICIENT_EVIDENCE","unknown",(),(),
                               tuple(sorted(evidence)),(),sha,False,False)
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
    safe_memory=memory.retrieve(topology.tenant,topology.project,root,
                                recommendation.hypothesis)
    return IncidentFinding("PENDING_HUMAN_APPROVAL",recommendation.hypothesis,
                           tuple(eligible[:3]),topology.affected_by(root),
                           tuple(sorted(evidence)),
                           tuple(sorted({r.runbook_id for r in safe_memory})),
                           sha,False,False)

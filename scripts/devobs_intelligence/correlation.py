"""Offline incident correlation; bounded numerical evidence and read-only findings."""
from __future__ import annotations
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from .adviser import propose
from .context import (
    ContextError, ServiceTopology, ServiceTopologySnapshot, Telemetry,
    normalize_telemetry,
)
from .contracts import parse_event
from .incident_memory import IncidentMemory, IncidentMemoryEvidence

_FINDING_VERSION = 2
_RANKING_INTERPRETATION = "fixed_heuristic_not_causal"
_RANKING_RULES = {
    "failed_checks_positive": ("failed_checks", 3),
    "error_rate_threshold_met": ("error_rate_pct", 2),
    "capacity_threshold_met": ("capacity_pct", 1),
}
_RANKING_SIGNAL_ORDER = {
    "failed_checks": 0, "error_rate_pct": 1, "capacity_pct": 2,
}
_RANKING_CATEGORY = {
    "failed_checks": "ci_failure",
    "error_rate_pct": "high_error_rate",
    "capacity_pct": "capacity_pressure",
}
_RANKED_SERVICE_FIELDS = frozenset({"service", "rank", "score", "signals"})
_RANKING_SIGNAL_FIELDS = frozenset({"metric", "reason_code", "points", "evidence_digest"})
_FINDING_FIELDS = frozenset({
    "schema_version", "tenant", "project", "status", "category",
    "ranked_services", "ranked_service_evidence", "ranking_interpretation",
    "impacted_services", "evidence_digests", "runbook_ids",
    "source_sha", "model_used", "calibrated",
    "topology_snapshot_digest", "topology_captured_at", "memory_provenance",
    "finding_digest",
})
_MEMORY_EVIDENCE_FIELDS = frozenset({
    "evidence_digest", "record_digest", "source_sha", "recorded_at",
    "approval_id", "approver_id", "approval_digest",
})
_FINDING_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_FINDING_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_FINDING_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_APPROVAL_ID = re.compile(r"[0-9a-f]{32}\Z")
_RUNBOOK_ID = re.compile(r"RB-[A-Z]{2,8}-[0-9]{2}\Z")
_FINDING_STATUSES = frozenset({"INSUFFICIENT_EVIDENCE", "PENDING_HUMAN_APPROVAL"})
_FINDING_CATEGORIES = frozenset({
    "unknown", "ci_failure", "high_error_rate", "capacity_pressure",
})


def _finding_canonical_json(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _finding_timestamp(value: object) -> bool:
    if type(value) is not str or len(value) > 35:
        return False
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if instant.tzinfo is None or instant.utcoffset() is None:
            return False
        canonical = instant.astimezone(timezone.utc).isoformat(
            timespec="microseconds").replace("+00:00", "Z")
    except (ValueError, OverflowError):
        return False
    return value == canonical


@dataclass(frozen=True)
class RankingSignal:
    metric: str
    reason_code: str
    points: int
    evidence_digest: str


@dataclass(frozen=True)
class RankedServiceEvidence:
    service: str
    rank: int
    score: int
    signals: tuple[RankingSignal, ...]


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
    tenant: str | None = None
    project: str | None = None
    ranked_service_evidence: tuple[RankedServiceEvidence, ...] = ()
    ranking_interpretation: str = _RANKING_INTERPRETATION

    def to_record(self) -> dict:
        """Return a strict JSON-compatible v2 record with an integrity digest."""
        try:
            memory = [{
                "evidence_digest": item.evidence_digest,
                "record_digest": item.record_digest,
                "source_sha": item.source_sha,
                "recorded_at": item.recorded_at,
                "approval_id": item.approval_id,
                "approver_id": item.approver_id,
                "approval_digest": item.approval_digest,
            } for item in self.memory_provenance]
            payload = {
                "schema_version": _FINDING_VERSION,
                "tenant": self.tenant,
                "project": self.project,
                "status": self.status,
                "category": self.category,
                "ranked_services": list(self.ranked_services),
                "ranked_service_evidence": [{
                    "service": item.service,
                    "rank": item.rank,
                    "score": item.score,
                    "signals": [{
                        "metric": signal.metric,
                        "reason_code": signal.reason_code,
                        "points": signal.points,
                        "evidence_digest": signal.evidence_digest,
                    } for signal in item.signals],
                } for item in self.ranked_service_evidence],
                "ranking_interpretation": self.ranking_interpretation,
                "impacted_services": list(self.impacted_services),
                "evidence_digests": list(self.evidence_digests),
                "runbook_ids": list(self.runbook_ids),
                "source_sha": self.source_sha,
                "model_used": self.model_used,
                "calibrated": self.calibrated,
                "topology_snapshot_digest": self.topology_snapshot_digest,
                "topology_captured_at": self.topology_captured_at,
                "memory_provenance": memory,
            }
            digest = hashlib.sha256(_finding_canonical_json(payload)).hexdigest()
        except (AttributeError, TypeError, ValueError, OverflowError):
            raise ContextError("invalid_incident_finding") from None
        record = {**payload, "finding_digest": digest}
        type(self).from_record(record)
        return record

    @classmethod
    def from_record(cls, record: dict) -> "IncidentFinding":
        """Parse one exact v2 result record and check ranking evidence and digest."""
        if type(record) is not dict or set(record) != _FINDING_FIELDS:
            raise ContextError("invalid_incident_finding_record")
        if (type(record["schema_version"]) is not int
                or record["schema_version"] != _FINDING_VERSION):
            raise ContextError("unsupported_incident_finding_schema")
        if (type(record["tenant"]) is not str
                or _FINDING_ID.fullmatch(record["tenant"]) is None
                or type(record["project"]) is not str
                or _FINDING_ID.fullmatch(record["project"]) is None
                or type(record["status"]) is not str
                or record["status"] not in _FINDING_STATUSES
                or type(record["category"]) is not str
                or record["category"] not in _FINDING_CATEGORIES
                or type(record["source_sha"]) is not str
                or _FINDING_SHA.fullmatch(record["source_sha"]) is None
                or type(record["model_used"]) is not bool
                or type(record["calibrated"]) is not bool):
            raise ContextError("invalid_incident_finding")

        has_root = record["status"] == "PENDING_HUMAN_APPROVAL"
        limits = {
            "ranked_services": (1 if has_root else 0, 3),
            "impacted_services": (1 if has_root else 0, 100),
            "evidence_digests": (1, 32),
            "runbook_ids": (0, 3),
        }
        sequences = {}
        for name, (minimum, maximum) in limits.items():
            value = record[name]
            if (type(value) is not list or len(value) < minimum
                    or len(value) > maximum or any(
                        type(item) is not str for item in value)):
                raise ContextError("invalid_incident_finding")
            if len(set(value)) != len(value):
                raise ContextError("duplicate_incident_finding_value")
            sequences[name] = tuple(value)

        if (any(_FINDING_ID.fullmatch(value) is None
                for value in sequences["ranked_services"] + sequences["impacted_services"])
                or any(_FINDING_DIGEST.fullmatch(value) is None
                       for value in sequences["evidence_digests"])
                or any(_RUNBOOK_ID.fullmatch(value) is None
                       for value in sequences["runbook_ids"])):
            raise ContextError("invalid_incident_finding")

        ranking_value = record["ranked_service_evidence"]
        if (record["ranking_interpretation"] != _RANKING_INTERPRETATION
                or type(ranking_value) is not list or len(ranking_value) > 3):
            raise ContextError("invalid_incident_finding_ranking")
        evidence_set = set(sequences["evidence_digests"])
        ranking = []
        rank_keys = []
        used_signal_evidence = set()
        for expected_rank, item in enumerate(ranking_value, start=1):
            if type(item) is not dict or set(item) != _RANKED_SERVICE_FIELDS:
                raise ContextError("invalid_incident_finding_ranking")
            if (type(item["service"]) is not str
                    or _FINDING_ID.fullmatch(item["service"]) is None
                    or type(item["rank"]) is not int or item["rank"] != expected_rank
                    or type(item["score"]) is not int or not 1 <= item["score"] <= 6
                    or type(item["signals"]) is not list
                    or not 1 <= len(item["signals"]) <= 3):
                raise ContextError("invalid_incident_finding_ranking")
            signals = []
            seen_metrics = set()
            previous_order = -1
            for signal in item["signals"]:
                if (type(signal) is not dict
                        or set(signal) != _RANKING_SIGNAL_FIELDS
                        or type(signal["metric"]) is not str
                        or type(signal["reason_code"]) is not str
                        or type(signal["points"]) is not int
                        or type(signal["evidence_digest"]) is not str):
                    raise ContextError("invalid_incident_finding_ranking")
                rule = _RANKING_RULES.get(signal["reason_code"])
                if (rule is None or rule != (signal["metric"], signal["points"])
                        or signal["metric"] in seen_metrics
                        or _RANKING_SIGNAL_ORDER[signal["metric"]] <= previous_order
                        or _FINDING_DIGEST.fullmatch(signal["evidence_digest"]) is None
                        or signal["evidence_digest"] not in evidence_set
                        or signal["evidence_digest"] in used_signal_evidence):
                    raise ContextError("invalid_incident_finding_ranking")
                seen_metrics.add(signal["metric"])
                used_signal_evidence.add(signal["evidence_digest"])
                previous_order = _RANKING_SIGNAL_ORDER[signal["metric"]]
                signals.append(RankingSignal(**signal))
            if sum(signal.points for signal in signals) != item["score"]:
                raise ContextError("invalid_incident_finding_ranking")
            rank_keys.append((-item["score"], item["service"]))
            ranking.append(RankedServiceEvidence(
                item["service"], item["rank"], item["score"], tuple(signals)))
        if (tuple(item.service for item in ranking) != sequences["ranked_services"]
                or rank_keys != sorted(rank_keys)):
            raise ContextError("invalid_incident_finding_ranking")
        if record["status"] == "INSUFFICIENT_EVIDENCE":
            if ranking:
                raise ContextError("invalid_incident_finding_ranking")
        elif (not ranking
                or _RANKING_CATEGORY[ranking[0].signals[0].metric] != record["category"]):
            raise ContextError("invalid_incident_finding_ranking")

        snapshot_digest = record["topology_snapshot_digest"]
        snapshot_time = record["topology_captured_at"]
        if ((snapshot_digest is None) != (snapshot_time is None)
                or (snapshot_digest is not None
                    and (type(snapshot_digest) is not str
                         or _FINDING_DIGEST.fullmatch(snapshot_digest) is None
                         or not _finding_timestamp(snapshot_time)))):
            raise ContextError("invalid_incident_finding_provenance")

        memory_value = record["memory_provenance"]
        if type(memory_value) is not list or len(memory_value) > 5:
            raise ContextError("invalid_incident_finding_provenance")
        if memory_value and snapshot_digest is None:
            raise ContextError("invalid_incident_finding_provenance")
        memory = []
        memory_ids = set()
        for item in memory_value:
            if (type(item) is not dict or set(item) != _MEMORY_EVIDENCE_FIELDS
                    or any(type(item[key]) is not str for key in _MEMORY_EVIDENCE_FIELDS)):
                raise ContextError("invalid_incident_finding_provenance")
            if (any(_FINDING_DIGEST.fullmatch(item[key]) is None for key in
                    ("evidence_digest", "record_digest", "approval_digest"))
                    or _FINDING_SHA.fullmatch(item["source_sha"]) is None
                    or not _finding_timestamp(item["recorded_at"])
                    or _APPROVAL_ID.fullmatch(item["approval_id"]) is None
                    or _FINDING_ID.fullmatch(item["approver_id"]) is None
                    or item["evidence_digest"] in memory_ids):
                raise ContextError("invalid_incident_finding_provenance")
            memory_ids.add(item["evidence_digest"])
            memory.append(IncidentMemoryEvidence(**item))

        if record["status"] == "INSUFFICIENT_EVIDENCE":
            if (record["category"] != "unknown" or sequences["ranked_services"]
                    or sequences["impacted_services"] or sequences["runbook_ids"]
                    or memory):
                raise ContextError("invalid_incident_finding")

        payload = {key: record[key] for key in _FINDING_FIELDS - {"finding_digest"}}
        if (type(record["finding_digest"]) is not str
                or _FINDING_DIGEST.fullmatch(record["finding_digest"]) is None):
            raise ContextError("invalid_incident_finding_digest")
        try:
            expected = hashlib.sha256(_finding_canonical_json(payload)).hexdigest()
        except (TypeError, ValueError, OverflowError):
            raise ContextError("invalid_incident_finding_record") from None
        if expected != record["finding_digest"]:
            raise ContextError("incident_finding_digest_mismatch")

        return cls(
            status=record["status"], category=record["category"],
            ranked_services=sequences["ranked_services"],
            impacted_services=sequences["impacted_services"],
            evidence_digests=sequences["evidence_digests"],
            runbook_ids=sequences["runbook_ids"], source_sha=record["source_sha"],
            model_used=record["model_used"], calibrated=record["calibrated"],
            topology_snapshot_digest=snapshot_digest,
            topology_captured_at=snapshot_time,
            memory_provenance=tuple(memory), tenant=record["tenant"],
            project=record["project"],
            ranked_service_evidence=tuple(ranking),
            ranking_interpretation=record["ranking_interpretation"],
        )


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
    per_service_evidence={}
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
        per_service_evidence.setdefault(point.service,{})[point.metric]=point.evidence_digest
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
                               snapshot.captured_at if snapshot is not None else None,
                               tenant=topology.tenant, project=topology.project)
    ranked_service_evidence = []
    for rank, service in enumerate(eligible[:3], start=1):
        values = per_service[service]
        source_evidence = per_service_evidence[service]
        signals = []
        if values.get("failed_checks", 0) > 0:
            signals.append(RankingSignal(
                "failed_checks", "failed_checks_positive", 3,
                source_evidence["failed_checks"]))
        if values.get("error_rate_pct", 0) >= 5:
            signals.append(RankingSignal(
                "error_rate_pct", "error_rate_threshold_met", 2,
                source_evidence["error_rate_pct"]))
        if values.get("capacity_pct", 0) >= 85:
            signals.append(RankingSignal(
                "capacity_pct", "capacity_threshold_met", 1,
                source_evidence["capacity_pct"]))
        ranked_service_evidence.append(RankedServiceEvidence(
            service, rank, scores[service], tuple(signals)))
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
                           memory_provenance,tenant=topology.tenant,
                           project=topology.project,
                           ranked_service_evidence=tuple(ranked_service_evidence))

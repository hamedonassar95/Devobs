"""Tenant/project exact-match, metadata-only incident memory; no embeddings."""
from __future__ import annotations
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from .context import ContextError, _id

if TYPE_CHECKING:
    from .incident_memory_approval import VerifiedIncidentMemoryApproval

_DIGEST=re.compile(r"[0-9a-f]{64}\Z")
_SHA=re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_RUNBOOK=re.compile(r"RB-[A-Z]{2,8}-[0-9]{2}\Z")
_CATEGORIES=frozenset({"ci_failure","high_error_rate","capacity_pressure"})
_RECORD_FIELDS=frozenset({
    "tenant", "project", "service", "category", "runbook_id", "outcome",
    "evidence_digest", "source_sha", "recorded_at",
})
_RECORD_SCHEMA_VERSION=1
_BUNDLE_SCHEMA_VERSION=1
_MAX_MEMORY_RECORDS=1000
_BUNDLE_FIELDS=frozenset({"schema_version", "records", "bundle_digest"})


def _canonical_json(value) -> bytes:
    return json.dumps(value,sort_keys=True,separators=(",", ":"),
                      ensure_ascii=False,allow_nan=False).encode("utf-8")


@dataclass(frozen=True)
class IncidentRecord:
    tenant: str
    project: str
    service: str
    category: str
    runbook_id: str
    outcome: str
    evidence_digest: str
    source_sha: str | None = None
    recorded_at: str | None = None

    def __post_init__(self):
        if (not all(_id(v) for v in (self.tenant,self.project,self.service))
                or type(self.category) is not str or self.category not in _CATEGORIES
                or type(self.runbook_id) is not str or _RUNBOOK.fullmatch(self.runbook_id) is None
                or type(self.outcome) is not str or self.outcome not in {"resolved","unresolved","false_positive"}
                or type(self.evidence_digest) is not str
                or _DIGEST.fullmatch(self.evidence_digest) is None):
            raise ContextError("invalid_memory")
        if self.source_sha is None and self.recorded_at is None:
            return
        if type(self.source_sha) is not str or _SHA.fullmatch(self.source_sha) is None:
            raise ContextError("invalid_memory")
        try:
            if type(self.recorded_at) is not str or len(self.recorded_at) > 35:
                raise ValueError
            instant = datetime.fromisoformat(self.recorded_at.replace("Z", "+00:00"))
            if instant.tzinfo is None or instant.utcoffset() is None:
                raise ValueError
            normalized = instant.astimezone(timezone.utc).isoformat(
                timespec="microseconds").replace("+00:00", "Z")
        except ValueError:
            raise ContextError("invalid_memory") from None
        object.__setattr__(self, "recorded_at", normalized)

    def to_record(self) -> dict:
        """Return a detached v1 JSON object with a content-integrity digest."""
        validated = IncidentRecord(
            self.tenant, self.project, self.service, self.category,
            self.runbook_id, self.outcome, self.evidence_digest,
            self.source_sha, self.recorded_at,
        )
        payload = {
            "schema_version": _RECORD_SCHEMA_VERSION,
            "tenant": validated.tenant,
            "project": validated.project,
            "service": validated.service,
            "category": validated.category,
            "runbook_id": validated.runbook_id,
            "outcome": validated.outcome,
            "evidence_digest": validated.evidence_digest,
            "source_sha": validated.source_sha,
            "recorded_at": validated.recorded_at,
        }
        payload["record_digest"] = hashlib.sha256(_canonical_json(payload)).hexdigest()
        return payload

    @property
    def record_digest(self) -> str:
        return self.to_record()["record_digest"]

    @classmethod
    def from_record(cls, value: dict) -> "IncidentRecord":
        """Parse only the exact v1 wire shape and verify its canonical digest."""
        if type(value) is not dict or set(value) != _RECORD_FIELDS | {
                "schema_version", "record_digest"}:
            raise ContextError("invalid_memory_record")
        if (type(value["schema_version"]) is not int
                or value["schema_version"] != _RECORD_SCHEMA_VERSION):
            raise ContextError("unsupported_memory_record")
        try:
            record = cls(
                value["tenant"], value["project"], value["service"],
                value["category"], value["runbook_id"], value["outcome"],
                value["evidence_digest"], value["source_sha"], value["recorded_at"],
            )
        except (TypeError, ContextError):
            raise ContextError("invalid_memory_record") from None
        expected = record.to_record()
        if (type(value["record_digest"]) is not str
                or value["record_digest"] != expected["record_digest"]):
            raise ContextError("memory_record_digest_mismatch")
        return record


@dataclass(frozen=True)
class IncidentMemoryEvidence:
    """Minimal provenance returned when a fresh memory item informs a finding."""

    evidence_digest: str
    record_digest: str
    source_sha: str
    recorded_at: str
    approval_id: str | None = None
    approver_id: str | None = None
    approval_digest: str | None = None


class IncidentMemory:
    """Only pre-reviewed resolved records; reject duplicate scoped evidence."""
    def __init__(self, records: list[IncidentRecord]):
        if (type(records) is not list or len(records)>_MAX_MEMORY_RECORDS
                or any(type(item) is not IncidentRecord for item in records)):
            raise ContextError("invalid_memory")
        rows=tuple(self._copy_record(item) for item in records)
        ids={(r.tenant,r.project,r.evidence_digest) for r in rows}
        if len(ids)!=len(records):
            raise ContextError("duplicate_memory")
        self._rows=rows
        self._approval_provenance = {}

    @classmethod
    def from_approved_envelopes(
            cls, envelopes: list[dict],
            trusted_public_keys: dict[tuple[str, str, str], bytes], *,
            now: datetime) -> "IncidentMemory":
        """Build memory only after every provenance-bound envelope verifies."""
        from .incident_memory_approval import verify_incident_memory_approvals

        approvals = verify_incident_memory_approvals(
            envelopes, trusted_public_keys, now=now,
        )
        memory = cls([item.record for item in approvals])
        memory._approval_provenance = {
            (item.record.tenant, item.record.project, item.record.evidence_digest): item
            for item in approvals
        }
        return memory

    def approval_provenance_for(
            self, record: IncidentRecord) -> VerifiedIncidentMemoryApproval | None:
        """Return verified approval metadata for this exact memory row, if present."""
        if type(record) is not IncidentRecord:
            raise ContextError("invalid_memory")
        key = (record.tenant, record.project, record.evidence_digest)
        approval = self._approval_provenance.get(key)
        if approval is None or approval.record.record_digest != record.record_digest:
            return None
        return approval

    def to_bundle(self) -> dict:
        """Return a deterministic, detached versioned bundle of incident records."""
        rows = sorted(self._validated_rows(), key=lambda row: (
            row.tenant, row.project, row.service, row.category, row.evidence_digest,
        ))
        payload = {
            "schema_version": _BUNDLE_SCHEMA_VERSION,
            "records": [row.to_record() for row in rows],
        }
        return {
            **payload,
            "bundle_digest": hashlib.sha256(_canonical_json(payload)).hexdigest(),
        }

    @classmethod
    def from_bundle(cls, value: dict) -> "IncidentMemory":
        """Load one strict, bounded memory bundle atomically; reject partial imports."""
        if type(value) is not dict or set(value) != _BUNDLE_FIELDS:
            raise ContextError("invalid_memory_bundle")
        if type(value["schema_version"]) is not int:
            raise ContextError("unsupported_memory_bundle")
        if value["schema_version"] != _BUNDLE_SCHEMA_VERSION:
            raise ContextError("unsupported_memory_bundle")
        records = value["records"]
        if type(records) is not list or len(records) > _MAX_MEMORY_RECORDS:
            raise ContextError("invalid_memory_bundle")
        digest = value["bundle_digest"]
        if type(digest) is not str or _DIGEST.fullmatch(digest) is None:
            raise ContextError("invalid_memory_bundle")
        parsed = [IncidentRecord.from_record(record) for record in records]
        canonical_records = [row.to_record() for row in sorted(parsed, key=lambda row: (
            row.tenant, row.project, row.service, row.category, row.evidence_digest,
        ))]
        if canonical_records != records:
            raise ContextError("noncanonical_memory_bundle")
        try:
            payload = {"schema_version": value["schema_version"],
                       "records": canonical_records}
            expected_digest = hashlib.sha256(_canonical_json(payload)).hexdigest()
        except (TypeError, ValueError, OverflowError):
            raise ContextError("invalid_memory_bundle") from None
        if digest != expected_digest:
            raise ContextError("memory_bundle_digest_mismatch")
        return cls(parsed)

    @staticmethod
    def _copy_record(record: IncidentRecord) -> IncidentRecord:
        try:
            return IncidentRecord(
                record.tenant, record.project, record.service, record.category,
                record.runbook_id, record.outcome, record.evidence_digest,
                record.source_sha, record.recorded_at,
            )
        except (AttributeError, TypeError, ContextError):
            raise ContextError("invalid_memory") from None

    @staticmethod
    def _validate_query(tenant: str, project: str, service: str,
                        category: str, limit: int) -> None:
        if (not all(_id(v) for v in (tenant,project,service))
                or type(category) is not str or category not in _CATEGORIES
                or type(limit) is not int or not 1<=limit<=5):
            raise ContextError("invalid_query")

    def _validated_rows(self) -> tuple[IncidentRecord, ...]:
        return tuple(self._copy_record(row) for row in self._rows)

    def retrieve(self, tenant: str, project: str, service: str,
                 category: str, limit: int=3) -> tuple[IncidentRecord,...]:
        self._validate_query(tenant, project, service, category, limit)
        rows=(r for r in self._validated_rows() if (r.tenant,r.project,r.service,r.category)==
              (tenant,project,service,category) and r.outcome=="resolved")
        return tuple(sorted(rows,key=lambda r:r.evidence_digest)[:limit])

    def retrieve_provenanced(self, tenant: str, project: str, service: str,
                             category: str, *, now: datetime,
                             max_age_seconds: int, limit: int=3
                             ) -> tuple[IncidentRecord,...]:
        """Retrieve only scoped records with source/time provenance within an explicit age."""
        self._validate_query(tenant, project, service, category, limit)
        if (type(now) is not datetime or now.tzinfo is None or now.utcoffset() is None
                or type(max_age_seconds) is not int
                or not 1<=max_age_seconds<=31_536_000):
            raise ContextError("invalid_query")
        instant=now.astimezone(timezone.utc)
        matches=[]
        for record in self._validated_rows():
            if ((record.tenant,record.project,record.service,record.category)!=
                    (tenant,project,service,category)
                    or record.outcome!="resolved"
                    or record.source_sha is None or record.recorded_at is None):
                continue
            recorded=datetime.fromisoformat(record.recorded_at.replace("Z", "+00:00"))
            age=(instant-recorded).total_seconds()
            if 0<=age<=max_age_seconds:
                matches.append(record)
        return tuple(sorted(matches,key=lambda r:r.evidence_digest)[:limit])

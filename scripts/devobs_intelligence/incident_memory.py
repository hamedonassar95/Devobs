"""Tenant/project exact-match, metadata-only incident memory; no embeddings."""
from __future__ import annotations
import re
from dataclasses import dataclass
from .context import ContextError, _id

_DIGEST=re.compile(r"[0-9a-f]{64}\Z")
_RUNBOOK=re.compile(r"RB-[A-Z]{2,8}-[0-9]{2}\Z")
_CATEGORIES=frozenset({"ci_failure","high_error_rate","capacity_pressure"})


@dataclass(frozen=True)
class IncidentRecord:
    tenant: str
    project: str
    service: str
    category: str
    runbook_id: str
    outcome: str
    evidence_digest: str

    def __post_init__(self):
        if (not all(_id(v) for v in (self.tenant,self.project,self.service))
                or type(self.category) is not str or self.category not in _CATEGORIES
                or type(self.runbook_id) is not str or _RUNBOOK.fullmatch(self.runbook_id) is None
                or type(self.outcome) is not str or self.outcome not in {"resolved","unresolved","false_positive"}
                or type(self.evidence_digest) is not str
                or _DIGEST.fullmatch(self.evidence_digest) is None):
            raise ContextError("invalid_memory")


class IncidentMemory:
    """Only pre-reviewed resolved records; reject duplicate scoped evidence."""
    def __init__(self, records: list[IncidentRecord]):
        if (type(records) is not list or len(records)>1000
                or any(type(item) is not IncidentRecord for item in records)):
            raise ContextError("invalid_memory")
        ids={(r.tenant,r.project,r.evidence_digest) for r in records}
        if len(ids)!=len(records):
            raise ContextError("duplicate_memory")
        self._rows=tuple(records)

    def retrieve(self, tenant: str, project: str, service: str,
                 category: str, limit: int=3) -> tuple[IncidentRecord,...]:
        if (not all(_id(v) for v in (tenant,project,service))
                or type(category) is not str or category not in _CATEGORIES
                or type(limit) is not int or not 1<=limit<=5):
            raise ContextError("invalid_query")
        rows=(r for r in self._rows if (r.tenant,r.project,r.service,r.category)==
              (tenant,project,service,category) and r.outcome=="resolved")
        return tuple(sorted(rows,key=lambda r:r.evidence_digest)[:limit])

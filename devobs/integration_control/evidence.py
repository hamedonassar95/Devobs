"""Deterministic evidence registry with duplicate rejection."""

from __future__ import annotations

from typing import Any

from .models import BLOCKER, Finding
from .security import digest_payload


class EvidenceRegistry:
    """Accept bounded evidence once; duplicate IDs or digests fail closed."""

    def __init__(self) -> None:
        self._by_id: dict[str, dict[str, Any]] = {}
        self._by_digest: dict[str, str] = {}

    def add(self, record: dict[str, Any]) -> tuple[bool, Finding | None]:
        evidence_id = record["id"]
        content = {
            key: value for key, value in record.items()
            if key not in {"id", "digest"}
        }
        digest = digest_payload(content)
        if evidence_id in self._by_id or digest in self._by_digest:
            return False, Finding("DUPLICATE_EVIDENCE", BLOCKER, "evidence")
        stored = dict(record)
        stored["digest"] = digest
        self._by_id[evidence_id] = stored
        self._by_digest[digest] = evidence_id
        return True, None

    def add_artifact(self, artifact: dict[str, Any]) -> tuple[bool, Finding | None]:
        return self.add({
            "id": artifact["id"],
            "kind": artifact["kind"],
            "source": artifact["source"],
            "excerpt": artifact["excerpt"],
        })

    def add_component(self, component_id: str, kind: str, detail: str) -> tuple[bool, Finding | None]:
        return self.add({
            "id": component_id,
            "kind": kind,
            "source": "component:integration_control",
            "excerpt": detail[:512],
        })

    @property
    def accepted_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_id))

    def records(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._by_id[key] for key in sorted(self._by_id))

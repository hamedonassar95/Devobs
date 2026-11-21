"""Evidence-first data models for the offline incident intelligence engine."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = "1.1"


@dataclass(frozen=True)
class Evidence:
    """A redacted observation that can be traced back to a source."""

    id: str
    source: str
    excerpt: str
    confidence: str


@dataclass(frozen=True)
class Hypothesis:
    """A deterministic, evidence-linked root-cause candidate."""

    id: str
    category: str
    statement: str
    confidence: str
    evidence_ids: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class Recommendation:
    """Advisory next step. It never authorizes or performs remediation."""

    id: str
    action: str
    rationale: str
    hypothesis_id: str
    requires_human_approval: bool = True


@dataclass(frozen=True)
class AIProviderReport:
    """Status and advisory text from an explicitly injected provider."""

    status: str
    summary: str


@dataclass(frozen=True)
class IncidentInput:
    """Normalized, sanitized input accepted by the analyzer."""

    title: str = ""
    job: str = ""
    step: str = ""
    logs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class IncidentReport:
    """Deterministic report suitable for JSON serialization."""

    schema_version: str
    source: str
    category: str
    signal: str
    confidence: str
    summary: str
    evidence: tuple[Evidence, ...]
    hypotheses: tuple[Hypothesis, ...]
    recommendations: tuple[Recommendation, ...]
    warnings: tuple[str, ...]
    ai_provider: AIProviderReport
    guardrails: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-normalized view (tuples become lists)."""
        return json.loads(json.dumps(asdict(self), sort_keys=True, separators=(",", ":")))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

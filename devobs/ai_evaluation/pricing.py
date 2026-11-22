"""Configurable pricing catalog with explicit UNKNOWN handling (offline only)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from .models import Confidence, EvaluationError, PricingEntry


@dataclass(frozen=True)
class CostEstimate:
    """An estimated token cost with an explicit confidence label."""

    total_usd: Decimal | None
    confidence: Confidence
    label: str
    source_url: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "estimated_cost_usd": None if self.total_usd is None else str(self.total_usd),
            "cost_confidence": self.confidence.value,
            "cost_source": self.label,
            "source_url": self.source_url,
        }


class PricingCatalog:
    """In-memory catalog loaded from a caller-supplied mapping.

    No network lookup is performed. Unverified or missing entries are reported
    as UNKNOWN rather than being silently treated as free (zero cost).
    """

    SCHEMA_VERSION = "ai-eval-pricing/1.0"

    def __init__(self, entries: Mapping[str, PricingEntry], currency: str = "USD") -> None:
        if not entries:
            raise EvaluationError("empty_pricing_catalog")
        if currency != "USD":
            raise EvaluationError("unsupported_currency")
        self._entries = dict(entries)
        self.currency = currency

    @classmethod
    def from_mapping(cls, mapping: Any) -> "PricingCatalog":
        if not isinstance(mapping, Mapping):
            raise EvaluationError("invalid_pricing_mapping")
        if mapping.get("schema_version") != cls.SCHEMA_VERSION:
            raise EvaluationError("unsupported_pricing_schema")
        currency = mapping.get("currency")
        if currency != "USD":
            raise EvaluationError("unsupported_currency")
        raw = mapping.get("entries")
        if not isinstance(raw, Mapping) or not raw:
            raise EvaluationError("invalid_pricing_entries")
        entries: dict[str, PricingEntry] = {}
        for model_id, entry in raw.items():
            if not isinstance(model_id, str) or not model_id or not isinstance(entry, Mapping):
                raise EvaluationError("invalid_pricing_entry")
            entries[model_id] = PricingEntry.from_mapping(model_id, entry)
        return cls(entries, currency)

    def estimate(self, model_id: str, prompt_tokens: int, completion_tokens: int) -> CostEstimate:
        if prompt_tokens < 0 or completion_tokens < 0:
            raise EvaluationError("invalid_token_counts")
        entry = self._entries.get(model_id)
        if entry is None or not entry.verified:
            return CostEstimate(None, Confidence.UNKNOWN, "UNKNOWN",
                                "" if entry is None else entry.source_url)
        assert entry.prompt_usd_per_million is not None
        assert entry.completion_usd_per_million is not None
        total = (Decimal(prompt_tokens) * entry.prompt_usd_per_million
                 + Decimal(completion_tokens) * entry.completion_usd_per_million) / Decimal(1_000_000)
        return CostEstimate(total, Confidence.ESTIMATED, entry.source_url, entry.source_url)

    def digest(self) -> str:
        payload = "|".join(
            f"{model}:{e.verified}:{e.prompt_usd_per_million}:{e.completion_usd_per_million}"
            for model, e in sorted(self._entries.items())
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

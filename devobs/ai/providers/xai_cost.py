"""Explicit, source-linked cost model for xAI text requests.

Pricing is VERIFIED from the official xAI documentation:

- https://docs.x.ai/developers/models (per-million rates, 200k threshold)
- https://docs.x.ai/developers/models/grok-4.7 (500k context window)
- https://docs.x.ai/developers/cost-tracking (1 USD = 10,000,000,000 ticks)

The estimate is an upper bound under this adapter's configured token caps.
xAI does not publish a hard cap on reasoning tokens, so the adapter supplies an
explicit ``XAI_MAX_REASONING_TOKENS`` allowance and enforces it as a policy
ceiling. Actual billed cost is checked against the authorization after the
response and fails closed on overage.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Mapping

from .xai_config import XaiConfig

TICKS_PER_USD = 10_000_000_000
_ONE_MILLION = Decimal(1_000_000)
_PRICING_SOURCE = "xAI Models documentation"
_PRICING_URL = "https://docs.x.ai/developers/models"
_MODEL_URL = "https://docs.x.ai/developers/models/grok-4.7"
_PRICING_OBSERVED_AT = "2026-11-21"
_CURRENCY = "USD"


class XaiCostError(ValueError):
    """Fixed safe reason for an unsupported or invalid cost calculation."""


@dataclass(frozen=True)
class TokenRates:
    """USD per one million tokens for one pricing tier."""

    input_per_1m: Decimal
    cached_input_per_1m: Decimal
    output_per_1m: Decimal

    def __post_init__(self) -> None:
        for name in ("input_per_1m", "cached_input_per_1m", "output_per_1m"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise XaiCostError("invalid_pricing_rate")


@dataclass(frozen=True)
class ModelPricing:
    """Source-linked pricing with explicit context thresholds."""

    model: str
    source: str
    source_url: str
    model_url: str
    observed_at: str
    currency: str
    context_window_tokens: int
    long_context_threshold_tokens: int
    short_context: TokenRates
    long_context: TokenRates

    def tier_for_prompt(self, prompt_tokens: int) -> str:
        if type(prompt_tokens) is not int or prompt_tokens < 0:
            raise XaiCostError("invalid_token_count")
        if prompt_tokens > self.context_window_tokens:
            raise XaiCostError("token_count_exceeds_context")
        return ("long_context" if prompt_tokens >= self.long_context_threshold_tokens
                else "short_context")

    def to_dict(self) -> dict[str, object]:
        return {
            "model": self.model,
            "source": self.source,
            "source_url": self.source_url,
            "model_url": self.model_url,
            "observed_at": self.observed_at,
            "currency": self.currency,
            "context_window_tokens": self.context_window_tokens,
            "long_context_threshold_tokens": self.long_context_threshold_tokens,
            "short_input_per_1m_usd": str(self.short_context.input_per_1m),
            "short_cached_input_per_1m_usd": str(self.short_context.cached_input_per_1m),
            "short_output_per_1m_usd": str(self.short_context.output_per_1m),
            "long_input_per_1m_usd": str(self.long_context.input_per_1m),
            "long_cached_input_per_1m_usd": str(self.long_context.cached_input_per_1m),
            "long_output_per_1m_usd": str(self.long_context.output_per_1m),
            "lowest_input_per_1m_usd": str(min(
                self.short_context.input_per_1m, self.long_context.input_per_1m)),
            "highest_output_per_1m_usd": str(max(
                self.short_context.output_per_1m, self.long_context.output_per_1m)),
        }


PRICING_CATALOG: Mapping[str, ModelPricing] = {
    "grok-4.7": ModelPricing(
        model="grok-4.7",
        source=_PRICING_SOURCE,
        source_url=_PRICING_URL,
        model_url=_MODEL_URL,
        observed_at=_PRICING_OBSERVED_AT,
        currency=_CURRENCY,
        context_window_tokens=500_000,
        long_context_threshold_tokens=200_000,
        short_context=TokenRates(
            input_per_1m=Decimal("2.00"),
            cached_input_per_1m=Decimal("0.50"),
            output_per_1m=Decimal("6.00"),
        ),
        long_context=TokenRates(
            input_per_1m=Decimal("4.00"),
            cached_input_per_1m=Decimal("1.00"),
            output_per_1m=Decimal("12.00"),
        ),
    ),
}


@dataclass(frozen=True)
class CostEstimate:
    """Maximum cost for one request under the configured token caps."""

    model: str
    currency: str
    tier: str
    prompt_tokens: int
    output_tokens: int
    reasoning_tokens: int
    max_cost_usd: Decimal
    source: str
    source_url: str
    model_url: str
    observed_at: str
    context_window_tokens: int
    long_context_threshold_tokens: int

    def to_dict(self) -> dict[str, object]:
        return {
            "model": self.model,
            "currency": self.currency,
            "tier": self.tier,
            "prompt_tokens": self.prompt_tokens,
            "output_tokens": self.output_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "max_cost_usd": str(self.max_cost_usd),
            "source": self.source,
            "source_url": self.source_url,
            "model_url": self.model_url,
            "observed_at": self.observed_at,
            "context_window_tokens": self.context_window_tokens,
            "long_context_threshold_tokens": self.long_context_threshold_tokens,
        }


def pricing_for(model: str) -> ModelPricing:
    pricing = PRICING_CATALOG.get(model)
    if pricing is None:
        raise XaiCostError("unpriced_model")
    return pricing


def estimate_max_request_cost(config: XaiConfig) -> CostEstimate:
    """Compute the worst-case charge for one request before it is sent.

    Cached input is assumed to be zero, which over-estimates rather than
    under-estimates cost. Reasoning tokens are billed as output tokens.
    """
    if not isinstance(config, XaiConfig):
        raise XaiCostError("invalid_configuration")
    pricing = pricing_for(config.model)
    tier = pricing.tier_for_prompt(config.max_input_tokens)
    rates = pricing.short_context if tier == "short_context" else pricing.long_context
    output_tokens = config.max_output_tokens + config.max_reasoning_tokens
    if output_tokens > pricing.context_window_tokens:
        raise XaiCostError("token_budget_exceeds_context")

    input_cost = rates.input_per_1m * Decimal(config.max_input_tokens) / _ONE_MILLION
    output_cost = rates.output_per_1m * Decimal(output_tokens) / _ONE_MILLION
    return CostEstimate(
        model=pricing.model,
        currency=pricing.currency,
        tier=tier,
        prompt_tokens=config.max_input_tokens,
        output_tokens=config.max_output_tokens,
        reasoning_tokens=config.max_reasoning_tokens,
        max_cost_usd=input_cost + output_cost,
        source=pricing.source,
        source_url=pricing.source_url,
        model_url=pricing.model_url,
        observed_at=pricing.observed_at,
        context_window_tokens=pricing.context_window_tokens,
        long_context_threshold_tokens=pricing.long_context_threshold_tokens,
    )


def ticks_to_usd(ticks: int) -> Decimal:
    """Convert xAI ``usage.cost_in_usd_ticks`` to USD (1 USD = 1e10 ticks)."""
    if type(ticks) is not int or ticks < 0 or ticks > 10**18:
        raise XaiCostError("invalid_cost_ticks")
    try:
        return Decimal(ticks) / Decimal(TICKS_PER_USD)
    except (InvalidOperation, ValueError):  # pragma: no cover - defensive
        raise XaiCostError("invalid_cost_ticks") from None

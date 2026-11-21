"""Fail-closed configuration for the optional xAI Grok adapter.

The configuration object never contains the API key. The key is read from the
process environment only when a caller explicitly builds a real provider.
Defaults are offline, disabled, and cost-free.

Official contract references:
- Base URL and chat completions: https://docs.x.ai/developers/rest-api-reference/inference/chat-completions
- Pricing and thresholds: https://docs.x.ai/developers/models
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Mapping

XAI_BASE_URL = "https://api.x.ai/v1"
CHAT_COMPLETIONS_PATH = "/chat/completions"
API_KEY_ENV = "XAI_API_KEY"

DEFAULT_ENABLED = False
DEFAULT_DRY_RUN = True
DEFAULT_MODEL = "grok-4.7"
DEFAULT_MAX_OUTPUT_TOKENS = 2048
DEFAULT_MAX_REQUESTS_PER_RUN = 0

# Additional bounded defaults. They are deliberately conservative: a real
# request cannot be sent until an operator raises the request/cost ceilings and
# supplies explicit per-call authorization.
DEFAULT_MAX_INPUT_TOKENS = 8192
DEFAULT_MAX_REASONING_TOKENS = 8192
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_MAX_RETRIES = 0
DEFAULT_MAX_RESPONSE_BYTES = 65536
DEFAULT_MAX_COST_USD = Decimal("0")
DEFAULT_REASONING_EFFORT = "low"

ALLOWED_MODELS = frozenset({"grok-4.7"})
ALLOWED_REASONING_EFFORTS = frozenset({"low", "medium", "high", "xhigh"})

_BOUNDS: dict[str, tuple[int, int]] = {
    "XAI_MAX_OUTPUT_TOKENS": (1, 100_000),
    "XAI_MAX_REQUESTS_PER_RUN": (0, 1000),
    "XAI_MAX_INPUT_TOKENS": (1, 500_000),
    "XAI_MAX_REASONING_TOKENS": (0, 500_000),
    "XAI_TIMEOUT_SECONDS": (1, 120),
    "XAI_MAX_RETRIES": (0, 3),
    "XAI_MAX_RESPONSE_BYTES": (1024, 4_194_304),
}

_PAID_CALL_ENV = "DEVOBS_AI_BUDGET_APPROVED"


class XaiConfigurationError(ValueError):
    """Fixed safe reason for invalid configuration; contains no values."""


@dataclass(frozen=True)
class XaiConfig:
    """Non-secret, validated settings for the xAI adapter."""

    enabled: bool = DEFAULT_ENABLED
    dry_run: bool = DEFAULT_DRY_RUN
    model: str = DEFAULT_MODEL
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    max_requests_per_run: int = DEFAULT_MAX_REQUESTS_PER_RUN
    max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS
    max_reasoning_tokens: int = DEFAULT_MAX_REASONING_TOKENS
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES
    max_cost_usd: Decimal = DEFAULT_MAX_COST_USD
    reasoning_effort: str = DEFAULT_REASONING_EFFORT
    api_key_present: bool = False
    budget_flag_present: bool = False

    def __repr__(self) -> str:  # pragma: no cover - defensive; never show secrets
        return (
            "XaiConfig(enabled=%r, dry_run=%r, model=%r, api_key_present=%r, "
            "budget_flag_present=%r)"
            % (self.enabled, self.dry_run, self.model,
               self.api_key_present, self.budget_flag_present)
        )

    def redacted_dict(self) -> dict[str, object]:
        """Return safe structured fields for logs, reports, and diagnostics."""
        return {
            "enabled": self.enabled,
            "dry_run": self.dry_run,
            "model": self.model,
            "max_output_tokens": self.max_output_tokens,
            "max_requests_per_run": self.max_requests_per_run,
            "max_input_tokens": self.max_input_tokens,
            "max_reasoning_tokens": self.max_reasoning_tokens,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "max_response_bytes": self.max_response_bytes,
            "max_cost_usd": str(self.max_cost_usd),
            "reasoning_effort": self.reasoning_effort,
            "api_key_present": self.api_key_present,
            "budget_flag_present": self.budget_flag_present,
            "endpoint": XAI_BASE_URL + CHAT_COMPLETIONS_PATH,
        }


def _read_bool(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = env.get(name)
    if raw is None:
        return default
    if type(raw) is not str:
        raise XaiConfigurationError("invalid_boolean_configuration")
    value = raw.strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    raise XaiConfigurationError("invalid_boolean_configuration")


def _read_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None:
        return default
    if type(raw) is not str:
        raise XaiConfigurationError("invalid_integer_configuration")
    try:
        value = int(raw.strip())
    except (TypeError, ValueError):
        raise XaiConfigurationError("invalid_integer_configuration") from None
    low, high = _BOUNDS[name]
    if not low <= value <= high:
        raise XaiConfigurationError("integer_out_of_bounds")
    return value


def _read_cost(env: Mapping[str, str], name: str, default: Decimal) -> Decimal:
    raw = env.get(name)
    if raw is None:
        return default
    if type(raw) is not str:
        raise XaiConfigurationError("invalid_cost_configuration")
    try:
        value = Decimal(raw.strip())
    except (InvalidOperation, ValueError):
        raise XaiConfigurationError("invalid_cost_configuration") from None
    if not value.is_finite() or value < 0 or value > Decimal("1000"):
        raise XaiConfigurationError("cost_out_of_bounds")
    return value


def load_xai_config(env: Mapping[str, str] | None = None) -> XaiConfig:
    """Build a validated config from a mapping (defaults to ``os.environ``).

    Only presence of ``XAI_API_KEY`` is recorded; its value is never copied.
    """
    source: Mapping[str, str] = os.environ if env is None else env
    model = source.get("XAI_MODEL", DEFAULT_MODEL)
    if type(model) is not str or model not in ALLOWED_MODELS:
        raise XaiConfigurationError("unsupported_model")

    reasoning_effort = source.get("XAI_REASONING_EFFORT", DEFAULT_REASONING_EFFORT)
    if (type(reasoning_effort) is not str
            or reasoning_effort not in ALLOWED_REASONING_EFFORTS):
        raise XaiConfigurationError("unsupported_reasoning_effort")

    api_key = source.get(API_KEY_ENV)
    budget_flag = _read_bool(source, _PAID_CALL_ENV, False)

    config = XaiConfig(
        enabled=_read_bool(source, "XAI_ENABLED", DEFAULT_ENABLED),
        dry_run=_read_bool(source, "XAI_DRY_RUN", DEFAULT_DRY_RUN),
        model=model,
        max_output_tokens=_read_int(
            source, "XAI_MAX_OUTPUT_TOKENS", DEFAULT_MAX_OUTPUT_TOKENS),
        max_requests_per_run=_read_int(
            source, "XAI_MAX_REQUESTS_PER_RUN", DEFAULT_MAX_REQUESTS_PER_RUN),
        max_input_tokens=_read_int(
            source, "XAI_MAX_INPUT_TOKENS", DEFAULT_MAX_INPUT_TOKENS),
        max_reasoning_tokens=_read_int(
            source, "XAI_MAX_REASONING_TOKENS", DEFAULT_MAX_REASONING_TOKENS),
        timeout_seconds=_read_int(
            source, "XAI_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
        max_retries=_read_int(source, "XAI_MAX_RETRIES", DEFAULT_MAX_RETRIES),
        max_response_bytes=_read_int(
            source, "XAI_MAX_RESPONSE_BYTES", DEFAULT_MAX_RESPONSE_BYTES),
        max_cost_usd=_read_cost(source, "XAI_MAX_COST_USD", DEFAULT_MAX_COST_USD),
        reasoning_effort=reasoning_effort,
        api_key_present=type(api_key) is str and bool(api_key.strip()),
        budget_flag_present=budget_flag,
    )
    if config.max_input_tokens + config.max_reasoning_tokens > 500_000:
        raise XaiConfigurationError("token_budget_exceeds_context")
    return config


def resolve_api_key(env: Mapping[str, str] | None = None) -> str:
    """Read the API key from the environment only. Never log or persist it."""
    source: Mapping[str, str] = os.environ if env is None else env
    value = source.get(API_KEY_ENV)
    if (type(value) is not str or not value.strip()
            or "\r" in value or "\n" in value or len(value) > 4096):
        raise XaiConfigurationError("api_key_unavailable")
    return value

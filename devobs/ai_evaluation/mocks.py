"""Deterministic offline provider mocks.

Each mock returns a structured ProviderResponse for a named scenario. Mocks are
seeded, never open a socket, never read credentials and cannot produce a
verified live response.
"""

from __future__ import annotations

from decimal import Decimal

from .models import (
    ErrorCategory,
    InvocationOutcome,
    ProviderResponse,
    ProviderStatus,
    SafetyPolicyResult,
)


class OfflineProviderMock:
    """Seeded in-memory provider mock for contract testing."""

    def __init__(self, seed: int = 20261122) -> None:
        self.seed = seed
        self.is_offline = True

    def invoke(
        self,
        *,
        provider_id: str,
        model_id: str,
        scenario: str,
        prompt: str,
        max_output_tokens: int = 512,
        spending_ceiling_usd: Decimal = Decimal("0"),
    ) -> ProviderResponse:
        """Return the deterministic response for ``scenario``.

        Latency and token counts are derived from the seed and scenario name so
        repeated runs produce byte-identical reports.
        """
        base = _scenario_profile(scenario)
        latency = base.latency_ms + Decimal(self.seed % 7)
        prompt_tokens = min(len(prompt) // 4, max_output_tokens)
        completion_tokens = base.completion_tokens
        common = dict(
            provider_id=provider_id,
            model_id=model_id,
            latency_ms=latency,
            attempts=base.attempts,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_tokens=prompt_tokens + completion_tokens,
        )
        if scenario == "success":
            return ProviderResponse(
                outcome=InvocationOutcome.SUCCESS,
                status=ProviderStatus.AVAILABLE,
                error_category=ErrorCategory.NONE,
                reliability_score=Decimal("1.0"),
                safety_policy_result=SafetyPolicyResult.ALLOWED,
                text='{"category":"ci_failure","confidence":"low"}',
                **common,
            )
        if scenario == "rate_limit_then_success":
            return ProviderResponse(
                outcome=InvocationOutcome.SUCCESS,
                status=ProviderStatus.AVAILABLE,
                error_category=ErrorCategory.RATE_LIMIT,
                reliability_score=Decimal("0.75"),
                safety_policy_result=SafetyPolicyResult.ALLOWED,
                text='{"recommendation":"inspect connection leaks"}',
                **common,
            )
        if scenario == "timeout":
            return ProviderResponse(
                outcome=InvocationOutcome.TIMEOUT,
                status=ProviderStatus.DEGRADED,
                error_category=ErrorCategory.TIMEOUT,
                reliability_score=Decimal("0.0"),
                safety_policy_result=SafetyPolicyResult.NOT_EVALUATED,
                text="",
                **common,
            )
        if scenario == "malformed_json":
            return ProviderResponse(
                outcome=InvocationOutcome.MALFORMED_RESPONSE,
                status=ProviderStatus.DEGRADED,
                error_category=ErrorCategory.INVALID_RESPONSE,
                reliability_score=Decimal("0.0"),
                safety_policy_result=SafetyPolicyResult.NOT_EVALUATED,
                text="{not valid json",
                **common,
            )
        if scenario == "missing_credentials":
            return ProviderResponse(
                outcome=InvocationOutcome.AUTHENTICATION_ERROR,
                status=ProviderStatus.BLOCKED,
                error_category=ErrorCategory.AUTHENTICATION,
                reliability_score=Decimal("0.0"),
                safety_policy_result=SafetyPolicyResult.NOT_EVALUATED,
                text="",
                **common,
            )
        if scenario == "cost_ceiling":
            return ProviderResponse(
                outcome=InvocationOutcome.BUDGET_BLOCKED,
                status=ProviderStatus.BLOCKED,
                error_category=ErrorCategory.COST,
                reliability_score=Decimal("0.0"),
                safety_policy_result=SafetyPolicyResult.NOT_EVALUATED,
                text="",
                **common,
            )
        if scenario == "unsafe_action":
            return ProviderResponse(
                outcome=InvocationOutcome.UNSAFE_ACTION_BLOCKED,
                status=ProviderStatus.BLOCKED,
                error_category=ErrorCategory.SAFETY,
                reliability_score=Decimal("0.0"),
                safety_policy_result=SafetyPolicyResult.BLOCKED,
                text="",
                **common,
            )
        if scenario == "outage":
            return ProviderResponse(
                outcome=InvocationOutcome.PROVIDER_UNAVAILABLE,
                status=ProviderStatus.UNAVAILABLE,
                error_category=ErrorCategory.UNAVAILABLE,
                reliability_score=Decimal("0.0"),
                safety_policy_result=SafetyPolicyResult.NOT_EVALUATED,
                text="",
                **common,
            )
        if scenario in ("redirect", "invalid_model"):
            return ProviderResponse(
                outcome=InvocationOutcome.OUTBOUND_BLOCKED,
                status=ProviderStatus.BLOCKED,
                error_category=ErrorCategory.OUTBOUND,
                reliability_score=Decimal("0.0"),
                safety_policy_result=SafetyPolicyResult.NOT_EVALUATED,
                text="",
                **common,
            )
        raise ValueError("invalid_scenario")


class _Profile:
    def __init__(self, latency_ms: Decimal, completion_tokens: int, attempts: int) -> None:
        self.latency_ms = latency_ms
        self.completion_tokens = completion_tokens
        self.attempts = attempts


def _scenario_profile(scenario: str) -> _Profile:
    profiles = {
        "success": (Decimal("12"), 32, 1),
        "rate_limit_then_success": (Decimal("40"), 24, 2),
        "timeout": (Decimal("1000"), 0, 1),
        "malformed_json": (Decimal("18"), 8, 1),
        "missing_credentials": (Decimal("1"), 0, 1),
        "cost_ceiling": (Decimal("2"), 0, 1),
        "unsafe_action": (Decimal("1"), 0, 1),
        "outage": (Decimal("3"), 0, 1),
        "redirect": (Decimal("1"), 0, 1),
        "invalid_model": (Decimal("1"), 0, 1),
    }
    if scenario not in profiles:
        raise ValueError("invalid_scenario")
    latency, tokens, attempts = profiles[scenario]
    return _Profile(latency, tokens, attempts)

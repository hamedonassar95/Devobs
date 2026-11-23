"""Offline-first evaluation engine: deterministic, advisory, no network calls."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from decimal import Decimal
from typing import Any, Mapping, Sequence

from .mocks import OfflineProviderMock
from .models import (
    Capability,
    CaseResult,
    Confidence,
    ErrorCategory,
    EvaluationReport,
    FixtureSet,
    InvocationOutcome,
    ProviderConfig,
    ProviderResponse,
    RoutingDecision,
    SafetyPolicyResult,
)
from .pricing import PricingCatalog

SCHEMA_VERSION = "ai-eval-provider/1.0"

_ALLOWED_SCENARIOS = frozenset({
    "success", "outage", "timeout", "rate_limit_then_success", "malformed_json",
    "missing_credentials", "invalid_model", "cost_ceiling", "redirect",
    "unsafe_action",
})

_DEFAULT_CONFIGS = (
    {
        "name": "fixture-primary",
        "model": "grok-4.7",
        "capabilities": [
            "incident_triage", "runbook_recommendation", "structured_json",
            "advisory_only", "cost_awareness",
        ],
        "timeout_seconds": 20,
        "max_retries": 1,
        "spending_ceiling_usd": "0.01",
        "offline": True,
        "source": "offline-fixture",
    },
    {
        "name": "fixture-fallback",
        "model": "gemini-2.5-pro",
        "capabilities": ["incident_triage", "advisory_only", "log_redaction"],
        "timeout_seconds": 15,
        "max_retries": 0,
        "spending_ceiling_usd": "0.01",
        "offline": True,
        "source": "offline-fixture",
    },
)


class EvaluationInputError(ValueError):
    """A fixed, non-sensitive diagnostic for invalid evaluation input."""


def build_default_configs() -> tuple[ProviderConfig, ...]:
    """Return two deterministic offline provider configurations."""
    return tuple(ProviderConfig.from_mapping(item) for item in _DEFAULT_CONFIGS)


class EvaluationEngine:
    """Compose deterministic mock outcomes into a structured comparison report."""

    def __init__(self, catalog: PricingCatalog, mock: OfflineProviderMock | None = None) -> None:
        self.catalog = catalog
        self.mock = mock or OfflineProviderMock()

    def evaluate(
        self,
        fixture: FixtureSet,
        configs: Sequence[ProviderConfig],
    ) -> EvaluationReport:
        if not isinstance(fixture, FixtureSet) or not configs:
            raise EvaluationInputError("invalid_evaluation_input")
        for case in fixture.cases:
            if case.scenario not in _ALLOWED_SCENARIOS:
                raise EvaluationInputError("invalid_scenario")
        if len({config.name for config in configs}) != len(configs):
            raise EvaluationInputError("duplicate_provider")

        cases: list[CaseResult] = []
        for case in fixture.cases:
            config = self._select_config(case, configs)
            result = self._invoke(case, config)
            cases.append(CaseResult(
                case_id=case.case_id,
                task=case.task,
                capabilities=case.capabilities,
                request_prompt=case.prompt,
                result=result,
                expected_outcome=case.expected_outcome,
                expected_status=case.expected_status,
            ))

        comparison = self._comparison(cases, configs)
        fingerprint = self._fingerprint(fixture, cases, comparison)
        return EvaluationReport(
            schema_version=SCHEMA_VERSION,
            fixture=fixture,
            cases=tuple(cases),
            comparison=comparison,
            fingerprint=fingerprint,
            offline=True,
            live_calls=0,
            configs=tuple(configs),
            routing=self._routing(cases, configs),
            limitations=(
                "Offline fixtures only; no live provider call or credential was used.",
                "Latency and token counts are seeded fixture values, not measurements.",
                "Estimated cost is advisory; UNKNOWN means pricing was not verified.",
                "Safety results are fixture assertions, not a live policy engine.",
            ),
        )

    @staticmethod
    def _select_config(case: Any, configs: Sequence[ProviderConfig]) -> ProviderConfig:
        for config in configs:
            if case.capabilities.issubset(config.capabilities):
                return config
        return configs[0]

    def _invoke(self, case: Any, config: ProviderConfig) -> ProviderResponse:
        response = self.mock.invoke(
            provider_id=config.name,
            model_id=config.model,
            scenario=case.scenario,
            prompt=case.prompt,
            max_output_tokens=512,
            spending_ceiling_usd=config.spending_ceiling_usd,
        )
        estimate = self.catalog.estimate(
            config.model, response.prompt_tokens, response.completion_tokens)
        values: dict[str, Any] = {
            "estimated_cost_usd": estimate.total_usd,
            "cost_confidence": estimate.confidence,
            "cost_source": estimate.label,
        }
        # Fail closed if an estimated cost would exceed the configured ceiling.
        if (estimate.total_usd is not None
                and estimate.total_usd > config.spending_ceiling_usd
                and response.safety_policy_result.value != "BLOCKED"
                and response.outcome == InvocationOutcome.SUCCESS):
            values.update(
                outcome=InvocationOutcome.BUDGET_BLOCKED,
                error_category=ErrorCategory.COST,
                safety_policy_result=SafetyPolicyResult.NOT_EVALUATED,
                reliability_score=Decimal("0"),
            )
        return _replace(response, **values)

    @staticmethod
    def _routing(
        cases: Sequence[CaseResult], configs: Sequence[ProviderConfig]
    ) -> tuple[RoutingDecision, ...]:
        candidates = tuple(config.name for config in configs)
        decisions: list[RoutingDecision] = []
        seen_tasks: set[str] = set()
        for case in cases:
            if case.task in seen_tasks:
                continue
            seen_tasks.add(case.task)
            decisions.append(RoutingDecision(
                task=case.task,
                required_capabilities=case.capabilities,
                selected_provider=case.result.provider_id,
                candidate_providers=candidates,
                status=case.result.status,
                confidence=Confidence.TESTED,
                rationale=(
                    "Offline fixture routing: first configured provider whose "
                    "capabilities cover the case. Advisory only."
                ),
            ))
        return tuple(decisions)

    @staticmethod
    def _comparison(
        cases: Sequence[CaseResult], configs: Sequence[ProviderConfig]
    ) -> dict[str, Any]:
        by_provider: dict[str, dict[str, Any]] = {}
        for config in configs:
            provider_cases = [c for c in cases if c.result.provider_id == config.name]
            costs = [c.result.estimated_cost_usd for c in provider_cases
                     if c.result.estimated_cost_usd is not None]
            by_provider[config.name] = {
                "provider_id": config.name,
                "model_id": config.model,
                "capabilities": sorted(c.value for c in config.capabilities),
                "cases": len(provider_cases),
                "estimated_cost_usd": str(sum(costs, Decimal("0"))),
                "cost_confidence": "UNKNOWN" if not costs else "ESTIMATED",
            }
        by_capability: dict[str, list[str]] = {}
        for capability in Capability:
            providers = sorted(
                config.name for config in configs
                if capability in config.capabilities
            )
            by_capability[capability.value] = providers
        return {"by_provider": by_provider, "by_capability": by_capability}

    @staticmethod
    def _fingerprint(
        fixture: FixtureSet, cases: Sequence[CaseResult], comparison: Mapping[str, Any]
    ) -> str:
        payload = "|".join(
            [fixture.version, str(fixture.seed)]
            + [f"{c.case_id}:{c.result.outcome.value}" for c in cases]
            + [f"{p}:{d['estimated_cost_usd']}" for p, d in
               sorted(comparison["by_provider"].items())]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _replace(response: ProviderResponse, **changes: Any) -> ProviderResponse:
    return replace(response, **changes)

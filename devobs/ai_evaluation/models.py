"""Provider-neutral contracts for the offline-first evaluation harness.

This module is data only. It performs no network call, reads no credential and
imports no provider SDK. Every result carries an explicit confidence label so
offline contract checks are never presented as live provider evidence.

The structured result records every field required for transparent comparison:
provider/model identifiers, latency, error category, reliability score,
estimated token usage and cost, and the safety policy result.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping

MAX_PROMPT_BYTES = 8192
MAX_ID_CHARS = 128

_FORBIDDEN_CONFIG_KEYS = frozenset({
    "endpoint", "base_url", "api_url", "api_base", "url", "host", "hostname",
    "proxy", "proxy_url", "dns", "ca_bundle", "tls_ca", "certificate",
    "api_key", "token", "access_token", "authorization", "secret", "password",
})

_SECURITY_SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bsk-(?:proj|svcacct|live)-[A-Za-z0-9_-]{20,}\b|\bsk-[A-Za-z0-9]{40,}\b"),
    re.compile(r"\bxai-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\bAuthorization\s*:\s*Bearer\s+\S+"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{16,}=*"),
    re.compile(r"(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|secret)\b"
               r"[\"']?\s*[:=]\s*[\\\"']?(?!\[REDACTED\])[^\s\\\"'`,;]{6,}"),
)


class EvaluationError(ValueError):
    """Fail-closed error with a fixed safe reason; never carries raw values."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class Confidence(str, Enum):
    CONFIRMED = "CONFIRMED"
    TESTED = "TESTED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


class Capability(str, Enum):
    INCIDENT_TRIAGE = "incident_triage"
    RUNBOOK_RECOMMENDATION = "runbook_recommendation"
    LOG_REDACTION = "log_redaction"
    STRUCTURED_JSON = "structured_json"
    ADVISORY_ONLY = "advisory_only"
    COST_AWARENESS = "cost_awareness"


class ProviderStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class InvocationOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    BUDGET_BLOCKED = "BUDGET_BLOCKED"
    OUTBOUND_BLOCKED = "OUTBOUND_BLOCKED"
    UNSAFE_ACTION_BLOCKED = "UNSAFE_ACTION_BLOCKED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"


class ErrorCategory(str, Enum):
    NONE = "NONE"
    TIMEOUT = "TIMEOUT"
    RATE_LIMIT = "RATE_LIMIT"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    AUTHENTICATION = "AUTHENTICATION"
    CONFIGURATION = "CONFIGURATION"
    COST = "COST"
    SAFETY = "SAFETY"
    UNAVAILABLE = "UNAVAILABLE"
    OUTBOUND = "OUTBOUND"


class SafetyPolicyResult(str, Enum):
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    NOT_EVALUATED = "NOT_EVALUATED"


def redact_sensitive(value: str) -> tuple[str, int]:
    """Redact credential-like content; deterministic and idempotent."""
    if type(value) is not str:
        raise EvaluationError("invalid_redaction_input")
    safe = value
    matches = 0
    for pattern in _SECURITY_SENSITIVE_PATTERNS:
        safe, count = pattern.subn("[REDACTED]", safe)
        matches += count
    return safe, matches


def _validate_text(value: Any, name: str, *, maximum: int = 8192) -> str:
    if type(value) is not str or not value.strip() or "\x00" in value:
        raise EvaluationError("invalid_" + name)
    if len(value) > maximum or len(value.encode("utf-8")) > maximum:
        raise EvaluationError(name + "_too_large")
    return value


def _validate_id(value: Any, name: str) -> str:
    text = _validate_text(value, name, maximum=MAX_ID_CHARS)
    if not re.fullmatch(r"[A-Za-z0-9._:-]+", text):
        raise EvaluationError("invalid_" + name)
    return text


def _validate_decimal(value: Any, name: str, *, minimum: Decimal, maximum: Decimal) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise EvaluationError("invalid_" + name)
    if value < minimum or value > maximum:
        raise EvaluationError("invalid_" + name)
    return value


def parse_decimal(value: Any, name: str) -> Decimal:
    """Parse a decimal without accepting NaN/Infinity or silent truncation."""
    if type(value) is bool or not isinstance(value, (str, int, Decimal)):
        raise EvaluationError("invalid_" + name)
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise EvaluationError("invalid_" + name) from None
    if not parsed.is_finite():
        raise EvaluationError("invalid_" + name)
    return parsed


def _capabilities(values: Any, name: str) -> frozenset[Capability]:
    if type(values) not in (tuple, list, frozenset, set) or not values:
        raise EvaluationError("invalid_" + name)
    try:
        return frozenset(Capability(item) for item in values)
    except ValueError:
        raise EvaluationError("invalid_" + name) from None


@dataclass(frozen=True)
class ProviderConfig:
    """Non-secret, validated provider settings. Endpoint and secret keys are forbidden."""

    name: str
    model: str
    capabilities: frozenset[Capability]
    timeout_seconds: int = 20
    max_retries: int = 0
    spending_ceiling_usd: Decimal = Decimal("0")
    offline: bool = True
    source: str = "offline-fixture"

    def __post_init__(self) -> None:
        _validate_id(self.name, "provider_name")
        _validate_id(self.model, "model")
        _capabilities(self.capabilities, "capabilities")
        if type(self.timeout_seconds) is not int or not 1 <= self.timeout_seconds <= 120:
            raise EvaluationError("invalid_timeout")
        if type(self.max_retries) is not int or not 0 <= self.max_retries <= 3:
            raise EvaluationError("invalid_max_retries")
        _validate_decimal(self.spending_ceiling_usd, "spending_ceiling",
                          minimum=Decimal("0"), maximum=Decimal("1000"))
        if type(self.offline) is not bool:
            raise EvaluationError("invalid_offline_flag")
        _validate_text(self.source, "source", maximum=512)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "ProviderConfig":
        """Build a config from a mapping; reject endpoint and secret keys."""
        if not isinstance(mapping, Mapping):
            raise EvaluationError("invalid_configuration")
        for key in mapping:
            if type(key) is str and key.strip().lower() in _FORBIDDEN_CONFIG_KEYS:
                raise EvaluationError("unsafe_config_key")
        return cls(
            name=mapping["name"],
            model=mapping["model"],
            capabilities=_capabilities(mapping.get("capabilities", ()), "capabilities"),
            timeout_seconds=mapping.get("timeout_seconds", 20),
            max_retries=mapping.get("max_retries", 0),
            spending_ceiling_usd=parse_decimal(
                mapping.get("spending_ceiling_usd", "0"), "spending_ceiling"),
            offline=mapping.get("offline", True),
            source=mapping.get("source", "offline-fixture"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_id": self.name,
            "model_id": self.model,
            "capabilities": sorted(item.value for item in self.capabilities),
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "spending_ceiling_usd": str(self.spending_ceiling_usd),
            "offline": self.offline,
            "source": self.source,
        }

    # Backwards-compatible alias used by older harness notes.
    redacted_dict = to_dict


@dataclass(frozen=True)
class LiveModeAuthorization:
    """In-memory record of an explicit operator decision for future live mode."""

    approved: bool
    approver: str
    spending_ceiling_usd: Decimal
    scope: str

    def __post_init__(self) -> None:
        if self.approved is not True:
            raise EvaluationError("live_mode_not_authorized")
        _validate_id(self.approver, "approver")
        _validate_decimal(self.spending_ceiling_usd, "spending_ceiling",
                          minimum=Decimal("0.01"), maximum=Decimal("1000"))
        _validate_text(self.scope, "scope", maximum=512)


def assert_live_mode_allowed(
    config: ProviderConfig, authorization: LiveModeAuthorization | None
) -> None:
    """Fail closed: this harness has no enabled live mode."""
    if config.offline:
        raise EvaluationError("live_mode_disabled")
    if not isinstance(authorization, LiveModeAuthorization):
        raise EvaluationError("live_authorization_required")
    if authorization.spending_ceiling_usd > config.spending_ceiling_usd:
        raise EvaluationError("live_ceiling_exceeds_config")


@dataclass(frozen=True)
class PricingEntry:
    """A configurable price entry; unverified prices are UNKNOWN, never zero."""

    model_id: str
    prompt_usd_per_million: Decimal | None
    completion_usd_per_million: Decimal | None
    verified: bool
    source_url: str = ""
    note: str = ""

    @classmethod
    def from_mapping(cls, model_id: str, mapping: Mapping[str, Any]) -> "PricingEntry":
        verified = mapping.get("verified", False)
        if type(verified) is not bool:
            raise EvaluationError("invalid_pricing_verified")
        prompt = mapping.get("prompt_usd_per_million")
        completion = mapping.get("completion_usd_per_million")
        prompt_dec = None if prompt is None else parse_decimal(prompt, "prompt_rate")
        completion_dec = None if completion is None else parse_decimal(completion, "completion_rate")
        if verified:
            if prompt_dec is None or completion_dec is None:
                raise EvaluationError("verified_price_requires_rates")
            if prompt_dec < 0 or completion_dec < 0:
                raise EvaluationError("negative_pricing_rate")
            if not _validate_text(mapping.get("source_url", ""), "source_url", maximum=512):
                raise EvaluationError("verified_price_requires_source")
        return cls(model_id, prompt_dec, completion_dec, verified,
                   str(mapping.get("source_url", "")), str(mapping.get("note", "")))


@dataclass(frozen=True)
class ProviderResponse:
    """A redacted provider outcome with explicit cost, safety and reliability data."""

    provider_id: str
    model_id: str
    outcome: InvocationOutcome
    status: ProviderStatus
    latency_ms: Decimal
    error_category: ErrorCategory = ErrorCategory.NONE
    reliability_score: Decimal = Decimal("0")
    safety_policy_result: SafetyPolicyResult = SafetyPolicyResult.NOT_EVALUATED
    attempts: int = 1
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_tokens: int = 0
    estimated_cost_usd: Decimal | None = None
    cost_confidence: Confidence = Confidence.UNKNOWN
    cost_source: str = "none"
    text: str = ""
    is_mock: bool = True

    def __post_init__(self) -> None:
        _validate_id(self.provider_id, "provider_id")
        _validate_id(self.model_id, "model_id")
        if not isinstance(self.outcome, InvocationOutcome):
            raise EvaluationError("invalid_outcome")
        if not isinstance(self.status, ProviderStatus):
            raise EvaluationError("invalid_status")
        if not isinstance(self.error_category, ErrorCategory):
            raise EvaluationError("invalid_error_category")
        if not isinstance(self.safety_policy_result, SafetyPolicyResult):
            raise EvaluationError("invalid_safety_policy_result")
        if not isinstance(self.latency_ms, Decimal) or self.latency_ms < 0:
            raise EvaluationError("invalid_latency")
        _validate_decimal(self.reliability_score, "reliability_score",
                          minimum=Decimal("0"), maximum=Decimal("1"))
        if type(self.attempts) is not int or not 1 <= self.attempts <= 10:
            raise EvaluationError("invalid_attempts")
        for name in ("prompt_tokens", "completion_tokens", "estimated_tokens"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise EvaluationError("invalid_" + name)
        if self.estimated_cost_usd is not None:
            _validate_decimal(self.estimated_cost_usd, "estimated_cost_usd",
                              minimum=Decimal("0"), maximum=Decimal("1000"))
        if not isinstance(self.cost_confidence, Confidence):
            raise EvaluationError("invalid_cost_confidence")
        if type(self.is_mock) is not bool:
            raise EvaluationError("invalid_is_mock")
        object.__setattr__(self, "text", redact_sensitive(self.text)[0])

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "outcome": self.outcome.value,
            "status": self.status.value,
            "latency_ms": str(self.latency_ms),
            "error_category": self.error_category.value,
            "reliability_score": str(self.reliability_score),
            "safety_policy_result": self.safety_policy_result.value,
            "attempts": self.attempts,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "estimated_tokens": self.estimated_tokens,
            "estimated_cost_usd": (None if self.estimated_cost_usd is None
                                   else str(self.estimated_cost_usd)),
            "cost_confidence": self.cost_confidence.value,
            "cost_source": self.cost_source,
            "text": self.text,
            "is_mock": self.is_mock,
        }


@dataclass(frozen=True)
class ProviderRequest:
    """A bounded advisory prompt with no tool, action or execution field."""

    case_id: str
    prompt: str
    required_capabilities: frozenset[Capability]
    scenario: str = "success"
    request_id: str = "ai-eval-request"
    expected_markers: tuple[str, ...] = ()
    forbidden_markers: tuple[str, ...] = ()
    max_output_tokens: int = 512

    def __post_init__(self) -> None:
        _validate_id(self.case_id, "case_id")
        _validate_id(self.request_id, "request_id")
        _validate_text(self.prompt, "prompt", maximum=MAX_PROMPT_BYTES)
        _capabilities(self.required_capabilities, "required_capabilities")
        if type(self.scenario) is not str or not re.fullmatch(r"[a-z_]{1,40}", self.scenario):
            raise EvaluationError("invalid_scenario")
        if type(self.max_output_tokens) is not int or not 1 <= self.max_output_tokens <= 8192:
            raise EvaluationError("invalid_max_output_tokens")
        for name in ("expected_markers", "forbidden_markers"):
            value = getattr(self, name)
            if type(value) is not tuple or not all(
                type(item) is str and 1 <= len(item) <= 256 for item in value
            ):
                raise EvaluationError("invalid_" + name)

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "prompt": redact_sensitive(self.prompt)[0],
            "required_capabilities": sorted(
                item.value for item in self.required_capabilities),
            "scenario": self.scenario,
            "request_id": self.request_id,
            "expected_markers": list(self.expected_markers),
            "forbidden_markers": list(self.forbidden_markers),
            "max_output_tokens": self.max_output_tokens,
        }


@dataclass(frozen=True)
class ScoreBreakdown:
    """Deterministic quality/reliability summary behind a gate decision."""

    quality: Decimal
    reliability: Decimal
    composite: Decimal
    confidence: Confidence
    rationale: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("quality", "reliability", "composite"):
            _validate_decimal(getattr(self, name), name,
                              minimum=Decimal("0"), maximum=Decimal("1"))
        if not isinstance(self.confidence, Confidence):
            raise EvaluationError("invalid_confidence")
        if type(self.rationale) is not tuple or not all(
            type(item) is str and len(item) <= 512 for item in self.rationale
        ):
            raise EvaluationError("invalid_rationale")

    def to_dict(self) -> dict[str, object]:
        return {
            "quality": str(self.quality),
            "reliability": str(self.reliability),
            "composite": str(self.composite),
            "confidence": self.confidence.value,
            "rationale": list(self.rationale),
        }


@dataclass(frozen=True)
class Evidence:
    """A short, redacted claim with an explicit confidence and source."""

    claim: str
    confidence: Confidence
    source: str

    def __post_init__(self) -> None:
        _validate_text(self.claim, "claim", maximum=512)
        if not isinstance(self.confidence, Confidence):
            raise EvaluationError("invalid_confidence")
        _validate_text(self.source, "source", maximum=512)

    def to_dict(self) -> dict[str, str]:
        return {
            "claim": redact_sensitive(self.claim)[0],
            "confidence": self.confidence.value,
            "source": self.source,
        }


@dataclass(frozen=True)
class RoutingDecision:
    """Advisory provider selection for one task; never authorizes a live call."""

    task: str
    required_capabilities: frozenset[Capability]
    selected_provider: str | None
    candidate_providers: tuple[str, ...]
    status: ProviderStatus
    confidence: Confidence
    rationale: str

    def __post_init__(self) -> None:
        _validate_id(self.task, "task")
        _capabilities(self.required_capabilities, "required_capabilities")
        if self.selected_provider is not None:
            _validate_id(self.selected_provider, "selected_provider")
        if type(self.candidate_providers) is not tuple or not all(
            type(item) is str and 1 <= len(item) <= MAX_ID_CHARS
            for item in self.candidate_providers
        ):
            raise EvaluationError("invalid_candidate_providers")
        if not isinstance(self.status, ProviderStatus):
            raise EvaluationError("invalid_status")
        if not isinstance(self.confidence, Confidence):
            raise EvaluationError("invalid_confidence")
        _validate_text(self.rationale, "rationale", maximum=1024)

    def to_dict(self) -> dict[str, object]:
        return {
            "task": self.task,
            "required_capabilities": sorted(
                item.value for item in self.required_capabilities),
            "selected_provider": self.selected_provider,
            "candidate_providers": list(self.candidate_providers),
            "status": self.status.value,
            "confidence": self.confidence.value,
            "rationale": redact_sensitive(self.rationale)[0],
        }


@dataclass(frozen=True)
class FixtureCase:
    """A deterministic offline scenario definition."""

    case_id: str
    task: str
    prompt: str
    capabilities: frozenset[Capability]
    scenario: str
    expected_outcome: InvocationOutcome = InvocationOutcome.SUCCESS
    expected_status: ProviderStatus = ProviderStatus.AVAILABLE
    expected_markers: tuple[str, ...] = ()
    forbidden_markers: tuple[str, ...] = ()
    notes: str = ""

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "FixtureCase":
        markers: dict[str, tuple[str, ...]] = {}
        for name in ("expected_markers", "forbidden_markers"):
            value = mapping.get(name, ())
            if type(value) not in (list, tuple):
                raise EvaluationError("invalid_" + name)
            markers[name] = tuple(value)
        return cls(
            case_id=mapping["case_id"],
            task=mapping["task"],
            prompt=mapping["prompt"],
            capabilities=_capabilities(mapping.get("capabilities", ()), "capabilities"),
            scenario=mapping["scenario"],
            expected_outcome=InvocationOutcome(mapping.get(
                "expected_outcome", "SUCCESS")),
            expected_status=ProviderStatus(mapping.get(
                "expected_status", "AVAILABLE")),
            expected_markers=markers["expected_markers"],
            forbidden_markers=markers["forbidden_markers"],
            notes=str(mapping.get("notes", "")),
        )

    def __post_init__(self) -> None:
        _validate_id(self.case_id, "case_id")
        _validate_id(self.task, "task")
        _validate_text(self.prompt, "prompt", maximum=MAX_PROMPT_BYTES)
        _capabilities(self.capabilities, "capabilities")
        if type(self.scenario) is not str or not re.fullmatch(r"[a-z_]{1,40}", self.scenario):
            raise EvaluationError("invalid_scenario")
        for name in ("expected_markers", "forbidden_markers"):
            value = getattr(self, name)
            if type(value) is not tuple or not all(
                type(item) is str and 1 <= len(item) <= 256 for item in value
            ):
                raise EvaluationError("invalid_" + name)
        if type(self.notes) is not str or len(self.notes) > 512 or "\x00" in self.notes:
            raise EvaluationError("invalid_notes")

    def to_request(self, request_id_prefix: str = "ai-eval") -> ProviderRequest:
        """Build the bounded request contract for this fixture case."""
        return ProviderRequest(
            case_id=self.case_id,
            prompt=self.prompt,
            required_capabilities=self.capabilities,
            scenario=self.scenario,
            request_id=_validate_id(
                request_id_prefix + "-" + self.case_id, "request_id"),
            expected_markers=self.expected_markers,
            forbidden_markers=self.forbidden_markers,
        )


@dataclass(frozen=True)
class FixtureSet:
    version: str
    seed: int
    generated_at: str
    cases: tuple[FixtureCase, ...]

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "FixtureSet":
        cases = mapping.get("cases", ())
        if type(cases) is not list:
            raise EvaluationError("invalid_fixture_cases")
        return cls(mapping["version"], mapping["seed"], mapping["generated_at"],
                   tuple(FixtureCase.from_mapping(item) for item in cases))

    def __post_init__(self) -> None:
        _validate_id(self.version, "fixture_version")
        if type(self.seed) is not int or not 0 <= self.seed <= 2**32 - 1:
            raise EvaluationError("invalid_seed")
        _validate_text(self.generated_at, "generated_at", maximum=64)
        if not self.cases or any(not isinstance(c, FixtureCase) for c in self.cases):
            raise EvaluationError("invalid_fixture_cases")
        if len({c.case_id for c in self.cases}) != len(self.cases):
            raise EvaluationError("duplicate_fixture_case_id")


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    task: str
    capabilities: frozenset[Capability]
    request_prompt: str
    result: ProviderResponse
    expected_outcome: InvocationOutcome
    expected_status: ProviderStatus
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "task": self.task,
            "capabilities": sorted(item.value for item in self.capabilities),
            "request_prompt": redact_sensitive(self.request_prompt)[0],
            "result": self.result.to_dict(),
            "expected_outcome": self.expected_outcome.value,
            "expected_status": self.expected_status.value,
            "notes": [redact_sensitive(n)[0] for n in self.notes],
        }


@dataclass(frozen=True)
class EvaluationReport:
    schema_version: str
    fixture: FixtureSet
    cases: tuple[CaseResult, ...]
    comparison: dict[str, Any]
    fingerprint: str
    offline: bool = True
    live_calls: int = 0
    limitations: tuple[str, ...] = ()
    configs: tuple[ProviderConfig, ...] = ()
    routing: tuple[RoutingDecision, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    base_sha: str = "unknown"
    head_sha: str = "unknown"

    def __post_init__(self) -> None:
        if not isinstance(self.offline, bool):
            raise EvaluationError("invalid_offline_flag")
        if type(self.live_calls) is not int or self.live_calls < 0:
            raise EvaluationError("invalid_live_calls")
        typed_fields = {
            "configs": ProviderConfig,
            "routing": RoutingDecision,
            "evidence": Evidence,
        }
        for name, expected in typed_fields.items():
            value = getattr(self, name)
            if type(value) is not tuple or not all(
                isinstance(item, expected) for item in value
            ):
                raise EvaluationError("invalid_" + name)
        for name in ("base_sha", "head_sha"):
            value = getattr(self, name)
            if value != "unknown" and (
                type(value) is not str or not re.fullmatch(r"[0-9a-f]{40}", value)
            ):
                raise EvaluationError("invalid_" + name)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "fingerprint": self.fingerprint,
            "offline": self.offline,
            "live_calls": self.live_calls,
            "fixture": {
                "version": self.fixture.version,
                "seed": self.fixture.seed,
                "generated_at": self.fixture.generated_at,
            },
            "configs": [config.to_dict() for config in self.configs],
            "cases": [c.to_dict() for c in self.cases],
            "comparison": self.comparison,
            "routing": [decision.to_dict() for decision in self.routing],
            "evidence": [item.to_dict() for item in self.evidence],
            "base_sha": self.base_sha,
            "head_sha": self.head_sha,
            "limitations": [redact_sensitive(x)[0] for x in self.limitations],
        }


__all__ = [
    "Capability", "CaseResult", "Confidence", "ErrorCategory", "EvaluationError",
    "EvaluationReport", "Evidence", "FixtureCase", "FixtureSet", "InvocationOutcome",
    "LiveModeAuthorization", "PricingEntry", "ProviderConfig", "ProviderRequest",
    "ProviderResponse", "ProviderStatus", "RoutingDecision", "SafetyPolicyResult",
    "ScoreBreakdown", "assert_live_mode_allowed", "parse_decimal", "redact_sensitive",
]

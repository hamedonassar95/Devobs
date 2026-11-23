"""Offline-first, provider-neutral evaluation harness.

No module in this package opens a socket, reads a credential or calls a paid
API. All evaluations use deterministic in-memory fixtures.
"""

from .engine import EvaluationEngine, EvaluationInputError, build_default_configs
from .gate import (
    EXPECTED_FINGERPRINT,
    GATE_SCHEMA_VERSION,
    GateDecision,
    GateResult,
    evaluate_gate,
)
from .models import (
    Capability,
    Confidence,
    ErrorCategory,
    EvaluationError,
    Evidence,
    InvocationOutcome,
    ProviderConfig,
    ProviderRequest,
    ProviderResponse,
    ProviderStatus,
    RoutingDecision,
    SafetyPolicyResult,
    ScoreBreakdown,
)
from .pricing import PricingCatalog

__all__ = [
    "Capability",
    "Confidence",
    "ErrorCategory",
    "EvaluationEngine",
    "EvaluationError",
    "EvaluationInputError",
    "Evidence",
    "EXPECTED_FINGERPRINT",
    "GATE_SCHEMA_VERSION",
    "GateDecision",
    "GateResult",
    "InvocationOutcome",
    "PricingCatalog",
    "ProviderConfig",
    "ProviderRequest",
    "ProviderResponse",
    "ProviderStatus",
    "RoutingDecision",
    "SafetyPolicyResult",
    "ScoreBreakdown",
    "build_default_configs",
    "evaluate_gate",
]

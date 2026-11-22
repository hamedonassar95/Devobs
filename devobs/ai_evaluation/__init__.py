"""Offline-first, provider-neutral evaluation harness.

No module in this package opens a socket, reads a credential or calls a paid
API. All evaluations use deterministic in-memory fixtures.
"""

from .engine import EvaluationEngine, EvaluationInputError, build_default_configs
from .models import (
    Capability,
    Confidence,
    ErrorCategory,
    EvaluationError,
    InvocationOutcome,
    ProviderConfig,
    ProviderResponse,
    ProviderStatus,
    SafetyPolicyResult,
)
from .pricing import PricingCatalog

__all__ = [
    "Capability",
    "Confidence",
    "ErrorCategory",
    "EvaluationEngine",
    "EvaluationError",
    "EvaluationInputError",
    "InvocationOutcome",
    "PricingCatalog",
    "ProviderConfig",
    "ProviderResponse",
    "ProviderStatus",
    "SafetyPolicyResult",
    "build_default_configs",
]

"""Provider adapters with deterministic offline defaults.

No network call, credential read, or billable request occurs on import.
The xAI adapter is exposed here for callers that explicitly opt in.
"""

from __future__ import annotations

from .xai_adapter import (
    XAI_BASE_URL,
    XaiAdapter,
    XaiAuthorization,
    XaiConfig,
    XaiProvider,
    XaiRequest,
    XaiResult,
    XaiState,
    create_xai_provider,
    load_xai_config,
)
from .xai_cost import CostEstimate, estimate_max_request_cost, ticks_to_usd

__all__ = (
    "XAI_BASE_URL",
    "XaiAdapter",
    "XaiAuthorization",
    "XaiConfig",
    "XaiProvider",
    "XaiRequest",
    "XaiResult",
    "XaiState",
    "CostEstimate",
    "create_xai_provider",
    "estimate_max_request_cost",
    "load_xai_config",
    "ticks_to_usd",
)

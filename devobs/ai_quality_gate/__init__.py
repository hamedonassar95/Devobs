"""Offline, advisory AI quality and agent coordination gate.

This package composes the repository's existing deterministic control plane,
two-agent contract, CI failure intelligence and human-approval semantics into a
single read-only ``DRY_RUN`` decision. It adds no execution path, no approval
authority and no network transport.
"""

from __future__ import annotations

from .engine import AIQualityGate
from .models import GATE_SCHEMA, MODE_DRY_RUN, finalize_result, validate_result

__all__ = [
    "AIQualityGate",
    "GATE_SCHEMA",
    "MODE_DRY_RUN",
    "finalize_result",
    "validate_result",
]

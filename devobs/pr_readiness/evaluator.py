"""Deterministic PR readiness evaluator.

Public entrypoint requested by PR Readiness Engine task.
"""
from __future__ import annotations

from typing import Any, Mapping

from .policy import evaluate_pr_readiness


def evaluate(evidence: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Evaluate PR evidence and return deterministic readiness report."""
    return evaluate_pr_readiness(evidence)

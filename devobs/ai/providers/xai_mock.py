"""Deterministic offline mock for the xAI adapter.

This module makes no network call, reads no credential, and produces text that
is explicitly labeled as a mock. It can never return ``VERIFIED_RESPONSE``.
"""
from __future__ import annotations

import hashlib
from decimal import Decimal

from .xai_adapter import (
    XaiAuthorization,
    XaiConfig,
    XaiInputError,
    XaiRequest,
    XaiResult,
    XaiState,
    _safe_log,
    _validate_text,
)
from .xai_cost import CostEstimate, estimate_max_request_cost

MOCK_SOURCE = "xai_offline_mock"
_MOCK_PREFIX = "MOCK RESPONSE - NOT a real Grok response"


class DeterministicXaiMock:
    """Stable, offline advisory responses for dry-run and tests."""

    def __init__(self, config: XaiConfig) -> None:
        if not isinstance(config, XaiConfig):
            raise XaiInputError("invalid_configuration")
        self.config = config

    def complete(
        self,
        request: XaiRequest,
        authorization: XaiAuthorization | None = None,
    ) -> XaiResult:
        try:
            prompt, redactions = _validate_text(request.prompt, "prompt")
        except XaiInputError as error:
            reason = str(error)
            logs = (_safe_log("mock_input_rejected",
                              state=XaiState.CONFIGURATION_BLOCKED,
                              reason=reason, request_id=request.request_id),)
            return XaiResult(
                state=XaiState.CONFIGURATION_BLOCKED,
                model=self.config.model,
                request_id=request.request_id,
                reason=reason,
                logs=logs,
            )

        digest_input = "\x1f".join(
            (self.config.model, request.request_id, prompt)).encode("utf-8")
        digest = hashlib.sha256(digest_input).hexdigest()
        text = (
            f"{_MOCK_PREFIX} [{digest[:12]}]: "
            "This deterministic offline reply is advisory only. No model was "
            "called, no credential was used, and no command, repository change, "
            "pull-request approval, or deployment was performed."
        )
        estimate: CostEstimate | None
        try:
            estimate = estimate_max_request_cost(self.config)
        except Exception:  # pragma: no cover - config is validated upstream
            estimate = None
        logs = (
            _safe_log("mock_response", state=XaiState.MOCK_SUCCESS,
                      model=self.config.model, request_id=request.request_id,
                      is_mock=True, source=MOCK_SOURCE,
                      input_redacted=bool(redactions)),
        )
        return XaiResult(
            state=XaiState.MOCK_SUCCESS,
            text=text,
            is_mock=True,
            source=MOCK_SOURCE,
            model=self.config.model,
            request_id=request.request_id,
            prompt_tokens=0,
            completion_tokens=0,
            reasoning_tokens=0,
            cost_usd=Decimal("0"),
            estimate=estimate,
            logs=logs,
        )


__all__ = ("DeterministicXaiMock", "MOCK_SOURCE")

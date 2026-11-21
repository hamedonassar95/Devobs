"""Schema validation for structured incident intelligence JSON summaries."""
from __future__ import annotations

from typing import Any

from .models import SCHEMA_VERSION
from .rules import (
    CATEGORY_CI_FAILURE,
    CATEGORY_CONFIGURATION,
    CATEGORY_DEPENDENCY,
    CATEGORY_INFRASTRUCTURE,
    CATEGORY_TEST,
    CATEGORY_TIMEOUT,
    CATEGORY_UNKNOWN,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    EVIDENCE_INFERRED,
    EVIDENCE_UNVERIFIED,
    EVIDENCE_VERIFIED,
)


class SchemaError(ValueError):
    """Fixed, non-sensitive validation code."""


_TOP_LEVEL = frozenset({
    "schema_version", "source", "category", "signal", "confidence", "summary",
    "evidence", "hypotheses", "recommendations", "warnings", "ai_provider", "guardrails",
})
_EVIDENCE_FIELDS = frozenset({"id", "source", "excerpt", "confidence"})
_HYPOTHESIS_FIELDS = frozenset({
    "id", "category", "statement", "confidence", "evidence_ids", "rationale",
})
_RECOMMENDATION_FIELDS = frozenset({
    "id", "action", "rationale", "hypothesis_id", "requires_human_approval",
})
_AI_FIELDS = frozenset({"status", "summary"})
_GUARDRAIL_FIELDS = frozenset({
    "read_only", "modifies_code", "reruns_workflows", "merges_prs", "deploys",
    "automatic_fixes", "external_api_calls_by_default", "human_approval_required",
})
_CATEGORIES = frozenset({
    CATEGORY_CI_FAILURE, CATEGORY_CONFIGURATION, CATEGORY_DEPENDENCY,
    CATEGORY_INFRASTRUCTURE, CATEGORY_TEST, CATEGORY_TIMEOUT, CATEGORY_UNKNOWN,
})
_CONFIDENCES = frozenset({CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW})
_EVIDENCE_CONFIDENCES = frozenset({EVIDENCE_VERIFIED, EVIDENCE_INFERRED, EVIDENCE_UNVERIFIED})
_AI_STATUSES = frozenset({"disabled", "available", "error", "skipped"})


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise SchemaError(code)


def _is_nonempty_string(value: Any) -> bool:
    return type(value) is str and bool(value.strip())


def _is_string_list(value: Any) -> bool:
    return type(value) is list and all(type(item) is str for item in value)


def validate_report_json(payload: Any) -> bool:
    """Validate a decoded report and its internal evidence references."""
    _require(type(payload) is dict and set(payload) == _TOP_LEVEL, "invalid_report_fields")
    _require(payload["schema_version"] == SCHEMA_VERSION, "unsupported_schema_version")
    for field in ("source", "category", "signal", "confidence", "summary"):
        _require(_is_nonempty_string(payload[field]), f"invalid_{field}")

    evidence = payload["evidence"]
    _require(type(evidence) is list and bool(evidence), "invalid_evidence")
    evidence_ids: set[str] = set()
    for item in evidence:
        _require(type(item) is dict and set(item) == _EVIDENCE_FIELDS, "invalid_evidence_fields")
        _require(_is_nonempty_string(item["id"]), "invalid_evidence_id")
        _require(_is_nonempty_string(item["source"]), "invalid_evidence_source")
        _require(type(item["excerpt"]) is str, "invalid_evidence_excerpt")
        _require(item["confidence"] in _EVIDENCE_CONFIDENCES, "invalid_evidence_confidence")
        _require(item["id"] not in evidence_ids, "duplicate_evidence_id")
        evidence_ids.add(item["id"])

    hypotheses = payload["hypotheses"]
    _require(type(hypotheses) is list and bool(hypotheses), "invalid_hypotheses")
    hypothesis_ids: set[str] = set()
    for item in hypotheses:
        _require(type(item) is dict and set(item) == _HYPOTHESIS_FIELDS, "invalid_hypothesis_fields")
        _require(_is_nonempty_string(item["id"]), "invalid_hypothesis_id")
        _require(item["category"] in _CATEGORIES, "invalid_hypothesis_category")
        _require(_is_nonempty_string(item["statement"]), "invalid_hypothesis_statement")
        _require(item["confidence"] in _CONFIDENCES, "invalid_hypothesis_confidence")
        _require(_is_string_list(item["evidence_ids"]) and bool(item["evidence_ids"]),
                 "invalid_evidence_references")
        _require(set(item["evidence_ids"]).issubset(evidence_ids),
                 "dangling_evidence_reference")
        _require(type(item["rationale"]) is str, "invalid_hypothesis_rationale")
        _require(item["id"] not in hypothesis_ids, "duplicate_hypothesis_id")
        hypothesis_ids.add(item["id"])

    recommendations = payload["recommendations"]
    _require(type(recommendations) is list and bool(recommendations), "invalid_recommendations")
    for item in recommendations:
        _require(type(item) is dict and set(item) == _RECOMMENDATION_FIELDS,
                 "invalid_recommendation_fields")
        _require(_is_nonempty_string(item["id"]), "invalid_recommendation_id")
        _require(_is_nonempty_string(item["action"]), "invalid_recommendation_action")
        _require(type(item["rationale"]) is str, "invalid_recommendation_rationale")
        _require(item["hypothesis_id"] in hypothesis_ids, "dangling_hypothesis_reference")
        _require(item["requires_human_approval"] is True, "human_approval_not_required")

    _require(_is_string_list(payload["warnings"]), "invalid_warnings")

    ai_provider = payload["ai_provider"]
    _require(type(ai_provider) is dict and set(ai_provider) == _AI_FIELDS,
             "invalid_ai_provider_fields")
    _require(ai_provider["status"] in _AI_STATUSES, "invalid_ai_provider_status")
    _require(type(ai_provider["summary"]) is str, "invalid_ai_provider_summary")

    guardrails = payload["guardrails"]
    _require(type(guardrails) is dict and set(guardrails) == _GUARDRAIL_FIELDS,
             "invalid_guardrail_fields")
    _require(all(type(value) is bool for value in guardrails.values()),
             "invalid_guardrail_value")
    _require(guardrails["automatic_fixes"] is False, "automatic_fixes_enabled")
    _require(guardrails["human_approval_required"] is True, "human_approval_not_required")
    return True

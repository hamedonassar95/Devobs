#!/usr/bin/env python3
"""Strict parser/validator for the Phase 8 machine-readable investigation contract."""

from __future__ import annotations
import json, math, re
from dataclasses import dataclass

MARKER = "<!-- devobs-investigation-contract:v1 -->"
FENCE = re.compile(r"\x60\x60\x60json\s*(\{.*?\})\s*\x60\x60\x60", re.S)
ALLOWED_DECISIONS = {"FIX_FORWARD", "MANUAL_REVIEW", "NO_ACTION"}
REQUIRED_KEYS = {"decision", "confidence", "reversible", "repository_scoped", "proposed_change"}


@dataclass(frozen=True)
class Contract:
    valid: bool
    reason: str
    data: dict | None = None


def parse(text: object) -> Contract:
    if not isinstance(text, str) or text.count(MARKER) != 1:
        return Contract(False, "exactly one contract marker is required")
    matches = FENCE.findall(text)
    if len(matches) != 1:
        return Contract(False, "exactly one JSON object fence is required")
    try:
        data = json.loads(matches[0])
    except json.JSONDecodeError:
        return Contract(False, "contract JSON is invalid")
    if not isinstance(data, dict) or set(data) != REQUIRED_KEYS:
        return Contract(False, "contract keys must match the v1 schema exactly")
    if data["decision"] not in ALLOWED_DECISIONS:
        return Contract(False, "decision is invalid")
    confidence = data["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
        return Contract(False, "confidence must be a finite number from 0 to 1")
    if type(data["reversible"]) is not bool or type(data["repository_scoped"]) is not bool:
        return Contract(False, "scope flags must be booleans")
    change = data["proposed_change"]
    if not isinstance(change, str) or not change.strip() or len(change) > 500:
        return Contract(False, "proposed_change must be 1..500 characters")
    return Contract(True, "valid v1 investigation contract", data)

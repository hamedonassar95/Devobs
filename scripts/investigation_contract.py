#!/usr/bin/env python3
"""Strict parser/validator for Phase 8 machine-readable investigation contracts."""

from __future__ import annotations
import json, math, re
from dataclasses import dataclass

MARKER_V1 = "<!-- devobs-investigation-contract:v1 -->"
MARKER_V2 = "<!-- devobs-investigation-contract:v2 -->"
FENCE = re.compile(r"\x60\x60\x60json\s*(\{.*?\})\s*\x60\x60\x60", re.S)
ALLOWED_DECISIONS = {"FIX_FORWARD", "MANUAL_REVIEW", "NO_ACTION"}
V1_KEYS = {"decision", "confidence", "reversible", "repository_scoped", "proposed_change"}
V2_KEYS = V1_KEYS | {"incident_number", "incident_run_id"}


@dataclass(frozen=True)
class Contract:
    valid: bool
    reason: str
    data: dict | None = None


def _validate_common(data: dict) -> Contract | None:
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
    return None


def parse(text: object, expected_incident_number: int | None = None, expected_run_id: str | None = None) -> Contract:
    if not isinstance(text, str):
        return Contract(False, "contract text is required")
    v1_count, v2_count = text.count(MARKER_V1), text.count(MARKER_V2)
    if v1_count + v2_count != 1:
        return Contract(False, "exactly one contract marker is required")
    matches = FENCE.findall(text)
    if len(matches) != 1:
        return Contract(False, "exactly one JSON object fence is required")
    try:
        data = json.loads(matches[0])
    except json.JSONDecodeError:
        return Contract(False, "contract JSON is invalid")
    if not isinstance(data, dict):
        return Contract(False, "contract JSON must be an object")

    if v2_count == 1:
        if set(data) != V2_KEYS:
            return Contract(False, "contract keys must match the v2 schema exactly")
        if type(data["incident_number"]) is not int or data["incident_number"] <= 0:
            return Contract(False, "incident_number must be a positive integer")
        run_id = data["incident_run_id"]
        if not isinstance(run_id, str) or not run_id.strip() or len(run_id) > 200:
            return Contract(False, "incident_run_id must be 1..200 characters")
        if expected_incident_number is None or expected_run_id is None:
            return Contract(False, "v2 contract requires trusted incident binding context")
        if data["incident_number"] != expected_incident_number:
            return Contract(False, "incident_number does not match trusted incident")
        if run_id != expected_run_id:
            return Contract(False, "incident_run_id does not match trusted incident")
        common = _validate_common(data)
        return common or Contract(True, "valid v2 investigation contract", data)

    if set(data) != V1_KEYS:
        return Contract(False, "contract keys must match the v1 schema exactly")
    common = _validate_common(data)
    return common or Contract(True, "valid v1 investigation contract", data)

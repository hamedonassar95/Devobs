"""Offline semantic version comparison for explicit compatibility requirements."""
from __future__ import annotations

import re
from typing import Any

from .models import CompatibilityError

_VERSION_RE = re.compile(r"^v?(\d+)(?:\.(\d+)){0,3}$")
_OPERATORS = ("==", "!=", ">=", "<=", ">", "<")


def parse_version(value: Any) -> tuple[int, int, int, int]:
    """Parse a bounded dotted numeric version into a comparable tuple."""
    if not isinstance(value, str):
        raise CompatibilityError("invalid_version")
    text = value.strip()
    if not _VERSION_RE.fullmatch(text):
        raise CompatibilityError("invalid_version")
    text = text[1:] if text.startswith("v") else text
    parts = [int(part) for part in text.split(".")]
    padded = parts + [0] * (4 - len(parts))
    return (padded[0], padded[1], padded[2], padded[3])


def parse_spec(spec: Any) -> tuple[tuple[str, tuple[int, int, int, int]], ...]:
    """Parse a bounded comma-separated version requirement."""
    if not isinstance(spec, str) or not spec.strip():
        raise CompatibilityError("invalid_version_spec")
    clauses: list[tuple[str, tuple[int, int, int, int]]] = []
    for raw in spec.split(","):
        clause = raw.strip()
        if not clause:
            raise CompatibilityError("invalid_version_spec")
        operator = next((op for op in _OPERATORS if clause.startswith(op)), "")
        if not operator:
            raise CompatibilityError("invalid_version_spec")
        version_text = clause[len(operator):].strip()
        if not version_text:
            raise CompatibilityError("invalid_version_spec")
        clauses.append((operator, parse_version(version_text)))
    return tuple(clauses)


def satisfies(version: Any, spec: Any) -> bool:
    """Return whether a version satisfies every clause of a version spec."""
    current = parse_version(version)
    for operator, expected in parse_spec(spec):
        if operator == "==" and current != expected:
            return False
        if operator == "!=" and current == expected:
            return False
        if operator == ">=" and current < expected:
            return False
        if operator == "<=" and current > expected:
            return False
        if operator == ">" and current <= expected:
            return False
        if operator == "<" and current >= expected:
            return False
    return True


__all__ = ["parse_spec", "parse_version", "satisfies"]

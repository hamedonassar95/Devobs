"""Immutable catalog of the deterministic adviser's supported runbooks."""
from types import MappingProxyType


# Each entry pairs a category with its stable runbook ID and offline test
# instruction. Keep this as the only category-to-runbook mapping.
RUNBOOK_CATALOG = MappingProxyType({
    "ci_failure": (
        "RB-CI-01",
        "Check the failing CI job and compare the pinned source SHA",
    ),
    "high_error_rate": (
        "RB-SLO-01",
        "Check recent error-rate changes against approved SLO windows",
    ),
    "capacity_pressure": (
        "RB-CAP-01",
        "Review resource saturation and capacity forecasts without changing resources",
    ),
})

"""Validate evaluation split assignments using opaque incident metadata only.

This module never reads incident content or establishes consent, anonymization,
label provenance, or label correctness. It only detects assigned group tokens
that would place related cases in different evaluation splits.
"""
from __future__ import annotations

import re
from typing import Any


class EvaluationSplitError(ValueError):
    """A fixed diagnostic that does not include case or group identifiers."""


_SPLITS = ("calibration", "development", "holdout")
_CASE_KEYS = frozenset({"case_token", "incident_group_token", "split", "category"})
_OPAQUE_TOKEN = re.compile(r"[a-f0-9]{32}\Z")
_CATEGORY = re.compile(r"[a-z][a-z0-9_]{0,39}\Z")
_MAX_CASES = 1_000


def summarize_review_splits(cases: Any) -> dict[str, Any]:
    """Reject cross-split incident groups and return aggregate counts only.

    Tokens must be opaque random identifiers. The format check cannot prove
    that a token is random or that its source was anonymized.
    """
    if type(cases) is not list or not cases:
        raise EvaluationSplitError("invalid_cases")
    if len(cases) > _MAX_CASES:
        raise EvaluationSplitError("too_many_cases")

    case_tokens: set[str] = set()
    group_splits: dict[str, str] = {}
    split_counts = {split: 0 for split in _SPLITS}
    group_counts = {split: 0 for split in _SPLITS}
    category_counts = {split: {} for split in _SPLITS}

    for case in cases:
        if type(case) is not dict or set(case) != _CASE_KEYS:
            raise EvaluationSplitError("invalid_case")

        case_token = case["case_token"]
        group_token = case["incident_group_token"]
        split = case["split"]
        category = case["category"]
        if (
            type(case_token) is not str
            or _OPAQUE_TOKEN.fullmatch(case_token) is None
            or type(group_token) is not str
            or _OPAQUE_TOKEN.fullmatch(group_token) is None
        ):
            raise EvaluationSplitError("invalid_case")
        if case_token in case_tokens:
            raise EvaluationSplitError("duplicate_case_token")
        case_tokens.add(case_token)

        if type(split) is not str or split not in _SPLITS:
            raise EvaluationSplitError("invalid_split")
        if type(category) is not str or _CATEGORY.fullmatch(category) is None:
            raise EvaluationSplitError("invalid_category")

        previous_split = group_splits.get(group_token)
        if previous_split is not None and previous_split != split:
            raise EvaluationSplitError("split_leakage")
        if previous_split is None:
            group_splits[group_token] = split
            group_counts[split] += 1

        split_counts[split] += 1
        category_counts[split][category] = category_counts[split].get(category, 0) + 1

    return {
        "case_count": len(cases),
        "split_counts": split_counts,
        "group_counts": group_counts,
        "category_counts_by_split": {
            split: dict(sorted(category_counts[split].items()))
            for split in _SPLITS
        },
    }

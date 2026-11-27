"""Deterministic, dependency-free metrics for the KI-3 evaluator."""

from __future__ import annotations

import math
from typing import Mapping, Sequence


class EvaluationError(ValueError):
    """Fixed validation code; does not disclose fixture text."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _fail(code: str) -> None:
    raise EvaluationError(code)


def _validate_k(k: object) -> int:
    if type(k) is not int or not 1 <= k <= 20:
        _fail("invalid_k")
    return k


def _unique_ids(values: Sequence[str]) -> list[str]:
    if isinstance(values, (str, bytes)):
        _fail("ranked_ids_invalid")
    result = []
    seen = set()
    for value in values:
        if type(value) is not str or not value:
            _fail("ranked_ids_invalid")
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _validate_relevance_ids(relevant_ids: object) -> set[str] | frozenset[str]:
    if (not isinstance(relevant_ids, (set, frozenset))
            or any(type(item) is not str for item in relevant_ids)):
        _fail("relevance_ids_invalid")
    return relevant_ids


def precision_at_k(
    ranked_ids: Sequence[str], relevant_ids: set[str] | frozenset[str], k: int,
) -> float:
    k = _validate_k(k)
    ranked = _unique_ids(ranked_ids)
    relevant = _validate_relevance_ids(relevant_ids)
    return sum(item in relevant for item in ranked[:k]) / k


def recall_at_k(
    ranked_ids: Sequence[str], relevant_ids: set[str] | frozenset[str], k: int,
) -> float | None:
    k = _validate_k(k)
    ranked = _unique_ids(ranked_ids)
    relevant = _validate_relevance_ids(relevant_ids)
    if not relevant:
        return None
    return sum(item in relevant for item in ranked[:k]) / len(relevant)


def hit_rate_at_k(
    ranked_ids: Sequence[str], relevant_ids: set[str] | frozenset[str], k: int,
) -> float | None:
    k = _validate_k(k)
    ranked = _unique_ids(ranked_ids)
    relevant = _validate_relevance_ids(relevant_ids)
    if not relevant:
        return None
    return float(any(item in relevant for item in ranked[:k]))


def mean_reciprocal_rank(
    ranked_ids: Sequence[str], relevant_ids: set[str] | frozenset[str],
) -> float | None:
    ranked = _unique_ids(ranked_ids)
    relevant = _validate_relevance_ids(relevant_ids)
    if not relevant:
        return None
    return next((1.0 / rank for rank, item in enumerate(ranked, 1) if item in relevant), 0.0)


def ndcg_at_k(
    ranked_ids: Sequence[str], graded_relevance: Mapping[str, int], k: int,
) -> float | None:
    k = _validate_k(k)
    ranked = _unique_ids(ranked_ids)
    if type(graded_relevance) is not dict:
        _fail("graded_relevance_invalid")
    if any(type(item) is not str or type(grade) is not int or not 1 <= grade <= 3
           for item, grade in graded_relevance.items()):
        _fail("graded_relevance_invalid")
    if not graded_relevance:
        return None
    def gain(grade: int) -> int:
        return (2 ** grade) - 1

    dcg = sum(gain(graded_relevance.get(item, 0)) / math.log2(rank + 1)
              for rank, item in enumerate(ranked[:k], 1))
    ideal = sorted(graded_relevance.values(), reverse=True)[:k]
    idcg = sum(gain(grade) / math.log2(rank + 1) for rank, grade in enumerate(ideal, 1))
    return dcg / idcg if idcg else None


def citation_reference_accuracy(results: Sequence[dict[str, object]], index) -> float | None:
    if not results:
        return None
    return sum(index.validates_citation(item) for item in results) / len(results)


def scope_exclusion_correctness(results: Sequence[dict[str, object]], index) -> float:
    if not results:
        return 1.0
    return sum(index.validates_scope(item) for item in results) / len(results)


def empty_result_correctness(
    results: Sequence[dict[str, object]], relevant_ids: set[str] | frozenset[str],
) -> float:
    relevant = _validate_relevance_ids(relevant_ids)
    return float((len(results) == 0) == (len(relevant) == 0))

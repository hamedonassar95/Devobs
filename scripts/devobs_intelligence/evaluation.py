"""Synthetic-only, offline evaluation contract (behavior pending)."""


class EvaluationError(ValueError):
    """Privacy-preserving fixed diagnostic."""


def evaluate_cases(cases: list[dict], *, target_accuracy: float = 0.85) -> dict[str, object]:
    raise NotImplementedError("synthetic evaluation pending")

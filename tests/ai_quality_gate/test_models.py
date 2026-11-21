"""Schema and digest contract tests for the AI quality gate."""

from __future__ import annotations

import unittest

from devobs.ai_quality_gate.engine import AIQualityGate
from devobs.ai_quality_gate.models import (
    GateValidationError,
    compute_digest,
    finalize_result,
    validate_result,
)

try:
    from . import helpers as h
except ImportError:  # unittest discover -s tests/ai_quality_gate
    import helpers as h


class AIQualityGateSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = AIQualityGate().evaluate(
            h.snapshot(), ci_run=h.ci_run(), ci_jobs=h.ci_jobs()
        )

    def test_result_digest_is_deterministic(self):
        self.assertEqual(
            compute_digest(self.result), self.result["gate_digest"]
        )
        again = AIQualityGate().evaluate(
            h.snapshot(), ci_run=h.ci_run(), ci_jobs=h.ci_jobs()
        )
        self.assertEqual(again, self.result)

    def test_any_authorization_assertion_is_rejected(self):
        for field, value in (
            ("merge_authorized", True),
            ("human_approval", "APPROVED"),
            ("offline", False),
            ("mode", "EXECUTE"),
            ("advisory", {**self.result["advisory"], "influenced_decision": True}),
        ):
            with self.subTest(field=field):
                tampered = dict(self.result)
                tampered[field] = value
                with self.assertRaises(GateValidationError):
                    validate_result(tampered)

    def test_tampered_digest_is_rejected(self):
        tampered = dict(self.result)
        tampered["gate_digest"] = "0" * 64
        with self.assertRaises(GateValidationError):
            validate_result(tampered)

    def test_finalize_rejects_unknown_fields(self):
        payload = dict(self.result)
        payload.pop("gate_digest")
        payload["unexpected"] = True
        with self.assertRaises(GateValidationError):
            finalize_result(payload)


if __name__ == "__main__":
    unittest.main()

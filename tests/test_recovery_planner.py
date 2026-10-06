import unittest

from scripts.recovery_planner import evaluate


def eligible_record():
    return {
        "trusted_incident": True,
        "incident_open": True,
        "conclusion": "failure",
        "investigation_count": 1,
        "decision": "FIX_FORWARD",
        "confidence": 0.91,
        "reversible": True,
        "repository_scoped": True,
        "existing_recovery_pr": False,
        "proposed_change": "Adjust deterministic HTML validation and add regression test.",
    }


class RecoveryPlannerTests(unittest.TestCase):
    def test_eligible_fix_forward(self):
        plan = evaluate(eligible_record())
        self.assertTrue(plan.eligible)
        self.assertEqual(plan.status, "ELIGIBLE")
        self.assertEqual(plan.final_state, "PENDING HUMAN APPROVAL")

    def test_missing_evidence_fails_closed(self):
        record = eligible_record()
        del record["confidence"]
        self.assertFalse(evaluate(record).eligible)

    def test_untrusted_incident_rejected(self):
        record = eligible_record()
        record["trusted_incident"] = False
        self.assertFalse(evaluate(record).eligible)

    def test_non_failure_conclusion_rejected(self):
        record = eligible_record()
        record["conclusion"] = "cancelled"
        self.assertFalse(evaluate(record).eligible)

    def test_requires_exactly_one_investigation(self):
        record = eligible_record()
        record["investigation_count"] = 2
        self.assertFalse(evaluate(record).eligible)

    def test_manual_review_rejected(self):
        record = eligible_record()
        record["decision"] = "MANUAL_REVIEW"
        self.assertFalse(evaluate(record).eligible)

    def test_low_confidence_rejected(self):
        record = eligible_record()
        record["confidence"] = 0.79
        self.assertFalse(evaluate(record).eligible)

    def test_irreversible_change_rejected(self):
        record = eligible_record()
        record["reversible"] = False
        self.assertFalse(evaluate(record).eligible)

    def test_existing_recovery_pr_rejected(self):
        record = eligible_record()
        record["existing_recovery_pr"] = True
        self.assertFalse(evaluate(record).eligible)

    def test_sensitive_scope_rejected(self):
        record = eligible_record()
        record["proposed_change"] = "Rotate production credentials and change access control."
        plan = evaluate(record)
        self.assertFalse(plan.eligible)
        self.assertEqual(plan.risk, "high")


if __name__ == "__main__":
    unittest.main()

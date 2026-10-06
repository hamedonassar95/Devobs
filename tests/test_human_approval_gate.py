import unittest

from scripts.human_approval_gate import evaluate


def record():
    return {
        "verification_status": "VERIFIED",
        "approval": "APPROVE",
        "approver_is_human": True,
        "approver_has_write": True,
        "pr_open": True,
        "pr_merged": False,
    }


class HumanApprovalGateTests(unittest.TestCase):
    def test_authorizes_explicit_human_approval(self):
        result = evaluate(record())
        self.assertTrue(result.authorized)
        self.assertEqual(result.status, "HUMAN_APPROVED")

    def test_blocks_unverified_candidate(self):
        value = record()
        value["verification_status"] = "BLOCKED"
        self.assertFalse(evaluate(value).authorized)

    def test_blocks_missing_approval(self):
        value = record()
        value["approval"] = ""
        self.assertEqual(evaluate(value).status, "PENDING")

    def test_records_human_rejection(self):
        value = record()
        value["approval"] = "REJECT"
        result = evaluate(value)
        self.assertFalse(result.authorized)
        self.assertEqual(result.status, "REJECTED")

    def test_blocks_nonhuman_approver(self):
        value = record()
        value["approver_is_human"] = False
        self.assertFalse(evaluate(value).authorized)

    def test_blocks_approver_without_write(self):
        value = record()
        value["approver_has_write"] = False
        self.assertFalse(evaluate(value).authorized)

    def test_blocks_closed_pr(self):
        value = record()
        value["pr_open"] = False
        self.assertFalse(evaluate(value).authorized)

    def test_blocks_merged_pr(self):
        value = record()
        value["pr_merged"] = True
        self.assertFalse(evaluate(value).authorized)

    def test_fails_closed_on_missing_evidence(self):
        value = record()
        del value["approver_has_write"]
        self.assertEqual(evaluate(value).status, "BLOCKED")

    def test_does_not_treat_boolean_as_approval(self):
        value = record()
        value["approval"] = True
        self.assertFalse(evaluate(value).authorized)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


class WorkflowReviewStatusTests(unittest.TestCase):
    def test_workflow_summaries_do_not_claim_human_review_without_review(self):
        ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        incident = Path(".github/workflows/incident-response.yml").read_text(encoding="utf-8")

        self.assertNotIn("Human review completed", ci)
        self.assertNotIn("Human review completed", incident)
        self.assertIn("PR preview artifact is ready for maintainer review.", ci)
        self.assertIn(
            "This workflow dispatched the investigator; human review remains a separate step.",
            incident,
        )


if __name__ == "__main__":
    unittest.main()

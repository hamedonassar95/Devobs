"""Keep the efficiency agent's applicability and provenance gate explicit."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/efficiency-improver.md"
DOC = ROOT / "docs/EFFICIENCY_IMPROVER.md"


class EfficiencyApplicabilityTests(unittest.TestCase):
    def test_workflow_classifies_candidates_before_editing(self):
        source = WORKFLOW.read_text()
        self.assertIn("APPLICABLE", source)
        self.assertIn("NOT APPLICABLE", source)
        self.assertIn("BLOCKED", source)
        self.assertIn("dependencies", source)

    def test_workflow_preserves_external_source_provenance(self):
        source = " ".join(WORKFLOW.read_text().split())
        self.assertIn("source URL or commit", source)
        self.assertIn("Never copy an external patch blindly", source)

    def test_efficiency_docs_describe_the_same_gate(self):
        doc = DOC.read_text()
        self.assertIn("applicability gate", doc.lower())
        self.assertIn("NOT APPLICABLE", doc)
        self.assertIn("BLOCKED", doc)


if __name__ == "__main__":
    unittest.main()

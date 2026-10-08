"""Regressions for AI publisher permissions and recovery branch isolation."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".github/workflows/phase8b-ai-patch-generator.md"
LOCK = ROOT / ".github/workflows/phase8b-ai-patch-generator.lock.yml"
JSON_PUBLISHER = ROOT / ".github/workflows/phase8b-patch-publisher.yml"


class Phase8bAiPublisherPolicyTests(unittest.TestCase):
    def test_safe_output_can_read_actions_for_live_evidence_recheck(self):
        safe_outputs = LOCK.read_text().split("  safe_outputs:\n", 1)[1]
        self.assertIn("    permissions:\n      actions: read\n      contents: write", safe_outputs)

    def test_publishers_share_incident_scoped_concurrency_group(self):
        ai_source = SOURCE.read_text()
        json_source = JSON_PUBLISHER.read_text()
        ai_group = ai_source.split("concurrency:\n", 1)[1].split("\n", 1)[0]
        json_group = json_source.split("concurrency:\n", 1)[1].split("\n", 1)[0]
        self.assertEqual(ai_group, json_group)

    def test_ai_safe_output_enforces_recovery_branch_prefix(self):
        source = SOURCE.read_text()
        lock = LOCK.read_text()
        expected = "recovery/incident-${{ inputs.incident_number }}-"
        self.assertIn(f'branch-prefix: "{expected}"', source)
        self.assertIn(expected, lock)


if __name__ == "__main__":
    unittest.main()

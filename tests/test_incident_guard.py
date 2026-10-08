"""Run the real JS gate tests and verify the workflow embeds the tested code."""
from pathlib import Path
import subprocess
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class IncidentGuardTests(unittest.TestCase):
    def test_guard_behavior(self):
        result = subprocess.run(
            ['node', '--test', 'tests/incident_guard.test.cjs'],
            cwd=ROOT, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_workflow_uses_tested_guard_at_both_boundaries(self):
        source = (ROOT / 'scripts/incident_guard.cjs').read_text().split('module.exports')[0].rstrip()
        workflow = (ROOT / '.github/workflows/incident-investigator.md').read_text()
        # Remove YAML indentation, preserving JS content for exact comparison.
        normalized = '\n'.join(line.lstrip() for line in workflow.splitlines())
        code = '\n'.join(line.lstrip() for line in source.splitlines())
        self.assertEqual(normalized.count(code), 2)
        self.assertIn("if: needs.pre_activation.outputs.eligible == 'true'", workflow)
        self.assertIn('cancel-in-progress: false', workflow)
        self.assertIn('target: "${{ github.event.issue.number || inputs.issue_number }}"', workflow)
        self.assertNotIn('github.run_id', workflow.split('concurrency:', 1)[1].split('jobs:', 1)[0])

    def test_compiled_lock_preserves_the_safety_boundaries(self):
        lock = (ROOT / '.github/workflows/incident-investigator.lock.yml').read_text()
        refs = re.findall(r'^\s*uses: (\S+)', lock, re.MULTILINE)
        self.assertTrue(refs)
        self.assertTrue(all(re.search(r'@[0-9a-f]{40}$', ref) for ref in refs))
        self.assertIn("needs.pre_activation.outputs.eligible == 'true'", lock)
        self.assertIn('await incidentGuard({ github, context, core }, true);', lock)
        self.assertIn('cancel-in-progress: false', lock)

    def test_eligible_investigation_requires_comment_without_noop_fallback(self):
        workflow = (ROOT / '.github/workflows/incident-investigator.md').read_text()
        lock = (ROOT / '.github/workflows/incident-investigator.lock.yml').read_text()
        frontmatter = workflow.split('---', 2)[1]
        prompt = workflow.split('---', 2)[2]

        self.assertIn('add-comment:', frontmatter)
        self.assertIn('max: 1', frontmatter)
        self.assertIn('missing-data: false', frontmatter)
        self.assertIn('noop: false', frontmatter)
        self.assertIn('report-incomplete: false', frontmatter)
        self.assertIn('Every incident that passes the deterministic trust gates must receive exactly one', prompt)
        self.assertIn('call `add_comment` exactly once', prompt)
        self.assertIn('Do not say that a comment was posted until the `add_comment` call succeeds.', prompt)

        self.assertIn('Tools: add_comment, missing_tool', lock)
        self.assertIn('GH_AW_SAFE_OUTPUTS_CONFIG:', lock)
        self.assertIn('\\"add_comment\\"', lock)
        self.assertNotIn('"noop":', lock)
        self.assertNotIn('"missing_data":', lock)
        self.assertNotIn('"report_incomplete":', lock)

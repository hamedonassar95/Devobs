"""Run the real JS gate tests and verify the workflow embeds the tested code."""
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

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

    def test_missing_published_comment_fails_the_workflow(self):
        workflow = (ROOT / '.github/workflows/incident-investigator.md').read_text()
        lock = (ROOT / '.github/workflows/incident-investigator.lock.yml').read_text()
        frontmatter = workflow.split('---', 2)[1]

        self.assertIn('safe-outputs:\n  steps:\n    - name: Checkout trusted report validator', frontmatter)
        self.assertIn('persist-credentials: false', frontmatter)
        self.assertIn('Verify required incident report output', workflow)
        self.assertIn('node scripts/validate_incident_report.cjs', workflow)
        self.assertIn('<!-- devobs-investigation:v1 -->', workflow)
        self.assertIn('## AI Incident Investigation', workflow)

        safe_outputs = lock.split('  safe_outputs:\n', 1)[1].split('\n  conclusion:\n', 1)[0]
        download_index = safe_outputs.index('Download agent output artifact')
        checkout_index = safe_outputs.index('Checkout trusted report validator')
        validate_index = safe_outputs.index('Verify required incident report output')
        publish_index = safe_outputs.index('Process Safe Outputs')
        self.assertLess(download_index, checkout_index)
        self.assertLess(checkout_index, validate_index)
        self.assertLess(validate_index, publish_index)
        self.assertIn('Verify required incident report output', lock)
        self.assertIn('validate_incident_report.cjs', lock)
        self.assertIn('<!-- devobs-investigation:v1 -->', lock)
        self.assertIn('## AI Incident Investigation', lock)

    def test_publication_postcondition_accepts_one_report_and_rejects_noop(self):
        validator = ROOT / 'scripts/validate_incident_report.cjs'
        body = '<!-- devobs-investigation:v1 -->\n## AI Incident Investigation\n'

        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / 'agent_output.json'

            def run_validator(item):
                output_path.write_text(json.dumps({'items': [item], 'errors': []}) + '\n')
                return subprocess.run(
                    ['node', str(validator), str(output_path)],
                    cwd=ROOT, text=True, capture_output=True,
                )

            valid = run_validator({'type': 'add_comment', 'body': body})
            self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)

            noop = run_validator({'type': 'noop', 'message': 'see comment'})
            self.assertNotEqual(noop.returncode, 0)
            self.assertIn('incident report comment', noop.stderr)

            missing = run_validator({'type': 'add_comment', 'body': '## AI Incident Investigation\n'})
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn('unique marker', missing.stderr)

            repeated = run_validator({'type': 'add_comment', 'body': body + '<!-- devobs-investigation:v1 -->'})
            self.assertNotEqual(repeated.returncode, 0)
            self.assertIn('unique marker', repeated.stderr)

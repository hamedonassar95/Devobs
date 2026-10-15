"""Run the real JS gate tests and verify the workflow embeds the tested code."""
import json
import os
import re
import stat
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

        self.assertIn('post-steps:', workflow)
        self.assertIn('Verify required incident report output', workflow)
        self.assertIn('exactly one safe incident report comment', workflow)
        self.assertIn('<!-- devobs-investigation:v1 -->', workflow)
        self.assertIn('## AI Incident Investigation', workflow)

        self.assertIn('Verify required incident report output', lock)
        self.assertIn('exactly one safe incident report comment', lock)
        self.assertIn('<!-- devobs-investigation:v1 -->', lock)
        self.assertIn('## AI Incident Investigation', lock)

    def test_publication_postcondition_accepts_one_report_and_rejects_noop(self):
        workflow = (ROOT / '.github/workflows/incident-investigator.md').read_text()
        frontmatter = workflow.split('---', 2)[1]
        post_steps = frontmatter.split('post-steps:', 1)[1].split('\npermissions:', 1)[0]
        self.assertIn('    run: |\n', post_steps)
        raw_script = post_steps.split('    run: |\n', 1)[1]
        script_lines = []
        for line in raw_script.splitlines():
            if line.startswith('      '):
                script_lines.append(line[6:])
            elif line.strip():
                break
            else:
                script_lines.append('')
        run_script = '\n'.join(script_lines)
        body = '<!-- devobs-investigation:v1 -->\n## AI Incident Investigation\n'

        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / 'outputs.jsonl'
            copy_path = Path(directory) / 'safeoutputs.jsonl'
            agent_output_path = Path(directory) / 'agent_output.json'
            env = {
                **os.environ,
                'GH_AW_SAFE_OUTPUTS': str(output_path),
                'GH_AW_SAFE_OUTPUTS_COPY': str(copy_path),
                'GH_AW_AGENT_OUTPUT': str(agent_output_path),
            }

            def write_outputs(item, agent_item=None):
                serialized = json.dumps(item) + '\n'
                output_path.write_text(serialized)
                copy_path.write_text(serialized)
                agent_output_path.write_text(
                    json.dumps({'items': [agent_item or item], 'errors': []}) + '\n'
                )

            write_outputs({'type': 'add_comment', 'body': body})
            valid = subprocess.run(
                ['bash', '-e', '-c', run_script], env=env, text=True, capture_output=True,
            )
            self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)

            write_outputs({'type': 'noop', 'message': 'see comment'})
            missing = subprocess.run(
                ['bash', '-e', '-c', run_script], env=env, text=True, capture_output=True,
            )
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn('exactly one safe incident report comment', missing.stdout)

            write_outputs(
                {'type': 'add_comment', 'body': body},
                {'type': 'noop', 'message': 'publisher has no report'},
            )
            missing_published = subprocess.run(
                ['bash', '-e', '-c', run_script], env=env, text=True, capture_output=True,
            )
            self.assertNotEqual(missing_published.returncode, 0)
            self.assertIn('Validated agent output must contain exactly one', missing_published.stdout)

            missing_marker = {
                'type': 'add_comment',
                'body': '## AI Incident Investigation\n\nA concise report.\n',
            }
            canonical_agent_comment = {
                'type': 'add_comment',
                'body': '## AI Incident Investigation\n\nA canonicalized report.\n',
            }
            write_outputs(missing_marker, canonical_agent_comment)
            read_only_mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
            for path in (output_path, copy_path, agent_output_path):
                path.chmod(read_only_mode)
            normalized = subprocess.run(
                ['bash', '-e', '-c', run_script], env=env, text=True, capture_output=True,
            )
            self.assertEqual(normalized.returncode, 0, normalized.stdout + normalized.stderr)
            result = json.loads(output_path.read_text().splitlines()[0])
            self.assertTrue(result['body'].startswith('<!-- devobs-investigation:v1 -->\n\n'))
            staged_result = json.loads(copy_path.read_text().splitlines()[0])
            self.assertTrue(staged_result['body'].startswith('<!-- devobs-investigation:v1 -->\n\n'))
            published_agent = json.loads(agent_output_path.read_text())
            self.assertTrue(
                published_agent['items'][0]['body'].startswith('<!-- devobs-investigation:v1 -->\n\n')
            )
            self.assertIn('A canonicalized report.', published_agent['items'][0]['body'])
            for path in (output_path, copy_path, agent_output_path):
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), read_only_mode)

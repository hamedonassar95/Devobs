import unittest
from pathlib import Path

WORKFLOW = Path('.github/workflows/one-click-deploy.yml').read_text()

class OneClickDeployContractTests(unittest.TestCase):
    def test_rollback_uses_a_separate_workflow_on_fallback_sha(self):
        self.assertIn('actions: write', WORKFLOW)
        self.assertIn('run: python3 scripts/dispatch_rollback.py', WORKFLOW)
        helper = Path('scripts/dispatch_rollback.py').read_text()
        self.assertIn('"ref": rollback_sha', helper)
        self.assertIn('rollback-pages.yml', helper)
        self.assertNotIn('id: rollback-deploy', WORKFLOW)

    def test_report_runs_for_terminal_paths_and_uses_unique_artifact_name(self):
        self.assertIn('if: ${{ always() }}', WORKFLOW)
        self.assertIn('github-pages-candidate-${{ github.run_id }}-${{ github.run_attempt }}', WORKFLOW)
        report = WORKFLOW.split('  report:\n', 1)[1]
        self.assertNotIn('if: ${{ needs.validate.result ==', report)

if __name__ == '__main__':
    unittest.main()

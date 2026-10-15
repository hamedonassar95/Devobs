import re
import unittest
from pathlib import Path

WORKFLOW = Path('.github/workflows/aws.yml').read_text()


class AwsWorkflowContractTests(unittest.TestCase):
    def test_aws_deployment_is_manually_confirmed(self):
        self.assertIn('workflow_dispatch:', WORKFLOW)
        self.assertIn('inputs.confirm_deploy == true', WORKFLOW)
        self.assertNotIn('\n  push:', WORKFLOW)

    def test_aws_configuration_is_checked_before_oidc_authentication(self):
        validation = WORKFLOW.index('Validate AWS deployment configuration')
        authentication = WORKFLOW.index('Configure AWS credentials through GitHub OIDC')
        self.assertLess(validation, authentication)
        self.assertIn('id-token: write', WORKFLOW)
        self.assertNotIn('AWS_ACCESS_KEY_ID', WORKFLOW)
        self.assertNotIn('AWS_SECRET_ACCESS_KEY', WORKFLOW)

    def test_external_actions_are_pinned_to_full_commit_hashes(self):
        for uses in re.findall(r'^\s+uses:\s+([^\s]+)', WORKFLOW, flags=re.MULTILINE):
            self.assertRegex(uses, r'@[0-9a-f]{40}(?:\s|$)')


if __name__ == '__main__':
    unittest.main()

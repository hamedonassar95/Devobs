import unittest
from devobs.integration_control.evidence import verify_commit_sha, verify_sha_pair, verify_ci_checks, verify_human_approval, verify_evidence_record, VERIFIED, UNVERIFIED, STALE, CONFLICTED, BLOCKED

class EvidenceTests(unittest.TestCase):
    def test_valid_commit_sha(self):
        self.assertEqual(verify_commit_sha('a'*40).state, VERIFIED)

    def test_invalid_commit_sha(self):
        self.assertEqual(verify_commit_sha('bad').state, BLOCKED)

    def test_mismatched_pr_sha(self):
        self.assertEqual(verify_sha_pair('pr_head_sha','a'*40,'b'*40).state, CONFLICTED)

    def test_missing_evidence(self):
        self.assertEqual(verify_sha_pair('remote_branch_sha','','').state, UNVERIFIED)

    def test_stale_ci(self):
        checks=[{'name':'validate','status':'completed','conclusion':'success','head_sha':'b'*40}]
        self.assertEqual(verify_ci_checks(checks,['validate'],'a'*40).state, STALE)

    def test_failed_ci(self):
        checks=[{'name':'validate','status':'completed','conclusion':'failure','head_sha':'a'*40}]
        self.assertEqual(verify_ci_checks(checks,['validate'],'a'*40).state, BLOCKED)

    def test_missing_human_approval(self):
        self.assertEqual(verify_human_approval({'approved':False,'approvals_count':0,'required_approvals':1}).state, UNVERIFIED)

    def test_evidence_record_invalid_sha(self):
        self.assertEqual(verify_evidence_record({'source':'s','kind':'k','ref':'r','sha':'nope'},'a'*40).state, BLOCKED)

if __name__ == '__main__':
    unittest.main()

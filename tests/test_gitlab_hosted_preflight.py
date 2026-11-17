"""Offline behavioral tests for manual hosted GitLab replication preflight."""
import json
from pathlib import Path
import sys
import unittest
from io import StringIO
import contextlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import gitlab_hosted_preflight as hosted  # noqa: E402
from gitlab_fast_forward_preflight import PreflightBlocked


class GitLabHostedPreflightTests(unittest.TestCase):
    SHA_A = 'a' * 40
    SHA_B = 'b' * 40

    def probe(self, status='FAST_FORWARD_CANDIDATE', gh=None, gl=None, wrote=False):
        return {"status": status, "github_sha": gh or self.SHA_B,
                "gitlab_sha": gl or self.SHA_A, "write_performed": wrote}

    def test_candidate_reports_human_review_without_write(self):
        result, code = hosted.evaluate(Path('.'), lambda _repo: self.probe())
        self.assertEqual(code, 0)
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        self.assertTrue(result['human_approval_required_for_sync'])
        self.assertFalse(result['write_performed'])
        self.assertFalse(result['gitlab_pipeline_started'])
        self.assertFalse(result['production_gates_changed'])

    def test_already_matched_is_not_backup_proof(self):
        result, code = hosted.evaluate(Path('.'), lambda _repo: self.probe('ALREADY_MATCHED', self.SHA_A, self.SHA_A))
        self.assertEqual(code, 0)
        self.assertEqual(result['status'], 'ALREADY_MATCHED')
        self.assertTrue(result['human_approval_required_for_sync'])

    def test_probe_cannot_claim_a_write(self):
        result, code = hosted.evaluate(Path('.'), lambda _repo: self.probe(wrote=True))
        self.assertEqual((result['status'], code), ('BLOCKED', 2))

    def test_mismatched_relation_blocks(self):
        result, code = hosted.evaluate(Path('.'), lambda _repo: self.probe('ALREADY_MATCHED'))
        self.assertEqual((result['reason'], code), ('inconsistent_probe_result', 2))

    def test_invalid_sha_blocks(self):
        result, code = hosted.evaluate(Path('.'), lambda _repo: self.probe(gh='BAD'))
        self.assertEqual((result['reason'], code), ('invalid_probe_result', 2))

    def test_extra_untrusted_field_blocks(self):
        def tampered(_repo):
            return {**self.probe(), 'TOKEN': 'DO_NOT_REPORT'}
        result, code = hosted.evaluate(Path('.'), tampered)
        self.assertEqual((result['reason'], code), ('invalid_probe_result', 2))
        self.assertNotIn('DO_NOT_REPORT', json.dumps(result))

    def test_safe_missing_local_checkout_is_reported(self):
        def denied(_repo):
            raise PreflightBlocked('checkout_unavailable')
        result, code = hosted.evaluate(Path('.'), denied)
        self.assertEqual((result['reason'], code), ('checkout_unavailable', 2))

    def test_unsanitized_provider_error_not_leaked(self):
        def denied(_repo):
            raise PreflightBlocked('PRIVATE_API_EXCEPTION_AND_SECRET')
        result, code = hosted.evaluate(Path('.'), denied)
        self.assertEqual((result['reason'], code), ('preflight_blocked', 2))

    def test_unknown_exceptions_fail_closed(self):
        def denied(_repo):
            raise ValueError('PRIVATE_API_EXCEPTION_AND_SECRET')
        result, code = hosted.evaluate(Path('.'), denied)
        self.assertEqual((result['reason'], code), ('unexpected_failure', 2))

    def test_cli_with_missing_checkout_exits_two_without_remote_call(self):
        output = StringIO()
        with contextlib.redirect_stdout(output):
            rc = hosted.main(['--repo', '/path/not/available/in/test'])
        self.assertEqual(rc, 2)
        result = json.loads(output.getvalue())
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertFalse(result['write_performed'])


if __name__ == '__main__':
    unittest.main()

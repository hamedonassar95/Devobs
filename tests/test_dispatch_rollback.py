import unittest
from unittest.mock import patch
from scripts import dispatch_rollback

class RollbackDispatchTests(unittest.TestCase):
    @patch.dict("os.environ", {"GH_TOKEN":"token", "GH_REPOSITORY":"owner/repo", "ROLLBACK_SHA":"a"*40,
        "ROLLBACK_TAG":"v1.2.3", "GH_API_URL":"https://api.github.com"})
    @patch("scripts.dispatch_rollback.time.sleep")
    @patch("scripts.dispatch_rollback.api_request")
    def test_dispatches_on_exact_rollback_sha_and_waits_for_child_run(self, api, sleep):
        api.side_effect = [(204, None), (200, {"workflow_runs":[{"head_sha":"a"*40,
            "created_at":"2026-10-15T00:00:00Z", "run_number":7, "status":"completed",
            "conclusion":"success", "html_url":"https://github.com/o/r/actions/runs/7"}]})]
        with patch("scripts.dispatch_rollback.time.time", return_value=1792000000):
            status, url = dispatch_rollback.dispatch_and_wait()
        self.assertEqual(status, "success")
        self.assertEqual(url, "https://github.com/o/r/actions/runs/7")
        dispatch_call = api.call_args_list[0]
        self.assertEqual(dispatch_call.args[0], "https://api.github.com/repos/owner/repo/actions/workflows/rollback-pages.yml/dispatches")
        self.assertEqual(dispatch_call.args[2], "POST")
        body = dispatch_call.args[3]
        self.assertEqual(body["ref"], "a"*40)
        self.assertEqual(body["inputs"]["confirmation"], "ROLLBACK")

if __name__ == "__main__": unittest.main()

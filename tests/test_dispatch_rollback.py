import unittest
from unittest.mock import patch
from scripts import dispatch_rollback


class RollbackDispatchTests(unittest.TestCase):
    @patch.dict("os.environ", {"GH_TOKEN": "token", "GH_REPOSITORY": "owner/repo",
        "ROLLBACK_SHA": "a" * 40, "ROLLBACK_TAG": "v1.2.3", "GH_API_URL": "https://api.github.com"})
    @patch("scripts.dispatch_rollback.time.sleep")
    @patch("scripts.dispatch_rollback.time.monotonic", side_effect=[0, 1])
    @patch("scripts.dispatch_rollback.uuid.uuid4")
    @patch("scripts.dispatch_rollback.api_request")
    def test_dispatches_supported_tag_and_finds_exact_queued_child(self, api, uuid4, monotonic, sleep):
        uuid4.return_value.hex = "unique-dispatch"
        api.side_effect = [
            (204, None),
            (200, {"workflow_runs": [
                {"head_sha": "a" * 40, "display_title": "Rollback Pages / other",
                 "html_url": "https://github.com/o/r/actions/runs/6"},
                {"head_sha": "a" * 40, "display_title": "Rollback Pages / unique-dispatch",
                 "status": "queued", "html_url": "https://github.com/o/r/actions/runs/7"},
            ]}),
        ]
        status, url = dispatch_rollback.dispatch_and_find_run()
        self.assertEqual(status, "dispatched")
        self.assertEqual(url, "https://github.com/o/r/actions/runs/7")
        dispatch_call = api.call_args_list[0]
        self.assertEqual(dispatch_call.args[0],
            "https://api.github.com/repos/owner/repo/actions/workflows/rollback-pages.yml/dispatches")
        body = dispatch_call.args[3]
        self.assertEqual(body["ref"], "v1.2.3")
        self.assertEqual(body["inputs"]["expected_commit_sha"], "a" * 40)
        self.assertEqual(body["inputs"]["dispatch_id"], "unique-dispatch")
        self.assertIn("workflow_dispatch", api.call_args_list[1].args[0])

    @patch.dict("os.environ", {"GH_TOKEN": "token", "GH_REPOSITORY": "owner/repo",
        "ROLLBACK_SHA": "a" * 40, "ROLLBACK_TAG": "v1.2.3", "GH_API_URL": "https://api.github.com"})
    @patch("scripts.dispatch_rollback.time.sleep")
    @patch("scripts.dispatch_rollback.time.monotonic", side_effect=[0, 1, 46])
    @patch("scripts.dispatch_rollback.uuid.uuid4")
    @patch("scripts.dispatch_rollback.api_request", side_effect=[(204, None), (200, {"workflow_runs": []})])
    def test_returns_accepted_without_waiting_for_child_completion(self, api, uuid4, monotonic, sleep):
        uuid4.return_value.hex = "unique-dispatch"
        status, url = dispatch_rollback.dispatch_and_find_run()
        self.assertEqual((status, url), ("accepted", ""))
        sleep.assert_called_once_with(3)

if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch
from scripts import dispatch_rollback


class RollbackDispatchTests(unittest.TestCase):
    ENV = {
        "GH_TOKEN": "token", "GH_REPOSITORY": "owner/repo",
        "ROLLBACK_SHA": "a" * 40, "ROLLBACK_TAG": "v1.2.3",
        "GH_API_URL": "https://api.github.com", "GH_SERVER_URL": "https://github.com",
    }

    @patch.dict("os.environ", ENV)
    @patch("scripts.dispatch_rollback.time.sleep")
    @patch("scripts.dispatch_rollback.time.monotonic", side_effect=[0, 1])
    @patch("scripts.dispatch_rollback.api_request")
    def test_dispatches_only_historical_inputs_and_finds_new_run(self, api, monotonic, sleep):
        api.side_effect = [
            (200, {"workflow_runs": [{"id": 6, "run_number": 22, "head_sha": "a" * 40, "event": "workflow_dispatch"}]}),
            (204, None),
            (200, {"workflow_runs": [
                {"id": 6, "run_number": 22, "head_sha": "a" * 40, "event": "workflow_dispatch",
                 "html_url": "https://github.com/o/r/actions/runs/6"},
                {"id": 1, "run_number": 3, "head_sha": "a" * 40, "event": "workflow_dispatch",
                 "html_url": "https://github.com/o/r/actions/runs/1"},
                {"id": 7, "run_number": 23, "head_sha": "a" * 40, "event": "workflow_dispatch",
                 "html_url": "https://github.com/o/r/actions/runs/7"},
            ]}),
        ]
        status, url = dispatch_rollback.dispatch_and_find_run()
        self.assertEqual((status, url), ("dispatched", "https://github.com/o/r/actions/runs/7"))
        dispatch_call = api.call_args_list[1]
        body = dispatch_call.args[3]
        self.assertEqual(body, {"ref": "v1.2.3",
            "inputs": {"release_tag": "v1.2.3", "confirmation": "ROLLBACK"}})
        self.assertIn("workflow_dispatch", api.call_args_list[0].args[0])

    @patch.dict("os.environ", ENV)
    @patch("scripts.dispatch_rollback.time.sleep")
    @patch("scripts.dispatch_rollback.time.monotonic", side_effect=[0, 1, 46])
    @patch("scripts.dispatch_rollback.api_request", side_effect=[
        (200, {"workflow_runs": []}), (204, None), (200, {"workflow_runs": []})])
    def test_reports_accepted_and_links_to_workflow_when_run_list_lags(self, api, monotonic, sleep):
        status, url = dispatch_rollback.dispatch_and_find_run()
        self.assertEqual(status, "accepted")
        self.assertEqual(url, "https://github.com/owner/repo/actions/workflows/rollback-pages.yml")
        sleep.assert_called_once_with(3)

    @patch.dict("os.environ", ENV)
    @patch("scripts.dispatch_rollback.time.sleep")
    @patch("scripts.dispatch_rollback.time.monotonic", side_effect=[0, 1])
    @patch("scripts.dispatch_rollback.api_request", side_effect=[
        (200, {"workflow_runs": []}), (204, None), (200, {"workflow_runs": [
            {"id": 10, "run_number": 23, "head_sha": "a" * 40, "event": "workflow_dispatch"},
            {"id": 11, "run_number": 24, "head_sha": "a" * 40, "event": "workflow_dispatch"},
        ]})])
    def test_avoids_claiming_a_run_when_multiple_new_runs_match(self, api, monotonic, sleep):
        status, url = dispatch_rollback.dispatch_and_find_run()
        self.assertEqual(status, "accepted")
        self.assertTrue(url.endswith("/actions/workflows/rollback-pages.yml"))
        sleep.assert_not_called()

if __name__ == "__main__":
    unittest.main()

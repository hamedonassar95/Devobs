"""Behavioral regression for fixed local free-readiness coordinator."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import free_readiness_one_command as check
from tests.platform_support import require_symlink_creation


class FreeReadinessCoordinatorTests(unittest.TestCase):
    def fake_tree(self, root):
        directory = root / "scripts"
        directory.mkdir()
        for _, filename, _, _ in check.CHECKS:
            (directory / filename).write_text("# offline fixture\n", encoding="utf-8")

    def test_all_expected_statuses_return_review_not_go(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fake_tree(root)
            seen = []
            codes = iter((0, 0, 0, 1, 1))

            def runner(cmd, **kwargs):
                seen.append((cmd, kwargs))
                return subprocess.CompletedProcess(cmd, next(codes), "", "")

            result = check.inspect_offline(root, runner)
            self.assertEqual(result["status"], "REVIEW_REQUIRED")
            self.assertEqual([x["state"] for x in result["checks"]], [
                "VALIDATED_OFFLINE", "VALIDATED_OFFLINE", "VALIDATED_OFFLINE",
                "REVIEW_REQUIRED", "REVIEW_REQUIRED",
            ])
            self.assertEqual(len(seen), 5)
            self.assertTrue(all(len(entry[0]) in (3, 4) for entry in seen))
            self.assertTrue(all(x[1]["stdout"] == subprocess.DEVNULL
                                and x[1]["stderr"] == subprocess.DEVNULL
                                and x[1]["env"] == {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
                                and x[1]["check"] is False
                                and x[1]["timeout"] == 25 for x in seen))
            for field in ("production_ready", "paid_activation_authorized",
                          "automatic_merge_authorized", "live_integration_verified",
                          "external_providers_contacted", "other_repositories_queried"):
                self.assertIs(result[field], False)

    def test_unexpected_green_staging_result_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fake_tree(root)
            codes = iter((0, 0, 0, 0, 0))
            result = check.inspect_offline(root, lambda cmd, **kw: subprocess.CompletedProcess(cmd, next(codes)))
            self.assertEqual(result["status"], "INVALID_CHECKS")
            self.assertEqual(result["checks"][3]["state"], "INVALID_OR_UNAVAILABLE")

    def test_missing_script_never_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fake_tree(root)
            bad = root / "scripts" / check.CHECKS[0][1]
            bad.unlink()
            called = []

            def runner(cmd, **kwargs):
                called.append(cmd)
                return subprocess.CompletedProcess(cmd, 1)

            result = check.inspect_offline(root, runner)
            self.assertEqual(result["status"], "INVALID_CHECKS")
            self.assertEqual(len(called), 4)

    def test_symlinked_script_never_runs(self):
        require_symlink_creation(self)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fake_tree(root)
            bad = root / "scripts" / check.CHECKS[0][1]
            bad.unlink()
            bad.symlink_to(root / "absent")
            called = []

            def runner(cmd, **kwargs):
                called.append(cmd)
                return subprocess.CompletedProcess(cmd, 1)

            result = check.inspect_offline(root, runner)
            self.assertEqual(result["status"], "INVALID_CHECKS")
            self.assertEqual(len(called), 4)

    def test_errors_and_negative_process_status_are_not_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fake_tree(root)
            def runner(cmd, **kwargs):
                if cmd[1].endswith("milestone_ledger.py"):
                    raise subprocess.TimeoutExpired(cmd, 25)
                return subprocess.CompletedProcess(cmd, -9)
            result = check.inspect_offline(root, runner)
            self.assertEqual(result["status"], "INVALID_CHECKS")
            self.assertTrue(all(x["state"] == "INVALID_OR_UNAVAILABLE" for x in result["checks"]))

    def test_cli_never_echoes_internal_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fake_tree(root)
            secret_like = "TEST_ONLY_PRIVATE_CONTENT"
            result = check.inspect_offline(root, lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0 if not cmd[1].endswith("check_free_staging_health.py") else 1, secret_like, secret_like))
            self.assertNotIn(secret_like, str(result))


if __name__ == "__main__":
    unittest.main()

"""Behavioral tests for the optional read-only Windows Plannotator preflight."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_plannotator_windows_preflight.py"
spec = importlib.util.spec_from_file_location("plannotator_windows_preflight", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WindowsPlannotatorPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        (self.root / ".git").mkdir()
        for name in module.REQUIRED_FILES:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture only", encoding="utf-8")
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()
        self.env = {"PLANNOTATOR_SHARE": "disabled", "PLANNOTATOR_REMOTE": "0"}

    def evaluate(self, **overrides):
        options = dict(
            repo=self.root,
            system_name="Windows",
            python_version=(3, 12),
            which=lambda command: "present" if command in ("git", "plannotator") else None,
            environ=self.env,
            home=self.home,
        )
        options.update(overrides)
        return module.inspect(**options)

    def test_synthetic_ready_only_reports_prerequisites_not_execution(self):
        result = self.evaluate()
        self.assertEqual(result["result"], "PREREQUISITES_PRESENT_RUNTIME_UNVERIFIED")
        self.assertFalse(result["installation_performed"])
        self.assertFalse(result["hooks_enabled"])
        self.assertFalse(result["runtime_verified"])
        self.assertFalse(result["production_approved"])
        self.assertTrue(all(v == "PASS" for v in result["checks"].values()))

    def test_windows_only(self):
        result = self.evaluate(system_name="Linux")
        self.assertEqual(result["result"], "BLOCKED")
        self.assertEqual(result["checks"]["native_windows"], "BLOCKED")

    def test_missing_binary_fails_closed(self):
        result = self.evaluate(which=lambda command: "present" if command == "git" else None)
        self.assertEqual(result["result"], "BLOCKED")
        self.assertEqual(result["checks"]["plannotator_on_path_unexecuted"], "BLOCKED")

    def test_missing_checkout_fails_closed(self):
        (self.root / ".git").rmdir()
        result = self.evaluate()
        self.assertEqual(result["checks"]["repository_directory"], "BLOCKED")
        self.assertEqual(result["result"], "BLOCKED")

    def test_missing_expected_file_fails_closed(self):
        (self.root / ".codex/config.toml").unlink()
        self.assertEqual(self.evaluate()["checks"]["expected_repository_files"], "BLOCKED")

    def test_repository_hook_presence_fails_closed_without_reading_file(self):
        hook = self.root / ".codex/hooks.json"
        hook.write_text("DO NOT OPEN", encoding="utf-8")
        self.assertEqual(self.evaluate()["checks"]["repository_hooks_absent"], "BLOCKED")
        self.assertEqual(hook.read_text(encoding="utf-8"), "DO NOT OPEN")

    def test_global_hook_presence_fails_closed(self):
        hook = self.home / ".codex/hooks.json"
        hook.parent.mkdir(parents=True)
        hook.write_text("DO NOT OPEN", encoding="utf-8")
        self.assertEqual(self.evaluate()["checks"]["user_hooks_absent"], "BLOCKED")

    def test_custom_codex_home_relative_is_blocked(self):
        result = self.evaluate(environ={**self.env, "CODEX_HOME": "relative/path"})
        self.assertEqual(result["checks"]["codex_home_path_valid"], "BLOCKED")
        self.assertEqual(result["result"], "BLOCKED")

    def test_sharing_must_be_explicitly_disabled(self):
        env = {"PLANNOTATOR_REMOTE": "0"}
        result = self.evaluate(environ=env)
        self.assertEqual(result["checks"]["sharing_disabled"], "BLOCKED")
        self.assertNotIn(str(self.root), str(result))

    def test_remote_mode_is_blocked(self):
        result = self.evaluate(environ={**self.env, "PLANNOTATOR_REMOTE": "1"})
        self.assertEqual(result["checks"]["remote_mode_disabled"], "BLOCKED")

    def test_does_not_change_environment_or_create_files(self):
        before = sorted(str(x.relative_to(self.root)) for x in self.root.rglob("*"))
        env = dict(self.env)
        self.evaluate()
        after = sorted(str(x.relative_to(self.root)) for x in self.root.rglob("*"))
        self.assertEqual(before, after)
        self.assertEqual(env, self.env)


if __name__ == "__main__":
    unittest.main()

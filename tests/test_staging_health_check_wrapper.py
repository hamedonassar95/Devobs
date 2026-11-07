"""Verify the shell entrypoint delegates to the existing read-only smoke check."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "staging_health_check.sh"
SMOKE = ROOT / "scripts" / "devobs_intelligence" / "staging_smoke.py"


class StagingHealthCheckWrapperTests(unittest.TestCase):
    def test_uses_repository_path_from_any_working_directory_and_propagates_exit(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            fake_bin = temp / "bin"
            fake_bin.mkdir()
            capture = temp / "argv.txt"
            fake_python = fake_bin / "python3"
            fake_python.write_text(
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' \"$@\" > \"$CAPTURE_FILE\"\n"
                "exit \"${MOCK_PYTHON_EXIT:-0}\"\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
            env["CAPTURE_FILE"] = str(capture)

            first = subprocess.run(
                ["bash", str(WRAPPER)], cwd=temp, env=env,
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(capture.read_text(encoding="utf-8").splitlines(), [str(SMOKE)])

            env["MOCK_PYTHON_EXIT"] = "7"
            second = subprocess.run(
                ["bash", str(WRAPPER)], cwd=temp, env=env,
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(second.returncode, 7, second.stderr)


if __name__ == "__main__":
    unittest.main()

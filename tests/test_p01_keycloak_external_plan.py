"""Offline plan behavior; no Render calls, DNS, credentials or identity runtime."""
import json
import importlib.util
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/p01_keycloak_external_plan.py"
TEMPLATE = ROOT / "deploy/keycloak-hosted/render.yaml"
SPEC = importlib.util.spec_from_file_location("external_plan", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExternalRoutePlanTests(unittest.TestCase):
    def run_plan(self, inventory, existing=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inventory.json"
            path.write_text(inventory if isinstance(inventory, str) else json.dumps(inventory))
            output = Path(directory) / "candidate.yaml"
            if existing:
                output.write_text("original-review-artifact")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--inventory", str(path), "--output", str(output)],
                text=True, capture_output=True, check=False,
            )
            return result, output.read_text() if output.exists() else None

    def inventory(self, cidrs=None):
        # Synthetic public-range shape fixtures, NOT verified Render egress.
        return {"schema_version": 1, "region": "frankfurt",
                "outbound_cidrs": cidrs if cidrs is not None else ["8.8.8.0/24", "1.1.1.1/32"]}

    def test_output_changes_only_database_allowlist_and_leaves_template_closed(self):
        original_text = TEMPLATE.read_text()
        result, text = self.run_plan(self.inventory())
        self.assertEqual(result.returncode, 0, result.stderr)
        allowlist_line, = [line for line in text.splitlines() if line.startswith("    ipAllowList: ")]
        entries = json.loads(allowlist_line.split(": ", 1)[1])
        self.assertEqual([entry["source"] for entry in entries],
                         self.inventory()["outbound_cidrs"])
        candidate = "\n".join(text.splitlines()[2:]) + "\n"
        self.assertEqual(candidate.replace(allowlist_line, "    ipAllowList: []"), original_text)
        self.assertEqual(TEMPLATE.read_text(), original_text)
        self.assertIn("PLAN_ONLY", result.stdout)
        self.assertIn("unverified", result.stdout)

    def test_unsafe_or_incomplete_inputs_leave_no_plan_and_no_echo(self):
        invalid = [self.inventory(cidrs) for cidrs in (
            [], ["0.0.0.0/0"], ["10.0.0.0/24"], ["127.0.0.1/32"],
            ["169.254.169.254/32"], ["192.0.2.0/24"], ["100.64.0.0/24"],
            ["224.0.0.0/24"], ["8.8.0.0/16"], ["8.8.8.1/24"],
            ["8.8.8.0/24", "8.8.8.0/24"], ["8.8.8.0/24", "8.8.8.1/32"],
            ["2001:4860::/64"], ["8.8.8.8"], ["supplied-marker"], [123],
        )] + [
            {}, {**self.inventory(), "region": "oregon"},
            {**self.inventory(), "schema_version": True},
            {**self.inventory(), "password": "supplied-marker"},
            '{"schema_version":1,"schema_version":1}', "[]", "[", "x" * 8193,
            "[" * 1100 + "]" * 1100,
        ]
        for inventory in invalid:
            with self.subTest(inventory=inventory if len(str(inventory)) < 200 else "oversized"):
                result, output = self.run_plan(inventory)
                self.assertEqual(result.returncode, 2)
                self.assertIsNone(output)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, "EXTERNAL_ROUTE_PLAN_BLOCKED\n")

    def test_refuses_to_overwrite_existing_plan(self):
        result, output = self.run_plan(self.inventory(), existing=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(output, "original-review-artifact")

    def test_changed_template_fails_before_creating_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "changed.yaml"
            path.write_text(TEMPLATE.read_text().replace("autoDeployTrigger: off", "autoDeployTrigger: commit"))
            inventory = Path(directory) / "inventory.json"
            inventory.write_text(json.dumps(self.inventory()))
            output = Path(directory) / "candidate.yaml"
            with patch.object(MODULE, "TEMPLATE", path), contextlib.redirect_stderr(io.StringIO()):
                result = MODULE.main(["--inventory", str(inventory), "--output", str(output)])
            self.assertEqual(result, 2)
            self.assertFalse(output.exists())

    def test_failed_write_does_not_publish_a_partial_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            inventory = Path(directory) / "inventory.json"
            inventory.write_text(json.dumps(self.inventory()))
            output = Path(directory) / "candidate.yaml"
            original_write = Path.write_text

            def interrupted_write(path, text, **kwargs):
                original_write(path, text[:80], **kwargs)
                raise OSError("supplied-marker")

            error = io.StringIO()
            with patch.object(Path, "write_text", interrupted_write), contextlib.redirect_stderr(error):
                result = MODULE.main(["--inventory", str(inventory), "--output", str(output)])
            self.assertEqual(result, 2)
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(directory).iterdir()), [inventory])
            self.assertEqual(error.getvalue(), "EXTERNAL_ROUTE_PLAN_BLOCKED\n")

    def test_invalid_cli_does_not_echo_supplied_arguments(self):
        for args in (["--unknown", "supplied-marker"], ["--inventory"], []):
            result = subprocess.run([sys.executable, str(SCRIPT), *args],
                                    text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "EXTERNAL_ROUTE_PLAN_BLOCKED\n")


if __name__ == "__main__":
    unittest.main()

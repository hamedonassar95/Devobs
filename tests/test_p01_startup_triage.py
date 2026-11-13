"""Behavioral tests for the offline, presence-only P01 startup triage tool."""
from __future__ import annotations

import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p01_startup_triage as triage_tool  # noqa: E402


def inventory_bytes(variables: dict[str, str]) -> bytes:
    return json.dumps({"schema_version": 1, "variables": variables}).encode("utf-8")


class P01StartupTriageTests(unittest.TestCase):
    def complete_inventory(self) -> dict[str, str]:
        return {name: "present" for name in triage_tool.REQUIRED_NAMES} | {
            "DEVOBS_PG_TLS_MODE": "present",
            "RENDER": "present",
            "RENDER_SERVICE_TYPE": "present",
        }

    def test_complete_inventory_reports_presence_without_claiming_validity(self):
        parsed = triage_tool.parse_inventory(inventory_bytes(self.complete_inventory()))
        report = triage_tool.triage(parsed)
        self.assertEqual(report["status"], "PRESENT_BUT_VALIDITY_UNVERIFIED")
        self.assertEqual(report["readiness_claim"], "NOT_ESTABLISHED")
        self.assertEqual(len(report["requirements"]), 6)
        self.assertTrue(all(
            item["status"] == "PRESENT_BUT_VALIDITY_UNVERIFIED"
            for item in report["requirements"]
        ))
        self.assertEqual(report["tls_assessment"]["status"], "PRESENT_BUT_VALIDITY_UNVERIFIED")

    def test_explicit_missing_required_name_is_confirmed_missing(self):
        variables = self.complete_inventory()
        variables["DEVOBS_OIDC_JWKS_JSON"] = "missing"
        report = triage_tool.triage(triage_tool.parse_inventory(inventory_bytes(variables)))
        self.assertEqual(report["status"], "CONFIRMED_MISSING_CONFIGURATION")
        row = next(item for item in report["requirements"]
                   if item["name"] == "DEVOBS_OIDC_JWKS_JSON")
        self.assertEqual(row["status"], "CONFIRMED_MISSING_CONFIGURATION")

    def test_unchecked_or_omitted_required_name_is_insufficient_evidence(self):
        variables = self.complete_inventory()
        variables["DEVOBS_OIDC_CLIENT_ID"] = "not_checked"
        del variables["DEVOBS_PG_DSN"]
        report = triage_tool.triage(triage_tool.parse_inventory(inventory_bytes(variables)))
        self.assertEqual(report["status"], "INSUFFICIENT_EVIDENCE")
        statuses = {item["name"]: item["status"] for item in report["requirements"]}
        self.assertEqual(statuses["DEVOBS_OIDC_CLIENT_ID"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(statuses["DEVOBS_PG_DSN"], "INSUFFICIENT_EVIDENCE")

    def test_tls_default_and_conditional_render_mode_are_not_overclaimed(self):
        variables = {name: "present" for name in triage_tool.REQUIRED_NAMES}
        variables.update({"DEVOBS_PG_TLS_MODE": "missing", "RENDER": "missing"})
        report = triage_tool.triage(variables)
        tls = report["tls_assessment"]
        self.assertEqual(tls["status"], "PRESENT_BUT_VALIDITY_UNVERIFIED")
        self.assertEqual(tls["default_mode_when_name_is_absent"], "verify-full")
        self.assertIn("sslrootcert", " ".join(tls["verification_required"]))
        self.assertEqual(
            tls["render_context"][0]["applicability"],
            "conditional_on_render_internal_tls_mode",
        )

    def test_explicit_tls_selector_without_render_context_inventory_is_insufficient(self):
        variables = {name: "present" for name in triage_tool.REQUIRED_NAMES}
        variables["DEVOBS_PG_TLS_MODE"] = "present"
        report = triage_tool.triage(variables)
        self.assertEqual(report["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(report["tls_assessment"]["status"], "INSUFFICIENT_EVIDENCE")

    def test_unknown_fields_and_environment_dump_are_rejected_without_echo(self):
        secret_marker = "SYNTHETIC_DO_NOT_PRINT"
        payload = {
            "schema_version": 1,
            "variables": {"OPENAI_API_KEY": secret_marker},
        }
        with self.assertRaises(triage_tool.InventoryError):
            triage_tool.parse_inventory(json.dumps(payload).encode())
        stdout, stderr = io.StringIO(), io.StringIO()
        raw = json.dumps(payload).encode("utf-8")
        with patch.object(triage_tool, "_read_inventory", return_value=raw):
            code = triage_tool.main(
                ["--inventory", "synthetic-inventory.json"],
                stdout=stdout,
                stderr=stderr,
            )
        self.assertEqual(code, 4)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "ERROR: invalid_inventory\n")
        self.assertNotIn(secret_marker, stdout.getvalue() + stderr.getvalue())

    def test_configuration_value_is_rejected_even_under_allowed_name(self):
        secret_marker = "dsn-value-that-is-not-an-allowed-presence-state"
        payload = {
            "schema_version": 1,
            "variables": {"DEVOBS_PG_DSN": secret_marker},
        }
        with self.assertRaises(triage_tool.InventoryError):
            triage_tool.parse_inventory(json.dumps(payload).encode())
        stdout, stderr = io.StringIO(), io.StringIO()
        raw = json.dumps(payload).encode("utf-8")
        with patch.object(triage_tool, "_read_inventory", return_value=raw):
            code = triage_tool.main(
                ["--inventory", "synthetic-inventory.json"],
                stdout=stdout,
                stderr=stderr,
            )
        self.assertEqual(code, 4)
        self.assertNotIn(secret_marker, stdout.getvalue() + stderr.getvalue())

    def test_duplicate_keys_invalid_schema_and_unsafe_states_are_rejected(self):
        for raw in (
            b'{"schema_version":1,"schema_version":1,"variables":{}}',
            b'{"schema_version":1,"variables":{},"unexpected":true}',
            b'{"schema_version":true,"variables":{}}',
            b'{"schema_version":1,"variables":{"DEVOBS_PG_DSN":"secret"}}',
            b'{"schema_version":1,"variables":{"DEVOBS_PG_DSN":true}}',
            b'{"schema_version":1,"variables":{},"x":NaN}',
            b'[]',
        ):
            with self.subTest(raw=raw[:32]), self.assertRaises(triage_tool.InventoryError):
                triage_tool.parse_inventory(raw)

    def test_oversized_malformed_and_unreadable_inventories_fail_closed(self):
        with self.assertRaises(triage_tool.InventoryError):
            triage_tool.parse_inventory(b" " * (triage_tool.MAX_INVENTORY_BYTES + 1))
        with self.assertRaises(triage_tool.InventoryError):
            triage_tool.parse_inventory(b"{not-json")
        stdout, stderr = io.StringIO(), io.StringIO()
        code = triage_tool.main(
            ["--inventory", "/path/that/does/not/exist/p01.json"],
            stdout=stdout,
            stderr=stderr,
        )
        self.assertEqual(code, 4)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "ERROR: inventory_unavailable\n")

    def test_cli_exit_codes_and_json_output_are_deterministic(self):
        variables = self.complete_inventory()
        raw = inventory_bytes(variables)
        report1 = triage_tool.triage(triage_tool.parse_inventory(raw))
        report2 = triage_tool.triage(triage_tool.parse_inventory(raw))
        self.assertEqual(report1, report2)

        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "inventory.json"
            path.write_bytes(raw)
            outputs = []
            for _ in range(2):
                stdout, stderr = io.StringIO(), io.StringIO()
                code = triage_tool.main(["--inventory", str(path)], stdout=stdout, stderr=stderr)
                outputs.append(stdout.getvalue())
                self.assertEqual(code, 0)
                self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(json.loads(outputs[0])["readiness_claim"], "NOT_ESTABLISHED")

    def test_cli_reports_missing_and_incomplete_inventories_with_nonzero_codes(self):
        scenarios = (
            ({"DEVOBS_OIDC_ISSUER": "missing"}, 2, "CONFIRMED_MISSING_CONFIGURATION"),
            ({"DEVOBS_OIDC_ISSUER": "not_checked"}, 3, "INSUFFICIENT_EVIDENCE"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "inventory.json"
            for variables, expected_code, expected_status in scenarios:
                with self.subTest(expected_status=expected_status):
                    path.write_bytes(inventory_bytes(variables))
                    stdout, stderr = io.StringIO(), io.StringIO()
                    code = triage_tool.main(["--inventory", str(path)], stdout=stdout, stderr=stderr)
                    self.assertEqual(code, expected_code)
                    self.assertEqual(json.loads(stdout.getvalue())["status"], expected_status)
                    self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()

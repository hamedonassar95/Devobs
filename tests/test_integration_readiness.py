"""Offline policy-contract tests; no provider connection or deployment approval."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_integration_readiness.py"
SPEC = importlib.util.spec_from_file_location("integration_readiness", SCRIPT)
MODULE = None
if SCRIPT.is_file():
    MODULE = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(MODULE)


def fixture(provider="pulumi_delivery"):
    return {
        "schema_version": 1,
        "provider": provider,
        "mode": "DRY_RUN",
        "read_only": True,
        "default_platform": "GITHUB_ACTIONS_GCP",
        "source_sha": "a" * 40,
        "human_approval_required": True,
        "authentication_required": True,
        "auth_failure_policy": "DENY",
        "authentication_status": "NOT_CHECKED",
        "automatic_production_deployment": False,
        "audit_redaction_required": True,
        "audit_fields": ["event_id", "occurred_at", "provider", "source_sha", "mode",
                         "auth_state", "approval_state", "decision", "reason_codes"],
    }


class IntegrationReadinessTests(unittest.TestCase):
    def assess(self, data):
        self.assertIsNotNone(MODULE, "Offline readiness checker must exist")
        return MODULE.assess(data)

    def assert_invalid(self, data):
        self.assertIsNotNone(MODULE, "Offline readiness checker must exist")
        with self.assertRaises(MODULE.ReadinessError):
            MODULE.assess(data)

    def test_both_providers_are_design_only_and_never_authorize_execution(self):
        for provider in ("pulumi_delivery", "azure_catalyst"):
            with self.subTest(provider=provider):
                data = fixture(provider)
                original = deepcopy(data)
                report = self.assess(data)
                self.assertEqual(report["status"], "OFFLINE_DESIGN_VALID_ONLY")
                self.assertEqual(report["provider"], provider)
                self.assertEqual(report["mode"], "DRY_RUN")
                self.assertFalse(report["execution_authorized"])
                self.assertFalse(report["provider_connection_verified"])
                self.assertFalse(report["production_ready"])
                self.assertEqual(report["authentication_status"], "NOT_CHECKED")
                self.assertEqual(report["human_approval_status"], "PENDING")
                self.assertEqual(data, original)

    def test_provider_must_be_explicit_and_known(self):
        for value in (None, "", "auto", "gcp", "azure", ["pulumi_delivery"], True):
            data = fixture()
            data["provider"] = value
            self.assert_invalid(data)

    def test_unsafe_modes_platform_switches_and_claimed_auth_are_rejected(self):
        for key, value in (("mode", "APPLY"), ("mode", "PREVIEW"),
                           ("default_platform", "AZURE"), ("read_only", False),
                           ("authentication_status", "VERIFIED"),
                           ("auth_failure_policy", "ALLOW")):
            with self.subTest(key=key, value=value):
                data = fixture()
                data[key] = value
                self.assert_invalid(data)

    def test_safety_flags_are_exact_booleans(self):
        for key in ("read_only", "human_approval_required", "authentication_required", "audit_redaction_required"):
            for value in (False, 1, "true", None):
                data = fixture()
                data[key] = value
                self.assert_invalid(data)
        for value in (True, 0, "false", None):
            data = fixture()
            data["automatic_production_deployment"] = value
            self.assert_invalid(data)

    def test_missing_unknown_fields_and_secret_slots_are_rejected(self):
        for key in fixture():
            data = fixture()
            del data[key]
            self.assert_invalid(data)
        for key in ("credentials", "access_token", "approval_received", "deploy_command", "endpoint"):
            data = fixture()
            data[key] = "SYNTHETIC_NON_SECRET_SENTINEL"
            self.assert_invalid(data)

    def test_revision_and_audit_schema_are_bounded(self):
        for value in ("a" * 39, "A" * 40, "../main", None, 123):
            data = fixture()
            data["source_sha"] = value
            self.assert_invalid(data)
        for value in ([], ["token"], fixture()["audit_fields"] * 2, [["provider"]], None):
            data = fixture()
            data["audit_fields"] = value
            self.assert_invalid(data)
        data = fixture()
        data["schema_version"] = True
        self.assert_invalid(data)

    def invoke(self, raw):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "synthetic.json"
            source.write_bytes(raw)
            return subprocess.run([sys.executable, str(SCRIPT), "--input", str(source)],
                                  capture_output=True, text=True, timeout=10)

    def test_cli_valid_and_invalid_results_do_not_echo_untrusted_values(self):
        self.assertIsNotNone(MODULE, "Offline readiness checker must exist")
        result = self.invoke(json.dumps(fixture()).encode())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["execution_authorized"])
        data = fixture()
        data["provider"] = "SYNTHETIC_NON_SECRET_SENTINEL"
        result = self.invoke(json.dumps(data).encode())
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("SYNTHETIC_NON_SECRET_SENTINEL", result.stdout + result.stderr)
        self.assertFalse(json.loads(result.stdout)["execution_authorized"])

    def test_cli_rejects_duplicate_keys_nonfinite_values_bad_utf8_and_oversize(self):
        self.assertIsNotNone(MODULE, "Offline readiness checker must exist")
        for raw in (b'{"mode":"DRY_RUN","mode":"APPLY"}', b'{"schema_version":NaN}',
                    b'\xff', b' ' * 16385, b'[]', b'{broken',
                    b'{"schema_version":' + b'9' * 5000 + b'}'):
            with self.subTest(length=len(raw)):
                result = self.invoke(raw)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stdout)["status"], "INVALID")
                self.assertFalse(json.loads(result.stdout)["execution_authorized"])


if __name__ == "__main__":
    unittest.main()

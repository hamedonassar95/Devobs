"""Security, reliability, and CLI tests for integration readiness."""
from __future__ import annotations

import copy
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import PurePosixPath
from unittest.mock import patch

from devobs.integration_readiness import (
    GUARDRAILS,
    NEEDS_APPROVAL,
    POLICY_VIOLATION,
    CatalogError,
    DEFAULT_FIXTURE_PATH,
    classify_license,
    evaluate_catalog,
    render_json_report,
    render_markdown_report,
    safe_relative_path,
)
from devobs.integration_readiness.cli import main
from scripts.assess_change import is_python
from tests.integration_readiness.test_integration_readiness_core import (
    base_catalog,
    clean_catalog,
    codes,
    integration,
)


class ReadinessSecurityTests(unittest.TestCase):
    def test_secret_like_config_keys_are_redacted_in_all_reports(self) -> None:
        catalog = base_catalog()
        secret = "synthetic-not-a-real-secret-9f8e7d"
        integration(catalog, "keycloak")["config"]["api_key"] = secret
        report = evaluate_catalog(catalog)
        self.assertIn("SECRET_EXPOSURE", codes(report))
        rendered = render_json_report(report) + render_markdown_report(report)
        self.assertNotIn(secret, rendered)
        self.assertIn("[REDACTED]", rendered)

    def test_external_tool_unavailable_is_reported(self) -> None:
        catalog = base_catalog()
        catalog["tool_availability"]["python"] = False
        report = evaluate_catalog(catalog)
        self.assertIn("EXTERNAL_TOOL_UNAVAILABLE", codes(report))
        self.assertNotIn("Traceback", render_json_report(report))

    def test_missing_human_approval_changes_decision(self) -> None:
        catalog = clean_catalog()
        integration(catalog, "keycloak")["approval"] = None
        report = evaluate_catalog(catalog)
        self.assertIn("MISSING_HUMAN_APPROVAL", codes(report))
        self.assertEqual(report["decision"], NEEDS_APPROVAL)
        self.assertTrue(report["human_review_required"])

    def test_agent_or_ai_identity_cannot_satisfy_approval(self) -> None:
        catalog = clean_catalog()
        integration(catalog, "keycloak")["approval"]["approved_by"] = "ci-agent"
        report = evaluate_catalog(catalog)
        self.assertIn("APPROVAL_NOT_HUMAN", codes(report))
        self.assertEqual(report["decision"], NEEDS_APPROVAL)

    def test_stale_approval_scope_is_rejected(self) -> None:
        catalog = base_catalog()
        integration(catalog, "keycloak")["approval"]["scope_sha"] = "1" * 40
        report = evaluate_catalog(catalog)
        self.assertIn("APPROVAL_SCOPE_STALE", codes(report))

    def test_failed_security_requirement_is_a_policy_violation(self) -> None:
        catalog = clean_catalog()
        integration(catalog, "gitleaks")["security_requirements"][0]["status"] = "fail"
        report = evaluate_catalog(catalog)
        self.assertIn("SECURITY_REQUIREMENT_FAILED", codes(report))
        self.assertEqual(report["decision"], POLICY_VIOLATION)

    def test_unknown_and_restricted_licenses_are_reported(self) -> None:
        catalog = clean_catalog()
        integration(catalog, "gunicorn")["license"] = "Proprietary"
        report = evaluate_catalog(catalog)
        self.assertIn("UNSUPPORTED_LICENSE", codes(report))
        self.assertEqual(classify_license("AGPL-3.0-only"), "restricted")
        integration(catalog, "gunicorn")["license"] = "AGPL-3.0-only"
        restricted = evaluate_catalog(catalog)
        self.assertEqual(restricted["decision"], POLICY_VIOLATION)

    def test_unsafe_paths_are_rejected(self) -> None:
        with self.assertRaises(CatalogError):
            safe_relative_path("../outside", "owned_path")
        catalog = base_catalog()
        integration(catalog, "gunicorn")["owned_paths"] = ["../outside"]
        report = evaluate_catalog(catalog)
        self.assertIn("UNSAFE_PATH", codes(report))

    def test_command_like_config_fields_are_never_executed(self) -> None:
        catalog = base_catalog()
        integration(catalog, "gunicorn")["config"]["command"] = "echo untrusted"
        with patch("os.system", side_effect=AssertionError("command executed")):
            report = evaluate_catalog(catalog)
        self.assertIn("UNTRUSTED_CONFIG_FIELD", codes(report))
        self.assertEqual(report["guardrails"], GUARDRAILS)
        self.assertFalse(report["guardrails"]["executes_repository_commands"])

    def test_artifact_dependency_requires_integrity_metadata(self) -> None:
        catalog = base_catalog()
        integration(catalog, "gunicorn")["dependencies"][0]["artifact"] = True
        report = evaluate_catalog(catalog)
        self.assertIn("MISSING_INTEGRITY_METADATA", codes(report))
        integration(catalog, "gunicorn")["dependencies"][0]["integrity"] = {
            "algorithm": "md5", "expected": "a" * 64
        }
        invalid = evaluate_catalog(catalog)
        self.assertIn("INVALID_INTEGRITY_METADATA", codes(invalid))

    def test_invalid_component_version_is_reported(self) -> None:
        catalog = base_catalog()
        catalog["component_versions"]["python"] = "3.x"
        report = evaluate_catalog(catalog)
        self.assertIn("INVALID_VERSION_SPEC", codes(report))

    def test_markdown_report_includes_diagnostics_and_no_secrets(self) -> None:
        report = evaluate_catalog(base_catalog())
        rendered = render_markdown_report(report)
        for expected in ("Decision", "Integration inventory", "Guardrails", "Diagnostics"):
            self.assertIn(expected, rendered)
        self.assertIn("no-network-access", rendered)
        self.assertIn("No merge, deploy, install", rendered)

    def test_cli_fails_closed_for_default_fixture_license_violation(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(["--input", str(DEFAULT_FIXTURE_PATH), "--format", "json"])
        self.assertEqual(exit_code, 1)
        self.assertIn("POLICY_VIOLATION", output.getvalue())
        self.assertIn("UNSUPPORTED_LICENSE", output.getvalue())

    def test_cli_diagnostic_is_structured_without_traceback(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["--input", "does-not-exist.json"])
        self.assertEqual(exit_code, 2)
        self.assertIn("catalog_not_found", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "")

    def test_cli_allows_explicit_finding_override(self) -> None:
        catalog = copy.deepcopy(base_catalog())
        integration(catalog, "gunicorn")["config"].clear()
        with temp_catalog_path(catalog) as path:
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["--input", str(path), "--allow-findings"])
        self.assertEqual(exit_code, 0)
        self.assertIn("MISSING_CONFIGURATION", output.getvalue())

    def test_change_classifier_selects_python_tests_for_devobs_source(self) -> None:
        self.assertTrue(is_python(PurePosixPath("devobs/integration_readiness/evaluator.py")))
        self.assertTrue(is_python(PurePosixPath("tests/integration_readiness/test_core.py")))
        self.assertFalse(is_python(PurePosixPath("docs/architecture/OPEN_SOURCE_INTEGRATIONS.md")))


class _TempCatalog:
    def __init__(self, catalog: dict) -> None:
        self.catalog = catalog
        self.path = None

    def __enter__(self):
        import json
        import tempfile
        from pathlib import Path

        folder = tempfile.TemporaryDirectory()
        path = Path(folder.name) / "catalog.json"
        path.write_text(json.dumps(self.catalog), encoding="utf-8")
        self.path = path
        self._folder = folder
        return path

    def __exit__(self, *args) -> None:
        self._folder.cleanup()


def temp_catalog_path(catalog: dict) -> _TempCatalog:
    return _TempCatalog(catalog)


if __name__ == "__main__":
    unittest.main()

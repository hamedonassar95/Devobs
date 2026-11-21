"""Core behavioral tests for offline integration readiness evaluation."""
from __future__ import annotations

import copy
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devobs.integration_readiness import (
    NEEDS_EVIDENCE,
    READY_FOR_HUMAN_REVIEW,
    evaluate_catalog,
    load_catalog,
)


def base_catalog() -> dict:
    return copy.deepcopy(load_catalog())


def clean_catalog() -> dict:
    """Return an in-memory copy with the known fixture violation remediated."""
    catalog = base_catalog()
    integration(catalog, "terraform-cli")["license"] = "MPL-2.0"
    return catalog


def integration(catalog: dict, identifier: str) -> dict:
    for item in catalog["integrations"]:
        if item["id"] == identifier:
            return item
    raise AssertionError(f"missing fixture integration: {identifier}")


def codes(report: dict) -> set[str]:
    return {item["code"] for item in report["findings"]}


class ReadinessCoreTests(unittest.TestCase):
    def test_empty_catalog_fails_closed_with_needs_evidence(self) -> None:
        catalog = base_catalog()
        catalog["integrations"] = []
        report = evaluate_catalog(catalog)
        self.assertEqual(report["decision"], NEEDS_EVIDENCE)
        self.assertIn("EMPTY_CATALOG", codes(report))
        self.assertTrue(report["human_review_required"])

    def test_fixture_is_deterministic_and_surfaces_terraform_license(self) -> None:
        first = evaluate_catalog(base_catalog())
        second = evaluate_catalog(base_catalog())
        self.assertEqual(first, second)
        self.assertEqual(first["decision"], "POLICY_VIOLATION")
        self.assertEqual(codes(first), {"UNSUPPORTED_LICENSE"})
        self.assertEqual(first["counts"]["integrations"], 11)
        finding = first["findings"][0]
        self.assertEqual(finding["integration_id"], "terraform-cli")
        self.assertEqual(finding["evidence"], ["BUSL-1.1"])
        self.assertEqual(len(first["report_digest"]), 64)

    def test_remediated_copy_can_reach_ready_for_human_review(self) -> None:
        report = evaluate_catalog(clean_catalog())
        self.assertEqual(report["decision"], READY_FOR_HUMAN_REVIEW)
        self.assertEqual(report["counts"]["findings"], 0)

    def test_missing_required_configuration_is_reported_without_inference(self) -> None:
        catalog = base_catalog()
        integration(catalog, "python-runtime")["config"].clear()
        report = evaluate_catalog(catalog)
        self.assertIn("MISSING_CONFIGURATION", codes(report))
        finding = next(item for item in report["findings"] if item["code"] == "MISSING_CONFIGURATION")
        self.assertIn("hash_lock_enabled", finding["evidence"])
        self.assertNotIn("true", finding["message"].lower())

    def test_invalid_version_specification_is_reported(self) -> None:
        catalog = base_catalog()
        integration(catalog, "python-runtime")["requirements"][0]["spec"] = "=>3.10"
        report = evaluate_catalog(catalog)
        self.assertIn("INVALID_VERSION_SPEC", codes(report))

    def test_invalid_integration_version_is_reported(self) -> None:
        catalog = base_catalog()
        integration(catalog, "gunicorn")["version"] = "1..2"
        report = evaluate_catalog(catalog)
        self.assertIn("INVALID_VERSION_SPEC", codes(report))

    def test_unsupported_dependency_is_reported(self) -> None:
        catalog = base_catalog()
        integration(catalog, "gunicorn")["dependencies"][0]["spec"] = ">=99,<100"
        report = evaluate_catalog(catalog)
        self.assertIn("UNSUPPORTED_DEPENDENCY", codes(report))

    def test_missing_dependency_is_reported(self) -> None:
        catalog = base_catalog()
        integration(catalog, "gunicorn")["dependencies"][0]["id"] = "absent-component"
        report = evaluate_catalog(catalog)
        self.assertIn("MISSING_DEPENDENCY", codes(report))

    def test_dependency_cycle_is_reported(self) -> None:
        catalog = base_catalog()
        integration(catalog, "python-runtime")["dependencies"].append(
            {"id": "gunicorn", "spec": ">=1,<2"}
        )
        report = evaluate_catalog(catalog)
        self.assertIn("DEPENDENCY_CYCLE", codes(report))
        finding = next(item for item in report["findings"] if item["code"] == "DEPENDENCY_CYCLE")
        self.assertIn("gunicorn", finding["evidence"])
        self.assertIn("python-runtime", finding["evidence"])

    def test_file_ownership_conflict_is_reported(self) -> None:
        catalog = clean_catalog()
        integration(catalog, "cosign")["owner"] = "security"
        report = evaluate_catalog(catalog)
        self.assertIn("OWNERSHIP_CONFLICT", codes(report))
        self.assertEqual(report["decision"], "POLICY_VIOLATION")

    def test_blocked_integration_is_reported(self) -> None:
        catalog = clean_catalog()
        integration(catalog, "conftest")["status"] = "blocked"
        report = evaluate_catalog(catalog)
        self.assertIn("INTEGRATION_BLOCKED", codes(report))
        self.assertEqual(report["decision"], "BLOCKED")

    def test_deprecated_integration_is_reported(self) -> None:
        catalog = base_catalog()
        integration(catalog, "gunicorn")["support_until"] = "2026-01-01"
        report = evaluate_catalog(catalog)
        self.assertIn("DEPRECATED_INTEGRATION", codes(report))

    def test_malformed_json_fails_closed(self) -> None:
        from devobs.integration_readiness import CatalogError

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text('{"schema_version":', encoding="utf-8")
            with self.assertRaises(CatalogError) as raised:
                load_catalog(path)
        self.assertIn("malformed_json", raised.exception.code)

    def test_oversized_catalog_fails_closed(self) -> None:
        catalog = base_catalog()
        integration(catalog, "python-runtime")["notes"] = "x" * 2_000_000
        report = evaluate_catalog(catalog)
        self.assertIn("MALFORMED_CATALOG", codes(report))
        self.assertEqual(report["decision"], "POLICY_VIOLATION")
        self.assertIn("P0", report["counts"]["by_priority"])

    def test_offline_evaluation_makes_no_network_attempt(self) -> None:
        def forbidden(*args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("network attempted")

        with patch.object(socket.socket, "connect", forbidden):
            report = evaluate_catalog(base_catalog())
        self.assertEqual(report["decision"], "POLICY_VIOLATION")
        self.assertIn("no-network-access", report["diagnostics"])

    def test_stable_report_schema_and_actionable_plan(self) -> None:
        catalog = base_catalog()
        integration(catalog, "gunicorn")["config"].clear()
        report = evaluate_catalog(catalog)
        expected = {
            "schema_version", "report_schema", "profile", "scope_sha", "evaluation_date",
            "decision", "human_review_required", "summary", "counts", "findings",
            "remediation_plan", "integration_inventory", "guardrails", "diagnostics",
            "report_digest",
        }
        self.assertEqual(set(report), expected)
        self.assertTrue(report["remediation_plan"])
        self.assertEqual(report["remediation_plan"][0]["rank"], 1)
        self.assertTrue(report["findings"][0]["remediation"])

    def test_incompatible_catalog_schema_fails_closed(self) -> None:
        catalog = base_catalog()
        catalog["schema_version"] = 99
        report = evaluate_catalog(catalog)
        self.assertIn("INCOMPATIBLE_SCHEMA", codes(report))
        self.assertEqual(report["decision"], "POLICY_VIOLATION")

    def test_impossible_evaluation_date_fails_closed(self) -> None:
        catalog = base_catalog()
        catalog["evaluation_date"] = "2026-99-99"
        report = evaluate_catalog(catalog)
        self.assertEqual(report["decision"], "POLICY_VIOLATION")
        self.assertEqual(codes(report), {"MALFORMED_CATALOG"})

    def test_json_renderer_is_stable_and_parseable(self) -> None:
        from devobs.integration_readiness import render_json_report

        report = evaluate_catalog(base_catalog())
        first = render_json_report(report)
        self.assertEqual(first, render_json_report(report))
        parsed = json.loads(first)
        self.assertEqual(parsed["report_digest"], report["report_digest"])


if __name__ == "__main__":
    unittest.main()

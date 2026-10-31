"""Offline behavioral checks for the review-only integration catalog."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_integration_catalog import validate_catalog  # noqa: E402


class IntegrationCatalogTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / "docs/integrations/service-inventory.json"
        self.inventory = json.loads(path.read_text(encoding="utf-8"))

    def invalid(self, mutated, expected):
        errors = validate_catalog(mutated)
        self.assertTrue(errors, "Invalid inventory must fail closed.")
        self.assertTrue(
            any(expected in e for e in errors),
            f"Expected {expected!r} in validation errors, got {errors!r}",
        )

    def test_real_catalog_is_valid(self):
        self.assertEqual(validate_catalog(self.inventory), [])

    def test_unknown_provider_rejected(self):
        data = copy.deepcopy(self.inventory)
        data["services"][0]["id"] = "unknown"
        self.invalid(data, "Service ids must match")

    def test_duplicate_provider_rejected(self):
        data = copy.deepcopy(self.inventory)
        data["services"][1]["id"] = "gitbook"
        self.invalid(data, "Duplicate service ids")

    def test_provider_write_claim_rejected(self):
        data = copy.deepcopy(self.inventory)
        data["services"][1]["provider_writes_authorized"] = True
        self.invalid(data, "provider writes require")

    def test_paid_operation_claim_rejected(self):
        data = copy.deepcopy(self.inventory)
        data["services"][3]["cost_authorized"] = True
        self.invalid(data, "paid operations require")

    def test_global_deploy_permission_rejected(self):
        data = copy.deepcopy(self.inventory)
        data["policy"]["production_deploy_allowed"] = True
        self.invalid(data, "production_deploy_allowed")

    def test_unverified_runtime_claim_rejected(self):
        data = copy.deepcopy(self.inventory)
        data["services"][2]["runtime_verified"] = True
        self.invalid(data, "runtime is not verified")

    def test_gitbook_main_scope_cannot_be_silently_changed(self):
        data = copy.deepcopy(self.inventory)
        data["services"][0]["observed_branch"] = "docs/gitbook-sync-prep"
        self.invalid(data, "observed source path")

    def test_missing_evidence_rejected(self):
        data = copy.deepcopy(self.inventory)
        data["services"][4]["evidence"] = []
        self.invalid(data, "evidence must contain")

    def test_openart_draft_cannot_be_promoted_to_live_connector(self):
        data = copy.deepcopy(self.inventory)
        record = next(s for s in data["services"] if s["id"] == "openart")
        record["integration_status"] = "import_confirmed"
        self.invalid(data, "only a draft handoff")

    def test_docs_mcp_must_not_claim_live_handshake(self):
        data = copy.deepcopy(self.inventory)
        record = next(s for s in data["services"] if s["id"] == "openai-docs-mcp")
        record["runtime_verified"] = True
        self.invalid(data, "runtime handshake is not verified")

    def test_docs_mcp_must_keep_source_path(self):
        data = copy.deepcopy(self.inventory)
        record = next(s for s in data["services"] if s["id"] == "openai-docs-mcp")
        record["observed_directory"] = "unknown.toml"
        self.invalid(data, "source path is not verified")

    def test_no_provider_can_claim_cost_authorization(self):
        for index in range(len(self.inventory["services"])):
            data = copy.deepcopy(self.inventory)
            data["services"][index]["cost_authorized"] = True
            self.invalid(data, "paid operations require")

    def test_non_object_rejected(self):
        self.invalid([], "Catalog must be a JSON object")

    def test_missing_services_rejected(self):
        data = copy.deepcopy(self.inventory)
        del data["services"]
        self.invalid(data, "services must be an array")

    def test_date_must_parse(self):
        data = copy.deepcopy(self.inventory)
        data["review_date"] = "2026-99-77"
        self.invalid(data, "review_date")


if __name__ == "__main__":
    unittest.main()

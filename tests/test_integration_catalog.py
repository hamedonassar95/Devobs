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

    def test_argocd_mcp_must_remain_unverified_and_opt_in(self):
        record = next(s for s in self.inventory["services"] if s["id"] == "argocd-mcp")
        self.assertEqual(record["integration_status"], "config_committed_unverified")
        self.assertIs(record["runtime_verified"], False)
        self.assertEqual(
            record["observed_directory"], ".codex/examples/argocd-mcp-readonly.toml"
        )

        data = copy.deepcopy(self.inventory)
        next(s for s in data["services"] if s["id"] == "argocd-mcp")["runtime_verified"] = True
        self.invalid(data, "Argo CD MCP runtime is not verified")

    def test_google_calendar_stays_local_optional_and_runtime_unverified(self):
        record = next(s for s in self.inventory["services"] if s["id"] == "google-calendar-ai7")
        self.assertEqual(record["integration_status"], "local_feature_unverified")
        self.assertIs(record["runtime_verified"], False)
        self.assertIs(record["provider_writes_authorized"], False)
        self.assertIs(record["cost_authorized"], False)
        self.assertEqual(
            record["observed_directory"],
            "scripts/ai_intelligence/dashboard_assets/google_calendar_followup.mjs",
        )

        data = copy.deepcopy(self.inventory)
        next(s for s in data["services"] if s["id"] == "google-calendar-ai7")["runtime_verified"] = True
        self.invalid(data, "Google Calendar OAuth/runtime is not verified")

    def test_google_docs_stays_local_optional_and_runtime_unverified(self):
        record = next(s for s in self.inventory["services"] if s["id"] == "google-docs-ai7")
        self.assertEqual(record["integration_status"], "local_feature_unverified")
        self.assertIs(record["runtime_verified"], False)
        self.assertIs(record["provider_writes_authorized"], False)
        self.assertIs(record["cost_authorized"], False)
        self.assertEqual(
            record["observed_directory"],
            "scripts/ai_intelligence/dashboard_assets/google_docs_export.mjs",
        )
        self.assertIn("drive.file", record["verified_capability"])
        self.assertIn("No OAuth Client ID", record["blocker"])

        data = copy.deepcopy(self.inventory)
        next(s for s in data["services"] if s["id"] == "google-docs-ai7")["runtime_verified"] = True
        self.invalid(data, "Google Docs OAuth/runtime is not verified")

    def test_google_sheets_stays_local_optional_and_runtime_unverified(self):
        record = next(s for s in self.inventory["services"] if s["id"] == "google-sheets-ai7")
        self.assertEqual(record["integration_status"], "local_feature_unverified")
        self.assertIs(record["runtime_verified"], False)
        self.assertIs(record["provider_writes_authorized"], False)
        self.assertIs(record["cost_authorized"], False)
        self.assertEqual(
            record["observed_directory"],
            "scripts/ai_intelligence/dashboard_assets/google_sheets_export.mjs",
        )

        data = copy.deepcopy(self.inventory)
        next(s for s in data["services"] if s["id"] == "google-sheets-ai7")["runtime_verified"] = True
        self.invalid(data, "Google Sheets OAuth/runtime is not verified")

    def test_google_slides_stays_local_optional_and_runtime_unverified(self):
        record = next(s for s in self.inventory["services"] if s["id"] == "google-slides-ai7")
        self.assertEqual(record["integration_status"], "local_feature_unverified")
        self.assertIs(record["runtime_verified"], False)
        self.assertIs(record["provider_writes_authorized"], False)
        self.assertIs(record["cost_authorized"], False)
        self.assertEqual(
            record["observed_directory"],
            "scripts/ai_intelligence/dashboard_assets/google_slides_export.mjs",
        )

        data = copy.deepcopy(self.inventory)
        next(s for s in data["services"] if s["id"] == "google-slides-ai7")["runtime_verified"] = True
        self.invalid(data, "Google Slides OAuth/runtime is not verified")

    def test_google_chat_stays_local_optional_and_runtime_unverified(self):
        record = next(s for s in self.inventory["services"] if s["id"] == "google-chat-ai7")
        self.assertEqual(record["integration_status"], "local_feature_unverified")
        self.assertIs(record["runtime_verified"], False)
        self.assertIs(record["provider_writes_authorized"], False)
        self.assertIs(record["cost_authorized"], False)
        self.assertEqual(
            record["observed_directory"],
            "scripts/ai_intelligence/dashboard_assets/google_chat_export.mjs",
        )

        data = copy.deepcopy(self.inventory)
        next(s for s in data["services"] if s["id"] == "google-chat-ai7")["runtime_verified"] = True
        self.invalid(data, "Google Chat OAuth/runtime is not verified")

    def test_google_tasks_stays_local_optional_and_runtime_unverified(self):
        record = next(s for s in self.inventory["services"] if s["id"] == "google-tasks-ai7")
        self.assertEqual(record["integration_status"], "local_feature_unverified")
        self.assertIs(record["runtime_verified"], False)
        self.assertIs(record["provider_writes_authorized"], False)
        self.assertIs(record["cost_authorized"], False)
        self.assertEqual(
            record["observed_directory"],
            "scripts/ai_intelligence/dashboard_assets/google_tasks_followup.mjs",
        )

        data = copy.deepcopy(self.inventory)
        next(s for s in data["services"] if s["id"] == "google-tasks-ai7")["runtime_verified"] = True
        self.invalid(data, "Google Tasks OAuth/runtime is not verified")

    def test_google_gmail_stays_local_optional_and_runtime_unverified(self):
        record = next(s for s in self.inventory["services"] if s["id"] == "google-gmail-ai7")
        self.assertEqual(record["integration_status"], "local_feature_unverified")
        self.assertIs(record["runtime_verified"], False)
        self.assertIs(record["provider_writes_authorized"], False)
        self.assertIs(record["cost_authorized"], False)
        self.assertEqual(
            record["observed_directory"],
            "scripts/ai_intelligence/dashboard_assets/google_gmail_summary.mjs",
        )

        data = copy.deepcopy(self.inventory)
        next(s for s in data["services"] if s["id"] == "google-gmail-ai7")["runtime_verified"] = True
        self.invalid(data, "Google Gmail OAuth/runtime is not verified")

    def test_no_provider_can_claim_cost_authorization(self):
        for index in range(len(self.inventory["services"])):
            data = copy.deepcopy(self.inventory)
            data["services"][index]["cost_authorized"] = True
            self.invalid(data, "paid operations require")

    def test_aictrl_repository_denial_is_not_runtime_proof(self):
        record = next(s for s in self.inventory["services"] if s["id"] == "aictrl")
        self.assertEqual(record["integration_status"], "account_connected_unlinked")
        self.assertIs(record["runtime_verified"], False)
        self.assertIn("not found", record["verified_capability"].lower())
        self.assertIn("authorize that exact repository", record["blocker"])

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

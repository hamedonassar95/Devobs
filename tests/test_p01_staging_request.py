"""P01 request is a non-authorizing scoped plan; no provider calls."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "docs/p01/p01-staging-authorization-request.json"
DOC = ROOT / "docs/p01/2026-10-31-scoped-staging-request.md"

class ScopedRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(REQUEST.read_text(encoding="utf-8"))
        cls.text = DOC.read_text(encoding="utf-8")

    def test_read_only_scope_never_authorizes_external_actions(self):
        self.assertEqual(self.data["decision"], "DRAFT_ONLY_NO_GO")
        scope = self.data["owner_authorized_scope"]
        self.assertTrue(scope["read_only_account_inspection"])
        self.assertTrue(scope["draft_scoped_request"])
        for key in ("create_resource", "upgrade_plan", "add_payment_method", "deploy", "enable_paid_ai", "use_customer_data"):
            with self.subTest(key=key):
                self.assertIs(scope[key], False)
        self.assertIs(self.data["spend_authorized"], False)
        self.assertIs(self.data["owner_p01_go"], False)
        self.assertIsNone(self.data["create_action_selected"])

    def test_owner_chose_separate_devobs_organization_not_repair_org(self):
        choice = self.data["owner_architecture_choice"]
        self.assertEqual(choice["authority_repository"], "hamedonassar95/Devobs")
        self.assertEqual(choice["central_organization_strategy"], "new_separate_free_organization")
        self.assertEqual(choice["central_organization_name_proposed"], "Devobs AI Intelligence")
        self.assertFalse(choice["central_organization_created"])
        self.assertFalse(choice["initial_lab_project_created"])
        self.assertTrue(choice["experiment_projects_remain_separate"])
        self.assertFalse(choice["external_workflow_changes_authorized"])

    def test_budget_target_and_examples_are_not_actual_quotes(self):
        b = self.data["budget_policy"]
        self.assertEqual(b, {"kind":"operating_target_not_guaranteed_cap",
                            "monthly_target_usd":100,"core_usd":60,"metered_usd":20,"reserve_usd":20})
        self.assertEqual(self.data["public_list_price_examples_usd_per_month"]["commercial_render_pro_starter_supabase_pro"],57)
        self.assertFalse(self.data["cost_quote_account_specific"])

    def test_projects_and_regions_separate(self):
        env = self.data["environment"]
        self.assertTrue(env["separate_from_phone_repair"])
        self.assertEqual(env["region_supabase"], "eu-central-1")
        self.assertEqual(env["region_render"], "frankfurt")
        self.assertFalse(env["public_endpoint_authorized"])
        self.assertFalse(self.data["existing"]["render_service_list_determinate"])

    def test_no_known_account_identifiers_or_secrets_are_published(self):
        serialized = REQUEST.read_text(encoding="utf-8") + self.text
        for disallowed in ("cezbdlenzevnvmplcaok", "jzdvhpezfiytojyoxpeo",
                           "tea-dafq4ue7bikc73d7tmig", "team_jFZl0k0MLyFdgqQWyzWJb6hI",
                           "mohammadnassar813@", "OPENAI_API_KEY=", "SUPABASE_SERVICE_ROLE_KEY="):
            with self.subTest(secret=disallowed):
                self.assertNotIn(disallowed,serialized)
        self.assertIn("NO-GO", self.text)
        self.assertIn("separate", self.text)

    def test_all_unknown_billing_categories_are_retained(self):
        self.assertFalse(self.data["existing"]["vercel_invoice_verified"])
        self.assertFalse(self.data["existing"]["auth0_account_verified"])
        self.assertFalse(self.data["existing"]["render_workspace_subscription_verified"])
        self.assertGreaterEqual(len(self.data["unknowns"]),10)

if __name__=="__main__":
    unittest.main()

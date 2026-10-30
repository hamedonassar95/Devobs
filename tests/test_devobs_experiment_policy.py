"""Negative/offline checks for control-plane versus experiment separation."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_devobs_experiment_policy import check  # noqa: E402


def policy():
    return json.loads((ROOT / "docs/architecture/devobs_experiment_policy.json").read_text())


class CoreExperimentBoundaryTests(unittest.TestCase):
    def test_shipped_policy_is_safe_proposal(self):
        self.assertEqual(check(policy()), [])

    def test_cannot_rename_or_move_core_away_from_devobs(self):
        for key, value in [("authority_repository","hamedonassar95/phone-repair-assistant-v2"),
                           ("architecture_status","LIVE"),
                           ("project","AL-DALA MOBILE")]:
            doc = policy()
            doc[key] = value
            with self.subTest(key=key):
                self.assertNotEqual(check(doc), [])

    def test_core_cloud_org_and_project_are_uncreated(self):
        doc = policy()
        for key in ("organization_created","project_created","account_quote_verified","p01_go"):
            bad = copy.deepcopy(doc)
            bad["central_control_plane"][key] = True
            with self.subTest(key=key):
                self.assertTrue(check(bad))

    def test_cross_project_access_must_never_be_automatically_enabled(self):
        for key in ("cross_project_database_access","shared_admin_credentials",
                    "shared_tenant_identity_without_verification","copy_customer_data_into_core",
                    "experiment_can_trigger_production","experiment_can_modify_main",
                    "unapproved_paid_ai_calls"):
            doc = policy()
            doc["integration_policy"][key] = True
            with self.subTest(key=key):
                self.assertTrue(check(doc))

    def test_experiments_cannot_be_misreported_as_integrated(self):
        doc = policy()
        doc["experiments"][0]["live_devobs_integration_verified"] = True
        self.assertTrue(check(doc))
        doc = policy()
        doc["experiments"].append(copy.deepcopy(doc["experiments"][0]))
        self.assertTrue(check(doc))

    def test_money_and_real_data_transfers_remain_unapproved(self):
        for key in ("real_external_connections_authorized","spend_authorized",
                    "customer_data_transfer_authorized"):
            doc = policy()
            doc[key] = True
            with self.subTest(key=key):
                self.assertTrue(check(doc))

    def test_experiment_cannot_directly_trigger_mutation(self):
        doc = policy()
        doc["allowed_conceptual_flow"].append("write_to_production")
        self.assertTrue(check(doc))

    def test_unexpected_extra_keys_or_production_mode_rejected(self):
        doc = policy()
        doc["api_secret"] = "untrusted"
        self.assertTrue(check(doc))
        doc = policy()
        doc["integration_policy"]["human_approval_required"] = False
        self.assertTrue(check(doc))


if __name__ == "__main__":
    unittest.main()

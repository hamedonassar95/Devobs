"""Offline behavioral tests for the Devobs-only free staging status guard."""
import contextlib
from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_free_staging_health as check  # noqa: E402

NOW = datetime(2026, 11, 17, 9, 0, tzinfo=timezone.utc)


def fixture():
    return {
        "schema_version": 2,
        "scope": "devobs-free-staging",
        "observed_on": "2026-11-17",
        "render": {
            "web_plan": "free", "web_suspended": False, "web_auto_deploy": False,
            "web_runtime_verified": False, "web_ingress_reviewed": False,
            "web_last_deploy_status": "update_failed",
            "web_last_deploy_commit": "1f1fd774f02579a500c07bd667865e51ed187948",
            "database_plan": "free",
            "database_status": "available", "database_expires_at": "2026-12-05T10:33:24.202776Z",
            "database_backup_verified": False,
        },
        "supabase": {"project_status": "INACTIVE", "hosted_isolation_verified": False},
    }


class FreeStagingHealthTests(unittest.TestCase):
    def test_current_provider_observations_block_go(self):
        r = check.assess_snapshot(fixture(), NOW)
        self.assertEqual(r["status"], "REVIEW_REQUIRED")
        self.assertIn("DEVOBS_SUPABASE_NOT_ACTIVE", r["blockers"])
        self.assertIn("RENDER_DATABASE_EXPIRY_REVIEW", r["blockers"])
        self.assertIn("RENDER_BACKUP_UNVERIFIED", r["blockers"])
        self.assertIn("RENDER_PUBLIC_INGRESS_UNREVIEWED", r["blockers"])
        self.assertIn("RENDER_LATEST_DEPLOY_NOT_LIVE", r["blockers"])
        self.assertEqual(r["render_latest_deploy_status"], "update_failed")
        self.assertFalse(r["production_ready"])
        self.assertFalse(r["paid_activation_authorized"])
        self.assertFalse(r["live_provider_request_performed"])

    def test_hypothetical_green_snapshot_never_claims_production_go(self):
        s = fixture()
        s["render"].update(web_runtime_verified=True, web_ingress_reviewed=True,
                           web_last_deploy_status="live",
                           database_backup_verified=True,
                           database_expires_at="2027-01-31T00:00:00Z")
        s["supabase"].update(project_status="ACTIVE_HEALTHY", hosted_isolation_verified=True)
        result = check.assess_snapshot(s, NOW)
        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["production_ready"])
        self.assertFalse(result["automatic_merge_authorized"])

    def test_failed_deploy_blocks_even_when_other_provider_checks_are_green(self):
        s = fixture()
        s["render"].update(web_runtime_verified=True, web_ingress_reviewed=True,
                           database_backup_verified=True,
                           database_expires_at="2027-01-31T00:00:00Z")
        s["supabase"].update(project_status="ACTIVE_HEALTHY", hosted_isolation_verified=True)
        r = check.assess_snapshot(s, NOW)
        self.assertEqual(r["blockers"], ["RENDER_LATEST_DEPLOY_NOT_LIVE"])
        self.assertEqual(r["status"], "REVIEW_REQUIRED")
        self.assertFalse(r["production_ready"])

    def test_running_or_failed_render_deploys_all_block(self):
        for status in ("created", "build_in_progress", "update_in_progress",
                       "build_failed", "update_failed", "canceled", "deactivated",
                       "pre_deploy_failed"):
            with self.subTest(status=status):
                s = fixture()
                s["render"]["web_last_deploy_status"] = status
                r = check.assess_snapshot(s, NOW)
                self.assertIn("RENDER_LATEST_DEPLOY_NOT_LIVE", r["blockers"])

    def test_invalid_or_missing_render_deploy_provenance_fails_closed(self):
        for mutation in (
            lambda s: s["render"].pop("web_last_deploy_status"),
            lambda s: s["render"].update(web_last_deploy_status="ready"),
            lambda s: s["render"].update(web_last_deploy_status=True),
            lambda s: s["render"].pop("web_last_deploy_commit"),
            lambda s: s["render"].update(web_last_deploy_commit="not-a-commit"),
            lambda s: s["render"].update(web_last_deploy_commit="A" * 40),
        ):
            s = fixture()
            mutation(s)
            with self.assertRaises(check.InvalidSnapshot):
                check.assess_snapshot(s, NOW)

    def test_stale_evidence_fails_closed(self):
        r = check.assess_snapshot(fixture(), datetime(2026, 11, 26, tzinfo=timezone.utc))
        self.assertIn("STALE_PROVIDER_EVIDENCE", r["blockers"])

    def test_expired_database_overrides_available(self):
        s = fixture()
        s["observed_on"] = "2026-12-06"
        r = check.assess_snapshot(s, datetime(2026, 12, 6, tzinfo=timezone.utc))
        self.assertIn("RENDER_DATABASE_EXPIRED", r["blockers"])
        self.assertNotIn("RENDER_DATABASE_EXPIRY_REVIEW", r["blockers"])

    def test_reject_paid_plan_and_cross_project_scope(self):
        for field, bad in (("scope", "phone-repair-assistant-v2"),
                           ("schema_version", True), ("schema_version", 1)):
            s = fixture()
            s[field] = bad
            with self.subTest(field=field), self.assertRaises(check.InvalidSnapshot):
                check.assess_snapshot(s, NOW)
        s = fixture()
        s["render"]["database_plan"] = "starter"
        with self.assertRaises(check.InvalidSnapshot):
            check.assess_snapshot(s, NOW)

    def test_reject_unknown_fields_credentials_and_invalid_booleans(self):
        for mutation in (lambda s: s.update(token="not-allowed"),
                         lambda s: s["render"].update(password="not-allowed"),
                         lambda s: s["render"].update(web_suspended="false"),
                         lambda s: s["supabase"].update(project_status="READY"),
                         lambda s: s["render"].update(database_status=[]),
                         lambda s: s["supabase"].update(project_status=[])):

            s = fixture()
            mutation(s)
            with self.assertRaises(check.InvalidSnapshot):
                check.assess_snapshot(s, NOW)

    def test_loader_rejects_duplicate_keys_and_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = root / "report.json"
            p.write_text('{"scope":"foo","scope":"bar"}', encoding="utf-8")
            with self.assertRaises(check.InvalidSnapshot):
                check.load_snapshot(p)
            link = root / "link.json"
            link.symlink_to(p)
            with self.assertRaises(check.InvalidSnapshot):
                check.load_snapshot(link)

    def test_cli_malformed_file_returns_no_go_without_raw_content(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "snapshot.json"
            p.write_text('{"access_token":"SYNTHETIC_PRIVATE_STRING"}', encoding="utf-8")
            errors = StringIO()
            with contextlib.redirect_stderr(errors):
                rc = check.main(["--file", str(p), "--json"])
            self.assertEqual(rc, 2)
            self.assertNotIn("SYNTHETIC_PRIVATE_STRING", errors.getvalue())

    def test_cli_valid_fixture_returns_review_required(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "snapshot.json"
            p.write_text(json.dumps(fixture()), encoding="utf-8")
            output = StringIO()
            with contextlib.redirect_stdout(output):
                rc = check.main(["--file", str(p), "--json"])
            self.assertEqual(rc, 1)
            self.assertEqual(json.loads(output.getvalue())["status"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()

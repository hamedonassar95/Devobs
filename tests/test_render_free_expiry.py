"""Offline behavior checks for the Render Free database expiry decision guard."""
import datetime as dt
import unittest
from pathlib import Path
import sys
import json
import tempfile
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_render_free_expiry import assess_expiry, InvalidSnapshot, load_snapshot

ROOT = Path(__file__).resolve().parents[1]

NOW = dt.datetime(2026, 11, 15, 20, 0, tzinfo=dt.timezone.utc)


def snapshot(**changes):
    record = {
        "plan": "free",
        "status": "available",
        "observed_on": "2026-11-15",
        "expires_at": "2026-12-05T10:33:24.202776Z",
    }
    record.update(changes)
    return record


class RenderFreeExpiryTests(unittest.TestCase):
    def test_2026_11_19_account_snapshot_blocks_production(self):
        """A fresh available Free DB is still REVIEW_REQUIRED, never P01 GO."""
        record = load_snapshot(ROOT / "docs/p01/render-free-expiry-snapshot.json")
        self.assertEqual(record["observed_on"], "2026-11-19")
        self.assertEqual(record["plan"], "free")
        self.assertEqual(record["status"], "available")
        self.assertEqual(record["expires_at"], "2026-12-05T10:33:24.202776Z")
        at_review = dt.datetime(2026, 11, 19, 9, 30, tzinfo=dt.timezone.utc)
        decision = assess_expiry(record, at_review)
        self.assertEqual(decision["status"], "REVIEW_REQUIRED")
        self.assertEqual(decision["exit_code"], 1)
        self.assertFalse(decision["production_approved"])
        self.assertFalse(decision["paid_activation_authorized"])
        self.assertFalse(decision["provider_access_performed"])
        # Offline evidence must not be treated as eternally fresh.
        stale = assess_expiry(record, dt.datetime(2026, 11, 27, 12, tzinfo=dt.timezone.utc))
        self.assertEqual(stale["status"], "STALE_INVENTORY")
        self.assertEqual(stale["exit_code"], 1)

    def test_expiry_within_30_days_requires_human_review(self):
        result = assess_expiry(snapshot(), NOW)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["exit_code"], 1)
        self.assertFalse(result["production_approved"])
        self.assertFalse(result["paid_activation_authorized"])

    def test_expired_is_blocked_even_if_snapshot_says_available(self):
        later = dt.datetime(2026, 12, 6, tzinfo=dt.timezone.utc)
        # Re-observing on the expiration day cannot restore the expired Free instance.
        result = assess_expiry(snapshot(observed_on="2026-12-06"), later)
        self.assertEqual(result["status"], "EXPIRED")
        self.assertEqual(result["exit_code"], 1)

    def test_stale_inventory_cannot_claim_database_is_available(self):
        result = assess_expiry(snapshot(), dt.datetime(2026, 11, 24, tzinfo=dt.timezone.utc))
        self.assertEqual(result["status"], "STALE_INVENTORY")
        self.assertEqual(result["exit_code"], 1)

    def test_non_available_provider_state_blocks(self):
        result = assess_expiry(snapshot(status="suspended"), NOW)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["exit_code"], 1)

    def test_far_expiry_is_never_hosted_release_approval(self):
        result = assess_expiry(snapshot(expires_at="2027-01-20T00:00:00Z"), NOW)
        self.assertEqual(result["status"], "NOT_IMMINENT")
        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(result["production_approved"])

    def test_untrusted_fields_and_paid_plan_rejected(self):
        for bad in (snapshot(password="accidental"), snapshot(plan="starter")):
            with self.subTest(bad=sorted(bad)):
                with self.assertRaises(InvalidSnapshot):
                    assess_expiry(bad, NOW)

    def test_future_date_and_invalid_expiry_are_rejected(self):
        for bad in (snapshot(observed_on="2026-11-18"),
                    snapshot(expires_at="2026-12-05T10:33:24+00:00"),
                    snapshot(expires_at="tomorrow")):
            with self.subTest(bad=bad["expires_at"]):
                with self.assertRaises(InvalidSnapshot):
                    assess_expiry(bad, NOW)

    def test_cli_returns_review_status_without_live_provider_access(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "snapshot.json"
            path.write_text(json.dumps(snapshot()), encoding="utf-8")
            run = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "check_render_free_expiry.py"),
                 "--file", str(path), "--json"],
                capture_output=True, text=True, check=False,
            )
            # The fixture is fixed to Nov 15, 2026; a later execution must fail
            # closed as REVIEW_REQUIRED, STALE_INVENTORY, or EXPIRED.
            self.assertEqual(run.returncode, 1, run.stderr)
            result = json.loads(run.stdout)
            self.assertIn(result["status"], {"REVIEW_REQUIRED", "STALE_INVENTORY", "EXPIRED"})
            self.assertFalse(result["provider_access_performed"])
            self.assertFalse(result["production_approved"])

    def test_loader_rejects_duplicate_fields_and_symlinks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "snapshot.json"
            path.write_text('{"plan":"free","plan":"free"}', encoding="utf-8")
            with self.assertRaises(InvalidSnapshot):
                load_snapshot(path)
            alias = root / "alias.json"
            alias.symlink_to(path)
            with self.assertRaises(InvalidSnapshot):
                load_snapshot(alias)


if __name__ == "__main__":
    unittest.main()

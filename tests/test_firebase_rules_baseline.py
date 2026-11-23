"""Offline behavioral regressions for the Devobs Firestore deny-all baseline."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_firebase_rules_baseline.py"

spec = importlib.util.spec_from_file_location("firebase_rules_baseline", CHECKER)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FirebaseRulesBaselineTests(unittest.TestCase):
    def test_canonical_source_passes(self):
        source = (ROOT / "apps/ai-intelligence-console/firestore.rules").read_text(encoding="utf-8")
        self.assertEqual(module.assess_rules(source), ("PASS", "CANONICAL_DENY_ALL_BASELINE"))

    def test_anonymous_read_grant_fails(self):
        insecure = """rules_version = '2';
            service cloud.firestore {
              match /databases/{database}/documents {
                match /servers/{serverId} {
                  allow read: if request.auth != null || true;
                }
              }
            }
        """
        self.assertEqual(module.assess_rules(insecure), ("FAIL", "UNCONDITIONAL_ALLOW_CONDITION"))

    def test_unconditional_allow_fails(self):
        self.assertEqual(module.assess_rules("allow read, write: if true;"),
                         ("FAIL", "UNCONDITIONAL_ALLOW_CONDITION"))

    def test_new_auth_only_policy_is_unverified_not_approved(self):
        self.assertEqual(module.assess_rules("allow write: if request.auth != null;"),
                         ("BLOCKED", "RULES_REQUIRE_INDEPENDENT_REVIEW"))

    def test_empty_or_unknown_is_blocked(self):
        self.assertEqual(module.assess_rules("\n"), ("BLOCKED", "EMPTY_RULESET"))
        self.assertEqual(module.assess_rules("unexpected input"),
                         ("BLOCKED", "RULES_REQUIRE_INDEPENDENT_REVIEW"))

    def test_cli_sanitized_and_no_network(self):
        proc = subprocess.run([sys.executable, str(CHECKER)], capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["scope"], "LOCAL_SOURCE_ONLY")
        self.assertNotIn("apiKey", proc.stdout)

    def test_cli_fails_closed_if_rules_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "absent.rules"
            proc = subprocess.run(
                [sys.executable, str(CHECKER), "--rules-file", str(missing)],
                capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stdout)["reason"], "RULES_FILE_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()

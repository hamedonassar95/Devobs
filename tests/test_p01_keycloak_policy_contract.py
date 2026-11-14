"""Regression checks for the narrowly scoped Keycloak policy exception."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY = (ROOT / "AGENTS.md").read_text(encoding="utf-8").lower()
PREFLIGHT = (ROOT / "docs/P01_KEYCLOAK_HTTPS_PREFLIGHT.md").read_text(
    encoding="utf-8"
).lower()
README = (ROOT / "README.md").read_text(encoding="utf-8").lower()
PUBLIC_SUMMARIES = {
    "AGENTS.md": POLICY,
    "docs/P01_KEYCLOAK_HTTPS_PREFLIGHT.md": PREFLIGHT,
    "README.md": README,
}


class KeycloakPolicyContractTests(unittest.TestCase):
    def test_all_policy_summaries_share_the_reconciliation_activation_boundary(self):
        stale_status = (
            "proposed, not active",
            "not an active exception",
            "separate proposed exception",
            "until the policy pr is merged",
        )
        for name, text in PUBLIC_SUMMARIES.items():
            with self.subTest(document=name):
                self.assertIn(
                    "effective only after this reconciliation pr is merged", text
                )
                self.assertIn("until this reconciliation pr is merged", text)
                self.assertIn("general secret-handling prohibition", text)
                for phrase in stale_status:
                    self.assertNotIn(phrase, text)

    def test_each_runtime_run_requires_exact_owner_approval_scope(self):
        for name, text in PUBLIC_SUMMARIES.items():
            with self.subTest(document=name):
                self.assertRegex(
                    text,
                    re.compile(
                        r"separate explicit owner approval for (?:every runtime test run|that run)"
                    ),
                )
                self.assertIn("full reviewed source sha", text)
                self.assertIn("unique docker compose project name", text)
                self.assertIn("exact test scope", text)

    def test_remote_or_non_unix_docker_endpoints_are_blocked(self):
        for name, text in PUBLIC_SUMMARIES.items():
            with self.subTest(document=name):
                self.assertIn("local unix socket", text)
                self.assertIn("ssh://", text)
                self.assertIn("tcp://", text)
                self.assertIn("remote", text)
                self.assertIn("blocked", text)
                self.assertRegex(text, r"(?:ssh://|tcp://).{0,100}blocked")
        self.assertIn("named-pipe", POLICY)
        self.assertIn("named-pipe", PREFLIGHT)

    def test_exception_does_not_authorize_production_or_paid_operations(self):
        for name, text in PUBLIC_SUMMARIES.items():
            with self.subTest(document=name):
                self.assertIn("does not authorize", text)
                self.assertIn("production", text)
                self.assertIn("deployment", text)
                self.assertIn("hosted", text)
                self.assertIn("paid ai inference", text)
        for term in ("render", "postgresql", "supabase", "cloud resources"):
            with self.subTest(term=term):
                self.assertIn(term, POLICY)
        for phrase in (
            "authorizes production",
            "permits production",
            "may modify hosted configuration",
            "authorizes cloud changes",
            "allows paid ai inference",
            "authorizes deployment",
        ):
            with self.subTest(forbidden_permission=phrase):
                self.assertNotIn(phrase, "\n".join(PUBLIC_SUMMARIES.values()))

    def test_private_material_export_and_secret_logging_remain_prohibited(self):
        for name, text in (("AGENTS.md", POLICY), ("preflight", PREFLIGHT)):
            with self.subTest(document=name):
                self.assertRegex(text, r"never (?:export|inspect).{0,100}private")
                self.assertIn("log credentials or tokens", text)
                self.assertIn("raw secret-bearing", text)
                self.assertIn("commit", text)
        self.assertIn("no private-key inspection/export", README)
        all_summaries = "\n".join(PUBLIC_SUMMARIES.values())
        for permission in (
            "may export private",
            "may inspect private",
            "may log credentials or tokens",
            "allowed to export private",
            "allowed to inspect private",
            "may capture raw secret-bearing",
        ):
            with self.subTest(forbidden_permission=permission):
                self.assertNotIn(permission, all_summaries)

    def test_general_secret_rule_has_only_the_runtime_generation_carveout(self):
        self.assertIn(
            "the sole exception to secret creation is keycloak's automatic generation",
            POLICY,
        )
        self.assertIn("all other secret handling remains prohibited", POLICY)
        self.assertIn("no person or agent may read, open, inspect, export", POLICY)

    def test_only_disposable_realm_signing_generation_is_in_scope(self):
        for term in (
            "automatic generation and internal use",
            "disposable realm signing material",
            "sha256:c68e286cacd87b942ac1939a0a1481461109d6acd3a57dc496969a319a76bbf0",
            "127.0.0.1:443:8443",
            "no named, persistent, or durable volume",
            "synthetic identities only",
            "project-scoped cleanup",
            "sanitized pass/fail/blocked evidence",
        ):
            with self.subTest(term=term):
                self.assertIn(term, POLICY)
        self.assertIn("operator manages the localhost certificate", POLICY)
        self.assertIn("public ca", POLICY)
        self.assertIn("read-only", POLICY)

    def test_policy_preserves_p01_and_ai9_gates(self):
        self.assertIn("p01", POLICY)
        self.assertIn("ai-9", POLICY)
        self.assertIn("p01 remains no-go", PREFLIGHT)
        self.assertIn("ai-9 remains blocked", PREFLIGHT)
        self.assertIn("p01 remains no-go", README)
        self.assertIn("ai-9 remains blocked", README)


if __name__ == "__main__":
    unittest.main()

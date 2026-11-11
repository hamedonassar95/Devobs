"""Offline contract for the proposed, non-provisioned Render Free Blueprint."""

from pathlib import Path
import json
import shutil
import subprocess
import unittest

try:
    import yaml
except ImportError:  # pragma: no cover - GitHub's Ubuntu runner includes Ruby/Psych.
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = ROOT / "render.yaml"
STAGING_DOC = ROOT / "docs" / "RENDER_SUPABASE_STAGING.md"
RUNBOOK_DOC = ROOT / "docs" / "RENDER_OPENAI_STAGING_RUNBOOK.md"


def parse_blueprint():
    source = BLUEPRINT.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.load(source, Loader=yaml.BaseLoader)

    ruby = shutil.which("ruby")
    if ruby is None:
        raise RuntimeError("A YAML parser is required: use PyYAML or runner-provided Ruby/Psych.")
    parser = (
        'require "yaml"; require "json"; '
        'data = YAML.load_file(ARGV.fetch(0), aliases: false); '
        'STDOUT.write(JSON.generate(data))'
    )
    result = subprocess.run(
        [ruby, "-e", parser, str(BLUEPRINT)], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def is_off(value):
    return value is False or str(value).lower() == "off"


def is_false(value):
    return value is False or str(value).lower() == "false"


class RenderFreeStagingBlueprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blueprint = parse_blueprint()
        cls.doc = STAGING_DOC.read_text(encoding="utf-8")
        cls.runbook = RUNBOOK_DOC.read_text(encoding="utf-8")

    def test_one_free_frankfurt_web_service_keeps_deploy_and_preview_guards(self):
        self.assertTrue(is_off(self.blueprint["previews"]["generation"]))
        services = self.blueprint["services"]
        self.assertEqual(len(services), 1)
        service = services[0]
        self.assertEqual(service["type"], "web")
        self.assertEqual(service["runtime"], "python")
        self.assertEqual(service["plan"], "free")
        self.assertEqual(service["region"], "frankfurt")
        self.assertTrue(is_off(service["autoDeployTrigger"]))
        self.assertEqual(service["healthCheckPath"], "/readyz")
        self.assertNotIn("preDeployCommand", service)
        self.assertNotIn("initialDeployHook", service)
        self.assertEqual(
            service["buildCommand"],
            "python3 -m pip install --disable-pip-version-check --require-hashes "
            "-r requirements-api.lock",
        )
        self.assertEqual(
            service["startCommand"],
            "gunicorn --chdir scripts --workers 1 --bind 0.0.0.0:$PORT --timeout 30 "
            "devobs_intelligence.staging_app:application",
        )

    def test_private_ephemeral_postgres_and_disabled_ai_defaults(self):
        service = self.blueprint["services"][0]
        env_vars = {item["key"]: item for item in service["envVars"]}
        self.assertEqual(env_vars["DEVOBS_PG_TLS_MODE"]["value"],
                         "render-internal-require")
        self.assertTrue(is_false(env_vars["DEVOBS_AI_DIAGNOSTICS_ENABLED"]["value"]))
        self.assertTrue(is_false(env_vars["DEVOBS_AI_BUDGET_APPROVED"]["value"]))
        self.assertEqual(env_vars["DEVOBS_AI_MODEL"]["value"], "gpt-6-luna")
        for key in (
            "DEVOBS_PG_DSN", "DEVOBS_OIDC_ISSUER", "DEVOBS_OIDC_AUDIENCE",
            "DEVOBS_OIDC_CLIENT_ID", "DEVOBS_OIDC_METADATA_JSON",
            "DEVOBS_OIDC_JWKS_JSON", "OPENAI_API_KEY",
        ):
            self.assertNotIn(key, env_vars)

        self.assertEqual(len(self.blueprint["databases"]), 1)
        database = self.blueprint["databases"][0]
        self.assertEqual(database["name"], "devobs-ai-staging-db")
        self.assertEqual(database["databaseName"], "devobs_ai_staging")
        self.assertEqual(database["user"], "devobs_ai_staging_admin")
        self.assertEqual(database["postgresMajorVersion"], "17")
        self.assertEqual(database["plan"], "free")
        self.assertEqual(database["region"], "frankfurt")
        self.assertEqual(database["ipAllowList"], [])

    def test_docs_keep_provisioning_and_data_access_gates_explicit(self):
        for required in (
            "P01 remains NO-GO / BLOCKED",
            "synthetic data only",
            "30 days",
            "OPENAI_API_KEY",
            "DEVOBS_AI_DIAGNOSTICS_ENABLED",
            "DEVOBS_AI_BUDGET_APPROVED",
            "5 diagnoses",
            "verify-full",
            "run each migration exactly once",
            "No successful hosted API request or live model call has been verified",
            "Do not import the Blueprint again",
            "temporary-migration",
            "invalid_staging_config",
        ):
            with self.subTest(required=required):
                if required not in self.runbook:
                    self.fail(f"staging runbook must state: {required}")


if __name__ == "__main__":
    unittest.main()

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

    def test_free_worker_entrypoint_and_required_settings_fail_closed(self):
        service = self.blueprint["services"][0]
        self.assertEqual(
            service["startCommand"],
            "gunicorn --chdir scripts --workers 1 --bind 0.0.0.0:10000 --timeout 30 "
            "devobs_intelligence.staging_app:application",
        )
        env_vars = service["envVars"]
        expected = {
            "DEVOBS_PG_DSN",
            "DEVOBS_OIDC_ISSUER",
            "DEVOBS_OIDC_AUDIENCE",
            "DEVOBS_OIDC_CLIENT_ID",
            "DEVOBS_OIDC_METADATA_JSON",
            "DEVOBS_OIDC_JWKS_JSON",
        }
        self.assertEqual({item["key"] for item in env_vars}, expected)
        for item in env_vars:
            self.assertTrue(is_false(item["sync"]), item["key"])
            self.assertNotIn("value", item, item["key"])
        self.assertNotIn("databases", self.blueprint)

    def test_docs_keep_provisioning_and_data_access_gates_explicit(self):
        for required in (
            "P01 remains NO-GO / BLOCKED",
            "synthetic data only",
            "initial build and deploy",
            "512 MB",
            "Data API",
            "FORCE ROW LEVEL SECURITY",
            "sslmode=verify-full",
            "Vercel preview",
            "no managed Free-tier backups",
        ):
            with self.subTest(required=required):
                if required not in self.doc:
                    self.fail(f"staging documentation must state: {required}")


if __name__ == "__main__":
    unittest.main()

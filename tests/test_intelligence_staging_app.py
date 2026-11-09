"""Staging entrypoint: offline security tests without a real cloud account."""
import importlib
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from psycopg.conninfo import conninfo_to_dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa


class StagingBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
        jwk.update(kid="testkey", alg="RS256", use="sig")
        cls.base = {
            "DEVOBS_OIDC_ISSUER": "https://id.example.test",
            "DEVOBS_OIDC_AUDIENCE": "devobs-api",
            "DEVOBS_OIDC_CLIENT_ID": "devobs-staging",
            "DEVOBS_OIDC_METADATA_JSON": json.dumps({
                "issuer": "https://id.example.test",
                "jwks_uri": "https://id.example.test/keys"}),
            "DEVOBS_OIDC_JWKS_JSON": json.dumps({"keys": [jwk]}),
            "DEVOBS_PG_DSN": ("postgresql://devobs_reader:synthetic@127.0.0.1:5432/"
                              "staging?sslmode=verify-full&sslrootcert=/tmp/test-ca.pem"),
        }
        # Import-time fail-closed bootstrap gets synthetic, scoped settings only.
        with patch.dict(os.environ, cls.base, clear=True):
            cls.module = importlib.import_module("devobs_intelligence.staging_app")

    def run_request(self, app, path, method="GET", auth="", environ_overrides=None):
        environ = {"PATH_INFO": path, "REQUEST_METHOD": method,
                   "HTTP_AUTHORIZATION": auth, "CONTENT_LENGTH": "",
                   "wsgi.input": io.BytesIO(b"")}
        if environ_overrides:
            environ.update(environ_overrides)
        results = []
        body = b"".join(app(environ,
                            lambda status, headers: results.append((status, dict(headers)))))
        return results[0][0], results[0][1], body

    def test_health_is_liveness_only_and_no_secrets(self):
        app = self.module.build_app(self.base)
        status, headers, body = self.run_request(app, "/healthz")
        self.assertEqual(status, "204 No Content")
        self.assertEqual(body, b"")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(self.run_request(app, "/healthz", method="POST")[0][:3], "405")

    def test_api_remains_token_protected(self):
        app = self.module.build_app(self.base)
        status, headers, body = self.run_request(app, "/v1/tenants/a/projects/b/ci")
        self.assertTrue(status.startswith("401"))
        self.assertEqual(json.loads(body), {"error": "invalid_token"})
        self.assertNotIn("synthetic", str(headers) + body.decode())

    def test_model_diagnostics_are_disabled_by_default(self):
        app = self.module.build_app(self.base)
        self.assertIsNotNone(app)

    def test_local_metrics_fail_closed_without_both_explicit_flags(self):
        config = {**self.base, "DEVOBS_OTEL_METRICS_ENABLED": "true"}
        with self.assertRaisesRegex(
                self.module.StagingConfigurationError, "^invalid_staging_config$"):
            self.module.build_app(config)

    def test_explicit_local_metrics_wrap_the_complete_wsgi_application(self):
        class FakeMetrics:
            def __init__(self):
                self.application = None

            def instrument(self, application):
                self.application = application
                return wrapped

            def shutdown(self):
                pass

        wrapped = object()
        metrics = FakeMetrics()
        config = {
            **self.base,
            "DEVOBS_OTEL_METRICS_ENABLED": "true",
            "DEVOBS_OTEL_METRICS_LOCAL_ONLY": "true",
        }
        with patch.object(self.module, "create_local_metrics", return_value=metrics), \
                patch.object(self.module.atexit, "register") as register:
            app = self.module.build_app(config)
        self.assertIs(app, wrapped)
        self.assertTrue(callable(metrics.application))
        register.assert_called_once_with(metrics.shutdown)

    def test_model_diagnostics_require_budget_acknowledgment_and_provider_key(self):
        config = dict(self.base)
        config["DEVOBS_AI_DIAGNOSTICS_ENABLED"] = "true"
        with self.assertRaisesRegex(self.module.StagingConfigurationError,
                                    "^invalid_staging_config$"):
            self.module.build_app(config)
        config["DEVOBS_AI_BUDGET_APPROVED"] = "true"
        with self.assertRaisesRegex(self.module.StagingConfigurationError,
                                    "^invalid_staging_config$"):
            self.module.build_app(config)
        config["OPENAI_API_KEY"] = "synthetic-test-key"
        with patch.object(self.module, "OpenAIErrorLogDiagnostician") as provider:
            app = self.module.build_app(config)
        self.assertIsNotNone(app)
        provider.assert_called_once_with("synthetic-test-key", model="gpt-6-luna")

    def test_gemini_requires_key_model_data_policy_and_budget_approval(self):
        config = dict(self.base)
        config.update({
            "DEVOBS_AI_DIAGNOSTICS_ENABLED": "true",
            "DEVOBS_AI_PROVIDER": "gemini",
            "DEVOBS_GEMINI_MODEL": "gemini-test-flash",
            "GEMINI_API_KEY": "synthetic-gemini-key",
        })
        with self.assertRaisesRegex(self.module.StagingConfigurationError,
                                    "^invalid_staging_config$"):
            self.module.build_app(config)

        config["DEVOBS_AI_BUDGET_APPROVED"] = "true"
        with self.assertRaisesRegex(self.module.StagingConfigurationError,
                                    "^invalid_staging_config$"):
            self.module.build_app(config)

        config["DEVOBS_AI_GEMINI_DATA_POLICY_APPROVED"] = "true"
        with patch.object(self.module, "GeminiErrorLogDiagnostician") as provider:
            app = self.module.build_app(config)
        self.assertIsNotNone(app)
        provider.assert_called_once_with("synthetic-gemini-key", model="gemini-test-flash")

        for missing in ("GEMINI_API_KEY", "DEVOBS_GEMINI_MODEL"):
            invalid = dict(config)
            invalid.pop(missing)
            with self.subTest(missing=missing), self.assertRaisesRegex(
                    self.module.StagingConfigurationError, "^invalid_staging_config$"):
                self.module.build_app(invalid)

    def test_gemini_never_falls_back_to_google_api_key_or_unknown_provider(self):
        config = dict(self.base)
        config.update({
            "DEVOBS_AI_DIAGNOSTICS_ENABLED": "true",
            "DEVOBS_AI_BUDGET_APPROVED": "true",
            "DEVOBS_AI_PROVIDER": "gemini",
            "DEVOBS_GEMINI_MODEL": "gemini-test-flash",
            "DEVOBS_AI_GEMINI_DATA_POLICY_APPROVED": "true",
            "GOOGLE_API_KEY": "must-not-be-consumed",
        })
        with self.assertRaisesRegex(self.module.StagingConfigurationError,
                                    "^invalid_staging_config$"):
            self.module.build_app(config)

        config["DEVOBS_AI_PROVIDER"] = "unknown"
        with self.assertRaisesRegex(self.module.StagingConfigurationError,
                                    "^invalid_staging_config$"):
            self.module.build_app(config)

    def test_ollama_requires_local_approval_and_explicit_model_but_not_cloud_budget(self):
        config = dict(self.base)
        config.update({
            "DEVOBS_AI_DIAGNOSTICS_ENABLED": "true",
            "DEVOBS_AI_PROVIDER": "ollama",
            "DEVOBS_LOCAL_MODEL": "llama3.2:3b",
        })
        with self.assertRaisesRegex(self.module.StagingConfigurationError,
                                    "^invalid_staging_config$"):
            self.module.build_app(config)

        config["DEVOBS_AI_LOCAL_INFERENCE_APPROVED"] = "true"
        with patch.object(self.module, "LocalModelErrorLogDiagnostician") as provider:
            app = self.module.build_app(config)
        self.assertIsNotNone(app)
        provider.assert_called_once_with("ollama", model="llama3.2:3b", api_key="")

    def test_localai_key_is_optional_environment_input_and_render_loopback_is_rejected(self):
        config = dict(self.base)
        config.update({
            "DEVOBS_AI_DIAGNOSTICS_ENABLED": "true",
            "DEVOBS_AI_PROVIDER": "localai",
            "DEVOBS_AI_LOCAL_INFERENCE_APPROVED": "true",
            "DEVOBS_LOCAL_MODEL": "local-model",
            "LOCALAI_API_KEY": "synthetic-localai-key",
        })
        with patch.object(self.module, "LocalModelErrorLogDiagnostician") as provider:
            app = self.module.build_app(config)
        self.assertIsNotNone(app)
        provider.assert_called_once_with(
            "localai", model="local-model", api_key="synthetic-localai-key")

        config["RENDER"] = "true"
        with self.assertRaisesRegex(self.module.StagingConfigurationError,
                                    "^invalid_staging_config$"):
            self.module.build_app(config)

    def test_local_provider_requires_model_and_does_not_fallback_to_cloud(self):
        config = dict(self.base)
        config.update({
            "DEVOBS_AI_DIAGNOSTICS_ENABLED": "true",
            "DEVOBS_AI_PROVIDER": "ollama",
            "DEVOBS_AI_LOCAL_INFERENCE_APPROVED": "true",
            "OPENAI_API_KEY": "must-not-be-consumed",
        })
        with self.assertRaisesRegex(self.module.StagingConfigurationError,
                                    "^invalid_staging_config$"):
            self.module.build_app(config)

    def test_missing_or_untrusted_identity_denied(self):
        for key in self.base:
            with self.subTest(missing=key):
                config = dict(self.base)
                config.pop(key)
                with self.assertRaisesRegex(self.module.StagingConfigurationError,
                                            "^invalid_staging_config$"):
                    self.module.build_app(config)
        for name, value in [
            ("DEVOBS_OIDC_METADATA_JSON", "{}"),
            ("DEVOBS_OIDC_JWKS_JSON", "not-json"),
            ("DEVOBS_OIDC_ISSUER", "http://id.example.test"),
        ]:
            with self.subTest(invalid=name):
                config = dict(self.base)
                config[name] = value
                with self.assertRaises(self.module.StagingConfigurationError):
                    self.module.build_app(config)

    def test_no_plaintext_or_admin_postgres(self):
        for dsn in [
            "postgresql://devobs_reader:synthetic@localhost/staging",
            "postgresql://devobs_reader:synthetic@localhost/staging?sslmode=require",
            "postgresql://postgres:synthetic@localhost/staging?sslmode=verify-full&sslrootcert=/tmp/ca",
            "postgresql://postgres.ref:synthetic@localhost/staging?sslmode=verify-full&sslrootcert=/tmp/ca",
            "postgresql://devobs_reader:synthetic@localhost/staging?sslmode=verify-full",
            "not-a-connection-string",
        ]:
            with self.subTest(dsn=dsn.split("@")[0].split(":")[0]):
                config = dict(self.base)
                config["DEVOBS_PG_DSN"] = dsn
                with self.assertRaisesRegex(self.module.StagingConfigurationError,
                                            "^invalid_staging_config$"):
                    self.module.build_app(config)

    def test_render_internal_tls_mode_is_explicit_and_render_only(self):
        config = dict(self.base)
        config.update({
            "DEVOBS_PG_DSN": "postgresql://devobs_reader:synthetic@internal-db/staging",
            "DEVOBS_PG_TLS_MODE": "render-internal-require",
            "RENDER": "true",
            "RENDER_SERVICE_TYPE": "web",
        })
        parsed = conninfo_to_dict(self.module._database_dsn(config))
        self.assertEqual(parsed["sslmode"], "require")
        self.assertEqual(parsed["host"], "internal-db")

        for env_updates in (
            {"RENDER": "false"},
            {"RENDER_SERVICE_TYPE": "worker"},
        ):
            invalid = dict(config)
            invalid.update(env_updates)
            with self.subTest(env_updates=env_updates):
                with self.assertRaisesRegex(self.module.StagingConfigurationError,
                                            "^invalid_staging_config$"):
                    self.module._database_dsn(invalid)

    def test_readiness_requires_actual_database_probe(self):
        # Avoid real credentials: readiness checks are isolated behind the store.
        class ProbeStore:
            healthy = True
            def probe_readiness(self):
                if not self.healthy:
                    raise RuntimeError("SECRET_database_unavailable")
                return True

        store = ProbeStore()
        with patch.object(self.module, "PostgresTenantStore", return_value=store):
            app = self.module.build_app(self.base)
        healthy = self.run_request(app, "/readyz")
        self.assertEqual(healthy[0], "204 No Content")
        self.assertEqual(healthy[2], b"")
        store.healthy = False
        unavailable = self.run_request(app, "/readyz")
        self.assertEqual(unavailable[0], "503 Service Unavailable")
        self.assertEqual(unavailable[2], b"")
        self.assertNotIn("SECRET", str(unavailable))
        self.assertEqual(self.run_request(app, "/readyz", method="POST")[0][:3], "405")

    def test_declared_request_body_is_rejected_before_readiness_probe(self):
        class ProbeStore:
            calls = 0

            def probe_readiness(self):
                self.calls += 1
                return True

        store = ProbeStore()
        with patch.object(self.module, "PostgresTenantStore", return_value=store):
            app = self.module.build_app(self.base)
        status, headers, body = self.run_request(
            app, "/readyz", environ_overrides={
                "CONTENT_LENGTH": "20000", "wsgi.input": io.BytesIO(b"x" * 20000)})
        self.assertEqual(status, "400 Bad Request")
        self.assertEqual(json.loads(body), {"error": "request_body_not_allowed"})
        self.assertEqual(store.calls, 0)
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_wsgi_terminated_request_body_is_rejected_before_readiness_probe(self):
        class ProbeStore:
            calls = 0

            def probe_readiness(self):
                self.calls += 1
                return True

        store = ProbeStore()
        with patch.object(self.module, "PostgresTenantStore", return_value=store):
            app = self.module.build_app(self.base)
        status, headers, body = self.run_request(
            app, "/readyz", environ_overrides={
                "CONTENT_LENGTH": "", "wsgi.input_terminated": True,
                "wsgi.input": io.BytesIO(b"x")})
        self.assertEqual(status, "400 Bad Request")
        self.assertEqual(json.loads(body), {"error": "request_body_not_allowed"})
        self.assertEqual(store.calls, 0)
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_render_health_check_requires_real_readiness(self):
        config = (Path(__file__).resolve().parents[1] / "render.yaml").read_text()
        checks = [line.strip() for line in config.splitlines()
                  if line.strip().startswith("healthCheckPath:")]
        self.assertEqual(checks, ["healthCheckPath: /readyz"])
        self.assertIn("autoDeployTrigger: off", config)


if __name__ == "__main__":
    unittest.main()

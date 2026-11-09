"""Privacy and fail-closed tests for the optional local WSGI metric."""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from opentelemetry.sdk.metrics.export import MetricExporter, MetricExportResult

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from devobs_intelligence import otel_metrics  # noqa: E402


class CapturingExporter(MetricExporter):
    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs
        self.exports = []

    def export(self, metrics_data, timeout_millis=10_000, **kwargs):
        self.exports.append(metrics_data)
        return MetricExportResult.SUCCESS

    def force_flush(self, timeout_millis=10_000):
        return True

    def shutdown(self, timeout_millis=30_000, **kwargs):
        return None


class OTelApiMetricsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="devobs-otel-api-test-")
        self.directory = Path(self.temp.name)
        self.cert = self.directory / "server.crt"
        self.cert.write_text("synthetic local CA certificate placeholder\n", encoding="ascii")
        self.token_file = self.directory / "app-token"
        self.token_file.write_text("a" * 64 + "\n", encoding="ascii")
        self.token_file.chmod(0o600)
        self.settings = {
            "DEVOBS_OTEL_METRICS_ENABLED": "true",
            "DEVOBS_OTEL_METRICS_LOCAL_ONLY": "true",
            "DEVOBS_OTEL_TLS_CERT_FILE": str(self.cert),
            "DEVOBS_OTEL_APP_TOKEN_FILE": str(self.token_file),
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_metrics_are_disabled_without_explicit_opt_in(self):
        self.assertIsNone(otel_metrics.create_local_metrics({}))
        self.assertIsNone(otel_metrics.create_local_metrics({
            "DEVOBS_OTEL_METRICS_LOCAL_ONLY": "true",
        }))

    def test_enabled_metrics_require_local_only_and_reject_hosted_runtime(self):
        invalid_settings = [
            {**self.settings, "DEVOBS_OTEL_METRICS_LOCAL_ONLY": "false"},
            {**self.settings, "CI": "true"},
            {**self.settings, "GITHUB_ACTIONS": "true"},
            {**self.settings, "RENDER": "true"},
            {**self.settings, "KUBERNETES_SERVICE_HOST": "10.0.0.1"},
            {**self.settings, "OTEL_EXPORTER_OTLP_HEADERS": "authorization=unexpected"},
            {**self.settings, "OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY": "/tmp/client.key"},
        ]
        for settings in invalid_settings:
            with self.subTest(rejected_key=next(
                    key for key in settings if settings.get(key) != self.settings.get(key))):
                with self.assertRaisesRegex(
                        otel_metrics.LocalMetricsConfigurationError,
                        "^invalid_local_metrics_config$"):
                    otel_metrics.create_local_metrics(settings)

    def test_missing_or_unsafe_local_token_fails_without_revealing_paths(self):
        missing = {**self.settings, "DEVOBS_OTEL_APP_TOKEN_FILE": str(self.directory / "missing")}
        public = {**self.settings, "DEVOBS_OTEL_APP_TOKEN_FILE": str(self.directory / "public-token")}
        public_path = Path(public["DEVOBS_OTEL_APP_TOKEN_FILE"])
        public_path.write_text("a" * 64 + "\n", encoding="ascii")
        public_path.chmod(0o644)
        malformed = {**self.settings, "DEVOBS_OTEL_APP_TOKEN_FILE": str(self.directory / "bad-token")}
        malformed_path = Path(malformed["DEVOBS_OTEL_APP_TOKEN_FILE"])
        malformed_path.write_text("synthetic-secret-marker\n", encoding="ascii")
        malformed_path.chmod(0o600)

        for settings in (missing, public, malformed):
            with self.subTest(token_path=settings["DEVOBS_OTEL_APP_TOKEN_FILE"]):
                with self.assertRaisesRegex(
                        otel_metrics.LocalMetricsConfigurationError,
                        "^invalid_local_metrics_config$") as error:
                    otel_metrics.create_local_metrics(settings)
                self.assertNotIn(str(self.directory), str(error.exception))
                self.assertNotIn("synthetic-secret-marker", str(error.exception))

    def test_request_histogram_has_no_request_attributes_or_exemplars(self):
        exporter = CapturingExporter()
        with patch.object(otel_metrics, "OTLPMetricExporter", return_value=exporter) as factory:
            metrics = otel_metrics.create_local_metrics(self.settings)
        self.assertIsNotNone(metrics)
        try:
            kwargs = factory.call_args.kwargs
            self.assertEqual(kwargs["endpoint"], "https://127.0.0.1:4318/v1/metrics")
            self.assertEqual(kwargs["certificate_file"], str(self.cert))
            self.assertEqual(kwargs["headers"], {"Authorization": "Bearer " + "a" * 64})
            self.assertFalse(kwargs["session"].trust_env)
            self.assertEqual(
                set(kwargs),
                {"endpoint", "certificate_file", "headers", "timeout", "compression",
                 "max_export_batch_size", "max_request_size", "session"},
            )

            response = []

            def app(environ, start_response):
                start_response("200 OK", [("Content-Type", "text/plain")])
                return [b"synthetic response"]

            request = {
                "PATH_INFO": "/v1/tenants/private-tenant/projects/project-x/ci",
                "QUERY_STRING": "email=private-person@example.invalid",
                "REQUEST_METHOD": "POST",
                "HTTP_AUTHORIZATION": "Bearer synthetic-private-request-token",
                "HTTP_X_TENANT_ID": "private-tenant",
                "HTTP_X_USER_EMAIL": "private-person@example.invalid",
                "CONTENT_LENGTH": "4",
                "wsgi.input": io.BytesIO(b"body"),
            }
            instrumented = metrics.instrument(app)
            body = b"".join(instrumented(request, lambda status, headers: response.append((status, headers))))
            self.assertEqual(body, b"synthetic response")
            self.assertEqual(response[0][0], "200 OK")
            self.assertTrue(metrics.provider.force_flush(timeout_millis=2000))

            resource_batches = [
                resource_metrics
                for batch in exporter.exports
                for resource_metrics in batch.resource_metrics
            ]
            exported = [
                metric
                for resource_metrics in resource_batches
                for scope_metrics in resource_metrics.scope_metrics
                for metric in scope_metrics.metrics
            ]
            self.assertEqual(len(exported), 1)
            metric = exported[0]
            self.assertEqual(metric.name, otel_metrics.REQUEST_DURATION_METRIC)
            self.assertEqual(metric.description, "")
            self.assertEqual(len(resource_batches), 1)
            self.assertEqual(resource_batches[0].resource.attributes, {"service.name": "devobs"})
            self.assertEqual(len(metric.data.data_points), 1)
            point = metric.data.data_points[0]
            self.assertEqual(dict(point.attributes), {})
            self.assertEqual(list(point.exemplars), [])
            self.assertEqual(point.count, 1)
            serialized = repr(exporter.exports)
            for marker in (
                "/v1/tenants/private-tenant",
                "private-person@example.invalid",
                "synthetic-private-request-token",
                "private-tenant",
            ):
                self.assertNotIn(marker, serialized)
        finally:
            metrics.shutdown()

    def test_wsgi_exception_is_preserved_and_metric_record_failure_is_non_disruptive(self):
        class BrokenHistogram:
            def record(self, _value):
                raise RuntimeError("synthetic metric failure")

        def failing_app(_environ, _start_response):
            raise RuntimeError("synthetic application failure")

        instrumented_failure = otel_metrics.instrument_wsgi_application(
            failing_app, BrokenHistogram())
        with self.assertLogs(otel_metrics.__name__, level="WARNING") as failure_logs:
            with self.assertRaisesRegex(RuntimeError, "synthetic application failure"):
                instrumented_failure({}, lambda _status, _headers: None)

        def success_app(_environ, start_response):
            start_response("200 OK", [])
            return [b"ok"]

        instrumented_success = otel_metrics.instrument_wsgi_application(
            success_app, BrokenHistogram())
        with self.assertLogs(otel_metrics.__name__, level="WARNING") as success_logs:
            body = b"".join(instrumented_success({}, lambda _status, _headers: None))
        self.assertEqual(body, b"ok")
        self.assertEqual(failure_logs.output, ["WARNING:devobs_intelligence.otel_metrics:optional_otlp_metric_record_failed"])
        self.assertEqual(success_logs.output, ["WARNING:devobs_intelligence.otel_metrics:optional_otlp_metric_record_failed"])

    def test_wsgi_close_is_preserved_after_response_iteration_and_metric_records_once(self):
        class RecordingHistogram:
            def __init__(self):
                self.values = []

            def record(self, value):
                self.values.append(value)

        class ClosingResponse:
            def __init__(self):
                self.closed = False

            def __iter__(self):
                return iter([b"ok"])

            def close(self):
                self.closed = True

        histogram = RecordingHistogram()
        response = ClosingResponse()
        wrapped = otel_metrics.instrument_wsgi_application(
            lambda _environ, _start_response: response, histogram)
        timed = wrapped({}, lambda _status, _headers: None)
        self.assertEqual(b"".join(timed), b"ok")
        timed.close()
        timed.close()
        self.assertTrue(response.closed)
        self.assertEqual(len(histogram.values), 1)
        self.assertGreaterEqual(histogram.values[0], 0)


if __name__ == "__main__":
    unittest.main()

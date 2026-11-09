import json
import os
import secrets
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "monitoring/compose.yml"
COMPOSE_TEXT = COMPOSE_FILE.read_text(encoding="utf-8")
COLLECTOR_CONFIG = (ROOT / "monitoring/otel-collector-config.yaml").read_text(encoding="utf-8")
PROMETHEUS_CONFIG = (ROOT / "monitoring/prometheus.yml").read_text(encoding="utf-8")
COLLECTOR_IMAGE = (
    "otel/opentelemetry-collector-contrib:0.165.0"
    "@sha256:e40d61f10c9a617cca1ffd1be4d7e2b3a4b0f0001798ff07e58cabe82e618cea"
)
SMOKE_CLIENT_IMAGE = (
    "python:3.12.14-alpine3.24"
    "@sha256:4c47124a8391cb7a9f571164147d154777cf012a4ece5f86097130d7a4478111"
)


class OTelCollectorConfigTests(unittest.TestCase):
    def test_collector_is_optional_authenticated_tls_metrics_only(self):
        self.assertIn("      - otel\n", COMPOSE_TEXT)
        self.assertIn("bearertokenauth:", COLLECTOR_CONFIG)
        self.assertIn("filename: /run/secrets/otel-bearer-token", COLLECTOR_CONFIG)
        self.assertIn("authenticator: bearertokenauth", COLLECTOR_CONFIG)
        self.assertEqual(COLLECTOR_CONFIG.count("cert_file: /run/secrets/otel-server.crt"), 2)
        self.assertEqual(COLLECTOR_CONFIG.count('min_version: "1.2"'), 2)
        self.assertIn("max_recv_msg_size_mib: 1", COLLECTOR_CONFIG)
        self.assertIn("max_request_body_size: 8388608", COLLECTOR_CONFIG)
        self.assertIn("limit_mib: 96", COLLECTOR_CONFIG)
        self.assertIn("spike_limit_mib: 20", COLLECTOR_CONFIG)
        self.assertIn("send_batch_max_size: 256", COLLECTOR_CONFIG)
        self.assertIn("error_mode: propagate", COLLECTOR_CONFIG)
        self.assertIn('keep_keys(attributes, [])', COLLECTOR_CONFIG)
        self.assertIn("without_scope_info: true", COLLECTOR_CONFIG)
        self.assertIn("enable_open_metrics: false", COLLECTOR_CONFIG)
        self.assertIn("translation_strategy: UnderscoreEscapingWithoutSuffixes", COLLECTOR_CONFIG)
        self.assertNotIn("debug:", COLLECTOR_CONFIG)
        self.assertNotIn("logging:", COLLECTOR_CONFIG)
        self.assertNotIn("traces:", COLLECTOR_CONFIG)
        self.assertNotIn("logs:", COLLECTOR_CONFIG)

    def test_only_the_existing_safe_metric_contract_and_smoke_metric_are_allowed(self):
        for name in (
            'metric.name == "error_rate_pct"',
            'metric.name == "capacity_pct"',
            'metric.name == "failed_checks"',
            'metric.name == "devobs_otel_smoke"',
            'resource.attributes["service.name"] != "devobs"',
            "metric.type != METRIC_DATA_TYPE_GAUGE",
        ):
            self.assertIn(name, COLLECTOR_CONFIG)

    def test_prometheus_reuses_existing_scrapes_and_adds_only_collector(self):
        for job in ("prometheus", "alertmanager", "node-exporter", "otel-collector"):
            self.assertIn(f"job_name: {job}", PROMETHEUS_CONFIG)
        for target in (
            "prometheus:9090",
            "alertmanager:9093",
            "node-exporter:9100",
            "otel-collector:8889",
        ):
            self.assertIn(f"- {target}", PROMETHEUS_CONFIG)
        self.assertEqual(PROMETHEUS_CONFIG.count("job_name:"), 4)
        self.assertIn("/etc/prometheus/alerts.yml", PROMETHEUS_CONFIG)
        self.assertIn("/etc/prometheus/alert_rules.yml", PROMETHEUS_CONFIG)


@unittest.skipUnless(
    os.environ.get("DEVOBS_RUN_OTEL_SMOKE") == "1" and shutil.which("docker"),
    "set DEVOBS_RUN_OTEL_SMOKE=1 to run the isolated Docker smoke test",
)
class OTelCollectorRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="devobs-otel-smoke-")
        cls.secret_dir = Path(cls.temp.name) / "secrets"
        cls.secret_dir.mkdir(mode=0o700)
        cls.cert = cls.secret_dir / "server.crt"
        cls.key = cls.secret_dir / "server.key"
        cls.token_file = cls.secret_dir / "token"
        cls.token = secrets.token_urlsafe(32)
        cls.token_file.write_text(cls.token + "\n", encoding="utf-8")
        cls.token_file.chmod(0o444)
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-sha256",
                "-nodes",
                "-days",
                "2",
                "-keyout",
                str(cls.key),
                "-out",
                str(cls.cert),
                "-subj",
                "/CN=127.0.0.1",
                "-addext",
                "subjectAltName=IP:127.0.0.1,DNS:localhost,DNS:otel-collector",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        cls.cert.chmod(0o444)
        cls.key.chmod(0o444)
        cls.project = f"devobs-otel-test-{secrets.token_hex(4)}"
        cls.env = os.environ.copy()
        cls.env.update(
            {
                "COMPOSE_PROJECT_NAME": cls.project,
                "DEVOBS_OTEL_TLS_DIR": str(cls.secret_dir),
                "DEVOBS_OTEL_TLS_CERT_FILE": str(cls.cert),
                "DEVOBS_OTEL_TLS_KEY_FILE": str(cls.key),
                "DEVOBS_OTEL_TOKEN_FILE": str(cls.token_file),
                "GRAFANA_ADMIN_PASSWORD": secrets.token_urlsafe(32),
            }
        )

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "env"):
            subprocess.run(
                cls.compose_command("--profile", "otel", "down", "--volumes", "--remove-orphans"),
                env=cls.env,
                check=False,
                capture_output=True,
                text=True,
            )
        if hasattr(cls, "temp"):
            cls.temp.cleanup()

    @classmethod
    def compose_command(cls, *args):
        return ["docker", "compose", "-f", str(COMPOSE_FILE), *args]

    @classmethod
    def run_compose(cls, *args, check=True):
        return subprocess.run(
            cls.compose_command(*args),
            cwd=ROOT,
            env=cls.env,
            check=check,
            capture_output=True,
            text=True,
            timeout=90,
        )

    def test_valid_invalid_and_synthetic_otlp_paths(self):
        base_env = self.env.copy()
        for name in (
            "DEVOBS_OTEL_TLS_DIR",
            "DEVOBS_OTEL_TLS_CERT_FILE",
            "DEVOBS_OTEL_TLS_KEY_FILE",
            "DEVOBS_OTEL_TOKEN_FILE",
        ):
            base_env.pop(name, None)
        base_config = subprocess.run(
            self.compose_command("config", "--format", "json"),
            cwd=ROOT,
            env=base_env,
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
        self.assertEqual(base_config.returncode, 0, base_config.stdout + base_config.stderr)
        self.assertNotIn("otel-collector", json.loads(base_config.stdout)["services"])

        compose = self.run_compose("--profile", "otel", "config", "--quiet")
        self.assertEqual(compose.returncode, 0)

        rendered = self.run_compose("--profile", "otel", "config", "--format", "json")
        model = json.loads(rendered.stdout)
        service = model["services"]["otel-collector"]
        self.assertEqual(service["image"], COLLECTOR_IMAGE)
        self.assertEqual(service["user"], "10001:10001")
        self.assertFalse(service.get("privileged", False))
        self.assertNotEqual(service.get("network_mode"), "host")
        self.assertTrue(model["networks"]["monitoring"]["internal"])
        published = {item["target"]: item["host_ip"] for item in service["ports"]}
        self.assertEqual(published, {4317: "127.0.0.1", 4318: "127.0.0.1"})
        self.assertEqual(model["services"]["prometheus"]["image"], "prom/prometheus:v3.15.1@sha256:fa3302279710be2f21a8301ec17a8b4f2301fd829bd113839b3b6b02b6f191a2")

        collector_validation = self.run_compose(
            "--profile",
            "otel",
            "run",
            "--rm",
            "--no-deps",
            "otel-collector",
            "validate",
            "--config=/etc/otelcol-contrib/config.yaml",
            check=False,
        )
        self.assertEqual(
            collector_validation.returncode,
            0,
            collector_validation.stdout + collector_validation.stderr,
        )

        prometheus_validation = self.run_compose(
            "run",
            "--rm",
            "--no-deps",
            "--entrypoint",
            "promtool",
            "prometheus",
            "check",
            "config",
            "/etc/prometheus/prometheus.yml",
            check=False,
        )
        self.assertEqual(
            prometheus_validation.returncode,
            0,
            prometheus_validation.stdout + prometheus_validation.stderr,
        )

        invalid = Path(self.temp.name) / "invalid-collector.yaml"
        invalid.write_text(
            "receivers:\n  otlp: {}\nexporters:\n  prometheus:\n    endpoint: 0.0.0.0:8889\n"
            "service:\n  pipelines:\n    metrics:\n      receivers: [missing]\n      exporters: [prometheus]\n",
            encoding="utf-8",
        )
        invalid_result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--volume",
                f"{invalid}:/tmp/invalid-collector.yaml:ro",
                COLLECTOR_IMAGE,
                "validate",
                "--config=/tmp/invalid-collector.yaml",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
        self.assertNotEqual(invalid_result.returncode, 0, "invalid Collector config must fail closed")

        self.run_compose("--profile", "otel", "up", "--detach", "prometheus", "otel-collector")
        network = model["networks"]["monitoring"]["name"]
        collector_id = self.run_compose("ps", "-q", "otel-collector").stdout.strip()
        prometheus_id = self.run_compose("ps", "-q", "prometheus").stdout.strip()
        self.assertTrue(collector_id)
        self.assertTrue(prometheus_id)
        sender_script = r'''
import json, ssl, sys, time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

token = open("/tmp/otel-token", encoding="utf-8").read().split()[0]
context = ssl.create_default_context(cafile="/tmp/otel-server.crt")
url = "https://127.0.0.1:4318/v1/metrics"
stamp = str(time.time_ns())
payload = {"resourceMetrics": [{"resource": {"attributes": [
    {"key": "service.name", "value": {"stringValue": "devobs"}},
    {"key": "customer.id", "value": {"stringValue": "synthetic-customer-marker"}}
]}, "scopeMetrics": [{"scope": {"name": "synthetic-test-scope"}, "metrics": [
    {"name": "devobs_otel_smoke", "description": "synthetic-description-marker", "unit": "1",
     "gauge": {"dataPoints": [{"timeUnixNano": stamp, "asInt": "1", "attributes": [
         {"key": "user.email", "value": {"stringValue": "synthetic-private@example.invalid"}}
     ]}]}},
    {"name": "unapproved_metric_name", "gauge": {"dataPoints": [{"timeUnixNano": stamp, "asInt": "1"}]}}
]}]}]}
body = json.dumps(payload).encode()
unauthorized = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
last_error = None
for _ in range(40):
    try:
        with urlopen(unauthorized, context=context, timeout=5) as response:
            raise SystemExit("unauthenticated OTLP request was accepted")
    except HTTPError as error:
        if error.code != 401:
            raise SystemExit(f"expected HTTP 401, got {error.code}")
        break
    except URLError as error:
        last_error = error
        time.sleep(0.5)
else:
    raise SystemExit(f"OTLP receiver did not become ready: {last_error!r}")
request = Request(url, data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer " + token}, method="POST")
with urlopen(request, context=context, timeout=10) as response:
    if response.status not in (200, 202):
        raise SystemExit(f"unexpected OTLP response: {response.status}")
exported = ""
for _ in range(15):
    with urlopen("http://127.0.0.1:8889/metrics", timeout=5) as response:
        exported = response.read().decode()
    if "devobs_otel_smoke" in exported:
        break
    time.sleep(1)
if "devobs_otel_smoke" not in exported or "unapproved_metric_name" in exported:
    raise SystemExit(
        "Collector exporter allowlist check failed: "
        f"expected_metric={('devobs_otel_smoke' in exported)} "
        f"disallowed_metric={('unapproved_metric_name' in exported)}"
    )
for marker in ("synthetic-customer-marker", "synthetic-private@example.invalid", "synthetic-description-marker", "synthetic-test-scope"):
    if marker in exported:
        raise SystemExit("synthetic free-form data escaped Collector sanitization")
print("synthetic OTLP accepted; unauthenticated request rejected; attributes and unknown metric filtered")
'''
        def run_in_namespace(container_id, script, *, mount_secrets=False):
            command = ["docker", "run", "--rm", "--network", f"container:{container_id}"]
            if mount_secrets:
                command.extend(
                    [
                        "--volume",
                        f"{self.cert}:/tmp/otel-server.crt:ro",
                        "--volume",
                        f"{self.token_file}:/tmp/otel-token:ro",
                    ]
                )
            command.extend([SMOKE_CLIENT_IMAGE, "python3", "-c", script])
            return subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=90,
            )

        collector_smoke = run_in_namespace(collector_id, sender_script, mount_secrets=True)
        self.assertEqual(collector_smoke.returncode, 0, collector_smoke.stdout + collector_smoke.stderr)

        prometheus_script = r'''
import json, time
from urllib.parse import urlencode
from urllib.request import urlopen

def query(name):
    url = "http://127.0.0.1:9090/api/v1/query?" + urlencode({"query": name})
    with urlopen(url, timeout=5) as response:
        return json.load(response).get("data", {}).get("result", [])

samples = []
for _ in range(40):
    samples = query("devobs_otel_smoke")
    if samples:
        break
    time.sleep(1)
if len(samples) != 1:
    with urlopen("http://127.0.0.1:9090/api/v1/targets?state=active", timeout=5) as response:
        targets = json.load(response).get("data", {}).get("activeTargets", [])
    otel_targets = [
        {key: target.get(key) for key in ("scrapeUrl", "health", "lastError")}
        for target in targets
        if target.get("labels", {}).get("job") == "otel-collector"
    ]
    with urlopen("http://127.0.0.1:9090/api/v1/label/__name__/values", timeout=5) as response:
        metric_names = json.load(response).get("data", [])
    devobs_names = [name for name in metric_names if name.startswith("devobs")]
    raise SystemExit(
        f"synthetic OTLP gauge query was empty; target status={otel_targets!r}; "
        f"Devobs metric names={devobs_names!r}"
    )
labels = json.dumps(samples[0]["metric"])
for marker in ("synthetic-customer-marker", "synthetic-private@example.invalid", "synthetic-test-scope"):
    if marker in labels:
        raise SystemExit("synthetic free-form attribute reached Prometheus")
if query("unapproved_metric_name"):
    raise SystemExit("unapproved metric reached Prometheus")
print("synthetic OTLP gauge reached existing Prometheus with safe labels only")
'''
        prometheus_smoke = run_in_namespace(prometheus_id, prometheus_script)
        client = prometheus_smoke
        network_detail = subprocess.run(
            ["docker", "network", "inspect", network, "--format", "{{json .Containers}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(
            client.returncode,
            0,
            collector_smoke.stdout
            + collector_smoke.stderr
            + prometheus_smoke.stdout
            + prometheus_smoke.stderr
            + "\nnetwork containers="
            + network_detail.stdout,
        )

        logs = self.run_compose("logs", "--no-color", "otel-collector")
        for marker in ("synthetic-customer-marker", "synthetic-private@example.invalid", "synthetic-description-marker", self.token):
            self.assertNotIn(marker, logs.stdout + logs.stderr)


if __name__ == "__main__":
    unittest.main()

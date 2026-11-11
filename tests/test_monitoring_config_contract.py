import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = (ROOT / "monitoring/compose.yml").read_text(encoding="utf-8")
PROMETHEUS = (ROOT / "monitoring/prometheus.yml").read_text(encoding="utf-8")
ALERTMANAGER = (ROOT / "monitoring/alertmanager/alertmanager.yml").read_text(encoding="utf-8")
ALERT_RULES = (ROOT / "monitoring/prometheus/alert_rules.yml").read_text(encoding="utf-8")
DASHBOARD = json.loads(
    (ROOT / "monitoring/grafana/dashboards/devobs-overview.json").read_text(encoding="utf-8")
)


class MonitoringConfigContractTests(unittest.TestCase):
    def test_local_only_stack_requires_password_and_uses_digest_pins(self):
        self.assertIn("127.0.0.1:9090:9090", COMPOSE)
        self.assertIn("127.0.0.1:9093:9093", COMPOSE)
        self.assertIn("127.0.0.1:3000:3000", COMPOSE)
        self.assertIn("${GRAFANA_ADMIN_PASSWORD:?", COMPOSE)
        self.assertRegex(COMPOSE, r"networks:\n  monitoring:\n    internal: true")
        images = re.findall(r"^\s+image:\s+(.+)$", COMPOSE, flags=re.MULTILINE)
        self.assertEqual(len(images), 5)
        self.assertTrue(all(re.search(r"@sha256:[0-9a-f]{64}$", image) for image in images))
        self.assertIn(
            "otel/opentelemetry-collector-contrib:0.165.0@sha256:e40d61f10c9a617cca1ffd1be4d7e2b3a4b0f0001798ff07e58cabe82e618cea",
            images,
        )

    def test_exporter_is_optional_and_has_only_read_only_host_access(self):
        match = re.search(r"  node-exporter:\n(?P<service>.*?)(?=\n  [a-z-]+:\n|\nnetworks:)", COMPOSE, re.DOTALL)
        self.assertIsNotNone(match)
        exporter = match.group("service")
        self.assertIn("profiles:\n      - linux-host", exporter)
        self.assertIn('user: "65534:65534"', exporter)
        self.assertIn("read_only: true", exporter)
        self.assertIn("cap_drop:\n      - ALL", exporter)
        self.assertIn("no-new-privileges:true", exporter)
        self.assertNotIn("ports:", exporter)
        self.assertEqual(exporter.count("read_only: true"), 4)
        for flag in ("path.procfs=/host/proc", "path.sysfs=/host/sys", "path.rootfs=/host"):
            self.assertIn(flag, exporter)

    def test_prometheus_scrapes_core_services_and_optional_exporter(self):
        for job in ("prometheus", "alertmanager", "node-exporter"):
            self.assertIn(f"job_name: {job}", PROMETHEUS)
        for target in ("prometheus:9090", "alertmanager:9093", "node-exporter:9100"):
            self.assertIn(f"- {target}", PROMETHEUS)
        self.assertIn("alertmanagers:", PROMETHEUS)
        self.assertIn("/etc/prometheus/alerts.yml", PROMETHEUS)
        self.assertIn("/etc/prometheus/alert_rules.yml", PROMETHEUS)

    def test_storage_retention_is_bounded_and_state_uses_named_volumes(self):
        self.assertIn("retention:\n      time: 15d\n      size: 5GB", PROMETHEUS)
        self.assertNotIn("--storage.tsdb.retention.time", COMPOSE)
        self.assertNotIn("--storage.tsdb.retention.size", COMPOSE)
        self.assertIn("prometheus-data:/prometheus", COMPOSE)
        self.assertIn("alertmanager-data:/alertmanager", COMPOSE)

    def test_alert_rules_cover_host_signals_and_core_service_down(self):
        for alert in ("HighCpuUsage", "HighMemoryUsage", "DiskSpaceRunningLow", "ServiceDown"):
            self.assertIn(f"alert: {alert}", ALERT_RULES)
        self.assertIn('mode="idle"', ALERT_RULES)
        self.assertIn("node_memory_MemAvailable_bytes", ALERT_RULES)
        self.assertIn("node_filesystem_avail_bytes", ALERT_RULES)
        self.assertIn('up{job=~"prometheus|alertmanager"} == 0', ALERT_RULES)

    def test_alertmanager_has_no_external_delivery_receiver(self):
        self.assertIn("receiver: local-only", ALERTMANAGER)
        self.assertIn("- name: local-only", ALERTMANAGER)
        self.assertNotIn("slack_configs:", ALERTMANAGER)
        self.assertNotIn("email_configs:", ALERTMANAGER)
        self.assertNotIn("webhook_configs:", ALERTMANAGER)

    def test_prometheus_self_scrape_alerts_are_preserved(self):
        alerts = (ROOT / "monitoring/alerts.yml").read_text(encoding="utf-8")
        self.assertIn("PrometheusScrapeTargetDown", alerts)
        self.assertIn("PrometheusScrapeTargetMissing", alerts)

    def test_dashboard_shows_host_and_optional_local_api_metrics(self):
        serialized = json.dumps(DASHBOARD)
        titles = {panel["title"] for panel in DASHBOARD["panels"]}
        self.assertEqual(DASHBOARD["uid"], "devobs-monitoring-starter")
        self.assertIn("static site has no /metrics endpoint", serialized)
        self.assertIn('up{job=\\"prometheus\\"}', serialized)
        self.assertTrue({
            "Linux host CPU usage",
            "Linux host memory usage",
            "Linux host filesystem usage",
            "Linux host network traffic",
        }.issubset(titles))
        network_panel = next(
            panel for panel in DASHBOARD["panels"] if panel["title"] == "Linux host network traffic"
        )
        self.assertEqual(len(network_panel["targets"]), 2)
        self.assertIn("node_network_receive_bytes_total", network_panel["targets"][0]["expr"])
        self.assertIn("node_network_transmit_bytes_total", network_panel["targets"][1]["expr"])

        latency_panel = next(
            panel for panel in DASHBOARD["panels"]
            if panel["title"] == "Local API p95 request duration"
        )
        latency_query = latency_panel["targets"][0]["expr"]
        self.assertIn("histogram_quantile(0.95", latency_query)
        self.assertIn("devobs_api_request_duration_bucket", latency_query)
        self.assertIn('service_name="devobs"', latency_query)
        self.assertIn("Local-only", latency_panel["description"])

        rate_panel = next(
            panel for panel in DASHBOARD["panels"]
            if panel["title"] == "Local API request rate"
        )
        rate_query = rate_panel["targets"][0]["expr"]
        self.assertIn("devobs_api_request_duration_count", rate_query)
        self.assertIn('service_name="devobs"', rate_query)
        for forbidden_dimension in ("tenant", "route", "user", "status"):
            self.assertNotIn(forbidden_dimension, latency_query + rate_query)
        self.assertIn("not Render or production telemetry", latency_panel["description"])


if __name__ == "__main__":
    unittest.main()

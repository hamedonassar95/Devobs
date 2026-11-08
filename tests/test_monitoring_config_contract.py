import json
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = (ROOT / "monitoring/compose.yml").read_text(encoding="utf-8")
PROMETHEUS = (ROOT / "monitoring/prometheus.yml").read_text(encoding="utf-8")
COMPOSE_CONFIG = yaml.safe_load(COMPOSE)
PROMETHEUS_CONFIG = yaml.safe_load(PROMETHEUS)
ALERTMANAGER_CONFIG = yaml.safe_load(
    (ROOT / "monitoring/alertmanager/alertmanager.yml").read_text(encoding="utf-8")
)
ALERT_RULES = yaml.safe_load(
    (ROOT / "monitoring/prometheus/alert_rules.yml").read_text(encoding="utf-8")
)
DASHBOARD = json.loads(
    (ROOT / "monitoring/grafana/dashboards/devobs-overview.json").read_text(encoding="utf-8")
)


class MonitoringConfigContractTests(unittest.TestCase):
    def test_local_only_stack_requires_password_and_uses_digest_pins(self):
        services = COMPOSE_CONFIG["services"]
        self.assertIn("127.0.0.1:9090:9090", COMPOSE)
        self.assertIn("127.0.0.1:9093:9093", COMPOSE)
        self.assertIn("127.0.0.1:3000:3000", COMPOSE)
        self.assertIn("${GRAFANA_ADMIN_PASSWORD:?", COMPOSE)
        self.assertTrue(COMPOSE_CONFIG["networks"]["monitoring"]["internal"])
        for service_name in ("prometheus", "alertmanager", "node-exporter", "grafana"):
            self.assertRegex(services[service_name]["image"], r"@sha256:[0-9a-f]{64}$")

    def test_exporter_is_optional_and_has_only_read_only_host_access(self):
        exporter = COMPOSE_CONFIG["services"]["node-exporter"]
        self.assertEqual(exporter["profiles"], ["linux-host"])
        self.assertEqual(exporter["user"], "65534:65534")
        self.assertTrue(exporter["read_only"])
        self.assertEqual(exporter["cap_drop"], ["ALL"])
        self.assertIn("no-new-privileges:true", exporter["security_opt"])
        self.assertNotIn("ports", exporter)
        mounts = {mount["target"]: mount for mount in exporter["volumes"]}
        self.assertEqual(set(mounts), {"/host", "/host/proc", "/host/sys"})
        self.assertTrue(all(mount["read_only"] for mount in mounts.values()))
        self.assertEqual(exporter["command"][:3], [
            "--path.procfs=/host/proc",
            "--path.sysfs=/host/sys",
            "--path.rootfs=/host",
        ])

    def test_prometheus_scrapes_core_services_and_optional_exporter(self):
        jobs = {job["job_name"]: job for job in PROMETHEUS_CONFIG["scrape_configs"]}
        self.assertEqual(set(jobs), {"prometheus", "alertmanager", "node-exporter"})
        self.assertEqual(jobs["prometheus"]["static_configs"][0]["targets"], ["prometheus:9090"])
        self.assertEqual(jobs["alertmanager"]["static_configs"][0]["targets"], ["alertmanager:9093"])
        self.assertEqual(jobs["node-exporter"]["static_configs"][0]["targets"], ["node-exporter:9100"])
        self.assertEqual(
            PROMETHEUS_CONFIG["alerting"]["alertmanagers"][0]["static_configs"][0]["targets"],
            ["alertmanager:9093"],
        )
        self.assertEqual(
            set(PROMETHEUS_CONFIG["rule_files"]),
            {"/etc/prometheus/alerts.yml", "/etc/prometheus/alert_rules.yml"},
        )

    def test_storage_retention_is_bounded_and_state_uses_named_volumes(self):
        services = COMPOSE_CONFIG["services"]
        prometheus = services["prometheus"]
        retention = PROMETHEUS_CONFIG["storage"]["tsdb"]["retention"]
        self.assertEqual(retention, {"time": "15d", "size": "5GB"})
        self.assertNotIn("--storage.tsdb.retention.time=15d", prometheus["command"])
        self.assertNotIn("--storage.tsdb.retention.size=5GB", prometheus["command"])
        self.assertIn("prometheus-data:/prometheus", prometheus["volumes"])
        self.assertIn("alertmanager-data:/alertmanager", services["alertmanager"]["volumes"])

    def test_alert_rules_cover_requested_host_signals_and_core_service_down(self):
        rules = [rule for group in ALERT_RULES["groups"] for rule in group["rules"]]
        self.assertEqual(
            {rule["alert"] for rule in rules},
            {"HighCpuUsage", "HighMemoryUsage", "DiskSpaceRunningLow", "ServiceDown"},
        )
        cpu_rule = next(rule for rule in rules if rule["alert"] == "HighCpuUsage")
        self.assertIn('mode="idle"', cpu_rule["expr"])
        self.assertIn("for", cpu_rule)
        service_down = next(rule for rule in rules if rule["alert"] == "ServiceDown")
        self.assertEqual(service_down["expr"], 'up{job=~"prometheus|alertmanager"} == 0')

    def test_alertmanager_has_no_external_delivery_receiver(self):
        self.assertEqual(ALERTMANAGER_CONFIG["route"]["receiver"], "local-only")
        self.assertEqual(ALERTMANAGER_CONFIG["receivers"], [{"name": "local-only"}])

    def test_prometheus_self_scrape_alerts_are_preserved(self):
        alerts = (ROOT / "monitoring/alerts.yml").read_text(encoding="utf-8")
        self.assertIn("PrometheusScrapeTargetDown", alerts)
        self.assertIn("PrometheusScrapeTargetMissing", alerts)

    def test_dashboard_shows_host_metrics_without_claiming_application_telemetry(self):
        serialized = json.dumps(DASHBOARD)
        titles = {panel["title"] for panel in DASHBOARD["panels"]}
        self.assertEqual(DASHBOARD["uid"], "devobs-monitoring-starter")
        self.assertIn("no application /metrics endpoint", serialized)
        self.assertIn("up{job=\\\"prometheus\\\"}", serialized)
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


if __name__ == "__main__":
    unittest.main()

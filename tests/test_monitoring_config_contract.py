import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = (ROOT / "monitoring/compose.yml").read_text(encoding="utf-8")
PROMETHEUS = (ROOT / "monitoring/prometheus.yml").read_text(encoding="utf-8")
DASHBOARD = json.loads((ROOT / "monitoring/grafana/dashboards/devobs-overview.json").read_text(encoding="utf-8"))


class MonitoringConfigContractTests(unittest.TestCase):
    def test_local_only_pinned_stack_requires_a_password_and_is_internal(self):
        self.assertIn("127.0.0.1:9090:9090", COMPOSE)
        self.assertIn("127.0.0.1:3000:3000", COMPOSE)
        self.assertIn("${GRAFANA_ADMIN_PASSWORD:?", COMPOSE)
        self.assertIn("internal: true", COMPOSE)
        self.assertIn("@sha256:", COMPOSE)

    def test_prometheus_only_scrapes_its_own_process(self):
        self.assertIn("job_name: prometheus", PROMETHEUS)
        self.assertIn("prometheus:9090", PROMETHEUS)
        self.assertNotIn("/metrics", PROMETHEUS)

    def test_dashboard_discloses_that_it_is_not_application_telemetry(self):
        serialized = json.dumps(DASHBOARD)
        self.assertEqual(DASHBOARD["uid"], "devobs-monitoring-starter")
        self.assertIn("no application /metrics endpoint", serialized)
        self.assertIn("up{job=\\\"prometheus\\\"}", serialized)


if __name__ == "__main__":
    unittest.main()

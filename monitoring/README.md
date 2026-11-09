# Local monitoring starter

This optional local Compose stack includes Prometheus, Alertmanager, Grafana, and an opt-in Node Exporter profile for Linux hosts. The opt-in `otel` profile adds an authenticated, TLS-protected, metrics-only OpenTelemetry Collector that exports a narrow allowlist to the existing Prometheus. OTLP listeners bind to loopback only; Prometheus scrapes the Collector exporter on the internal Docker network. The static Devobs site still has no application `/metrics` endpoint, and local alerts have no external email, Slack, Telegram, or webhook receiver. Without the Node Exporter profile, Prometheus shows that target as down but excludes it from the `ServiceDown` alert.

Prometheus, Alertmanager, Grafana, and OTLP listener ports bind to loopback. The Prometheus exporter endpoint is not published and remains on the internal network. Node Exporter has no published port and reads host paths through read-only mounts; on Windows or macOS Docker Desktop it measures the Linux VM, not the physical host. See [`docs/MONITORING.md`](../docs/MONITORING.md) and the [OpenTelemetry integration guide](../docs/integrations/opentelemetry.md) for setup, limitations, and validation.

## Component licenses

| Component | Version | License |
| --- | --- | --- |
| Prometheus | v3.15.1 | Apache-2.0 |
| Alertmanager | v0.34.2 | Apache-2.0 |
| Node Exporter | v1.12.1 | Apache-2.0 |
| Grafana | 13.2.4 | AGPL-3.0 |
| OpenTelemetry Collector Contrib | v0.165.0 | Apache-2.0 |

Images are pinned by registry digest in `compose.yml`. Upstream licenses: [Prometheus](https://github.com/prometheus/prometheus/blob/v3.15.1/LICENSE), [Alertmanager](https://github.com/prometheus/alertmanager/blob/v0.34.2/LICENSE), [Node Exporter](https://github.com/prometheus/node_exporter/blob/v1.12.1/LICENSE), [Grafana](https://github.com/grafana/grafana/blob/v13.2.4/LICENSE), and [OpenTelemetry Collector Contrib](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.165.0/LICENSE).

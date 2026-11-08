# Local monitoring starter

This optional local Compose stack includes Prometheus, Alertmanager, Grafana, and an opt-in Node Exporter profile for Linux hosts. The static Devobs site has no application `/metrics` endpoint, and local alerts have no external email, Slack, Telegram, or webhook receiver. Without the profile, Prometheus shows the Node Exporter target as down, but excludes it from the `ServiceDown` alert.

Ports bind to loopback. Node Exporter has no published port and reads host paths through read-only mounts; on Windows or macOS Docker Desktop it measures the Linux VM, not the physical host. See [`docs/MONITORING.md`](../docs/MONITORING.md) for setup, limitations, and validation.

## Component licenses

| Component | Version | License |
| --- | --- | --- |
| Prometheus | v3.15.1 | Apache-2.0 |
| Alertmanager | v0.34.2 | Apache-2.0 |
| Node Exporter | v1.12.1 | Apache-2.0 |
| Grafana | 13.2.4 | AGPL-3.0 |

Images are pinned by registry digest in `compose.yml`. Upstream licenses: [Prometheus](https://github.com/prometheus/prometheus/blob/v3.15.1/LICENSE), [Alertmanager](https://github.com/prometheus/alertmanager/blob/v0.34.2/LICENSE), [Node Exporter](https://github.com/prometheus/node_exporter/blob/v1.12.1/LICENSE), and [Grafana](https://github.com/grafana/grafana/blob/v13.2.4/LICENSE).

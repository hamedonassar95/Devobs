# Local monitoring starter

An [offline Alertmanager export adapter](../docs/integrations/ALERTMANAGER_BRIDGE.md)
can convert an explicitly supplied notification into project-scoped AI-1 incident
metadata. It does not enable a webhook receiver or change this monitoring stack.

This optional local Compose stack includes Prometheus, Alertmanager, Grafana, and an opt-in Node Exporter profile for Linux hosts. The opt-in `otel` profile adds an authenticated, TLS-protected, metrics-only OpenTelemetry Collector that exports a narrow allowlist to the existing Prometheus. The staging WSGI API can optionally send one request-duration histogram to that Collector from a local host process; it is disabled by default and has no request labels. The Grafana dashboard includes a fixed-bucket p95 latency estimate and request-rate panel for this local histogram; both remain empty unless the Collector profile and API opt-in are enabled. They do not show Render or production traffic. OTLP listeners bind to loopback only; Prometheus scrapes the Collector exporter on the internal Docker network. The static Devobs site still has no application `/metrics` endpoint, and local alerts have no external email, Slack, Telegram, or webhook receiver. Without the Node Exporter profile, Prometheus shows that target as down but excludes it from the `ServiceDown` alert.

Prometheus, Alertmanager, Grafana, and OTLP listener ports bind to loopback. The Prometheus exporter endpoint is not published and remains on the internal network. Node Exporter has no published port and reads host paths through read-only mounts; on Windows or macOS Docker Desktop it measures the Linux VM, not the physical host. See [`docs/MONITORING.md`](../docs/MONITORING.md) and the [OpenTelemetry integration guide](../docs/integrations/opentelemetry.md) for setup, limitations, and validation.

## Offline performance reports

The manual benchmark commands can produce execution-time or Linux sampled
peak-private-memory reports. To send one validated summary or comparison to the
local Grafana dashboard, run
`python3 -m performance_intelligence.prometheus_export <report.json>` from the
repository root with `PYTHONPATH=scripts`. The exporter writes one allowlisted
Prometheus textfile under `monitoring/performance-metrics/`; the file is ignored
by Git. The exporter creates it atomically with mode `0644`, so the existing
Node Exporter process (UID 65534) can read the file through its read-only mount;
the report contains only fixed benchmark IDs, source revisions, Python
versions, modes and numeric measurements. It contains no paths, hostnames,
inputs or customer data. Refreshing it requires the explicit `--overwrite` flag.

The textfile collector is read-only and exists only in the opt-in `linux-host`
Node Exporter profile. Start the local monitoring stack with that profile to
scrape the latest manually exported report. Nothing polls or runs benchmarks
automatically. This reports local benchmark artifacts, not Render, production
traffic or a live Devobs service. Stop the profile or remove the ignored report
file to roll back the local export.

The textfile collector requires `--collector.textfile.directory`; this is
configured as `/var/lib/node_exporter/textfile` and mounted read-only from the
ignored local directory. The configuration follows the official
[Node Exporter 1.12.1 textfile collector documentation](https://github.com/prometheus/node_exporter/blob/v1.12.1/README.md#textfile-collector)
(checked 2026-11-26). Docker Desktop exposes the Linux VM filesystem and memory,
not the physical Windows/macOS host.

## Component licenses

| Component | Version | License |
| --- | --- | --- |
| Prometheus | v3.15.1 | Apache-2.0 |
| Alertmanager | v0.34.2 | Apache-2.0 |
| Node Exporter | v1.12.1 | Apache-2.0 |
| Grafana | 13.2.4 | AGPL-3.0 |
| OpenTelemetry Collector Contrib | v0.165.0 | Apache-2.0 |
| OpenTelemetry Python SDK/API and OTLP/HTTP exporter | v1.45.2 | Apache-2.0 |

Images are pinned by registry digest in `compose.yml`. Upstream licenses: [Prometheus](https://github.com/prometheus/prometheus/blob/v3.15.1/LICENSE), [Alertmanager](https://github.com/prometheus/alertmanager/blob/v0.34.2/LICENSE), [Node Exporter](https://github.com/prometheus/node_exporter/blob/v1.12.1/LICENSE), [Grafana](https://github.com/grafana/grafana/blob/v13.2.4/LICENSE), and [OpenTelemetry Collector Contrib](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.165.0/LICENSE).

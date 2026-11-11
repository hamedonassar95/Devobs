# Local monitoring starter

Devobs provides a local Compose stack with Prometheus, Alertmanager, and Grafana. Node Exporter is opt-in through the `linux-host` profile and is intended for Docker Engine running directly on Linux. The static Devobs site has no application `/metrics` endpoint, so this stack does not report site availability or application health.

## Start and stop

From the repository root, set a temporary local Grafana password and start the core services:

```sh
export GRAFANA_ADMIN_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose -f monitoring/compose.yml up --detach
```

To include host CPU, memory, filesystem, and network metrics on a Linux host:

```sh
docker compose --profile linux-host -f monitoring/compose.yml up --detach
```

The optional exporter has no published port, runs as uid/gid 65534, drops Linux capabilities, and reads host `/`, `/proc`, and `/sys` through read-only mounts. Review those mounts before enabling the profile. Docker Desktop on Windows or macOS runs Docker inside a Linux VM, so this profile reports the VM rather than the physical workstation. See the official [Node Exporter container guidance](https://github.com/prometheus/node_exporter#using-docker), [procfs/sysfs/rootfs flags](https://github.com/prometheus/node_exporter/blob/v1.12.1/collector/paths.go), and [filesystem exclusion flag](https://github.com/prometheus/node_exporter/blob/v1.12.1/collector/filesystem_common.go).

Open Prometheus at <http://127.0.0.1:9090>, Alertmanager at <http://127.0.0.1:9093>, and Grafana at <http://127.0.0.1:3000>. The UIs bind to loopback and share an internal Compose network. Grafana provisions the Prometheus datasource and the overview dashboard. Prometheus retention is capped at 15 days or 5 GB. Named volumes keep monitoring data when containers stop.

Stop the services and remove the temporary password from the current shell:

```sh
docker compose --profile linux-host -f monitoring/compose.yml down
unset GRAFANA_ADMIN_PASSWORD
```

## Alerts and boundaries

Prometheus keeps its existing self-scrape alerts and adds `HighCpuUsage`, `HighMemoryUsage`, `DiskSpaceRunningLow`, and `ServiceDown`. When the `linux-host` profile is off, the optional Node Exporter scrape target appears as down in Prometheus; the `ServiceDown` alert intentionally excludes it, and host metric panels remain empty. Alertmanager groups alerts into a local-only receiver with no email, Slack, Telegram, or webhook integration; no alert data leaves this local Compose network. This stack is a development starter, not a production monitoring service.

The pinned component licenses are listed in [monitoring/README.md](../monitoring/README.md). Production use requires a separately reviewed authentication and TLS design, secret handling, alert delivery, retention policy, and application instrumentation.

## Validation

Validate Compose interpolation and resolved configuration without starting containers:

```sh
GRAFANA_ADMIN_PASSWORD=contract-only docker compose -f monitoring/compose.yml config --quiet
```

The repository's monitoring configuration contract tests parse the YAML and dashboard JSON, and verify the local-only scope, image digests, mounts, retention, alert names, and dashboard panels. A successful config check does not prove that containers have been started or that host metrics are being collected.

References: [Prometheus v3.15.1 TSDB retention configuration](https://github.com/prometheus/prometheus/blob/v3.15.1/docs/configuration/configuration.md), [Prometheus configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/), [Prometheus alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/), [Alertmanager configuration](https://prometheus.io/docs/alerting/latest/configuration/), [Grafana dashboard provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/), [Docker Compose profiles](https://docs.docker.com/compose/how-tos/profiles/), and [`docker compose config`](https://docs.docker.com/reference/cli/docker/compose/config/).

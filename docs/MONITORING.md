# Local Prometheus and Grafana starter

This optional local stack checks Prometheus and provisions a small Grafana dashboard. The current Devobs product is a static HTML site and does not expose an application metrics endpoint; the dashboard therefore reports Prometheus' own scrape target and process memory, not website availability or Devobs service health. Prometheus loads two starter alerts for its own scrape target being down or missing. They appear in the Prometheus Alerts page; no Alertmanager is configured, so they do not send notifications.

## Run locally

From the repository root, create an uncommitted local admin password and start the stack:

```sh
export GRAFANA_ADMIN_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose -f monitoring/compose.yml up --detach
```

Open Prometheus at <http://127.0.0.1:9090> and Grafana at <http://127.0.0.1:3000>. Sign in to Grafana as `admin` using the password in the current shell. The Prometheus datasource and dashboard are provisioned automatically. Stop the local containers with:

```sh
docker compose -f monitoring/compose.yml down
unset GRAFANA_ADMIN_PASSWORD
```

The ports bind to loopback, the Compose network is internal, images are pinned by registry digest, and the configuration contains no credentials. The generated password is passed to the local container environment; do not reuse it or use this local setup as a production credential design. Production monitoring needs application instrumentation, authenticated access, TLS, retention, and a secrets-management plan.

References: [Prometheus configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/), [Prometheus alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/), [Grafana dashboard provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/), [Docker Compose environment interpolation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/), and [`docker compose config`](https://docs.docker.com/reference/cli/docker/compose/config/).

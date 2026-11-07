# Monitoring configuration

The existing local Compose setup starts Prometheus and Grafana. Prometheus currently scrapes itself; the static site does not expose application metrics. Both published ports bind to loopback, the Compose network is internal, and Grafana requires `GRAFANA_ADMIN_PASSWORD` at startup.

The checked-in alert rules cover Prometheus self-scrape health. There is no Alertmanager, Node Exporter, or external notification receiver in this configuration. Do not describe this as production observability. See [`docs/MONITORING.md`](../docs/MONITORING.md) before changing the stack.

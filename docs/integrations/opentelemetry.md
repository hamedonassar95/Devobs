# Local OpenTelemetry metrics integration

**Status:** optional local-development integration. It is not a deployed service, a production ingest endpoint, or evidence that P02, AI-9, or P01 is complete. The existing static Devobs site still has no application instrumentation.

## Existing monitoring and the new gap

| Capability | Existing stack | OpenTelemetry addition |
| --- | --- | --- |
| Storage and queries | Existing Prometheus, 15-day/5-GB retention | Reuses the same Prometheus; no second TSDB or remote backend |
| Dashboards | Existing Grafana and dashboard | Reuses the same Grafana; no dashboard copy or second instance |
| Alerting | Existing Alertmanager and local rules | Preserved; no new Alertmanager or outbound notification |
| Host metrics | Optional Linux Node Exporter | Unchanged |
| Application telemetry | No app `/metrics` or live OTLP receiver; offline trusted-snapshot adapters are not network listeners | Optional authenticated OTLP receiver for a narrowly allowlisted metrics contract |
| Logs and traces | No live application logs/traces pipeline | Deliberately not enabled |

The Collector is justified as a protocol bridge from OTLP metrics to the Prometheus deployment already present. It does not replace Prometheus, Alertmanager, Grafana, Node Exporter, or the offline Devobs adapters.

## Architecture and data flow

```text
Local SDK / synthetic sender
    └─ TLS 1.2+ and a local bearer token
       └─ 127.0.0.1:4317 (OTLP/gRPC) or 127.0.0.1:4318/v1/metrics (OTLP/HTTP)
          └─ optional Collector on the internal Compose network
             ├─ memory limit → allowlisted service/name/type → remove free-form attributes
             └─ Prometheus exporter at otel-collector:8889/metrics (internal only)
                └─ existing Prometheus scrape job → existing Grafana
```

The `otel` Compose profile is off by default. OTLP ports are published only on host loopback, never on a public interface. The monitoring Docker network is marked `internal`; Prometheus reaches the Collector exporter on that network. Port 8889 is not published to the host. No Collector debug/logging exporter is configured, and no logs or traces pipeline exists.

Only metric data points with `service.name=devobs`, gauge type, and one of these exact names pass the filter:

- `error_rate_pct`
- `capacity_pct`
- `failed_checks`
- `devobs_otel_smoke` (synthetic smoke test only)

All other resource attributes and data-point attributes are removed before export; metric descriptions are cleared and scope labels/exemplars are disabled. Prometheus translation preserves these allowlisted metric names without inferred unit/type suffixes, matching the existing numeric snapshot contract. Keep metric values numeric and non-identifying. Do not send secrets, personal data, raw logs, prompts, traces, or customer/production telemetry to this local profile. The filter and local auth token are not tenant identity or production authorization.

## Versions, image digest, and licenses

| Component | Version | License | Immutable image digest |
| --- | --- | --- | --- |
| OpenTelemetry Collector Contrib | 0.165.0 | Apache-2.0 | `sha256:e40d61f10c9a617cca1ffd1be4d7e2b3a4b0f0001798ff07e58cabe82e618cea` |
| Prometheus | 3.15.1 | Apache-2.0 | `sha256:fa3302279710be2f21a8301ec17a8b4f2301fd829bd113839b3b6b02b6f191a2` |
| Alertmanager | 0.34.2 | Apache-2.0 | `sha256:39d8bb3966c694a124428a3a88fbcffd40bd069129ecd47c059f8a3f17c55f3b` |
| Node Exporter | 1.12.1 | Apache-2.0 | `sha256:1b4e4438faca4dd7e001dd445d161a4a2091b0fededa84093b3a8dfeae1f1be0` |
| Grafana | 13.2.4 | AGPL-3.0 | `sha256:dbbc38ea21103cefb50396340cd88afec779c7e070b0a7bf5a75b4ce46651d3f` |

The smoke-test-only client uses the official `python:3.12.14-alpine3.24` image pinned to `sha256:4c47124a8391cb7a9f571164147d154777cf012a4ece5f86097130d7a4478111` (Python Software Foundation License 2.0); it is not part of the monitoring runtime.

The Collector reference is the official [`otel/opentelemetry-collector-contrib` image](https://hub.docker.com/r/otel/opentelemetry-collector-contrib), pinned to the immutable multi-architecture manifest digest resolved from the official registry on 2026-11-09. Its release source and [Apache-2.0 license](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.165.0/LICENSE) are versioned at v0.165.0. Existing component pins are retained from `monitoring/compose.yml`.

## Local setup

Requirements: Docker Engine with Docker Compose v2, and OpenSSL. This creates only a short-lived local self-signed certificate and random development token; it does not use a production credential or contact a paid service.

```sh
umask 077
export DEVOBS_OTEL_TLS_DIR="$(mktemp -d)"
chmod 700 "$DEVOBS_OTEL_TLS_DIR"
openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 2 \
  -keyout "$DEVOBS_OTEL_TLS_DIR/server.key" \
  -out "$DEVOBS_OTEL_TLS_DIR/server.crt" \
  -subj '/CN=127.0.0.1' \
  -addext 'subjectAltName=IP:127.0.0.1,DNS:localhost'
openssl rand -hex 32 > "$DEVOBS_OTEL_TLS_DIR/token"
chmod 444 "$DEVOBS_OTEL_TLS_DIR/server.crt" "$DEVOBS_OTEL_TLS_DIR/server.key" "$DEVOBS_OTEL_TLS_DIR/token"
export DEVOBS_OTEL_TLS_CERT_FILE="$DEVOBS_OTEL_TLS_DIR/server.crt"
export DEVOBS_OTEL_TLS_KEY_FILE="$DEVOBS_OTEL_TLS_DIR/server.key"
export DEVOBS_OTEL_TOKEN_FILE="$DEVOBS_OTEL_TLS_DIR/token"
export GRAFANA_ADMIN_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose --profile otel -f monitoring/compose.yml up --detach
```

The temporary directory stays mode `0700`; Compose mounts each file read-only as a container secret so the non-root Collector can read it. Keep the token value out of shell output and logs. Configure a local SDK to trust `server.crt`, use TLS, send an `Authorization: Bearer …` header from the token file, and set `service.name=devobs`.

| Protocol | Local endpoint | Prometheus endpoint |
| --- | --- | --- |
| OTLP/gRPC over TLS | `https://127.0.0.1:4317` | Not directly scraped |
| OTLP/HTTP over TLS | `https://127.0.0.1:4318/v1/metrics` | Not directly scraped |
| Collector Prometheus exporter | Not host-published | `http://otel-collector:8889/metrics` inside the Compose network |

The existing Prometheus scrape interval (15 seconds), retention (15 days or 5 GB), alerts, and Grafana datasource remain unchanged. New metric samples expire from the Collector exporter after five minutes without updates.

## Resource and security limits

- Collector image is digest-pinned; only OTLP, bearer-token auth, memory-limiter, filter, transform, batch, and Prometheus exporter are configured.
- TLS requires at least 1.2. gRPC receive messages are limited to 1 MiB and OTLP/HTTP bodies to 8 MiB.
- Container: pinned Collector image runs as UID/GID `10001:10001`, with a read-only root filesystem, all Linux capabilities dropped, `no-new-privileges`, internal network only, 160 MiB container memory, 0.5 CPU, and 64 processes.
- Collector memory limiter: 96 MiB heap limit with a 20 MiB spike limit and one-second checks; batches are capped at 256 items.
- Only four exact gauge names from the single `devobs` service pass. Free-form resource/data-point attributes, descriptions, scope labels, logs, traces, and exemplars are not exported.
- Local bearer token and TLS files are required when the `otel` profile starts. Without paths configured, Compose maps `/dev/null`; invalid TLS causes Collector startup to fail closed. There is no default token or committed certificate.
- Prometheus remains the only metrics store. No external backend, network receiver, public listener, privileged container, cloud resource, production deployment, or production credential is added.

## Validation and synthetic smoke test

The optional Docker runtime test creates a temporary local token/certificate, checks the Compose render and Collector config, checks Prometheus via the already-pinned Prometheus image's `promtool`, confirms malformed Collector configuration fails validation, verifies that an unauthenticated OTLP request gets 401, and sends a synthetic gauge. It then checks the sample reached Prometheus and that synthetic resource/data-point markers were not exported or logged.

```sh
python3 -m unittest tests.test_otel_collector_config -v
DEVOBS_RUN_OTEL_SMOKE=1 python3 -m unittest tests.test_otel_collector_config.OTelCollectorRuntimeTests -v
GRAFANA_ADMIN_PASSWORD=contract-only \
  DEVOBS_OTEL_TLS_CERT_FILE="$DEVOBS_OTEL_TLS_CERT_FILE" \
  DEVOBS_OTEL_TLS_KEY_FILE="$DEVOBS_OTEL_TLS_KEY_FILE" \
  DEVOBS_OTEL_TOKEN_FILE="$DEVOBS_OTEL_TOKEN_FILE" \
  docker compose --profile otel -f monitoring/compose.yml config --quiet
```

The runtime test uses a unique Compose project name and removes only its test containers and test volumes. A successful synthetic smoke test proves local plumbing only; it is not application instrumentation, security certification, SaaS readiness, or P02 production acceptance.

## Failure modes and troubleshooting

- **Collector exits during startup with a TLS or secret-file error:** when the optional profile is off, the base stack needs no OTLP credentials. When enabling `otel`, generate the local TLS directory and token file above and export all three file paths; absent paths intentionally resolve to invalid `/dev/null` inputs and the Collector fails closed. Never add their values to Git.
- **Collector exits during startup:** validate the mounted config with `docker compose --profile otel -f monitoring/compose.yml run --rm --no-deps otel-collector validate --config=/etc/otelcol-contrib/config.yaml`; inspect only sanitized startup errors with `docker compose --profile otel -f monitoring/compose.yml logs --no-color otel-collector`.
- **HTTP 401:** confirm the client reads the same local token file and sends a Bearer authorization header. Do not print the header while debugging.
- **No Prometheus series:** confirm the profile is active, `service.name` is exactly `devobs`, the metric is a gauge with an allowlisted exact name, Prometheus targets show `otel-collector:8889`, and wait for the next 15-second scrape.
- **Memory limiter rejects data:** reduce local telemetry volume; do not increase limits blindly. The Collector intentionally fails closed under pressure.
- **Prometheus is unavailable:** the Collector has no persistent queue or remote storage; a restart/recovery is required and data can be lost. The Prometheus scrape target exposes availability in the existing UI; no new alert rule was added.

## Disable or roll back

Stop only the Collector and remove its container without touching Prometheus data:

```sh
docker compose --profile otel -f monitoring/compose.yml stop otel-collector
docker compose --profile otel -f monitoring/compose.yml rm --stop --force otel-collector
```

Do not use `down --volumes` for the regular local stack; that would delete existing Prometheus and Alertmanager data. To remove the temporary local TLS/token material after stopping the Collector:

```sh
rm -rf -- "$DEVOBS_OTEL_TLS_DIR"
unset DEVOBS_OTEL_TLS_DIR DEVOBS_OTEL_TLS_CERT_FILE DEVOBS_OTEL_TLS_KEY_FILE \
  DEVOBS_OTEL_TOKEN_FILE GRAFANA_ADMIN_PASSWORD
```

Code rollback removes the Collector service/secrets, `monitoring/otel-collector-config.yaml`, and the `otel-collector` Prometheus scrape job, then reverts the corresponding tests/docs. Existing Prometheus, Grafana, Alertmanager, Node Exporter, dashboards, alerts, volumes, and retention remain untouched.

## Limits and future tracing work

This local profile does not implement traces, logs, multi-tenant identity, sender provenance, durable storage, deletion workflows, rate/quota enforcement, production TLS/identity lifecycle, or hosted cost controls. The shared local token is a workstation-level development boundary only. No Devobs application is currently instrumented to send these gauges. Production P02 still needs a separately reviewed authenticated sender/tenant design, approved staging instrumentation and synthetic/negative tests, privacy and retention/deletion evidence, quota/cost controls, and owner sign-off. Future tracing requires trace-context/provenance rules, tenant isolation, attribute allowlists, privacy tests, sampling, retention, and a reviewed trace backend. Nothing here changes AI-9 or P01.

## Official references

- [OpenTelemetry Collector installation and Docker Compose](https://opentelemetry.io/docs/collector/install/docker/)
- [Collector components and configuration](https://opentelemetry.io/docs/collector/components/)
- [OTLP receiver](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.165.0/receiver/otlpreceiver/README.md)
- [Bearer Token Authenticator](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.165.0/extension/bearertokenauthextension/README.md)
- [Memory Limiter Processor](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.165.0/processor/memorylimiterprocessor/README.md)
- [Batch Processor](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.165.0/processor/batchprocessor/README.md)
- [Filter Processor](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.165.0/processor/filterprocessor/README.md)
- [Transform Processor](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.165.0/processor/transformprocessor/README.md)
- [Prometheus Exporter](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.165.0/exporter/prometheusexporter/README.md)

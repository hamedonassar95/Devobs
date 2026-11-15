# Alertmanager notification export → AI-1 incident metadata

**VERIFIED source implementation; live monitoring delivery UNVERIFIED.** This
local converter reads one supplied JSON notification and writes existing AI-1
incident JSONL. It creates no listener, receiver, account, schedule, deployment,
model call or remediation. Existing Alertmanager configuration stays local-only.

## Open-source integration research — 2026-11-15

Inventory baseline: `f883025e8a9f2088a561bb02b8dc99a6175ae9d8`.
Official web documentation and versioned upstream source were reviewed before
choosing the missing notification adapter. These are implementation decisions
within the existing source-development scope, not live activation.

| Integration type | Existing capability / decision | Official source |
| --- | --- | --- |
| Telemetry collection | Reuse the existing opt-in, TLS-protected metrics-only OTel Collector; no duplicate collector. | [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/) |
| Portable application events | Reuse the existing narrow CloudEvents CI bridge and its seven project namespaces. This is not a universal event broker. | [CloudEvents 1.0.2](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md) |
| Monitoring notifications | Implement the missing Alertmanager export converter using Node built-ins and existing AI-1 validation. | [Pinned webhook format](https://github.com/prometheus/alertmanager/blob/v0.34.2/docs/configuration.md#webhook_config) |
| GitOps inspection | Keep the existing optional read-only Argo CD MCP example; live access remains unverified. | [Argo CD declarative setup](https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/) |
| Cost allocation | Defer OpenCost: allocation does not establish the required Render invoice ceiling, and no applicable deployed workload is verified. | [OpenCost overview](https://opencost.io/docs/) |

Alertmanager is already pinned at software version **0.34.2** in monitoring;
its default webhook protocol is **`"4"`**. Compatibility was checked against
[message construction](https://github.com/prometheus/alertmanager/blob/v0.34.2/notify/webhook/webhook.go),
[serialized fields and initialized maps](https://github.com/prometheus/alertmanager/blob/v0.34.2/template/template.go#L497),
and [firing zero-end-time behavior](https://github.com/prometheus/alertmanager/blob/v0.34.2/alert/alert.go#L153).
The upstream [license is Apache-2.0](https://github.com/prometheus/alertmanager/blob/v0.34.2/LICENSE).
No upstream server code or dependency is copied/installed. Existing Grafana
licensing and commercial-clearance requirements remain separate.

## Explicit local scope and protocol boundary

Run from the repository root using the public synthetic fixture:

```sh
node scripts/integrations/alertmanager_adapter.mjs --input examples/integrations/synthetic-alertmanager.json --source https://github.com/hamedonassar95/Devobs --service monitoring
```

`--input -` reads stdin. `--source` must exactly match one of the seven existing
[project namespaces](CLOUDEVENTS_CI_BRIDGE.md#architecture-and-source-allowlist);
`--service` is a required local identifier (1–64 lowercase slug characters,
starting with a letter). These arguments are operator-asserted namespaces, not
sender authentication or hosted tenant/service authorization. Use a separate
approved service binding/store per project. No other repository is modified.
Reserved `devobs_project` / `devobs_service` label claims, if present in group,
common, route or alert labels, must agree with the supplied binding. Payload
labels cannot select a different output project or service.

Only default v4 notification fields are accepted; `routeLabels` and
`notification_reason` are supported and optional for older default payloads.
Custom templated payloads are unsupported. Input is at most 1 MiB and 100 alerts;
nonzero truncation, unknown rules, malformed maps/time/status, duplicate JSON keys
or fingerprints and inconsistent group status reject the complete notification.
There is no partial output. CLI errors are fixed categories with exit code 2;
success emits JSONL only, with exit code 0. No input, file path or exception is echoed.

The four accepted rule names are the existing local `HighCpuUsage`,
`HighMemoryUsage`, `DiskSpaceRunningLow` and `ServiceDown`. Only `warning` and
`critical` severities are supported. Each alert's own `firing`/`resolved` claim
maps to `open`/`resolved`, independently of mixed group status. Firing events use
`startsAt`; resolved events use `endsAt`, which must not precede the start.
Firing zero/future end times do not establish resolution. Long-running starts
are valid; the converter does not attest clock accuracy or evidence freshness.

Output uses AI-1 source `operator`: a supplied local export, not an authenticated
application event. Summaries contain only selected project/service, approved rule
and an opaque SHA-256 episode digest. Annotations, URLs, instance addresses,
arbitrary labels and raw fingerprints are excluded; URLs are never fetched.
Identity binds project, service, fingerprint and UTC-normalized start including
nanoseconds. AI-1 timestamps retain their existing millisecond precision. Input
permutation does not change output; replay is deduplicated by AI-1 ingestion.

## Validation and limits

`node --test tests/alertmanager_adapter.test.mjs tests/cloudevents_ci_adapter.test.mjs tests/local_advisory_acceptance.test.mjs`
checks conversion, scoped IDs, replay through the actual local event store and
AI-7 aggregate counts, privacy, protocol errors and existing bridge compatibility.
No notification server or external connection is started by this converter.
Incident metadata does not supply numeric telemetry or log-based root-cause
clusters/recommendations. Local synthetic tests establish neither natural-incident
evaluation nor hosted identity, tenant isolation or a live monitoring connection.
P01/AI-9 remain BLOCKED, Codex runtime OPEN; no paid activation is authorized.

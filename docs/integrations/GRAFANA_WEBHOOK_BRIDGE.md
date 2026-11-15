# Grafana OSS webhook export → local AI-1 incidents

**VERIFIED local implementation; live delivery UNVERIFIED.** This optional
converter reads a supplied default Grafana notification JSON and emits bounded
AI-1 incident JSONL. It opens no receiver, connects no account, installs no server
and performs no model call or remediation. Grafana and Alertmanager payloads are
different protocols; the existing strict Alertmanager v4 converter stays intact.

## Official open-source research — 2026-11-15

The [Grafana webhook documentation](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/integrations/webhook-notifier/)
documents the default payload and custom templates. Devobs monitoring already
pins **Grafana 13.2.4**. Its [dependency manifest](https://github.com/grafana/grafana/blob/v13.2.4/go.mod)
pins alerting revision `7f02604ca93b1d6db805848d6a9b4d3c82540507`.
The [versioned serializer](https://github.com/grafana/alerting/blob/7f02604ca93b1d6db805848d6a9b4d3c82540507/receivers/webhook/v1/webhook.go)
defines webhook version **`"1"`**, organization, title, state, message and mandatory
`truncatedAlerts`. The [versioned alert fields](https://github.com/grafana/alerting/blob/7f02604ca93b1d6db805848d6a9b4d3c82540507/templates/template_data.go)
show two details omitted by the documentation example: `valueString` can be
serialized empty and `values` can be null. Both forms are accepted here.

Grafana and its alerting library are [AGPL-3.0](https://github.com/grafana/alerting/blob/7f02604ca93b1d6db805848d6a9b4d3c82540507/LICENSE).
This separately implemented data-format adapter copies or installs no upstream
server code. Existing commercial-clearance requirements remain separate; this is
not approval to bundle or host Grafana commercially. Larger OpenMetrics ingestion
is deferred: the existing [OTLP gauge bridge](OTLP_ERROR_RATE_BRIDGE.md) already
covers its reviewed telemetry subset without another collector.

## Local use and project portability

With Node.js 24, from the repository root:

```sh
node scripts/integrations/grafana_webhook_adapter.mjs --input examples/integrations/synthetic-grafana.json --source https://github.com/hamedonassar95/Devobs --service grafana-local
```

`--input -` reads stdin. Success writes JSONL only (exit 0); errors write a fixed
category to stderr and no partial output (exit 2). Existing
`node scripts/ai_intelligence/event_ingest.mjs --input <jsonl-file|-> --store <local-jsonl-file>`
and the [local dashboard](../AI_LOCAL_DASHBOARD.md) consume this format. Keep a
separate private store and service binding for each project/Grafana instance.
No other repository or provider setting is changed by running the converter.

Select exactly one existing namespace with `--source`; the fixed prefix is
`https://github.com/hamedonassar95/`:

| Project namespace | Intended review/use |
| --- | --- |
| `Devobs` | Local observability fixture and incident pipeline |
| `devobs-saas` | Separately reviewed SaaS monitoring export |
| `phone-repair-assistant-v2` | Technical alerts only; no customer/device data |
| `al-dala-mobile` | Technical alerts only; separate business ownership |
| `LiveOps-Integration` | Technical alerts only; no media or generation |
| `DevObs-ai-Intelligence-` | Separately reviewed local intelligence alerts |
| `CineForge-AI` | Technical alerts only; no private source or CI logs |

These are operator-asserted namespaces, not authenticated senders or tenant
grants. `--service` is a 1–64 character lowercase slug starting with a letter.
Reserved `devobs_project` / `devobs_service` label claims must match that scope.
The project table proves converter portability, not installed project connections.

## Deliberately narrow payload contract

Only default v1 fields are supported, with optional root `appVersion`; custom
templates and unknown fields fail closed. Each alert requires the default
Alertmanager-compatible fields plus `silenceURL`, `dashboardURL`, `panelURL` and
`values` (null or at most 64 finite numeric entries). Optional `valueString`,
`orgId`, `ruleUID` and `imageURL` are accepted and discarded; alert `orgId`, when
present, must equal the positive safe-integer root organization. Image/enrichment
extensions (`embeddedImage`, `enrichments`) are unsupported and rejected.
Discarded strings are bounded to 4096 characters (version/rule IDs to 128).

Input is at most 1 MiB/100 alerts. Nonzero truncation, duplicate JSON keys or
fingerprints, impossible timestamps, inconsistent group status/state and unknown
rules or severities reject the whole input. Only the existing four rules
`HighCpuUsage`, `HighMemoryUsage`, `DiskSpaceRunningLow`, `ServiceDown` and
`warning`/`critical` severities are accepted. Grafana test alerts are unsupported.
Group `firing` must mean `state:alerting`; `resolved` must mean `state:ok`.
Per-alert states and timestamps use existing Alertmanager normalization.

Output contains only the selected project/service, approved rule/severity/status,
normalized time and an opaque episode hash. Titles, messages, arbitrary labels,
annotations, values, URLs, rule identifiers and raw organization/fingerprint IDs
never reach output; URLs are never fetched. Grafana, organization, project and
service identities are separated; nanosecond episode identity is retained.
Claims still do not prove origin, freshness, authenticity or redaction approval.

`node --test tests/grafana_webhook_adapter.test.mjs tests/alertmanager_adapter.test.mjs`
checks all seven namespaces, limits/privacy, malformed inputs and actual local
store replay/AI-7 counts. Existing Node CI runs it; fixture-only edits select Node.
Rollback is a code revert; no account or deployment rollback is needed.
P01 remains **NO-GO/BLOCKED**, AI-9 **BLOCKED**, Codex runtime **OPEN**.

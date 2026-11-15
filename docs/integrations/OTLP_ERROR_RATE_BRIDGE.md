# Offline OTLP/HTTP JSON error-rate bridge to AI-1

**Status: SYNTHETIC / OFFLINE ONLY.** This is a narrowly scoped OpenTelemetry
Protocol JSON adapter, not a network receiver, Collector replacement, authenticated
telemetry exporter, production monitor or tenant-isolation mechanism.

## Why this exists

Devobs already has an optional local OpenTelemetry Collector, Prometheus and
Grafana stack, plus an Alertmanager incident bridge and a CloudEvents CI bridge.
Neither bridge converts a reviewed, synthetic OTLP/HTTP JSON metric payload into
the existing AI-1 `server_metric` contract. This adapter handles exactly one
explicitly named gauge, without introducing new infrastructure or dependencies.

The official OTLP metrics request is an `ExportMetricsServiceRequest`, encoded
as protobuf JSON over OTLP/HTTP at `/v1/metrics`. The **adapter accepts a strict
subset** of that JSON: one resource, `service.name=devobs`, one scope, one metric
`error_rate_pct` with unit `%`, and 1–100 gauge data points containing only
`timeUnixNano` and numeric `asDouble`. Other valid OTLP exports are intentionally
unsupported, including histograms, sums, exemplars and datapoint attributes.

## Exact synthetic input

```json
{
  "resourceMetrics": [{
    "resource": {
      "attributes": [{
        "key": "service.name",
        "value": { "stringValue": "devobs" }
      }]
    },
    "scopeMetrics": [{
      "metrics": [{
        "name": "error_rate_pct",
        "unit": "%",
        "gauge": {
          "dataPoints": [{
            "timeUnixNano": "1763208000000000000",
            "asDouble": 12.5
          }]
        }
      }]
    }]
  }]
}
```

The output is an AI-1 `server_metric` JSONL event with `source=server`,
`severity=info`, `data.name=error_rate`, `data.unit=percent`, and
`data.value=12.5`. The existing AI-1 parser and deterministic event hashing
remain authoritative. Time is converted from decimal Unix nanoseconds to
millisecond-precision UTC; the accepted range is 2000-01-01 through 2099-12-31.
Two input points collapsing to the same millisecond are rejected, not merged.

## Manual local use

Review a **synthetic** JSON payload first. From the repository root:

```sh
node scripts/integrations/otlp_error_rate_adapter.mjs --input /path/to/synthetic-otlp.json
node --test tests/otlp_error_rate_adapter.test.mjs
```

`--input -` reads bounded UTF-8 from standard input. On success, only normalized
AI-1 JSONL is written to stdout; no file or persistent event store is written.
For optional local ingestion, separately review and save the output, then follow
`docs/AI_EVENT_INGESTION.md`; no ingestion happens automatically.

## Trust boundary, errors and limitations

- Full input limit is 1 MiB and maximum 100 points. Conversion is atomic: one
  invalid point rejects the whole payload with exit status 2 and zero stdout.
- The strict AI-1 JSON parser rejects duplicate keys. Unexpected attributes,
  private labels, extra resource/scope/metric fields, multiple resources,
  unsupported metric types, invalid timestamps, non-finite/negative/out-of-range
  rates, and duplicate normalized timestamps all fail closed.
- No private identifiers or free-form labels are retained. The only allowed
  resource attribute is `service.name=devobs`; other project names are rejected,
  not silently relabeled as Devobs. This does not authorize combining tenant data.
- Errors print fixed categories only, never input text or secret-bearing values.
- No source attestation, signature verification, token, transport, webhook,
  live Collector connection, SLO claim, anomaly improvement or P02 evidence is
  established by a synthetic snapshot.
- No external dependency, outbound request, listener, cloud resource, production
  change, paid inference or automatic response is introduced.

## Official specifications and rollback

- [OTLP specification (stable metrics protocol)](https://opentelemetry.io/docs/specs/otlp/)
- [OpenTelemetry metric data model (Gauge)](https://opentelemetry.io/docs/specs/otel/metrics/data-model/)
- [OTLP/HTTP exporter transport](https://opentelemetry.io/docs/specs/otel/protocol/exporter/)
- [Collector transformation and filtering](https://opentelemetry.io/docs/collector/transforming-telemetry/)

OpenTelemetry components are open source and governed under the OpenTelemetry
project; this adapter uses Node built-ins and the existing Devobs AI-1 parser.
Revert the single feature PR to remove this optional offline bridge. No deployment
rollback is needed. P01 stays NO-GO, AI-9 stays BLOCKED, and the owner must review
any later real-world telemetry transfer separately.

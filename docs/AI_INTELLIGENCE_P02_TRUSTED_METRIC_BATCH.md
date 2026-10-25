# DevObs P02/T17 — bounded trusted metric batch (offline subset)

**Status: implemented and testable locally; hosted P02 remains BLOCKED.** This change provides a small batch adapter on top of the existing single-snapshot `from_trusted_metric` validator. It is **not** an OTLP listener, OpenTelemetry collector, real metrics export, model invocation, billing feature, or evidence of cloud readiness.

## Contract

`from_trusted_metric_batch(metrics, *, tenant, project, source_sha, now_utc)` takes up to **32** independently trusted, OTLP-like numeric snapshot objects. Each must have exactly `resource: {"service.name": ...}`, `name`, `value`, and `time_unix_nano`. The allowed metric names remain `error_rate_pct`, `capacity_pct`, and `failed_checks`; this is a DevObs application mapping, **not** a claim those are standard OpenTelemetry instrument names. Unknown fields and raw bodies/prompts are rejected.

Identity (`tenant`, `project`) and pinned `source_sha` are supplied by a **separate, authenticated caller** and must never be derived from metric metadata. A UTC-aware comparison clock is mandatory. The batch rejects evidence older than 900 seconds or more than 60 seconds in the future; duplicate `(service, metric)` readings; non-list, empty or over-limit batches; NaN, extra attributes, and invalid scope. A single invalid point rejects the **whole** batch. Results are deterministic, sorted and contain SHA-256 evidence digests; the digests are **not** source authenticity signatures.

This batch parser **does not** authorize a sender, establish that clock or SHA is authentic, enforce tenancy at a network boundary, or make the evidence tamper-proof. It does not persist any data. Do not connect it to public OTLP or customer input. The existing `correlate` function applies its own freshness and scope gates before issuing review-only findings. No autonomous action is enabled.

## Validation

```bash
python3 -m unittest discover -s tests -p 'test_trusted_metric_batch.py' -v
python3 -m compileall -q scripts/devobs_intelligence tests/test_trusted_metric_batch.py
```

Tests use synthetic data only. Before marking P02/T17 complete, separately verify an authenticated collector, signed/verified source provenance, quota enforcement at ingress, consented hosted staging, secure storage/retention, and negative tenancy tests. Track that work in [#222](https://github.com/hamedonassar95/Devobs/issues/222); do **not** treat unit tests as a production release gate.

## Official technical references

- [OpenTelemetry semantic conventions 1.44.0](https://opentelemetry.io/docs/specs/semconv/): common telemetry naming conventions; DevObs currently implements a narrow mapping, not generic OTLP.
- [OpenTelemetry service.name](https://opentelemetry.io/docs/specs/semconv/resource/service/): standard service resource attribute.
- [MCP protocol 2026-07-28](https://blog.modelcontextprotocol.io/posts/2026-07-28/): future integration guidance; no MCP server or credential exchange is added here.
- [MCP authorization security considerations](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/authorization/security-considerations.mdx): future HTTP authorization must enforce audience-bound tokens and secure storage.

# DevObs P02/T18 — privacy-first, metadata-only log/trace gate

**Scope:** Offline contract only, related to [P02 issue #222](https://github.com/hamedonassar95/Devobs/issues/222). The repository now has a local file/stdin adapter for a narrow OTLP/JSON Logs subset; this is **not** an OpenTelemetry Collector, network receiver, complete redaction engine, or production-grade privacy assessment. P02/T18 remains **BLOCKED** until hosted collectors, end-to-end checks, and data policies are independently verified.

## Why this design

OpenTelemetry warns that logs, attributes, and traces may contain credentials or personal data and recommends minimization and allowlist-based scrubbing. OWASP recommends narrowly scoped, schema-validated agent/tool inputs and explicit human control. To avoid pretending that best-effort regular expressions can make arbitrary log bodies safe, DevObs accepts **only small, pre-classified metadata** and rejects any raw bodies, prompts, tokens, URLs, exception stacks, user attributes, or extra fields.

## Implemented offline interface

`from_trusted_safe_signals(records, *, tenant, project, source_sha, now_utc)`:

- Requires separately authenticated **caller-provided** tenant, project, immutable 40/64-hex `source_sha` and timezone-aware comparison time. This module **does not authenticate** the caller or prove source authenticity.
- Accepts 1–32 structured Python dictionaries. Every record requires exact `kind`, `resource: {"service.name": ...}`, `operation`, `status`, `time_unix_nano`. `trace` additionally requires integer `duration_ms` (0–600,000); `log` must not include it.
- Restricted kinds: `log`, `trace`; DevObs-specific operations: `ci.check`, `http.request`, `deploy.change`, `agent.review`; statuses: `ok`, `error`, `unknown`. These event labels are **local DevObs vocabulary**, not official OTel semantic convention mappings.
- Refuses input more than 900 seconds old or more than 60 seconds in the future, duplicate `(kind, service, operation, timestamp)` identifiers, malformed IDs, arbitrary attributes, sensitive text, and any unexpected field. On one error **the whole batch fails**; no partial success, I/O, or storage.
- Returns immutable, deterministically ordered, minimal `SafeSignal` objects and SHA-256 digests over canonical non-sensitive metadata. Hashes are **not** signatures or anonymization guarantees. Service IDs may still contain identifying information if the upstream registry is not controlled.

## Tests and stage gate

The optional [OTLP Logs and Traces offline adapter](integrations/OTLP_LOGS_TRACES_OFFLINE_ADAPTER.md) accepts only a closed subset of OTLP/JSON and emits this SafeSignal contract. It rejects log bodies, span attributes/events/links, severity and free-text status messages; trace and span identifiers are validated but never preserved in output. It does not write to AI-1 or enable a Collector. The CLI's tenant/project/SHA flags are manual labels and are unverified. An in-process `ScopedOtlpConverter` composes an injected access-token verifier with `OfflineTenantGate`, derives the SHA from an authorized project snapshot, and calls the existing signed topology verifier. OTLP `service.name` must occur in the verified topology for the same tenant, project and source SHA, and that topology must be fresh. This authenticates the requester and restricts labels only when the injected verifier, trust keys and membership/snapshot configuration are trusted; it still does not attest that the telemetry file originated from that service or prevent a permitted requester from supplying fabricated metadata.

```bash
python3 -m unittest discover -s tests -p 'test_intelligence_safe_signal_adapter.py' -v
python3 -m unittest tests.test_otlp_logs_traces_adapter -v
python3 -m unittest tests.test_otlp_authenticated_scope -v
python3 -m compileall -q scripts/devobs_intelligence scripts/integrations/otlp_logs_traces_adapter.py tests/test_intelligence_safe_signal_adapter.py tests/test_otlp_logs_traces_adapter.py tests/test_otlp_authenticated_scope.py
```

Offline adversarial fixtures include token-looking bodies, private prompt text, unexpected PII attributes, extra resource properties, time replay, invalid scope, duplicate events, oversized batches, and invalid trace durations. They do **not** use customer telemetry or communicate with a live model or service.

The PR must pass repository CI/security/CodeQL on the exact SHA and receive human review before merging. **Do not check off P02/T18** on this basis. Missing work includes upstream authenticated collection with no public exposure, approved service-name registry, PII classification and privacy review, field redaction **before any durable logs**, retention and deletion enforcement, negative cross-tenant hosted tests, load/cardinality limits and audit evidence.

## Official primary sources

- [OpenTelemetry: Handling sensitive data](https://opentelemetry.io/docs/security/handling-sensitive-data/)
- [OpenTelemetry: Collector configuration best practices](https://opentelemetry.io/docs/security/config-best-practices/)
- [OWASP MCP Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html)

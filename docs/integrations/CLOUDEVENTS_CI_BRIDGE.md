# Offline CloudEvents CI bridge

This bridge is a local, offline adapter from a deliberately narrow structured CloudEvents JSON subset to the existing AI-1 `ci_result` input schema. It does not receive webhooks, authenticate a sender, read project accounts, persist events, call a model, trigger remediation, or deploy anything. Its source names are conversion allowlist entries, not proof that an event came from those repositories.

## Architecture and source allowlist

The adapter in `scripts/integrations/cloudevents_ci_adapter.mjs` uses the existing AI-1 `event_schema.mjs` normalization/parser and `event_ingest.mjs` bounded input reader. It does not define a second AI-1 schema or storage path. Each input line is validated and normalized in memory; the complete batch is passed through `parseEventLines` before any output is written.

The only accepted `source` identifiers are:

| Project label | CloudEvents `source` |
| --- | --- |
| Devobs | `https://github.com/hamedonassar95/Devobs` |
| devobs-saas | `https://github.com/hamedonassar95/devobs-saas` |
| phone-repair-assistant-v2 | `https://github.com/hamedonassar95/phone-repair-assistant-v2` |
| al-dala-mobile | `https://github.com/hamedonassar95/al-dala-mobile` |
| LiveOps-Integration | `https://github.com/hamedonassar95/LiveOps-Integration` |
| DevObs-ai-Intelligence- | `https://github.com/hamedonassar95/DevObs-ai-Intelligence-` |

These names are configured only for synthetic/local conversion. This task does not connect to or modify any of these other repositories.

## Supported event format

Input is newline-delimited structured JSON, one CloudEvent per nonempty line. The accepted subset is CloudEvents stable `specversion: "1.0"`, `type: "devobs.ci.result.v1"`, an explicitly allowlisted source, a nonempty bounded safe `id` (1–100 ASCII letters, digits, periods, underscores, or hyphens; it must contain a letter), an RFC3339 timestamp with seconds, an explicit timezone, and at most nine fractional digits. Leap-second values are rejected because the existing JavaScript timestamp normalization does not represent them. The event must have `datacontenttype: "application/json"` and a `data` object containing exactly:

```json
{"workflow":"CI build","job":"Node tests","conclusion":"success","commit_sha":"1111111111111111111111111111111111111111"}
```

The only permitted data fields are `workflow`, `job`, `conclusion`, and `commit_sha`. The commit SHA must be 40 lowercase hexadecimal characters or `null`. Workflow and job are bounded AI-1 labels; URLs, emails, known credential patterns, phone-like strings, unsafe characters, extra fields, and invalid labels are rejected. The existing AI-1 event schema remains authoritative for normalization and its secret/PII pattern checks.

`source` is preserved as a safe project distinction by prefixing the validated workflow label with the configured project label. The converted AI-1 record contains only its existing fields: `schema_version`, `occurred_at`, `source`, `kind`, `severity`, and `data`. CloudEvent `id` is used only to reject duplicate `(source, id)` pairs and is not forwarded. Same-content AI-1 events with different CloudEvent IDs are rejected rather than silently deduplicated.

Conclusions map deterministically:

| CI conclusion | AI-1 severity |
| --- | --- |
| `success`, `neutral` | `info` |
| `skipped`, `cancelled`, `action_required` | `warning` |
| `failure`, `timed_out` | `error` |
| `unknown` | `unknown` |

The adapter rejects duplicate JSON keys, unknown event attributes, malformed formats/timestamps/SHAs, duplicate IDs, unsupported sources/types, unsafe labels, empty lines, batches over 100 events, and inputs over 1 MiB. A failure returns a nonzero exit code and a fixed error category on stderr. It emits no partial event output. Error categories do not include the input value or path.

## Local CLI

Convert the included deterministic synthetic fixture:

```sh
node scripts/integrations/cloudevents_ci_adapter.mjs --input examples/integrations/synthetic-ci-events.jsonl
```

Read a bounded batch from standard input:

```sh
cat examples/integrations/synthetic-ci-events.jsonl | node scripts/integrations/cloudevents_ci_adapter.mjs --input -
```

Successful output is normalized AI-1 JSONL on stdout. Redirecting it to a file is an explicit operator action. The adapter itself never writes files or stores results. To check the output against the existing parser, save reviewed output locally and use the existing AI-1 ingestion instructions in [AI event ingestion](../AI_EVENT_INGESTION.md); ingestion and storage remain separate operator actions.

Before any optional ingestion, review the complete converted batch and confirm its source labels, timestamps, conclusions, commit SHAs, and data classification. Do not ingest untrusted provider data merely because conversion succeeded.

## Trust, privacy, and limitations

CloudEvents `source` and `id` are untrusted claims. This adapter has no signature verification, webhook authentication, repository lookup, source attestation, or network access; an allowlisted source does not authenticate provenance or prove a CI run succeeded. The example data is synthetic and conveys no evidence about actual project status.

Only workflow/job labels, the conclusion, commit SHA, and event time are mapped. Raw logs, test output, branch names, user identities, email addresses, URLs, tokens, and arbitrary CI payload fields are not accepted. AI-1's existing pattern checks and this adapter's bounded-label checks reduce accidental leakage but cannot identify every form of sensitive or personal data. Treat input as untrusted and review it before local ingestion.

No live adapter is approved by this change. Any future live source needs a separately reviewed design and owner approval covering authentication/signature verification, exact event scope, data minimization, retention, least-privilege sender/receiver access, replay handling, observability, and failure behavior. Any workflow, webhook, cloud resource, credential, or production change requires its own approval and security review. P01 remains **NO-GO / BLOCKED** and AI-9 remains **BLOCKED**.

## Specification and license

The adapter targets the CloudEvents stable v1.0.2 specification. The upstream repository's v1.0.2 tag resolves to commit `fc1f6f31f5f011a72183f1bcea20c987cb683ade` (checked 2026-11-14).

- [CloudEvents v1.0.2 specification](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md)
- [CloudEvents JSON format](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/formats/json-format.md)
- [CloudEvents v1.0.2 source and license](https://github.com/cloudevents/spec/tree/v1.0.2)
- [Apache-2.0 license](https://github.com/cloudevents/spec/blob/v1.0.2/LICENSE)

The adapter adds no CloudEvents package or external dependency; these links document the wire format and upstream license.

## Rollback

Revert the integration PR or remove the adapter, its tests, fixture, this document, and the README link. No existing deployment, CI workflow, production OIDC, PostgreSQL, AI-9 gate, persistence, or external integration is changed by this bridge.

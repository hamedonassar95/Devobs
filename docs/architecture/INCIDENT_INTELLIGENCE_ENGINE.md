# Incident Intelligence Engine Architecture

Status: **offline-first, advisory-only**. Source base for this change:
`c244ab2368d43ca1f7b9cee949650bc377747258` (`origin/main`, the merge commit of
PR #736). This document describes an orchestration layer; it does not change
P01, AI-9, or Codex runtime gates.

## Purpose

`devobs/incidents/` turns sanitized CI and operational evidence into a
deterministic incident report. It answers:

1. What happened, and when?
2. Which bounded category is supported by the evidence?
3. What evidence is missing?
4. Are multiple incidents recurrence or duplicates?
5. Which diagnostic step can a human take next?
6. Which actions require explicit human approval, and which are forbidden?

It never executes remediation, deploys, changes infrastructure, rotates
secrets, deletes resources, merges PRs, performs billing operations, or closes
an incident without evidence.

## Relationship to existing components

The new package deliberately does not duplicate prior merged work.

| Existing component | Reused behavior |
|---|---|
| `devobs/incident_intelligence/` | Provider-neutral `AIProvider` protocol, evidence/confidence models, deterministic rule classifier, strict report patterns, and disabled-by-default provider behavior |
| `scripts/ci_failure_intelligence.py` | Canonical `redact_secrets`, `normalize_log`, `signature_id`, workflow-run analysis, repeated-signature detection, and bounded CI finding conventions |
| `scripts/devobs_intelligence/` | Existing strict envelope, adviser, policy, state-machine, audit, and observability patterns inform the approval and event boundaries; new code does not claim to have verified signed approval or live tracing |
| `docs/agents/AI_INCIDENT_INTELLIGENCE.md` | Existing offline library contract remains the foundation; this document describes the orchestration added on top |

The `docs/incident_intelligence/`-style replacement paths were not used because
the repository already has canonical modules and documentation. The net-new
paths are `devobs/incidents/`, `tests/incidents/`, this architecture document,
and `docs/runbooks/INCIDENT_TRIAGE.md`.

## Components and data flow

```text
offline payloads / fixtures
        |
        v
ingestion.py  -- validate, bound, redact, derive IDs and signatures
        |
        v
classification.py -- map to eight categories; record missing information
        |
        v
rca.py -- repeated signatures, recurrence, heuristic symptom/cause links
        |
        v
approval.py -- explicit advisory approval states; no execution path
        |
        v
reports.py -- schema-validated JSON + Markdown rendering
        |
        v
observability.py -- bounded local structured events
        |
        v
engine.py -- deterministic orchestration of the steps above
```

### Ingestion

`ingest_incident()` accepts one payload and supports five kinds:

- `github_actions_failure`
- `sanitized_ci_log`
- `failed_test_summary`
- `deployment_health_evidence`
- `operational_incident_report`

Controls:

- Fixed maximum payload size of 131,072 UTF-8 encoded bytes.
- Fixed maximum of 100 evidence items and 100 log/summary entries per payload.
- String fields are bounded and passed through the canonical redactor.
- Unsupported objects, severity values, kinds, timestamps, and evidence
  confidences fail closed with fixed error codes.
- Missing evidence produces an `ev-no-evidence` `UNVERIFIED` item and a
  `missing_evidence` warning rather than an invented fact.
- GitHub Actions payloads and strict adviser envelopes reuse the existing
  analyzers when `run`/`jobs` or `envelope`/`signals` are supplied.
- The optional AI provider is called only through the existing provider
  interface and is absent by default.

### Classification

The merged lowercase categories remain the primary deterministic rules. The
new layer maps them to the required bounded vocabulary:

| Category | Typical supported signal | Default confidence |
|---|---|---|
| `CI_CONFIGURATION_FAILURE` | invalid workflow, required check/signal evidence | `MEDIUM` |
| `TEST_FAILURE` | assertion or failed-test evidence | `HIGH` |
| `DEPENDENCY_FAILURE` | resolver, manifest, or install evidence | `HIGH` |
| `CONTAINER_BUILD_FAILURE` | Docker build/OCI/build-context evidence | `HIGH` |
| `AUTHENTICATION_CONFIGURATION` | identity/permission/issuer configuration evidence | `MEDIUM` |
| `INFRASTRUCTURE_CONFIGURATION` | quota, capacity, runner, or resource evidence | `MEDIUM` |
| `SERVICE_HEALTH_FAILURE` | readiness, liveness, or health-probe evidence | `HIGH` |
| `UNKNOWN_FAILURE` | no trusted pattern matched | `LOW` |

Every classification contains evidence IDs, a confidence category, explicit
missing information, a next diagnostic step, a rationale, and normalized
signature IDs. A generic unmatched event is never promoted to a verified root
cause.

### Rule-based RCA

`correlate_incidents()` produces an `InvestigationReport` using bounded rules:

- Repeated normalized signatures link distinct incident IDs.
- Recurring bounded categories link separate incidents.
- A symptom category may be linked to a cause category only as
  `symptom_of`; the rationale explicitly says this is a heuristic, not proof.
- Probable cause is selected only from allowed cause categories with at least
  `MEDIUM` confidence.
- Multiple cause categories, low confidence, or missing information are
  recorded in `insufficient_evidence`.
- No evidence means `UNKNOWN_FAILURE` with `LOW` confidence.
- Timeline and output ordering are deterministic.

### Advisory approvals

`ApprovalEngine` has no executor. Closed states are:

| State | Meaning |
|---|---|
| `NOT_REQUIRED` | Read-only diagnostic step; still not an execution instruction |
| `PENDING` | No matching human approval record supplied |
| `APPROVED` | Matching owner-supplied record exists; still advisory only |
| `REJECTED` | Matching human rejection exists |
| `FORBIDDEN` | Action class is never available to an autonomous agent |

Forbidden action classes: `production_deployment`,
`infrastructure_modification`, `secret_rotation`, `resource_deletion`,
`pull_request_merge`, and `billing_operation`. Incident closure without
evidence is also forbidden. `require_approval()` raises a fixed error for
forbidden, rejected, or pending actions.

The engine emits two recommendation classes per finding:

- A read-only diagnostic step with its approval decision.
- A `prepare_remediation_plan` advisory item that remains pending unless a
  matching human approval record is supplied.

### Reports

`render_engine_json()` validates before rendering and emits sorted, compact
JSON. `render_engine_markdown()` renders the same structured report sections:
timeline, evidence, classifications, correlation, insufficient evidence,
advisory actions, verification instructions, warnings, and AI provider status.
The report schema is `incident-engine/1.0` and validates closed vocabularies,
internal evidence references, unique evidence IDs, and approval guardrails.

### Observability

The repository's existing OpenTelemetry adapter is metrics-only; it is not a
generic trace/log pipeline. `EventSink` is therefore a documented local adapter
boundary, with `MemoryEventSink`, `LoggingEventSink`, and `NullEventSink`
implementations. Events are allowlisted, redacted, and size-bounded. Event
names are:

- `incident_received`
- `validation_completed`
- `classification_completed`
- `evidence_missing`
- `report_generated`
- `approval_required`

This is local structured observability, not a claim of live tracing or remote
telemetry.

## Public API

```python
from devobs.incidents import IncidentIntelligenceEngine, render_engine_json

engine = IncidentIntelligenceEngine()  # no AI provider, no network, no sinks
report = engine.analyze([payload_one, payload_two])
json_text = render_engine_json(report)
```

A single payload can be passed with `analyze_one()`. An optional
`ai_provider` implements `devobs.incident_intelligence.analyzer.AIProvider`.
Optional `event_sinks` implement `EventSink.emit(event)`. Optional
`approval_records` are treated as caller-supplied inputs; this package does not
authenticate signatures or issue approvals.

## Security assessment

- Secret redaction reuses the canonical CI redactor before classification,
  reporting, or event emission.
- Input size, item counts, string lengths, event sizes, and closed vocabularies
  are enforced.
- Log content is treated as data only; no string from a payload is executed,
  interpreted as a command, or used as an approval grant.
- AI provider use stays behind the existing provider-neutral interface and is
  disabled by default.
- No secrets, credentials, tokens, hosted configuration, cloud resources,
  production accounts, or customer data were accessed by this implementation.
- The engine writes no files and opens no sockets. Callers choose where to
  persist the rendered report.

## Verification

The repository's Python CI uses `python -m unittest discover -s tests -v` across
Python 3.12 and 3.15. The Python documentation for unittest discovery is
<https://docs.python.org/3/library/unittest.html#unittest-test-discovery>; the
documentation for compileall is <https://docs.python.org/3/library/compileall.html>.

Focused local verification:

```sh
python -m compileall -q devobs/incidents tests/incidents
python -m unittest discover -s tests/incidents -v
python -m unittest tests.incidents.test_engine -v
python -m unittest discover -s tests -v
git diff --check
```

`pytest`, `ruff`, `bandit`, `flake8`, and `pip-audit` were not installed locally;
do not report them as passing unless hosted CI or a provisioned environment
runs them.

## Limits and non-goals

- No CLI, HTTP server, workflow, dashboard, or live provider client is added.
- No signed approval verification, IAM change, deployment, or release-gate
  change is performed.
- No claim is made that heuristic correlation proves causality.
- No repository-wide CI scan configuration was changed by this layer; the
  existing CodeQL, Trivy, RLS, security, and human gates remain authoritative.

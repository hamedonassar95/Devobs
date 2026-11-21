# Incident Triage Runbook — Offline Intelligence Engine

Use this runbook for local, offline triage of CI failures and operational
incidents. The engine is advisory only. It does not execute remediation and it
never grants approval by itself.

## Safety boundary

Do not use this runbook to:

- deploy, rerun a production workflow, merge a PR, or push to `main`;
- modify infrastructure, delete resources, rotate secrets, or change IAM;
- perform billing operations or close an incident without evidence;
- paste raw logs, tokens, customer data, or private URLs into external tools;
- treat `PENDING` or `APPROVED` in a report as permission to execute.

Related architecture: [INCIDENT_INTELLIGENCE_ENGINE.md](../architecture/INCIDENT_INTELLIGENCE_ENGINE.md).
The existing library contract remains [AI_INCIDENT_INTELLIGENCE.md](../agents/AI_INCIDENT_INTELLIGENCE.md).

## 1. Prepare sanitized evidence

Each incident payload must include a supported `kind`:

- `github_actions_failure`
- `sanitized_ci_log`
- `failed_test_summary`
- `deployment_health_evidence`
- `operational_incident_report`

Use redacted excerpts, not full raw secrets. Include a stable `incident_id`,
`timestamp`, `severity`, bounded `logs`/`summary` text, and `metadata` such as
`job` and `step`. For GitHub Actions data, supply `run` and `jobs` offline JSON;
the existing analyzer converts findings into evidence.

If no evidence is available, leave it absent. The engine will mark the record
`UNVERIFIED`, emit `evidence_missing`, and keep the probable cause
`UNKNOWN_FAILURE` with `LOW` confidence.

## 2. Run the offline engine

```python
from devobs.incidents import (
    IncidentIntelligenceEngine,
    render_engine_json,
    render_engine_markdown,
)

engine = IncidentIntelligenceEngine()
report = engine.analyze([payload])
print(render_engine_markdown(report))
json_report = render_engine_json(report)
```

There is no network call, provider call, file write, or remediation path in the
default configuration. Optional sinks can receive bounded local events:

```python
from devobs.incidents import IncidentIntelligenceEngine, MemoryEventSink

sink = MemoryEventSink()
report = IncidentIntelligenceEngine(event_sinks=(sink,)).analyze([payload])
print([event["event"] for event in sink.events])
```

## 3. Read the report in order

1. **Timeline** — confirm incident IDs, timestamps, and ordering.
2. **Evidence** — confirm every cited `ev-...` ID and its confidence label.
3. **Classifications** — review category, confidence, missing information, and
   next diagnostic step for each incident.
4. **Correlation** — repeated signatures show recurrence; `symptom_of` is a
   heuristic link, not proof of causality.
5. **Probable cause** — only use it if the category is not `UNKNOWN_FAILURE`,
   confidence is not `LOW`, and `insufficient_evidence` is understood.
6. **Recommended actions** — diagnostic steps are read-only. Remediation
   planning is advisory and usually `PENDING`.
7. **Verification instructions** — follow them before any human change.

## 4. Interpret categories

| Category | First safe check |
|---|---|
| `CI_CONFIGURATION_FAILURE` | Inspect workflow and required-check configuration at the pinned revision |
| `TEST_FAILURE` | Reproduce the assertion locally from the pinned source |
| `DEPENDENCY_FAILURE` | Compare manifest, lockfile, and resolved versions |
| `CONTAINER_BUILD_FAILURE` | Inspect Dockerfile, build context, and builder status only |
| `AUTHENTICATION_CONFIGURATION` | Review key names and issuer metadata without reading secret values |
| `INFRASTRUCTURE_CONFIGURATION` | Read quotas, runner health, and provider status only |
| `SERVICE_HEALTH_FAILURE` | Collect bounded readiness, liveness, and upstream health evidence |
| `UNKNOWN_FAILURE` | Collect more sanitized evidence; do not infer a cause |

## 5. Approval handling

| State | Triage action |
|---|---|
| `NOT_REQUIRED` | A read-only diagnostic step may be performed by an authorized operator |
| `PENDING` | Stop; obtain separate owner approval through the existing process |
| `APPROVED` | Still advisory; confirm scope, evidence IDs, and change authorization |
| `REJECTED` | Do not proceed |
| `FORBIDDEN` | Never proceed through this engine |

The following are always forbidden to autonomous agents: production
deployment, infrastructure modification, secret rotation, resource deletion,
PR merging, and billing operations. Incident closure without evidence is also
forbidden.

## 6. Escalate

Escalate to the human incident owner when any of these is true:

- probable cause is `UNKNOWN_FAILURE` or `LOW` confidence;
- `insufficient_evidence` is non-empty;
- multiple cause categories appear;
- a required approval is `PENDING`, `REJECTED`, or `FORBIDDEN`;
- evidence references cannot be verified;
- the payload was malformed and failed with a fixed error code.

## 7. Verify locally

Follow the official Python documentation for
[unittest discovery](https://docs.python.org/3/library/unittest.html#unittest-test-discovery).

```sh
python -m unittest discover -s tests/incidents -v
python -m unittest tests.incidents.test_engine -v
python -m unittest discover -s tests -v
git diff --check
```

A report is valid when `render_engine_json()` returns without an
`incident-engine/1.0` schema error and the JSON contains:

- `incident_ids`, `severity`, and `timeline`;
- evidence IDs referenced by classifications and recommendations;
- explicit `missing_information` for every classification;
- explicit approval state and `requires_human` for every recommendation;
- `verification_instructions`.

## Failure codes

The engine uses fixed codes that do not echo private incident content. Common
codes are `invalid_object`, `unsupported_kind`, `invalid_severity`,
`payload_too_large`, `missing_evidence` (warning), `no_incidents`,
`too_many_incidents`, `conflicting_duplicate_id`, `approval_pending`,
`approval_rejected`, and `approval_forbidden`.

Treat any unexpected exception, redirect, empty output, or missing tool as a
failure. Do not silently substitute a provider, approval, or remediation path.

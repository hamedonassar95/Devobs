# AI Incident Intelligence

`devobs/incident_intelligence` is an offline-first Python library that converts
sanitized GitHub Actions failure evidence into deterministic incident reports.
It produces evidence-linked hypotheses, explicit confidence levels, advisory
recommendations, and a human-readable summary.

It is **advisory only**. It never applies a fix, reruns a workflow, merges a PR,
pushes to `main`, deploys, calls an external API by default, or runs
`terraform apply`.

## Relationship to existing components

- It reuses the redaction and normalization primitives from
  `scripts/ci_failure_intelligence.py` (PR #734) rather than adding a second
  sanitizer.
- `analyze_workflow_run()` wraps PR #734's `analyze_run()` so GitHub Actions job
  and step findings become incident evidence.
- It reuses `scripts/devobs_intelligence/contracts.py` and
  `scripts/devobs_intelligence/adviser.py` through `analyze_signals()`. The
  strict envelope hashes raw project identifiers; this package returns only
  derived digests, bounded classifications, and advisory recommendations.
- It adds no CLI, no web server, no workflow, and no live provider client.

The hardening work uses the repository's existing corresponding paths. The
requested `tests/incident_intelligence/` and `docs/incident-intelligence/`
directories do not exist, so tests remain in `tests/test_incident_intelligence.py`
and this document remains at `docs/agents/AI_INCIDENT_INTELLIGENCE.md`. The
implementation stays in `devobs/incident_intelligence/`; no duplicate service
was added.

## Public API

```python
from devobs.incident_intelligence import analyze_incident, render_summary

report = analyze_incident(
    {
        "title": "nightly CI",
        "job": "build",
        "step": "Install dependencies",
        "logs": ["pip install failed: ResolutionImpossible for requests>=2"],
    }
)

print(report.category)       # dependency
print(report.confidence)     # HIGH
print(report.summary)        # human-readable, redacted
print(render_summary(report))
print(report.to_dict())      # JSON-serializable evidence, hypotheses, actions
```

For a GitHub Actions run already available as offline JSON:

```python
from devobs.incident_intelligence import analyze_workflow_run

report = analyze_workflow_run(run_metadata, jobs_data)
```

For bounded aggregate signals from the existing offline adviser:

```python
from devobs.incident_intelligence import analyze_signals

event = {
    "schema_version": 1,
    "event_id": "ci-123",
    "provider": "github",
    "project_ref": "internal-project-name",
    "source_sha": "a" * 40,
    "kind": "incident",
    "observed_at": "2026-11-21T12:00:00Z",
    "evidence_digests": ["b" * 64],
}
signals = {"failed_checks": 1, "error_rate_pct": 0.0, "capacity_pct": 20.0}

report = analyze_signals(event, signals)
print(report.category)   # ci_failure
print(report.signal)     # ci_failure
```

The strict contract hashes `project_ref` into `project_digest`; `source_sha`
stays inside the validated envelope and adviser digest boundary. Neither raw
value is copied into the incident report or an injected AI provider prompt.
Invalid envelopes or signals fail closed as `unknown` with fixed,
non-sensitive warnings.

## Categories

| Category | Typical evidence |
| --- | --- |
| `ci_failure` | Existing adviser classification from `failed_checks` in a valid evidence envelope |
| `dependency` | `pip install failed`, `npm ERR!`, resolution conflicts, missing modules |
| `configuration` | `ConfigurationError`, missing required environment variable, invalid config keys |
| `timeout` | `ETIMEDOUT`, `TimeoutError`, `timed out`, timeout exceeded |
| `test` | `FAILED`, `AssertionError`, `FAIL:`, failed test suite |
| `infrastructure` | Lost runner, disk quota, OOM, 502/503, rate limits, DNS or connection resets, high error rate, capacity pressure |
| `unknown` | No trusted pattern matched; root cause remains unverified |

Rules are ordered and deterministic. A dependency-install signal wins over a
generic timeout when both appear in the same line; a direct log match wins over
a job/step-name-only match.

## Evidence and confidence

- Evidence labels reuse PR #734's `VERIFIED`, `INFERRED`, and `UNVERIFIED`
  vocabulary.
- Hypothesis confidence is explicit: `HIGH`, `MEDIUM`, or `LOW`.
  - A trusted pattern in sanitized log text produces `HIGH`.
  - A pattern found only in job/step metadata produces `MEDIUM`.
  - No trusted match produces `LOW` and category `unknown`.
- Each hypothesis carries `evidence_ids` that resolve to the report's redacted
  evidence entries.
- Unknown or malformed input fails closed with warnings instead of inventing a
  root cause.
- Bounded adviser signals are `HIGH` for `ci_failure` and `MEDIUM` for
  `high_error_rate` or `capacity_pressure`; these are rule labels, not calibrated
  probabilities.

## Structured JSON schema

Reports use schema version `1.1`. `Report.to_dict()` is JSON-normalized and
`Report.to_json()` emits deterministic, sorted JSON. Every summary includes:

- `source`, `category`, `signal`, and a `HIGH`/`MEDIUM`/`LOW` `confidence` label.
- `evidence` entries with stable `id`, `source`, redacted `excerpt`, and
  `VERIFIED`/`INFERRED`/`UNVERIFIED` confidence.
- `hypotheses` whose `evidence_ids` resolve to those evidence entries.
- `recommendations` whose `hypothesis_id` resolves to a hypothesis and whose
  `requires_human_approval` is always `true`.
- An `ai_provider` status and a `guardrails` map.

`validate_report_json()` checks the complete decoded structure, supported
values, and internal references. It rejects dangling evidence or hypothesis
references, missing fields, and any report that permits automatic fixes.

## Advisory AI boundary

AI is disabled by default. No provider object is created and no network call is
made unless a caller explicitly injects one:

```python
class AdvisoryProvider:
    def diagnose(self, prompt: str) -> str:
        ...  # caller-controlled; receives redacted evidence only

report = analyze_incident(incident, ai_provider=AdvisoryProvider())
```

- The provider receives redacted evidence and cannot change the deterministic
  category, hypothesis, or recommendations.
- Provider text is redacted again and marked advisory.
- Provider errors or empty responses become `AIProviderReport(status="error")`
  while the deterministic report remains usable.

## Guardrails

Every report includes a `guardrails` map with `automatic_fixes: false`,
`external_api_calls_by_default: false`, `human_approval_required: true`, and
`read_only: true`. Recommendations are advisory next steps, not executable
commands or authorizations.

## Limitations

- Confidence is rule-based and heuristic, not a calibrated probability.
- Novel failure modes are classified `unknown` until a reviewed rule is added.
- Redaction reuses the existing CI Failure Intelligence patterns; callers must
  still avoid providing secrets in incident input.
- The library does not verify that a recommended investigation succeeded.

## Verification

```bash
python -m unittest tests.test_incident_intelligence tests.test_ci_failure_intelligence -v
python -m py_compile devobs/incident_intelligence/*.py
python -m compileall -q devobs/incident_intelligence
git diff --check
```

`python -m pytest` can be used instead when `pytest` is installed; it was not
available in the verification environment, so the equivalent `unittest` runner
above was used.

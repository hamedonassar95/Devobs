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
- It complements `scripts/devobs_intelligence/adviser.py`, which works from
  bounded aggregate signals. This package adds incident-level hypotheses for
  failed jobs and steps.
- It adds no CLI, no web server, no workflow, and no live provider client.

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

## Categories

| Category | Typical evidence |
| --- | --- |
| `dependency` | `pip install failed`, `npm ERR!`, resolution conflicts, missing modules |
| `configuration` | `ConfigurationError`, missing required environment variable, invalid config keys |
| `timeout` | `ETIMEDOUT`, `TimeoutError`, `timed out`, timeout exceeded |
| `test` | `FAILED`, `AssertionError`, `FAIL:`, failed test suite |
| `infrastructure` | Lost runner, disk quota, OOM, 502/503, rate limits, DNS or connection resets |
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
git diff --check
```

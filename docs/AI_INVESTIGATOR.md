# AI Incident Investigator — Phase 7

## Objective

Phase 7 turns the Phase 6 incident evidence bundle into a guarded investigation:

```text
Incident
  -> Evidence
  -> AI Investigator
  -> Root Cause Hypotheses
  -> Confidence Scores
  -> Recommended Tests
  -> Fix Forward vs Rollback
  -> Proposed PR / Recovery Plan
  -> Human Approval Gate
```

The investigator is advisory. It never merges, pushes directly to `main`, disables protections, or executes rollback.

## Architecture

The workflow uses two layers:

1. **Deterministic triage** — `scripts/incident_triage.py`
   - owns the production safety classification;
   - determines `FIX_FORWARD`, `MANUAL_REVIEW`, or `ROLLBACK_CANDIDATE`;
   - cannot be bypassed by model output.

2. **Guarded investigator** — `scripts/ai_investigator.py`
   - generates hypotheses, confidence scores, diagnostic tests, a recovery decision, and a proposed PR plan;
   - uses the OpenAI Responses API when `OPENAI_API_KEY` is available;
   - falls back to deterministic investigation when the key/provider is unavailable.

This means incident handling continues even during AI-provider outages or before an API key is configured.

## Inputs

The investigator consumes only the structured Phase 6 evidence:

- `incident.json`
- `incident-jobs.json`
- `incident-workflow-run.json`

Raw workflow logs are not automatically sent to the model.

All evidence is treated as **untrusted data**. Job names, metadata, links, and other evidence are never treated as instructions. This reduces prompt-injection risk from CI output.

## Outputs

### `investigation.json`

Machine-readable fields include:

- source: `ai` or `deterministic_fallback`
- root-cause hypotheses
- confidence per hypothesis, bounded from `0.0` to `1.0`
- recommended diagnostic tests
- decision: `FIX_FORWARD`, `ROLLBACK`, or `MANUAL_REVIEW`
- decision confidence
- recovery strategy
- proposed PR title, branch, and candidate file changes
- mandatory human-approval state

### `investigation.md`

Human-readable report containing:

1. incident summary;
2. ranked root-cause hypotheses;
3. evidence for each hypothesis;
4. recommended tests and risk level;
5. fix-forward vs rollback decision;
6. recovery plan;
7. proposed PR metadata;
8. **Human Approval Gate — PENDING**.

## Policy enforcement

AI recommendations are post-processed by deterministic policy.

| Deterministic triage | AI recommendation | Effective decision |
| --- | --- | --- |
| `FIX_FORWARD` | `FIX_FORWARD` | `FIX_FORWARD` |
| `FIX_FORWARD` | `ROLLBACK` | `MANUAL_REVIEW` |
| `MANUAL_REVIEW` | any automatic direction | `MANUAL_REVIEW` |
| `ROLLBACK_CANDIDATE` | `ROLLBACK` | may remain `ROLLBACK`, but approval is still mandatory |
| any | direct push / protection bypass | prohibited |

No confidence score removes the human gate.

## Confidence policy

Confidence is evidence quality, not permission.

- every confidence value is clamped to `0.0..1.0`;
- deterministic fallback intentionally uses low confidence (`0.35`);
- high confidence does not authorize deployment or rollback;
- conflicting AI and deterministic decisions resolve toward manual review.

## Recommended-test policy

The investigator should prefer tests in this order:

1. read-only metadata inspection;
2. reproducible local/CI checks;
3. isolated PR validation;
4. production mutation only after human approval.

The model is explicitly prohibited from exposing secrets or recommending protection bypasses.

## OpenAI mode

The implementation uses the OpenAI **Responses API** with strict JSON-schema output and `store: false`.

Configure GitHub Actions with:

- Repository Actions secret: `OPENAI_API_KEY`
- Optional repository variable: `OPENAI_MODEL`

If `OPENAI_MODEL` is absent, the code defaults to `gpt-6-sol`.

If the key is missing, inaccessible, the request times out, or the provider returns unusable structured output, the workflow automatically uses deterministic fallback and continues.

## GitHub permissions

The Incident Response workflow remains scoped to:

```yaml
permissions:
  actions: read
  contents: read
  issues: write
```

The OpenAI key is exposed only to the investigator process through the workflow environment. It is never included in artifacts, issues, summaries, or model evidence.

## Human Approval Gate

A recovery decision remains **PENDING** until a human reviews:

- the original incident evidence;
- hypotheses and confidence;
- recommended tests;
- proposed recovery plan;
- rollback safety when applicable.

After approval, implementation must still use the protected pull-request flow and existing CI, CodeQL, deployment, and health-check gates.

## Safe verification

Before enabling live AI, repository CI verifies:

- deterministic fallback produces a complete investigation contract;
- confidence values remain bounded;
- AI cannot upgrade `MANUAL_REVIEW` to an automatic action;
- AI cannot replace a deterministic `FIX_FORWARD` classification with rollback;
- every report contains a pending Human Approval Gate.

A real API key is not required for these tests.

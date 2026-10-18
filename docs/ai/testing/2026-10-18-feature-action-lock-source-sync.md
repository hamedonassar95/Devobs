---
phase: testing
title: Testing Strategy
description: Verification plan for generated workflow pins and incident report gating
---

# Testing Strategy

## Test Coverage Goals

Preserve the existing incident trust gate and validate malformed agent output before a privileged GitHub comment can be published.

## Existing Unit and Contract Coverage

- `tests/test_incident_guard.py` continues to assert that the generated workflow preserves the trust boundaries and safe-output policy.
- Its report-output case now exercises `scripts/validate_incident_report.cjs` for a valid report, a noop result, a missing marker, and a duplicate marker.
- CI's existing `validate` job checks the generated action pins, workflow contracts, and repository tests.

## Integration Scenarios

- `gh aw compile --no-check-update --force-refresh-action-pins --validate` compiles all five Markdown sources.
- The `safe_outputs` job must download the agent artifact, check out validator code with `persist-credentials: false`, validate the report, and only then run `Process Safe Outputs`.
- A missing agent artifact or failed validator step must prevent the later publisher step from running.
- Actionlint 1.7.12 passes all five generated locks when ignoring its unsupported `concurrency.queue` key; the unfiltered `gh aw lint` limitation is recorded below.
- The Vertex normalization step and Gemini consumer must appear in the same generated `agent` job.

## Manual and Hosted Verification

- No tests were run locally during this phase.
- The GitHub pull-request run must pass the required `validate` and CodeQL checks before merge.
- Do not dispatch an incident or AI workflow to exercise this change; that could call a model and is unnecessary for the deterministic gate.

## Known Limits

Compiler validation does not prove a live workflow artifact download or issue comment publication. Validate those paths through hosted CI contract checks and a separately authorized, cost-aware incident drill.

Actionlint 1.7.12 does not recognize `concurrency.queue: max`, which the pinned `gh-aw` compiler emits in the Vertex lock file. The narrow local ignore is for that single schema gap; compiler `--validate` remains enabled. No repository-wide lint suppression was added.

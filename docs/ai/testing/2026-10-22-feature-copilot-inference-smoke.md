---
phase: testing
title: Testing Strategy
description: Static validation and separately approved runtime verification for Copilot inference
---

# Testing Strategy

## Acceptance Contract

- The workflow can start only on `main`, by the repository owner, after both approval inputs and the repository budget variable pass.
- The model is explicitly pinned to `gpt-6-luna`, and remote session sync/export settings are disabled.
- The workflow does not checkout the repository, provide Copilot tools/MCPs, or dispatch Vertex.
- The output validator accepts exactly `{ "status": "ok", "diagnosis": "..." }`, with a non-empty diagnosis of no more than 25 whitespace-delimited words.
- Logs and the summary contain no prompt, response, diagnosis, or credential. No artifact is uploaded; temporary files are removed.

## Static Verification

- Review generated workflow syntax with a GitHub Actions workflow linter if available.
- Run repository documentation lint, feature-doc lint, and `git diff --check`.
- Inspect the source diff for the owner/quota/budget gates, action SHA pin, CLI flags, no-checkout behavior, permissions, cleanup, and minimal summary.

## Live Inference

- **UNVERIFIED / not run:** no model call was made while implementing this change.
- A future live run requires the repository owner to verify current quota and explicitly dispatch with both Boolean inputs enabled while `DEVOBS_AI_BUDGET_APPROVED` is `true`.
- Success means the CLI invocation returned and its output passed the JSON contract. It does not prove the number of underlying HTTP requests or provider-side retention behavior.
- On failure, review only the generic status and workflow metadata. Do not enable shell tracing, print the response file, or upload it as an artifact.

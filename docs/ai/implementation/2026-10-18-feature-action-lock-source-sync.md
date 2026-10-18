---
phase: implementation
title: Implementation Guide
description: Source-consistent generated workflow pins and pre-publication incident output validation
---

# Implementation Guide

## Development Setup

- Install GitHub CLI and the official compiler: `gh extension install github/gh-aw --pin v0.92.0`.
- Use an isolated `feature-action-lock-source-sync` worktree based on the current `origin/main`.
- No dependency bootstrap is needed for this static HTML repository or the Node built-in validator.

## Code Structure

- `scripts/validate_incident_report.cjs` checks the agent output artifact without changing it.
- The investigator Markdown sources add a trusted checkout and report-validation step under `safe-outputs.steps`.
- `incident-investigator-vertex.md` defines `vertex_provider` under `jobs.agent.pre-steps`, the same job as its Gemini CLI consumer.
- Compiler output is stored beside each source as `.lock.yml`.

## Implementation Notes

- The validator rejects a missing artifact, symlink/non-file, invalid JSON, extra output items, a non-comment output, a missing or repeated marker, and a missing report heading.
- The validator emits only a fixed status or error, never the report body.
- The validation step runs in the compiler-managed safe-output job before publication. Its trusted checkout disables persisted credentials; the validator itself only reads the artifact and prints fixed diagnostics.
- Five sources were compiled with `gh aw compile --no-check-update --force-refresh-action-pins --validate` under v0.92.0.
- Actionlint identified a pre-existing cross-job `steps.vertex_provider` reference in the Vertex workflow; moving the step into `agent.pre-steps` fixed the scope mismatch.
- Generated `actions/upload-artifact` is v7.0.2, `actions/setup-node` is v7.1.0, and generated `actions/download-artifact` is v8.0.2; all references are immutable SHA pins.

## Integration Points

The compiler downloads the `agent` artifact to `/tmp/gh-aw/agent_output.json`. The safe-output job checks that file before `Process Safe Outputs` and keeps the existing single-comment policy.

## Error Handling

Any missing, malformed, or nonconforming output exits nonzero. That failure stops the later `Process Safe Outputs` step, so no comment is published. The report is not rewritten.

## Security Notes

- No new secret, token, AI endpoint, or write permission is introduced.
- `actions/checkout` disables persisted credentials.
- The Vertex normalization step emits a fixed error and its normalized provider output; it never prints the raw provider value.
- AWS and GitHub Pages deployment workflows are not modified by this feature.

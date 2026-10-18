---
phase: monitoring
title: Monitoring & Observability
description: Signals and follow-up for generated action security updates and report validation
---

# Monitoring & Observability

## Key Metrics

- GitHub Actions required-check result for `validate` and CodeQL.
- Number of agent artifacts accepted or rejected by the deterministic report validator.
- Current compiler metadata and SHA pins in generated workflow manifests.

## Monitoring Tools

Use the pull request's GitHub Actions and code-scanning checks. Dependabot continues to report action and Python dependency updates.

## Logging Strategy

The validator logs a fixed success/error message and never logs the AI report body or environment secrets.

## Alerts & Incident Response

- A failed validator blocks the safe-output job; inspect its fixed diagnostic and the agent run without exposing secrets.
- A stale compiler-generated pin should be corrected by updating the official compiler version and recompiling the Markdown sources.

## Cost Controls

No AI inference or cloud resource is launched by this change. Do not use an incident workflow as a smoke test while API billing is unavailable.

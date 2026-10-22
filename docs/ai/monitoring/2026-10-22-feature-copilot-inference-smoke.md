---
phase: monitoring
title: Monitoring & Observability
description: Minimal outcome-only receipt for a manually authorized Copilot inference check
---

# Monitoring & Observability

## Minimal Run Receipt

The workflow summary contains only:

- pass/fail or unverified outcome;
- source SHA;
- GitHub Actions run URL;
- UTC completion time.

It does not record the prompt, model response, diagnosis, token, or raw provider error. The CLI output and session home are deleted from runner temporary storage, and no artifact is uploaded.

## Interpreting Results

- **VERIFIED (runtime):** only when a separately approved owner-run completes and the exact JSON contract passes.
- **UNVERIFIED:** skipped by a gate, failed before inference, returned an error, or produced malformed output.
- Do not infer that a credential or model works from repository configuration or a successful setup step.

## Privacy and Cost Limits

- **VERIFIED (documentation):** GitHub says disabling CLI client telemetry does not disable server-side collection. Session-sync is set off, but the service-side handling remains governed by GitHub Copilot policy. See [Copilot CLI configuration](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/configure-copilot-cli) and [session data](https://docs.github.com/en/copilot/concepts/security-governance-and-network-settings/session-data).
- Review available quota before dispatch. The existing repository budget variable and per-dispatch confirmation are required; no quota value is fetched or recorded by this workflow.

---
phase: implementation
title: Implementation Guide
description: Build and operate the isolated manual Copilot inference smoke check
---

# Implementation Guide

## Code Structure

- `.github/workflows/copilot-inference-smoke.yml` is the executable source.
- Seven date-prefixed files under `docs/ai/` record requirements, design, planning, implementation, testing, deployment, and monitoring.
- No generated `.lock.yml` is used because the workflow is standard GitHub Actions YAML rather than a GH-AW Markdown workflow.

## Workflow Behavior

1. A dispatch from `main` must be initiated by the repository owner. Both Boolean confirmations must be true, and `DEVOBS_AI_BUDGET_APPROVED` must equal `true`; otherwise the job is skipped.
2. `actions/setup-node` uses a full SHA pin. npm installs the exact `@github/copilot` version `1.0.103`.
3. The CLI receives `COPILOT_GITHUB_TOKEN` only in the inference step. It runs once from a fresh temporary directory using the currently recommended opt-in model `gpt-6-luna`, an empty available-tools list, disabled built-in MCPs, no-ask-user, and silent mode. Model access still depends on the account's plan and quota.
4. A private temp response file captures stdout and stderr. Python checks JSON syntax, exact keys, `status == "ok"`, and diagnosis length. The diagnosis is never printed.
5. `remote: off` and `remoteExport: false` disable session sync and remote session export. Client-side telemetry is disabled for this invocation. These settings do not disable provider-side collection. The cleanup trap removes the temporary response file and CLI home even when validation fails.
6. The final summary records only outcome, SHA, run URL, and UTC timestamp. No artifact is uploaded.

## Security Notes

- `contents: none`, no checkout, no `actions: write`, no issues/PR permissions, and no GCP/OIDC permissions.
- The workflow has no incident trigger and no connection to the automatic Vertex circuit breaker.
- The CLI uses an authentication secret to reach Copilot; the workflow does not expose or inspect its value.
- **VERIFIED (documentation):** `--available-tools` excludes all tools not listed; GitHub CLI documentation also describes session-sync, session-export, model, and client-telemetry controls. See [tool controls](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/allowing-tools), [programmatic CLI options](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference), [supported models](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference#supported-models), and [CLI settings](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference).
- **UNVERIFIED (runtime):** the configured token, model access, billing/quota, and response have not been exercised.

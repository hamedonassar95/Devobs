# Devobs — Integration Control Plane (review-only)

> **Status:** documentation and evidence inventory only. This directory does **not** install GitHub Apps, connect provider accounts, enable deployments, grant scopes, or create automation schedules. The trusted Codex config separately declares an opt-in-at-runtime public read-only documentation MCP, not an authenticated third-party account.

**Review date:** 2026-10-31 (the original five observations date from 2026-10-25; new checks date from 2026-10-31). **Repository:** public `hamedonassar95/Devobs`. The evidence below is a point-in-time observation and must not be treated as a continuously monitored status page.

## Scope and source of truth

- `service-inventory.json` is the machine-readable evidence and decision ledger for the seven named integrations.
- `RUNBOOK.md` defines the human approval gates and next diagnostic steps. The read-only validator is `scripts/check_integration_catalog.py`.
- Existing documentation remains authoritative for the CI/automation architecture: [Automation Hub](../AUTOMATION_HUB.md), [integration workflow](../INTEGRATION_WORKFLOW.md), [AI DevKit](../AI_DEVKIT.md), and [SaaS readiness](../PRODUCT_SAAS_READINESS.md).
- GitBook's existing three-page Git-sync import under `docs/gitbook-sync-prep/` is a **separate content pipeline**. Do not copy private GitBook backup pages into this public repository.

## Provider snapshot

| Provider | Verified observation (as dated) | Not established | Next safe step |
| --- | --- | --- | --- |
| GitBook | Git Sync is **active**; the GitHub → GitBook import succeeded; scoped to `docs/gitbook-sync-prep` on `main`. | Safe future write-back, publication, or preserved original primary space. | Freeze edits to the synced space; review branch/writeback setup while preserving its separate private 10-page backup. |
| ChatGPT Codex Connector | Installed GitHub App shown in account screenshot; repository contains gated `ai-code-review.yml` and AI DevKit. | The installed app's exact repository grant or a successful Codex inference for Devobs. | Verify repository grant and optional budget gate; never assume any billed inference is approved. |
| aictrl.dev | Read-only check on **2026-10-31** confirmed a personal organization. A generic onboarding banner said automatic review was on, but `list_tasks` for `hamedonassar95/Devobs` returned **Organization or repository not found**. | Devobs repository grant, runnable tasks, or completed automatic code review. | Owner verifies and approves the exact repository grant in aictrl; re-run read-only task listing before any external execution. |
| Fly.io | GitHub App shown as installed. | Deployment, app existence, connectivity, billing or repository grant. | Defer until a verified workload needs Fly; obtain separate cost/deploy approval. |
| Lovable.dev | Authenticated workspace with one **unrelated** invoice application; no custom connectors. | Devobs application or GitHub project mapping. | If a Devobs UI is needed, agree on scope, cost, visibility and repo isolation first. |
| OpenArt MCP | PR #330 merged a private DRAFT validator and opt-in example. OpenArt account checked read-only 2026-10-31: Free, **0 credits**. | Codex OAuth, actual generation, or approved credits. | Keep generation disabled until exact cost quote and separate approval. |
| OpenAI Developer Docs MCP | Public docs MCP endpoint recorded in repo-scoped `.codex/config.toml` for trusted Codex checkouts. | Actual MCP handshake, tool discovery, or live Codex use. | Verify `codex mcp list` and an innocuous read-only query locally; never send private logs or secrets. |

### Verification vocabulary

- **VERIFIED(source):** configuration or repository file was read. This does *not* imply successful provider execution.
- **VERIFIED(runtime):** dated evidence of the **specific** action succeeding. Only the **GitBook initial import** was observed at the older five-provider snapshot; it is not evidence of a safe reverse sync.
- **UNVERIFIED:** installed app, API access, or a feature name is insufficient to claim a working Devobs integration.

## Approval boundaries

1. No direct edits to `main`, auto-merge, release, production publishing, rollback or infrastructure deployment.
2. No changes to external app authorizations, OAuth scopes, secrets, account integrations, billing or schedulers without a new, specific owner approval.
3. Every code change uses an independent branch, documented validation and **Draft PR**. Do not label the PR as proof that integrations were activated.
4. Provider access should be restricted to the exact repository and least privilege. Existing broad permissions must **not** be silently changed or assumed safe.
5. The public repository must contain no private GitBook page exports, tokens, customer data or operational secrets.
6. Do not combine the Devobs repository with AL-DALA MOBILE or PHONE REPAIR ASSISTANT accounts, secrets or deployments.

## Local validation (no provider calls)

Run `python3 scripts/check_integration_catalog.py` and `python3 -m unittest discover -s tests -p 'test_integration_catalog.py' -v`. These commands parse local JSON and check invariants; they do not authenticate to, mutate, or charge any provider.

**Maintenance:** refresh only after evidence is rechecked; update `review_date`, source details, repository scope and verification claims through a reviewed PR. Historical observations can become stale.

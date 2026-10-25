# Integration enablement runbook — human approvals first

This playbook is deliberately **non-executable**. It does not install apps, send API requests, synchronize GitBook pages, or provision cloud services. A GitHub App may be installed on the account yet **not configured for Devobs**.

## Step 0 — preserve the current state

- Verify current `main` SHA and [Protect main](https://github.com/hamedonassar95/Devobs/rules/24507159) ruleset before a PR. The ruleset was observed active on 2026-10-25; reconfirm when acting.
- Preserve the original GitBook ten-page private backup. **Do not connect the backup to Git Sync.** The primary GitBook space currently contains three imported pages and has an active Git Sync pointed at `main`.
- Confirm CI on the Draft PR is non-production; do not merge to `main` as that would run the existing production-release workflow.
- Record new evidence under `service-inventory.json` and use a separate approval for anything changing grants or reaching external services.

## Step 1 — GitBook

1. Read the current Git Sync repo, base branch, directory, last import and settings directly in GitBook before making a change.
2. Review the risks of **bidirectional** synchronization. The existing primary space was replaced by a three-page import, while the ten prior pages were saved separately.
3. Prepare a private isolated test space if additional synchronization experiments are required. Never use the private backup as a writeback source to the public repository.
4. **STOP for approval** before any reconfiguration, import, export, sync, public site or app-permission adjustment.
5. Verify with a GitBook revision and an exact GitHub commit; log whether files/pages changed and close any leakage risk.

## Step 2 — ChatGPT Codex Connector

1. Check GitHub Installed Apps → **ChatGPT Codex Connector** → Configure, read-only. Confirm the exact repo grant; never assume account-wide installation grants Devobs.
2. Review the existing `docs/AI_DEVKIT.md` and `.github/workflows/ai-code-review.yml` instead of creating a duplicate agent workflow.
3. The repo's AI code review is gated on `DEVOBS_AI_BUDGET_APPROVED` and `OPENAI_API_KEY`. **Do not set these or run inference** under this preparation approval.
4. Request explicit, bounded cost and credential approval before any paid live inference; distinguish skipped checks from completed reviews.

## Step 3 — aictrl.dev

1. Read aictrl organization readiness again. On 2026-10-25 the ready repository was `hamedonassar95/mohammadnassar`, **not Devobs**, with zero published workflows.
2. From the owner's aictrl account, review repository selection and authorize only `hamedonassar95/Devobs` with minimum permissions, **after separate approval**.
3. Require Devobs to appear in aictrl's readiness/task listing; review workflow purpose, writes, external effects and cost before any task run.
4. Do not start workflows as a connectivity smoke test; use read-only readiness first.

## Step 4 — Fly.io

1. Owner reviews installed-app repository access and the Fly account/app list. App installation alone is **not** proof of a hosted Devobs workload.
2. Establish a real deployment requirement and evaluate plan costs, tenancy, data flows and rollback ownership.
3. Propose changes only in a new isolated PR, with static checks first. Deployment, secrets, new app creation and billing all require separate consent.

## Step 5 — Lovable.dev

1. The existing Lovable workspace holds an unrelated invoice app; it must not be reused as Devobs without explicit product authorization.
2. Review project mapping, connector list, expected visibility and repository permissions. No Devobs project was confirmed at the snapshot date.
3. If approved later, build a separate scoped Devobs interface prototype and a dedicated Draft PR; keep provider accounts and customers isolated.
4. No publish, public visibility changes, database enablement or metered services without approval.

## Evidence and sign-off record

| Field | Required for every activation decision |
| --- | --- |
| Provider and project | Exact GitHub repository, app/project and environment |
| Permission scope | Read/write scopes and explicit account owner approval |
| Data handling | Private/public destinations; secrets never in this repository |
| Change surface | Files/settings impacted and rollback or recovery plan |
| Cost ceiling | Known provider quota/pricing and affirmative consent |
| Verification | Timestamped command/run URL, observed result and failure mode |
| Outcome | Approved / blocked / verified with specific boundaries |

Fail closed whenever a setting is missing, an OAuth flow is unfinished, or the reported provider result differs from observed behavior. No approval is implied by this read-only inventory PR.

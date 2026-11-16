# Portfolio public CI observer — 2026-11-16

**Feature status: Manual CLI / read-only / public metadata only.** This is not a hosted dashboard, cross-repository deployment, authenticated connection, private repository monitoring, production readiness, or a replacement for the existing Devobs-only browser [public CI reader](PUBLIC_CI_READER.md).

## Evidence-first inventory

GitHub's linked account listing returned **26 repositories** under the account during the review. It included **21 public and 5 private** repositories. The inventory includes copied/forked upstream projects, training exercises, independent products, and Devops-related repositories; do **not** assume ownership of third-party licenses, common organization control, deploy eligibility, or permission to share their private data.

Existing Devobs capability inventory already includes [six inactive integration candidates](../portfolio/PORTFOLIO_FREE_READINESS.md), seven synthetic [portfolio converter namespaces](PORTFOLIO_ACCEPTANCE.md), and separate adapters for CloudEvents, Alertmanager and Grafana. These are **not live cross-repo connections**. No other repository's source code, customer records, media, logs, env files, credentials or API tokens are copied into Devobs.

The new observer covers **four verified public repos only** with `.github/workflows/ci.yml` present on their default `main` branches:

| Source | Verified public CI file | Why selected |
| --- | --- | --- |
| [Devobs](https://github.com/hamedonassar95/Devobs) | `.github/workflows/ci.yml` | Existing central DevOps project |
| [devobs-saas](https://github.com/hamedonassar95/devobs-saas) | `.github/workflows/ci.yml` | Separate tenant-oriented SaaS project |
| [LiveOps-Integration](https://github.com/hamedonassar95/LiveOps-Integration) | `.github/workflows/ci.yml` | Separate content-production integration |
| [ops](https://github.com/hamedonassar95/ops) | `.github/workflows/ci.yml` | Separate infrastructure/console project |

**The other 22 repositories are not queried by this tool.** In particular, private repos are excluded entirely. Nothing tries to discover undocumented source URLs, secrets or non-public build results.

## How to run (manual, on a trusted machine)

From the Devobs checkout using Node.js 24:

```sh
node scripts/portfolio_public_ci.mjs
node --check scripts/portfolio_public_ci.mjs
node --test tests/portfolio_public_ci.test.mjs
```

The CLI has **no arguments**. It makes **eight anonymous GET requests** at most in a successful full run: one public branch lookup and one latest push CI workflow-run lookup for each of four fixed repositories. It does not set credentials, use webhooks, save raw responses, start services, or poll. Browser and account rate limits may apply. API reads are performed only when the operator invokes the CLI; tests inject synthetic HTTP responses and make **zero network requests**.

- `status=success` means GitHub returned a completed **push CI** result matching the observed `main` SHA for that repository, not that a cloud application is healthy.
- `failure`, `cancelled`, `timed_out`, `neutral`, `skipped`, and `action_required` reflect GitHub's supported conclusions.
- `stale` means the latest run does **not** match the observed branch head; this is never shown as an up-to-date pass.
- `pending` or `running` means no completed conclusion.
- `missing` means GitHub reported no such workflow run; no success is invented.
- `unverified` means a response failed to verify, was unavailable or rate-limited. The CLI exits **1** if any repository is unverified, **0** if all returned structurally verified states, and **2** on invalid invocation. Exit 0 does **not** mean all CIs passed.

The parser checks repository ownership, `private=false`, workflow path, push event, branch, 40-character SHA, status/conclusion, redirected responses and bounded JSON (64 KiB). Results contain public repository names, branch heads, run hashes/IDs and status only; never log bodies, names of jobs, private data or source files. The latest branch commit can change after observation, so this is a **point-in-time view**, not strong attestation or an authenticated webhook.

Official GitHub REST references: [Get a branch](https://docs.github.com/en/rest/branches/branches#get-a-branch) and [List workflow runs for a workflow](https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-workflow).

## Next gate

Review one chosen additional repository's explicit source license, CI contract, owner consent and expected data fields before extending the allowlist or adding a service-side adapter. Any authenticated or private-repository integration requires a separate least-privilege design, no secret copying, privacy approval, and exact-SHA PR review. Do not automatically merge, deploy or run incident response based on the observer's status.

P01 remains **BLOCKED / NO-GO**, AI-9 remains **BLOCKED**, and Codex runtime acceptance stays **OPEN**. An account listing or passing CI does not establish production SaaS readiness.

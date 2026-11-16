# Portfolio public CI observer — 2026-11-16

**Feature status: Manual CLI plus optional static browser view / read-only / public metadata only.** This is not an authenticated or continuously hosted dashboard, cross-repository deployment, authenticated connection, private repository monitoring, production readiness, or a replacement for the existing Devobs-only browser [public CI reader](PUBLIC_CI_READER.md).

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

## Browser view (manual, public only)

The existing [public CI webpage](https://hamedonassar95.github.io/Devobs/assets/public-ci/) now includes a second, opt-in **فحص المشاريع الأربعة** button. No additional HTTP requests occur when loading the page. A click fetches four public repositories using the **same browser-compatible normalization module** as the CLI, displays each repository's confirmed CI state or `unverified` separately, and never writes to GitHub. The existing Devobs-only CI CloudEvents export is unchanged; the **separate** portfolio export described below now supports a manual four-project local AI-7 handoff. Pages publishing and new UI availability remain unverified until exact-head CI and a post-merge deployed-site smoke test pass.

The page retains a strict GitHub-only Content Security Policy; no user-provided repository URLs, credentials, free-form HTML or raw GitHub responses are accepted or rendered. The app uses `textContent`, does not request private repositories, never polls, and does not claim a public CI pass is a production health signal. Test behavior is exercised using fake DOM and synthetic HTTP responses in `tests/public_portfolio_browser.test.mjs`.

## One-command GitHub public CI → AI-7 (manual, no files or credentials)

From a trusted checkout with Node.js 24, explicitly run:

```sh
node scripts/portfolio_ci_ai7_live.mjs
node --test tests/portfolio_ci_ai7_live.test.mjs
```

This **manual alternative to the download-then-import route** reuses the existing fixed allowlist HTTP client, the existing public-CI CloudEvents exporter, the existing AI-1 adapter and the actual AI-7 local snapshot. It is not a daemon, browser-side AI inference, deployment action or privileged connector. No repo code, job logs, authentication data or file content are read; the four fixed public repositories receive a maximum of eight anonymous GitHub REST GETs per explicit run. Results are only public metadata.

The output clearly separates each repository's *observed CI status* from whether it supplied eligible evidence to AI-7. A completed and matching CI result can be a failure and still count as **eligible evidence**; `complete_observation` means all four observations qualified, **not** that all CIs passed. Partial/none output is labeled `partial_observation`/`no_eligible_evidence` and exits **1**. An invalid invocation/provider contract exits **2**; complete observations exit **0**. Rate limits, missing run-attempt/time, stale CI, unverified source and nonterminal status never silently count as complete. Tests inject synthetic HTTP responses; tests do **not** hit GitHub.

The AI-7 output contains no fabricated AI-3 root cause or AI-4 recommendation when only CI conclusions are available. This is a point-in-time, **unauthenticated public** observation, not signed provenance, production health, tenancy or paid-model capability. No scripts, workflow runs, deployments or repairs are triggered remotely.

## Manual CI → CloudEvents → AI-7 handoff (no inference or cloud changes)

**End-to-end feature:** after clicking **فحص المشاريع الأربعة** in the existing static [public CI viewer](https://hamedonassar95.github.io/Devobs/assets/public-ci/), a second button **تنزيل أحداث CI لتحليل AI-7 المحلي** can download `devobs-portfolio-ci.cloudevents.jsonl`. No extra network request is made to download. The browser exports only **completed, current main-SHA-matched** CI results with a verified positive run ID, run attempt and valid GitHub creation timestamp. Missing attempt/time, stale, pending, unavailable, unsupported, and unverified results are **excluded**, never invented. The screen says how many eligible events were exported out of four; a partial export is not full project coverage.

Run the *existing AI-1 conversion* and *real AI-7 snapshot algorithm* locally (Node.js 24, from the repository checkout) without starting any server or writing any data:

```sh
node scripts/portfolio_ci_ai7.mjs --input /path/to/devobs-portfolio-ci.cloudevents.jsonl
```

This manual CLI validates CloudEvents against the existing `cloudevents_ci_adapter`, checks only the four reviewed public project namespaces, feeds normalized records into the actual `buildDashboardSnapshot` function, and outputs a small **non-sensitive JSON summary** (per-project CI conclusion, total CI observations, failed/timed-out count, seven AI stages, and the true local recommendation count). It makes **zero HTTP requests and no writes**. It does not trust CloudEvents' self-declared `source` as authenticated provenance: download from the reviewed page; review your local file first. Never ingest private job logs, environment variables, secrets, or paid-model output here.

To **persist a local AI-1 store for the optional AI-7 dashboard**, use the already existing documented two-stage process (in a private temporary directory outside Git):

```sh
export DEVOBS_CI_EXPORT_DIR="$(mktemp -d)"
node scripts/integrations/cloudevents_ci_adapter.mjs --input /path/to/devobs-portfolio-ci.cloudevents.jsonl > "$DEVOBS_CI_EXPORT_DIR/ai1.jsonl"
node scripts/ai_intelligence/event_ingest.mjs --input "$DEVOBS_CI_EXPORT_DIR/ai1.jsonl" --store "$DEVOBS_CI_EXPORT_DIR/events.jsonl"
node scripts/ai_intelligence/dashboard_server.mjs --store "$DEVOBS_CI_EXPORT_DIR/events.jsonl" --port 8765
```

**Interpretation:** CI conclusions alone are **not error logs or RCA evidence**. It is correct for AI-2 to show `no_metrics`, AI-3 `no_logs`, and AI-4 `no_matches`; the tool must **not fabricate** a cause, incident prediction, anomaly or runbook. An actual diagnosis requires a **separate, privacy-reviewed** source of logs/metrics and human approval before any repair, PR, production change or deployment. This does not alter AI-9, P01 cost, hosted authentication, paid services or runtime acceptance.

Validation commands (offline synthetic fixtures, no GitHub API):

```sh
node --check assets/public-ci/portfolio-export.mjs
node --check scripts/portfolio_ci_ai7.mjs
node --test tests/portfolio_ci_ai7_handoff.test.mjs tests/public_portfolio_browser.test.mjs tests/portfolio_public_ci.test.mjs
```

The handoff test covers four distinct CI runs through the existing converter, the **real AI-1 event store** with replay de-duplication, and AI-7's actual calculated snapshot, plus rejected, stale and partial evidence. The static site checks require the new export module and button. Existing Devobs-only CI export is unchanged.

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

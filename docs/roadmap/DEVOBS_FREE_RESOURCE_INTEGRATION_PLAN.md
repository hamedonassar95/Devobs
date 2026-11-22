# Devobs free-resource and open-source integration plan (2026-11-23)

Status: **PLAN ONLY — NOT ACTIVATED.** No account, token, secret, paid tier,
scheduled job, hosted resource or deployment was created. Every provider claim
below is linked to its official page; re-verify limits at activation time
because free tiers change. This plan does not change P01/AI-9/Codex gates.

## 1. Guardrails

- Free tier first; no paid plan, card, overage or billable AI inference.
- No secret in Git, chat, logs or docs. Provider credentials stay owner-managed.
- No production data, customer data, hosted IdP or cloud resource is touched.
- Every activation is a separate owner decision naming the provider, scope,
  cost ceiling and exact reviewed SHA.
- Local/offline evidence is never treated as hosted proof.
- Open-source adoption requires a license check from the upstream `LICENSE`
  before adding a dependency; links below are documentation, not legal advice.

## 2. Verified free-tier matrix (official sources)

| Provider | Free allowance (as published) | Fit for Devobs | Official source |
|---|---|---|---|
| GitHub Free | 2,000 Actions minutes/month for private repos; free minutes for public repos; 500 MB artifact storage; 10 GB cache per repo | CI, CodeQL, Dependabot, Pages, GHCR | [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [Actions limits](https://docs.github.com/en/actions/reference/limits), [plans](https://github.com/pricing) |
| GitHub Pages | Static hosting for public repositories | Public docs/status site | [Pages docs](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) |
| GitHub Packages / GHCR | Free for public packages | Container images for public builds | [Packages billing](https://docs.github.com/en/packages/learn-github-packages/about-github-packages#about-billing-for-github-packages) |
| Cloudflare Pages | 500 builds/month, 1 concurrent build; static requests not metered like Functions | Static console/docs preview | [Pages limits](https://developers.cloudflare.com/pages/platform/limits/) |
| Cloudflare Workers | 100,000 requests/day, 10 ms CPU/invocation, 128 MB memory, 64 MiB bundle | Lightweight edge health/redirect API only | [Workers limits](https://developers.cloudflare.com/workers/platform/limits/), [pricing](https://developers.cloudflare.com/workers/platform/pricing/) |
| Supabase Free | 500 MB Postgres per project, 1 GB file storage, 2 active projects; **no automatic backups** | Staging Postgres with RLS experiments | [pricing](https://supabase.com/pricing), [storage pricing](https://supabase.com/docs/guides/storage/pricing) |
| Neon Free | 100 projects, 1 GB Postgres/project, 20 GB account total, 100 CU-hours/project, scale-to-zero after 5 min, 6-hour history; no card | Disposable per-tenant/RLS test databases | [pricing](https://neon.com/pricing) |
| Render Hobby | $0 workspace + free compute; 25 services, 5 GB bandwidth, 500 build minutes; free web 512 MB, free Postgres 256 MB/100 connections, free Key Value 25 MB | Staging API/console, not production | [pricing](https://render.com/pricing), [free docs](https://render.com/docs/free) |
| Grafana Cloud Free | 10,000 active series, 50 GB logs, 50 GB traces, 50 GB profiles, 3 users, 14-day retention, no card | Remote observability for OTLP/metrics/logs | [pricing](https://grafana.com/pricing/), [free tier](https://grafana.com/products/cloud/free-tier/) |
| Sentry Developer | Free, 1 user, 5k errors, 5 GB logs, 5 GB app metrics, 5M spans, 50 replays, 1 uptime monitor, 30-day lookback | Error/trace intake for API and console | [pricing](https://sentry.io/pricing/) |

Limits are **VERIFIED from the linked pages on 2026-11-23** but remain
provider-controlled. Anything not listed here is UNVERIFIED and must not be
assumed free.

## 3. Open-source component matrix

| Component | Role | Integration point | License check |
|---|---|---|---|
| Keycloak | OIDC issuer, PKCE, JWKS for local/staging | `scripts/devobs_intelligence/oidc_tokens.py` | Apache-2.0 (verify `LICENSE`) |
| PostgreSQL | RLS, tenant isolation | `deploy/postgres/*.sql` | PostgreSQL License |
| OpenTelemetry Collector | Vendor-neutral traces/metrics/logs | existing OTLP bridge | Apache-2.0 |
| Prometheus + Alertmanager | Local metrics/alerting | `monitoring/compose.yml` | Apache-2.0 |
| Grafana OSS / Loki / Tempo | Local dashboards/logs/traces | `monitoring/compose.yml` | AGPL-3.0 (verify) |
| Trivy | Container/filesystem/IaC scanning | CI `security` job | Apache-2.0 |
| CodeQL | Static analysis | GitHub Actions | free for public repos; verify terms |
| Renovate or Dependabot | Dependency update automation | GitHub App/Actions | Renovate AGPL-3.0; Dependabot GitHub-native |
| Uptime Kuma | Self-hosted uptime/status page | local compose only | MIT |
| Langfuse (self-host) | LLM/agent trace observability | optional AI observability | verify upstream `LICENSE` |
| Ollama (local) | Local open-weight models | optional offline AI, no billable API | MIT (verify) |
| Gitea/Forgejo | Self-hosted Git mirror (optional) | not required for GitHub flow | MIT / GPL-3.0 (verify) |

## 4. Gap → free/open-source mapping

| Confirmed gap | Free-first solution | Acceptance evidence | Phase |
|---|---|---|---|
| Hosted OIDC/JWKS proof | Keycloak local + owner-approved disposable runtime | HTTPS discovery + public JWKS preflight; no token issuance | P0 (owner) |
| Hosted RLS denial proof | Neon/Supabase staging Postgres + existing RLS SQL | cross-tenant query denied under two synthetic roles | P0 (owner) |
| Live observability/SLO | OTel Collector → Grafana Cloud free | one metric, one log, one trace visible; 14-day retention noted | P1 (owner) |
| Error tracking | Sentry Developer free | one synthetic error and one trace with release tag | P1 (owner) |
| Uptime/status | Uptime Kuma self-hosted | local monitor + status page; no public exposure | P1 (local) |
| Dependency drift | Renovate/Dependabot | PR opened for one pinned action/dependency | P1 (owner) |
| Static previews | Cloudflare Pages or GitHub Pages | preview build from a non-main branch | P1 (owner) |
| AI observability | Langfuse self-host + local Ollama | trace of an offline run; no paid inference | P2 (owner) |
| Governance drift | already resolved upstream by #750 | ledger `latest_pr:747`, 305 milestones | DONE upstream |

## 5. Phased backlog

**P0 — correctness and security (no new provider account)**
1. Merge the reviewed D1 repair after hosted CI passes on the exact SHA.
2. Run the owner-approved disposable Keycloak discovery/JWKS preflight.
3. Prove RLS denial on a disposable staging Postgres.
4. Keep all gates BLOCKED until evidence is attached to a reviewed SHA.

**P1 — free managed observability and delivery**
5. Add OTLP export to a Grafana Cloud free stack (owner-created, secret in
   provider UI only).
6. Add Sentry DSN through the provider UI; never commit it.
7. Self-host Uptime Kuma locally for status evidence — **local opt-in
   profile added** in `monitoring/compose.yml` (`--profile uptime`,
   `127.0.0.1:3001`, digest-pinned, persistent volume; not started).
8. Enable Renovate or Dependabot for pinned actions/dependencies.

**P2 — optional, only with a separate scope decision**
9. Self-host Langfuse for agent traces.
10. Evaluate local Ollama models; no paid API.
11. Evaluate Gitea/Forgejo mirror; not required for GitHub flow.

## 6. What this pass did and did not do

- DID: verify official free-tier limits, map gaps to free/open-source options,
  record phases and acceptance evidence, preserve all existing gates; add an
  offline, opt-in Uptime Kuma profile with digest pinning and a contract test
  that enforces loopback-only ports and pinned images for the whole stack.
- DID NOT: create accounts, tokens, DSNs, webhooks, workflows, scheduled jobs,
  paid resources, cloud resources or deployments; start Uptime Kuma or any
  container; change P01/AI-9/Codex gates; merge to `main`.
- Next executable step without credentials: owner creates the Draft PR from
  `feature/devobs-production-recovery`, lets hosted CI run, and records the
  exact SHA. Then the reviewed repair can be merged under the repo's human gate.

**PENDING HUMAN APPROVAL**

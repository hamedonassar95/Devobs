# Devobs — Priority remediation roadmap (advisory, from audit)

Source audit: [DEVOBS_FULL_GAP_AUDIT.md](../audits/DEVOBS_FULL_GAP_AUDIT.md), SHA `10f8dd9b1e884e16cea3ffd847cf20405794cb8b`. Machine-readable task list: [DEVOBS_IMPLEMENTATION_BACKLOG.json](DEVOBS_IMPLEMENTATION_BACKLOG.json). Nothing in this roadmap authorizes a merge, deploy, spend, provider action or gate promotion. Each task is independently executable on its own feature branch/worktree with a Draft PR and no merge.

## P0 — immediate security, data-loss or deadline risks (evidence-backed)

| ID | Risk / task | Evidence | Owner decision required |
| --- | --- | --- | --- |
| P0-1 | Maintain P01 NO-GO; collect 8 hosted acceptances (SPEND, PROVIDER, OIDC, RLS, TLS_NETWORK, BACKUP, OWNER, RELEASE) on one reviewed SHA | `docs/p01/P01_NO_GO_DECISION_2026-11-19.md:7-16`; all BLOCKED | Exact-SHA, exact-scope owner approval for each hosted test |
| P0-2 | Render Free PostgreSQL expiry 2026-12-05 — obtain preserve-or-retire decision; no delete/upgrade/export | `docs/p01/render-free-expiry-snapshot.json`; fresh `check_render_free_expiry.py --json` `REVIEW_REQUIRED` exit 1; `docs/plans/2026-11-19-render-free-postgres-retirement-plan.md:3,13` | Decision naming resource ID, action, UTC window; no standing permission |
| P0-3 | Backup/restore: encrypted hosted backup + isolated restore with observed RPO/RTO | `docs/p01/p01-no-go-matrix-2026-11-19.json:44-49`; `docs/ENTERPRISE_OPERATIONS.md:55-60` | Backup product + staging approval |
| P0-4 | Spend control: keep `DEVOBS_AI_BUDGET_APPROVED=false`; produce enforced combined USD cap evidence; add token/USD accounting | `render.yaml:19-24`; `agent-spec.yaml:4-10`; `docs/P01_RENDER_BUDGET_ENVELOPE.md:3-21` | Finance/provider configuration; no USD activation without approval |
| P0-5 | AI-9: obtain 7 controls with exact SHA/reviewer/HTTPS evidence; keep BLOCKED | `docs/ai9/evidence.json` 7/7 UNVERIFIED; `check_ai9_evidence.py` auto-GO forbidden | Independent evaluation owner/reviewer |
| P0-6 | Render network exposure: restrict `0.0.0.0/0` allowlist before any startup fix | `docs/DEVOBS_READINESS_CURRENT.md:172-173` | Owner provider-network change |
| P0-7 | Do not treat DRY_RUN dispatch/config as agent runtime; complete Codex/MCP runtime acceptance | Ledger `codex-agent-runtime-acceptance: OPEN`; `agent_dispatch_preflight.py` | Trusted client + harmless public docs lookup; keep gate OPEN until evidence |
| P0-8 | Define SLOs/error budgets and burn-rate alerts before production claims | `monitoring/*` has host alerts only; SLO terms docs-only | Owner SLO targets |

## P1 — blocking production readiness, isolation, CI reliability or approval controls

| ID | Task | Evidence | Notes |
| --- | --- | --- | --- |
| P1-1 | Hosted OIDC + RLS negative-tenant test at reviewed SHA | `oidc_tokens.py:29-96`, `001_tenant_rls.sql:4-56`; historical `invalid_staging_config stage=oidc` | Redacted evidence only |
| P1-2 | Fix V-01 review-count policy (writer could merge after checks without approver) | `docs/security/DEVOBS_SECURITY_REVIEW_2026-11-16.md:38,80-82` | Separate reviewed PR; keep ruleset minimal |
| P1-3 | Implement runtime wheel-hash verification (F04) | `docs/audits/DEVOBS_RECOVERY_AUDIT.md:63` | Do not weaken CI |
| P1-4 | Complete WIF preflight (provider/audience/trust, firewall fix dispatch) | `docs/VERTEX_AI_FALLBACK.md:206-261` | No `gcloud` in agent environment; owner runs Cloud Shell |
| P1-5 | Extend rollback to hosted stack + DB (currently Pages only) | `docs/RELEASE_ROLLBACK.md:1-87` | Restore evidence required |
| P1-6 | Add adversarial prompt-injection tests for provider adapters | adapter system prompts + strict schema only | Behavioral, not string checks |
| P1-7 | Update remaining medium multi-agent audit findings (AUD-01/03/04/05/12) at current SHA; AUD-02 already fixed in `37475b0` (#732) | `docs/audits/TWO_AGENT_SECURITY_AUDIT_2026-11-21.md`; `git merge-base --is-ancestor 37475b0 origin/main` → 0 | Add regressions |
| P1-8 | Human triage of the 1 HIGH Dependabot alert; no audit suppression | `STATE.md:40` | Owner-authenticated security tab |
| P1-9 | Decide on merging the offline provider evaluation harness from `feature/ai-provider-evaluation-finalization` (`7dff0c0`) | 16 tests on that branch; 0 open PRs at audit time | Owner merge decision; do not duplicate work |
| P1-10 | Trace one release end-to-end to prove CI/Pages/Vercel shared-artifact claim | `ci.yml:415-486` | Until traced: UNVERIFIED |
| P1-11 | Document per-panel synthetic/live labeling decision and English LTR approach | `index.html:2`, `App.tsx:448` | UX, no security authority |

## P2 — missing platform functionality, observability, AI ops, dashboard

Billing/metering design (no implementation), tenant lifecycle/retention/export/delete, hosted audit anchoring, a11y behavioral tests, per-panel source badges, read-only approval-queue view, application-level alert rules, K8s/Terraform apply design (never in CI), OWASP abuse-case tests, zizmor/Scorecard report review, CodeQL config verification, provider failover documentation.

## P3 — optional enhancements

Graphify/Plannotator optional integrations, Pulumi/Azure readiness work, UX polish beyond LTR/badges, future creative media workflows. All require separate scope approval; none affects a gate.

## Estimated implementation phases (advisory sequencing, no auto-execution)

1. **Phase A — decisions (P0-1..P0-8):** owner decisions on P01 evidence, database deadline, backup product, spend cap, AI-9 corpus, network allowlist, runtime acceptance, SLOs. No code changes required to start.
2. **Phase B — independent P1 patches:** one feature branch/worktree each, Draft PRs only; keep CI, CodeQL, Trivy, RLS and Phase 8 human gate intact; no batch merge.
3. **Phase C — P2 platform work:** billing/retention/observability/UX, after Phase A decisions establish requirements.
4. **Phase D — P3 optional:** only after owner prioritization and budget disclosure.

## Avoid

Unnecessary rewrites or new frameworks; duplicating merged work (`ai_quality_gate`, `integration_control`, offline evaluation harness on its unmerged branch); adding redundant scanning pipelines; enabling paid inference; touching `main` directly; Terraform apply/destroy; Keycloak runtime before activation conditions; any destructive provider action.

## Compliance reminder

`AGENTS.md` requires: small reviewable commits, VERIFIED/UNVERIFIED labeling, official doc quotes for flags/APIs, behavioral tests over string checks, fail closed, no secrets, pinned Actions with comments, minimal permissions, shared staging step, Draft PR only on request, no merge/deploy without exact-SHA owner approval, and ledger/state reconciliation after merges. This roadmap complies by producing analysis and tasks only.

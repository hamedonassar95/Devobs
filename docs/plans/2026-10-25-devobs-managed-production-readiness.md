# DevObs AI Intelligence 2027 Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reach verifiable, security-reviewed managed staging before a separately approved commercial production release.

**Architecture:** Keep GitHub/Codex for source and reviewed CI; Render is the proposed managed Python WSGI runtime and Supabase a proposed managed PostgreSQL provider. Reuse the existing signed access-token validator, tenant-restricted Postgres adapter, offline correlation engine and gated CI. Never treat human-review-only reasoning as execution authority.

**Tech Stack:** Python 3.12, gunicorn, PostgreSQL 17+ with FORCE RLS, Supabase managed Postgres, Render managed web service, OIDC/JWKS, GitHub Actions and unittest.

## Global Constraints

- Canonical source `hamedonassar95/Devobs`, branch `plan/devobs-intelligence-2027-execution-20261025`, protected `main` unchanged by this plan.
- Reviewable PRs and passing exact-SHA CI and security checks are prerequisites, not optional. The existing `production-release` GitHub Pages job may publish after a main push.
- No account/service creation, production publishing, paid services, DB migration or secret setting without independently approved operator action and evidence.
- Preserve Level 0 read-only safe behavior. Do not grant model output execution rights, shell access or access to tenant data from unauthenticated headers.
- Supabase Postgres runtime must use a restricted, non-owner, non-BYPASSRLS role, and valid TLS configuration. OIDC documents must come from a separately authenticated provider.

## Verified execution snapshot (2026-10-25; read-only provider checks)

- Current `main`: `85956696df6f8722e2c8d7d1d88f7a03653c2d56`, merged through PR #245. AI roadmap PRs #213/#216/#218/#219 are merged at `b93f4de`/`a060412`/`d9adfb0`/`35108f1` respectively. The merge commit links are recorded in the AI core and gap-execution documents.
- Latest observed main CI: run [40216497498](https://github.com/hamedonassar95/Devobs/actions/runs/40216497498), exact head `85956696df6f8722e2c8d7d1d88f7a03653c2d56`; `validate`, Python validation, security scans, PostgreSQL RLS integration, Pages publish and production verification succeeded. Node tests were skipped. This proves the static Pages publication path for that SHA, not a hosted AI service.
- Deployment triggers: pull requests run validation and upload a short-lived downloadable site artifact; `production-release` requires a successful `validate` job and a push to `main`. The separate `one-click-deploy` is manually dispatched and can deploy only after explicit `confirm_deploy`, candidate/rollback validation and quality CI. The Vercel staging workflow is manual and requires configured environment credentials; the connected Vercel account returned no project linked to `hamedonassar95/Devobs`, so a Vercel staging run is not evidenced.
- Active `Protect main` ruleset `24507159` requires a pull request and the `validate` check, prohibits deletion/non-fast-forward, and configures CodeQL alert thresholds. Its required approval count is **0**, so independent human review is not enforced by this ruleset ([GitHub documents zero as the minimum and treats approvals as optional at zero](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)). The current CodeQL analysis result was not verified. P00 T04 remains blocked until an authorized owner changes/reviews that policy; this work does not alter repository settings.
- Connected-account discovery returned no GitLab Devobs project and no Devobs Supabase project; the visible Supabase project belongs to Phone Repair Assistant v2. No environment variables, secrets, database contents, or deployment settings were read or changed.
- Local candidate on `fix/devobs-audit-atomic-append` adds an atomic SQLite audit append fix; its focused synthetic unit suite passed 10/10. It is not pushed and has not passed full repository CI or CodeQL. SQLite transaction behavior follows the official [Python sqlite3 transaction documentation](https://docs.python.org/3/library/sqlite3.html#transaction-control) and [SQLite transaction documentation](https://www.sqlite.org/lang_transaction.html).

**P00 disposition:** T01 inventory is prepared in [`docs/AI_DEVOPS_2027_BASELINE.md`](../AI_DEVOPS_2027_BASELINE.md); T02 merge-state reconciliation is prepared locally; T03 trigger paths and T05 the exact-SHA CI baseline are documented above. T04 is blocked by the zero-review rule and unverified CodeQL analysis. T06 remains open pending named cost, privacy, and staging owners. The GitHub issue remains open; none of these items is marked complete until its required reviewed PR and exact-SHA CI/security evidence exist.

---

## Execution sequence and interface boundaries

### P00: Baseline and release safety

**GitHub epic:** [#220](https://github.com/hamedonassar95/Devobs/issues/220) — 6 independently testable acceptance items.

- [ ] Add focused failure/deny tests; use synthetic fixtures and reject wrong identity, tenant and stale evidence.
- [ ] Implement the minimum reviewed branch change; expose no unapproved write/production interface.
- [ ] Execute focused tests, affected integration tests, full CI `validate`, security/CodeQL on the exact head SHA; link outputs in the issue.
- [ ] Where infrastructure is necessary, use a separately authorized staging tenant with real TLS/identity/restore proofs; without it keep the stage blocked.
- [ ] Open a reviewed PR and only mark the issue complete after every acceptance criterion is proven.

### P01: Managed staging (Render + PostgreSQL + OIDC)

**GitHub epic:** [#221](https://github.com/hamedonassar95/Devobs/issues/221) — 9 independently testable acceptance items.

- [ ] Add focused failure/deny tests; use synthetic fixtures and reject wrong identity, tenant and stale evidence.
- [ ] Implement the minimum reviewed branch change; expose no unapproved write/production interface.
- [ ] Execute focused tests, affected integration tests, full CI `validate`, security/CodeQL on the exact head SHA; link outputs in the issue.
- [ ] Where infrastructure is necessary, use a separately authorized staging tenant with real TLS/identity/restore proofs; without it keep the stage blocked.
- [ ] Open a reviewed PR and only mark the issue complete after every acceptance criterion is proven.

### P02: Live OpenTelemetry

**GitHub epic:** [#222](https://github.com/hamedonassar95/Devobs/issues/222) — 6 independently testable acceptance items.

- [ ] Add focused failure/deny tests; use synthetic fixtures and reject wrong identity, tenant and stale evidence.
- [ ] Implement the minimum reviewed branch change; expose no unapproved write/production interface.
- [ ] Execute focused tests, affected integration tests, full CI `validate`, security/CodeQL on the exact head SHA; link outputs in the issue.
- [ ] Where infrastructure is necessary, use a separately authorized staging tenant with real TLS/identity/restore proofs; without it keep the stage blocked.
- [ ] Open a reviewed PR and only mark the issue complete after every acceptance criterion is proven.

### P03: Topology and incident memory

**GitHub epic:** [#223](https://github.com/hamedonassar95/Devobs/issues/223) — 6 independently testable acceptance items.

- [ ] Add focused failure/deny tests; use synthetic fixtures and reject wrong identity, tenant and stale evidence.
- [ ] Implement the minimum reviewed branch change; expose no unapproved write/production interface.
- [ ] Execute focused tests, affected integration tests, full CI `validate`, security/CodeQL on the exact head SHA; link outputs in the issue.
- [ ] Where infrastructure is necessary, use a separately authorized staging tenant with real TLS/identity/restore proofs; without it keep the stage blocked.
- [ ] Open a reviewed PR and only mark the issue complete after every acceptance criterion is proven.

### P04: Evaluation and KPIs

**GitHub epic:** [#224](https://github.com/hamedonassar95/Devobs/issues/224) — 5 independently testable acceptance items.

- [ ] Add focused failure/deny tests; use synthetic fixtures and reject wrong identity, tenant and stale evidence.
- [ ] Implement the minimum reviewed branch change; expose no unapproved write/production interface.
- [ ] Execute focused tests, affected integration tests, full CI `validate`, security/CodeQL on the exact head SHA; link outputs in the issue.
- [ ] Where infrastructure is necessary, use a separately authorized staging tenant with real TLS/identity/restore proofs; without it keep the stage blocked.
- [ ] Open a reviewed PR and only mark the issue complete after every acceptance criterion is proven.

### P05: Tamper-evident audit

**GitHub epic:** [#225](https://github.com/hamedonassar95/Devobs/issues/225) — 5 independently testable acceptance items.

- [ ] Add focused failure/deny tests; use synthetic fixtures and reject wrong identity, tenant and stale evidence.
- [ ] Implement the minimum reviewed branch change; expose no unapproved write/production interface.
- [ ] Execute focused tests, affected integration tests, full CI `validate`, security/CodeQL on the exact head SHA; link outputs in the issue.
- [ ] Where infrastructure is necessary, use a separately authorized staging tenant with real TLS/identity/restore proofs; without it keep the stage blocked.
- [ ] Open a reviewed PR and only mark the issue complete after every acceptance criterion is proven.

### P06: Model governance

**GitHub epic:** [#226](https://github.com/hamedonassar95/Devobs/issues/226) — 5 independently testable acceptance items.

- [ ] Add focused failure/deny tests; use synthetic fixtures and reject wrong identity, tenant and stale evidence.
- [ ] Implement the minimum reviewed branch change; expose no unapproved write/production interface.
- [ ] Execute focused tests, affected integration tests, full CI `validate`, security/CodeQL on the exact head SHA; link outputs in the issue.
- [ ] Where infrastructure is necessary, use a separately authorized staging tenant with real TLS/identity/restore proofs; without it keep the stage blocked.
- [ ] Open a reviewed PR and only mark the issue complete after every acceptance criterion is proven.

### P07: Scoped actions and approvals

**GitHub epic:** [#227](https://github.com/hamedonassar95/Devobs/issues/227) — 5 independently testable acceptance items.

- [ ] Add focused failure/deny tests; use synthetic fixtures and reject wrong identity, tenant and stale evidence.
- [ ] Implement the minimum reviewed branch change; expose no unapproved write/production interface.
- [ ] Execute focused tests, affected integration tests, full CI `validate`, security/CodeQL on the exact head SHA; link outputs in the issue.
- [ ] Where infrastructure is necessary, use a separately authorized staging tenant with real TLS/identity/restore proofs; without it keep the stage blocked.
- [ ] Open a reviewed PR and only mark the issue complete after every acceptance criterion is proven.

### P08: Recovery and backup

**GitHub epic:** [#228](https://github.com/hamedonassar95/Devobs/issues/228) — 5 independently testable acceptance items.

- [ ] Add focused failure/deny tests; use synthetic fixtures and reject wrong identity, tenant and stale evidence.
- [ ] Implement the minimum reviewed branch change; expose no unapproved write/production interface.
- [ ] Execute focused tests, affected integration tests, full CI `validate`, security/CodeQL on the exact head SHA; link outputs in the issue.
- [ ] Where infrastructure is necessary, use a separately authorized staging tenant with real TLS/identity/restore proofs; without it keep the stage blocked.
- [ ] Open a reviewed PR and only mark the issue complete after every acceptance criterion is proven.

### P09: DevSecOps and compliance

**GitHub epic:** [#229](https://github.com/hamedonassar95/Devobs/issues/229) — 5 independently testable acceptance items.

- [ ] Add focused failure/deny tests; use synthetic fixtures and reject wrong identity, tenant and stale evidence.
- [ ] Implement the minimum reviewed branch change; expose no unapproved write/production interface.
- [ ] Execute focused tests, affected integration tests, full CI `validate`, security/CodeQL on the exact head SHA; link outputs in the issue.
- [ ] Where infrastructure is necessary, use a separately authorized staging tenant with real TLS/identity/restore proofs; without it keep the stage blocked.
- [ ] Open a reviewed PR and only mark the issue complete after every acceptance criterion is proven.

### P10: SaaS and metering

**GitHub epic:** [#230](https://github.com/hamedonassar95/Devobs/issues/230) — 5 independently testable acceptance items.

- [ ] Add focused failure/deny tests; use synthetic fixtures and reject wrong identity, tenant and stale evidence.
- [ ] Implement the minimum reviewed branch change; expose no unapproved write/production interface.
- [ ] Execute focused tests, affected integration tests, full CI `validate`, security/CodeQL on the exact head SHA; link outputs in the issue.
- [ ] Where infrastructure is necessary, use a separately authorized staging tenant with real TLS/identity/restore proofs; without it keep the stage blocked.
- [ ] Open a reviewed PR and only mark the issue complete after every acceptance criterion is proven.

### P11: Reliability and operations

**GitHub epic:** [#231](https://github.com/hamedonassar95/Devobs/issues/231) — 5 independently testable acceptance items.

- [ ] Add focused failure/deny tests; use synthetic fixtures and reject wrong identity, tenant and stale evidence.
- [ ] Implement the minimum reviewed branch change; expose no unapproved write/production interface.
- [ ] Execute focused tests, affected integration tests, full CI `validate`, security/CodeQL on the exact head SHA; link outputs in the issue.
- [ ] Where infrastructure is necessary, use a separately authorized staging tenant with real TLS/identity/restore proofs; without it keep the stage blocked.
- [ ] Open a reviewed PR and only mark the issue complete after every acceptance criterion is proven.

### P12: Controlled pilot and production gate

**GitHub epic:** [#232](https://github.com/hamedonassar95/Devobs/issues/232) — 5 independently testable acceptance items.

- [ ] Add focused failure/deny tests; use synthetic fixtures and reject wrong identity, tenant and stale evidence.
- [ ] Implement the minimum reviewed branch change; expose no unapproved write/production interface.
- [ ] Execute focused tests, affected integration tests, full CI `validate`, security/CodeQL on the exact head SHA; link outputs in the issue.
- [ ] Where infrastructure is necessary, use a separately authorized staging tenant with real TLS/identity/restore proofs; without it keep the stage blocked.
- [ ] Open a reviewed PR and only mark the issue complete after every acceptance criterion is proven.


## Phase 1 proposed interfaces (do not assume live provider setup)

- `scripts/devobs_intelligence/staging_app.py`: `build_app(settings: Mapping[str,str]) -> WSGI callable` consuming operator-supplied issuer, audience, client ID, authenticated metadata and public JWKS, and TLS-verifying Postgres DSN; emits only read-only API + liveness endpoint.
- `render.yaml`: a proposed manually provisioned Staging web service with `autoDeployTrigger: off`, build/start commands and `sync: false` secret placeholders.
- `tests/test_intelligence_staging_app.py`: reject absent/insecure configuration, test health/method paths and unauthenticated access. Real hosted OIDC and Postgres remain separate gates.

**Acceptance:** local/test gate verifies staging code and config shapes; production requires real controlled staging, restore, isolation under load, authenticated OIDC rotation, audit anchoring and independent go-live approval. Do not conflate code review with operational readiness.

## Operator decisions before cloud changes

Region/data residency, Render plan and cost ceiling, Supabase project ownership and backups, dedicated runtime database role and TLS CA, identity provider with RFC 9068-style access tokens, retention/terms, support owner, and production access. None is assumed by a green unit test.

**Docs:** https://render.com/docs/blueprint-spec ; https://supabase.com/docs/guides/database/connecting-to-postgres

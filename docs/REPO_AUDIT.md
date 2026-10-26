# Devobs repository status audit

Audit date: 2026-10-26 (Asia/Amman).
Repository: hamedonassar95/Devobs.
Baseline: `85956696df6f8722e2c8d7d1d88f7a03653c2d56` (main at inspection).
Delivery branch: `audit/repo-status`.
Scope: repository source, selected GitHub CI evidence, open PR inventory and repository ruleset. No production configuration access or operational certification.

## Evidence labels and executive verdict

- **VERIFIED** means directly inspected source or GitHub API/run evidence. Source verification proves implementation exists, not that it is deployed.
- **UNVERIFIED** means external/live behavior or completeness was not established.
- **ASSUMED** marks recommendations, proposed priorities and acceptance criteria.
- **VERIFIED — Not production-ready as a multi-tenant subscription platform:** a static site and substantial repository automation exist, together with a narrow authenticated, tenant-isolated read API. Customer onboarding, subscription billing and a complete tenant lifecycle are absent from the inspected baseline.
- **VERIFIED — Important positive evidence:** PostgreSQL RLS is implemented and 18 integration tests passed in an existing CI run. JWT access-token verification and fail-closed database readiness are implemented. These must not be described as entirely missing.
- **UNVERIFIED:** hosted API readiness, configured identity provider, backup restoration, customer isolation beyond the implemented read path, production SLOs and commercial eligibility.
- **VERIFIED:** only this report is proposed by this audit. Existing source, main, migrations and provider settings were not changed; no terraform apply or deployment was executed by the auditor.

## Method and scope limits

**VERIFIED:** read root [AGENTS.md](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/AGENTS.md). The recursive tree was not truncated and contained 378 files, with only one AGENTS.md. Inspected architecture/auth/storage/approval source, schema, CI and deployment workflows, operational documentation, test inventory and historical job results.
**VERIFIED:** reviewed the latest 50 main-branch workflow runs, the baseline check-runs, selected job steps/log summaries, and all six open PRs returned at inspection.
**VERIFIED:** an attempted local clone via the available Git proxy failed with "could not read Username"; no credentials were requested or read. Repository inspection and delivery use the authenticated GitHub connector.
**UNVERIFIED:** this is not an exhaustive penetration test, full historical incident review, dependency-license clearance, live cloud audit or full line-by-line review of every generated workflow.
**VERIFIED:** tests reported below are existing GitHub executions, not newly run by this audit. No local suite was run, especially the PostgreSQL integration suite that creates a disposable schema. Provider environments, secrets and deployment settings were not read.
**ASSUMED:** missing-feature findings mean no implementation was found in the baseline tree and reviewed entrypoints/schema; external systems or unmerged branches may add functionality.

## 1. Project structure and technologies

| Path / component | Observed state | Evidence |
| --- | --- | --- |
| index.html, devobs/, examples/al-dala-mobile/ | VERIFIED: static HTML pages/examples; not an authenticated SaaS dashboard | [README](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/README.md), baseline tree |
| scripts/devobs_intelligence/ | VERIFIED: Python intelligence core: contracts, collectors, policy, correlation, advisory, evaluations, tenant stores, OIDC and WSGI API | [API](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/scripts/devobs_intelligence/api_app.py), [adviser](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/scripts/devobs_intelligence/adviser.py) |
| scripts/ | VERIFIED: repository policy checks, incident triage, guarded recovery planning/publishing, GitLab read-only collection and deployment helpers | Baseline tree; [approval gate](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/scripts/human_approval_gate.py) |
| deploy/postgres/ | VERIFIED: PostgreSQL reference schema for a read-only tenant/project status service | [schema](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/deploy/postgres/001_tenant_rls.sql) |
| .github/workflows/ | VERIFIED: CI, security, static publishing, AI workflows, reusable language CI and manual/cloud deployment paths | [CI](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/.github/workflows/ci.yml) |
| tests/ | VERIFIED: Python unittest tests, CommonJS Node guard tests, synthetic evaluation fixtures and PostgreSQL integration tests | [RLS tests](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/tests/test_postgres_rls_integration.py) |
| docs/, .agents/, .claude/ | VERIFIED: extensive runbooks, plans and contributor skills; documentation is not runtime capability | [readiness document](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/docs/PRODUCT_SAAS_READINESS.md) |
| requirements-api.txt, render.yaml | VERIFIED: pinned PyJWT crypto, cryptography, psycopg and Gunicorn dependencies; proposed Python staging process | [dependencies](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/requirements-api.txt), [Render declaration](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/render.yaml) |

**VERIFIED:** no application monorepo apps/packages layout or frontend package manifest was found in the baseline tree. Runtime architecture is static pages plus Python scripts/WSGI, not a delivered customer-facing subscription application.
**UNVERIFIED:** actual cloud resources cannot be inferred from render.yaml or documentation.

## 2. Multi-tenancy and data isolation

**VERIFIED — Existing:**
- [PostgreSQL schema](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/deploy/postgres/001_tenant_rls.sql) has project_ci keyed by (tenant_id, project_id), and memberships keyed by (tenant_id, project_id, subject_id).
- Both tables ENABLE and FORCE RLS. Reader role is NOLOGIN, NOSUPERUSER and NOBYPASSRLS; only SELECT is granted. No application write policies exist.
- Membership policy checks tenant and subject; project policy requires matching tenant plus a membership row.
- [PostgresTenantStore](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/scripts/devobs_intelligence/postgres_store.py) uses parameterized SQL, per-read transactions, transaction-local identity context, timeouts, non-owner/non-bypass checks and exact policy checks. It locks policy tables during verification/read and fails closed on unexpected policies.
- [OfflineTenantGate](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/scripts/devobs_intelligence/tenant_scope.py) defines viewer/operator/owner membership roles. [OfflineTenantStore](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/scripts/devobs_intelligence/tenant_store.py) is explicitly an in-memory SQLite reference.
- Historical PostgreSQL CI proves cross-tenant denial, missing-context denial, forbidden DB roles/policy drift and signed-token-to-RLS behavior for the covered API.

**VERIFIED — Missing from inspected baseline:** dedicated organization/team entities, invitations, tenant creation/deletion, membership administration, production write authorization, tenant-scoped subscription records and customer onboarding UI.
**UNVERIFIED:** isolation for future list/search/write/export endpoints, object storage, queues, caches, audit retrieval, AI memory/retrieval and background workers.
**ASSUMED — Acceptance:** extend the data model only when a product flow requires it; prove tenant boundaries for every added resource/action before onboarding external tenants.

## 3. Identity and access

**VERIFIED:**
- [AccessTokenVerifier](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/scripts/devobs_intelligence/oidc_tokens.py) verifies RS256 signatures using a pinned public key set, issuer, audience, client_id, typed access token, expiry, issued-at, jti presence and devobs.read scope. Token lifetime is bounded to 900 seconds; ID tokens are not accepted as API access tokens.
- [API](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/scripts/devobs_intelligence/api_app.py) exposes GET /v1/tenants/{tenant}/projects/{project}/ci with uniform authentication/authorization errors and no-store responses. All data access uses the verified subject.
- [Staging app](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/scripts/devobs_intelligence/staging_app.py) wires OIDC and PostgreSQL; rejects incomplete configuration and unsafe DSN settings including missing verify-full/CA.
- [Key rotation](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/scripts/devobs_intelligence/oidc_rotation.py) provides an operator-verified, process-local atomic swap primitive; it is not a distributed refresh service.
- Offline roles exist, but the PostgreSQL API uses read membership; it does not deliver a complete production role/action matrix.

**VERIFIED — Missing from inspected baseline:** browser login/logout/session product flow, identity provisioning, tenant administration, MFA configuration workflow, customer API-key issuance/hashing/revocation, tenant-specific SSO setup, SAML/SCIM and permission management UI.
**UNVERIFIED:** live IdP interoperability and rotation propagation across Gunicorn workers; provider revocation/logout enforcement.
**VERIFIED — Compatibility restriction:** subject IDs accept a limited 64-character alphanumeric/underscore/hyphen format, and one configured issuer/audience/client. Broader enterprise identity formats require deliberate mapping/testing.
**ASSUMED:** jti presence must not be advertised as a replay-prevention ledger; use an appropriate revocation/session strategy for the chosen identity architecture.

## 4. Billing, subscriptions and metering

**VERIFIED:** [PRODUCT_SAAS_READINESS.md](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/docs/PRODUCT_SAAS_READINESS.md) explicitly describes Sandbox/Team/Enterprise as draft plans and says no billing system exists.
**VERIFIED — Not found:** payment SDK/service, checkout/customer portal, billing schema, subscriptions, entitlements, webhook verification, idempotent event ledger, invoice generation/reconciliation, usage aggregation and subscription cancellation/dunning behavior.
**VERIFIED:** the AI workflow budget-approval switch and adviser max-call bound are operational guards, not customer usage metering, hard currency budgets or subscription enforcement.
**UNVERIFIED:** payment-provider availability for the owner's business, legal/tax eligibility and merchant-account status; none was checked.
**ASSUMED — Acceptance:** first implement tenant-scoped entitlements and an append-only idempotent usage ledger with synthetic tests; only then integrate a chosen provider in test mode and verify webhook replay, cancellation, quotas and reconciliation before real charges.

## 5. Core DevOps features

| Capability | Baseline finding |
| --- | --- |
| CI/CD | VERIFIED: shared Python/Node/PHP/Bash workflow definitions, change-aware CI, security gates and static Pages publishing/health verification exist. |
| Repository connection | VERIFIED: [collectors](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/scripts/devobs_intelligence/collectors.py) provide bounded injected read transport for GitHub/GitLab CI evidence and exact SHA/stale-state handling. UNVERIFIED: customer GitHub App installation/OAuth onboarding and per-tenant credential lifecycle. |
| Infrastructure as code | VERIFIED: Render Blueprint and SQL declaration exist. No Terraform files were found on baseline main; PR #249 proposes a baseline. |
| Containers | VERIFIED: [AWS ECS workflow](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/.github/workflows/aws.yml) expects a Dockerfile and task definition and fails when prerequisites are absent. No Dockerfile exists on baseline main; PR #248 proposes a static-site image. |
| Kubernetes | VERIFIED: no Kubernetes deployment manifests were found on baseline main; PR #250 proposes optional manifests. |
| Customer orchestration | VERIFIED: no customer deployment API, isolated execution workers, tenant quotas or job scheduler service was found in inspected application entrypoints. |

**VERIFIED:** the AWS path requires manual confirmation and a production environment, but its workflow does not call the shared CI gate itself. Environment reviewer configuration and cloud-side OIDC restrictions are **UNVERIFIED**.
**ASSUMED:** before activating optional deployment paths, bind deployment to a tested immutable revision/image and verified approval; installing infrastructure templates alone does not implement SaaS.

### Work already in progress, not merged

**VERIFIED:** the following PRs were open at inspection. Descriptions indicate intended scope; implementation quality and deployment status were not independently certified by this audit.

| PR | Intended scope | Status observed |
| --- | --- | --- |
| [#246](https://github.com/hamedonassar95/Devobs/pull/246) | Atomic audit append and honest readiness/review wording | Draft |
| [#247](https://github.com/hamedonassar95/Devobs/pull/247) | CI on every push and pull request | Open |
| [#248](https://github.com/hamedonassar95/Devobs/pull/248) | Pinned static-site Docker image | Open |
| [#249](https://github.com/hamedonassar95/Devobs/pull/249) | Validated Artifact Registry Terraform baseline | Open |
| [#250](https://github.com/hamedonassar95/Devobs/pull/250) | Optional Kubernetes manifests | Open |
| [#251](https://github.com/hamedonassar95/Devobs/pull/251) | Local Prometheus/Grafana starter | Open |

**ASSUMED:** review these before creating duplicate implementations. A static-site image or local monitoring starter does not establish API/customer workload readiness.

## 6. AI capabilities and human control

**VERIFIED — Implemented source:**
- [AI review](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/.github/workflows/ai-code-review.yml): optional read-only Codex review, explicit budget switch, conditional credential check, isolated publishing of advisory findings and no merge decision.
- [Incident investigator](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/.github/workflows/incident-investigator.md): trusted bot incident, human-reviewed label, duplicate prevention, bounded report with root-cause hypotheses/recommended tests and no recovery authority. Claude/Vertex alternative workflow sources also exist in the tree.
- [Adviser](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/scripts/devobs_intelligence/adviser.py): deterministic categories from aggregate signals, optional bounded model callback, kill switch, evidence hashes and PENDING_HUMAN_APPROVAL output. Its 0.55 confidence is explicitly uncalibrated.
- [Policy](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/scripts/devobs_intelligence/policy.py): read allowed, patches/branches/Draft PRs proposal-only, high-impact actions denied. Model text is deliberately not authorization.
- [Human approval helper](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/scripts/human_approval_gate.py) checks explicit approval, human/write authority and open/unmerged PR state supplied as input.
- [Patch publisher](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/.github/workflows/phase8b-patch-publisher.yml) rechecks live incident evidence and produces an isolated review PR.

**VERIFIED — Limitations:** the local approval helper trusts supplied evidence fields; it is not itself an authenticated approval issuance/consumption service. The adviser is not a general production LLM backend.
**VERIFIED:** incident workflow source includes failed-job log retrieval for investigation. No separately exposed, tenant-scoped log-summary API or tested production log-redaction/retention pipeline was found in inspected application entrypoints.
**UNVERIFIED:** inference quality on customer incidents, provider uptime/cost, end-to-end log summarization and operational failover.
**VERIFIED — Workflow status caveat:** [AI review run 40242847779](https://github.com/hamedonassar95/Devobs/actions/runs/40242847779) succeeded, but the Codex inference step and credential check were skipped. Success is not proof AI executed.
**ASSUMED:** add authenticated action/parameter-bound approvals with expiry and atomic one-time consumption before any future customer write capability. Existing static publishing/restoration paths must be assessed separately from model policy.

## 7. Security, observability and reliability

**VERIFIED — Existing controls:**
- [CI](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/.github/workflows/ci.yml): SHA-pinned Actions check, Bandit, pip-audit, Gitleaks and agent inventory validation.
- Baseline check-runs include successful CodeQL Analyze (python), Analyze (actions), and Analyze (javascript-typescript).
- [Active Protect main ruleset](https://github.com/hamedonassar95/Devobs/rules/24507159): blocks deletion/non-fast-forward, requires strict validate check and PR, includes CodeQL thresholds, no listed bypass actors.
- **VERIFIED:** required approving review count is **0**; code-owner and last-push approval are not required. A required PR is not an independent human approval gate.
- [Staging app](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/scripts/devobs_intelligence/staging_app.py): /healthz is liveness; /readyz checks database role/schema/RLS contract and returns 503 on failure.
- [AuditStore](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/scripts/devobs_intelligence/audit_store.py): local SQLite hash-linked logical ledger with duplicate checks; module explicitly warns privileged writers can rewrite the chain.

**VERIFIED — Concrete gaps/risks:**
- Audit append verifies/reads/inserts without a surrounding serialization transaction. Concurrent writers can derive the same previous hash and invalidate the ledger; PR #246 proposes a fix but is unmerged.
- Audit rows have no explicit tenant field or tenant authorization layer. Do not expose a shared ledger to customers as tenant-isolated audit history.
- The inspected WSGI route has no implemented rate limiter; every read opens a database connection and performs catalog/policy checks. Load/abuse behavior is unmeasured.
- Exact PostgreSQL 17 deparser/policy comparison intentionally fails closed. Database version/policy changes can cause unavailability and require compatibility rehearsal.
- Two-worker staging plus process-local key rotation requires a consistent key delivery mechanism.
- [CI preview summary](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/.github/workflows/ci.yml) prints "Human review completed" automatically after preview generation; that text is not proof of review. PR #246 targets this wording.

**UNVERIFIED:** managed secret store configuration, encrypted backups, restoration drills, live alerts, retention/deletion, at-rest encryption, operational dashboards and actual on-call coverage.
**VERIFIED:** [enterprise operations document](https://github.com/hamedonassar95/Devobs/blob/85956696df6f8722e2c8d7d1d88f7a03653c2d56/docs/ENTERPRISE_OPERATIONS.md) treats SLOs, observability and backups as proposals; it states no restore drill has run. PR #251 is an unmerged local monitoring starter.
**VERIFIED:** source references GitHub secret names and uses OIDC for some cloud workflows. Actual values were not read or tested. Scan success is not a claim that no secret can exist anywhere.
**ASSUMED:** preserve fail-closed guards while adding bounded monitoring, per-tenant quotas, privacy-safe audit persistence and tested recovery.

## 8. Tests and current CI evidence

**VERIFIED:** [baseline CI run 40216497498](https://github.com/hamedonassar95/Devobs/actions/runs/40216497498), on the exact audited SHA, completed successfully.

| Check | Observed evidence |
| --- | --- |
| Python suite | VERIFIED: existing log: Ran 474 tests in 11.744s; OK (skipped=18). These 18 were disposable-Postgres tests. |
| PostgreSQL RLS job | VERIFIED: existing log: Ran 18 tests in 0.433s; OK. Separate service job executed the previously skipped cases. |
| Security | VERIFIED: Bandit, dependency audit, Gitleaks and immutable Action checks succeeded. |
| Site/validate | VERIFIED: site contract and aggregate validate succeeded. |
| Node guard suite | VERIFIED: skipped in this run by change-impact selection; not claimed as newly passed. |
| Pages | VERIFIED: static publishing and production site verification jobs succeeded in this existing run. Not evidence of SaaS API availability. |
| CodeQL | VERIFIED: three baseline language/action analyses succeeded via check-runs API. |
| Incident/Claude | VERIFIED: sampled recent main runs were skipped, not executed investigations. |
| AI review sample | VERIFIED: workflow successful but inference skipped, as described in section 6. |

**VERIFIED — Coverage present in test inventory/source:** JWT boundaries, OIDC metadata/rotation, tenant membership, PostgreSQL policy drift, request errors, audit consistency, deterministic policies, AI evaluation fixtures, recovery guards, workflow contracts and site validation.
**VERIFIED — No customer-flow implementation/coverage found:** subscription lifecycle, invoice reconciliation, signup/invite/team management, production write/list/export tenant isolation, customer repository installation and tenant secret rotation.
**UNVERIFIED:** numerical coverage percentage, browser E2E coverage, distributed/load tests, live SSO, real provider failures and backup restore results.
**ASSUMED:** synthetic fixture success should be supplemented with staging evidence, not substituted for it.

### Exact commands and outputs from existing CI

**VERIFIED:** these commands are documented/configured in the inspected repository; outputs are historical job logs, not local audit executions.

```text
python3 -m unittest discover -s tests -v
Ran 474 tests in 11.744s
OK (skipped=18)

python3 -m unittest discover -s tests -p 'test_postgres_rls_integration.py' -v
Ran 18 tests in 0.433s
OK
```

**VERIFIED:** no migrations, terraform commands, cloud CLI commands or full test suite were run by this audit. Creating this PR may trigger the repository's pre-existing CI, including its disposable PostgreSQL fixture; this report does not change those workflows.

## 9. Prioritized risks and inconsistencies

| Priority | Evidence status | Gap and consequence |
| --- | --- | --- |
| P0 before customers | VERIFIED | Missing billing/entitlements and tenant lifecycle: cannot operate subscriptions or onboard organizations safely. |
| P0 before shared audit exposure | VERIFIED | Unserialized, unscoped local audit ledger: concurrent integrity failure and no tenant-facing authorization. Review PR #246. |
| P0 before sensitive writes | VERIFIED | Zero required approving reviewers; local approval booleans are not signed approvals. Independent review is not currently enforced by the observed rule. |
| P1 | VERIFIED | Narrow read-only RLS coverage must not be marketed as all-resource SaaS isolation. |
| P1 | UNVERIFIED | Staging IdP/DB readiness, recovery and operational safeguards lack independently collected live evidence in this audit. |
| P1 | VERIFIED | No application rate limiting and no distributed key rotation delivery in inspected runtime. |
| P1 | VERIFIED | AWS workflow exists without baseline Dockerfile; optional deploy path lacks its own shared CI invocation. |
| P2 | VERIFIED | Readiness docs say auth/RBAC are not implemented, while OIDC verification and offline roles now exist; status is stale and must distinguish partial from absent. |
| P2 | VERIFIED | Automatic "Human review completed" text and green AI workflow can overstate actual review/inference. |
| P2 | VERIFIED | Docker/Kubernetes/Terraform/monitoring work exists only in open PRs at this baseline; do not count it as merged/deployed. |

**ASSUMED:** these priorities are a release-risk ordering, not a CVSS rating or proof of active exploitation.

## 10. Roadmap — smallest and safest first

1. **ASSUMED — Reconcile status documentation and truthful workflow wording.** Acceptance: every feature has code/test/runtime status, a source SHA and evidence; no auto-generated human approval claim. Reuse PR #246.
2. **ASSUMED — Finish the narrow audit concurrency fix.** Acceptance: independent concurrent writers preserve one valid chain, conflicts roll back, and idempotency tests pass; review #246 before duplicating it.
3. **ASSUMED — Make approval policy explicit.** Acceptance: document solo-owner policy today and independent-review requirements for future operators; any ruleset/environment change requires separate authorization. Do not lock a sole operator out through an unreviewed setting change.
4. **ASSUMED — Define the first product slice as authenticated read-only tenant CI status.** Acceptance: verified identity mapping, tenant/project membership lifecycle, an API contract and deliberate negative authorization tests; keep write execution out of the initial slice.
5. **ASSUMED — Extend identity/key lifecycle and request controls.** Acceptance: tested IdP integration, coordinated rotation/revocation, rate/request limits and outage behavior; secrets provisioned outside the repository.
6. **ASSUMED — Prove managed staging readiness.** Acceptance: exact-SHA valid/invalid token and cross-tenant tests, /readyz evidence, verified DB identity/TLS and dependency failure/recovery. No production migration or paid setup is authorized by this audit.
7. **ASSUMED — Add tenant-aware audit and privacy lifecycle.** Acceptance: explicit tenant scope, authorization on export, retention/deletion rules, anchored integrity and restore rehearsal.
8. **ASSUMED — Introduce organizations/teams only for the agreed onboarding flow.** Acceptance: invitations, membership changes/revocation and all read/write/list/search paths tested against cross-tenant access.
9. **ASSUMED — Add read-only customer repository onboarding.** Acceptance: install/uninstall, repository scope restrictions, per-tenant credentials and revocation; signed/idempotent event ingestion if webhooks are introduced.
10. **ASSUMED — Implement synthetic entitlements and usage accounting.** Acceptance: tenant-bound counters/ledger, quota enforcement, retries/deduplication and reconciliation tests, with no real charges.
11. **ASSUMED — Integrate subscriptions in provider test mode.** Acceptance: signed webhooks, plans, checkout, cancellation/dunning, invoices/refunds and entitlement transitions; confirm merchant/legal eligibility before charging.
12. **ASSUMED — Operationalize monitoring and backups.** Acceptance: measured SLOs, alerts/on-call route, tested restore with measured RPO/RTO, load limits and bounded cost. Evaluate PR #251 as a starter only.
13. **ASSUMED — Review optional packaging/IaC PRs by hosting need.** Acceptance: reproducible image and deployment validation, trusted artifacts and explicit approval; #248–#250 are not prerequisites to every SaaS architecture.
14. **ASSUMED — Expand live AI only after tenant/privacy/cost gates.** Acceptance: measured evaluation corpus, provenance, redaction, quotas and human feedback; no model-generated permission grants.
15. **ASSUMED — Production gate.** Acceptance: complete end-to-end tenant and subscription flows, security review, recovery rehearsal, live observability, support/privacy commitments and an owner-approved release. No automatic promotion from this audit.

## Audit validation and remaining assumptions

**VERIFIED:** report-only change; repository instructions inspected, links bind source claims to the audited commit, CI evidence distinguishes passed/skipped/unverified.
**UNVERIFIED:** remote secrets, environments, provider accounts, staging data and production configuration were intentionally outside scope; no inference about them is presented as fact.
**ASSUMED:** Devobs is the requested DevOps SaaS repository, as distinguished from phone-repair-assistant-v2 earlier in this conversation. Audit baseline is main; open-PR work is listed separately.
**ASSUMED:** production readiness must be re-evaluated after merges and live acceptance checks; this snapshot is not a certification.

## Official API/platform references

**VERIFIED:** repository source/run results above are the primary audit evidence. These official references document the API fields and platform behavior used for inspection/delivery:
- Git tree inventory: https://docs.github.com/en/rest/git/trees#get-a-tree
- Workflow runs/jobs and logs: https://docs.github.com/en/rest/actions/workflow-runs and https://docs.github.com/en/rest/actions/workflow-jobs
- Check-run results: https://docs.github.com/en/rest/checks/runs#list-check-runs-for-a-git-reference
- Ruleset fields: https://docs.github.com/en/rest/repos/rules#get-a-repository-ruleset
- File creation: https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents
- Branch references: https://docs.github.com/en/rest/git/refs#create-a-reference
- Pull requests: https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request

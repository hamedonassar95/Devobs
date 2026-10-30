# P01 Managed Staging: Owner Activation Decision

**Decision status: OWNER-SIGNED NO-GO / BLOCKED (2026-10-30); conditional P01 approval is pending enforcement proof.** The owner approved the bounded P01 scope with a USD 100 total monthly ceiling only if verifiable automatic enforcement covers every P01 resource. Railway's official documentation establishes a minimum USD 10 Compute hard limit and says it takes workloads offline, but it does not establish a bounded delay/overrun or managed-database and post-shutdown storage coverage. No Railway account or resources were created. See the [Railway evidence and pre-registered test design](P01_RAILWAY_SPEND_ENFORCEMENT_EVIDENCE.md). Decision-time `main` was [`4ec9fd138f004498827b5c3b903a78971a8e6706`](https://github.com/hamedonassar95/Devobs/commit/4ec9fd138f004498827b5c3b903a78971a8e6706), with required `validate` passing in [CI run 40991673938](https://github.com/hamedonassar95/Devobs/actions/runs/40991673938). Repository checks do not establish provider settings or service health.

## Authorization boundary

**VERIFIED:** The owner recorded P00 GO with bounded repository-governance risks in the [P00 decision comment](https://github.com/hamedonassar95/Devobs/pull/277#issuecomment-6423508484) and [decision packet](P00_OWNER_DECISION.md). That decision does **not** approve P01, staging resources, a provider/account, data transfer, a deployment, a budget, service integrations, or AI/API inference. The canonical [P00–P12 roadmap](plans/2026-10-26-devobs-production-execution-roadmap.md) keeps P01–P12 blocked pending separate approvals.

**ASSUMED for safety until explicitly decided:** absence of a completed checklist means **NO-GO**. A future GO must name its exact provider, service, region, budget enforcement, data scope, identity and runtime controls below. It authorizes only that bounded P01 staging scope; production release, customer data, commercial use, and P13–P19 remain outside scope.

## Evidence available now

| Area | Evidence and status | What it does not establish |
| --- | --- | --- |
| Staging architecture | **VERIFIED (proposal):** [Render + Supabase staging plan](RENDER_SUPABASE_STAGING.md) describes a read-only WSGI API, PostgreSQL RLS and OIDC/JWKS; `render.yaml` is proposed configuration, not a live service. Railway Amsterdam is a candidate under evaluation only. | No provider has been selected or deployed for P01; provider eligibility, contractual residency, and a live endpoint remain unverified. |
| Provider workspace | **VERIFIED (owner-provided prior read-only evidence, planning reference only):** the “Primary” and “Render” connector aliases resolved to the same Render workspace, “My Workspace” (`tea-dafq4ue7bikc73d7tmig`). Service listings returned null. **UNVERIFIED:** Railway account/workspace, Supabase organization, and any P01 service. | A null listing does not prove no service exists. Workspace identification grants no creation permission. |
| Synthetic tenant isolation | **VERIFIED (offline contract):** [STAGING_ACCEPTANCE.md](STAGING_ACCEPTANCE.md) and [`test_intelligence_staging_smoke.py`](../tests/test_intelligence_staging_smoke.py) exercise six mocked calls: liveness, readiness, anonymous denial, authorized tenant read, a separate denied-tenant fixture, then cross-tenant denial. The test uses queued synthetic responses and makes no network call. | Hosted tenancy, real identity, actual database RLS, TLS, network, or concurrent isolation. |
| Application and authorization | **VERIFIED (source/tests):** [`test_intelligence_staging_app.py`](../tests/test_intelligence_staging_app.py), [`test_intelligence_api_security.py`](../tests/test_intelligence_api_security.py), and [`test_intelligence_tenant_scope.py`](../tests/test_intelligence_tenant_scope.py) cover mocked startup/authentication and tenant-scope denial. | An operator-selected IdP, verified live issuer/JWKS lifecycle, or real user membership. |
| PostgreSQL boundary | **VERIFIED (source/CI fixture):** [RLS staging evidence](POSTGRES_RLS_STAGING.md) documents a restricted non-owner, non-BYPASSRLS reader, forced RLS and parameterized tenant/subject-scoped reads. [`test_postgres_rls_integration.py`](../tests/test_postgres_rls_integration.py) is a disposable-PostgreSQL integration suite. | A live managed database, its runtime role/policies, or production protection from direct SQL access. |
| Health and recovery | **VERIFIED (source contract):** offline tests distinguish liveness from readiness. The staging proposal requires real runtime-role checks and a restore rehearsal. | Live readiness, backup integrity, restore time, RPO/RTO, incident response, or rollback performance. |
| Spend, privacy and network | **VERIFIED (owner decision):** USD 100 total monthly ceiling approved conditionally. **VERIFIED (Railway public docs):** a USD 10 minimum Compute hard limit takes workloads offline; Compute includes CPU, memory, storage, and network egress; Agent usage has a separate limit. **UNVERIFIED:** total invoice enforcement, delay/overrun, managed databases, and charges/retention for volumes/backups/PITR after shutdown. Detailed evidence is in [P01_RAILWAY_SPEND_ENFORCEMENT_EVIDENCE.md](P01_RAILWAY_SPEND_ENFORCEMENT_EVIDENCE.md). | No live P01 resources may be created until the budget gate and other pre-provisioning controls are evidenced. Alerts and a compute-only limit do not prove a combined USD 100 cap. |
| Publication / preview | **VERIFIED (runtime, 2026-10-29):** PR #290 produced a Vercel preview at [the PR preview URL](https://devobs-git-docs-readiness-evidence-after-pr-289-hamedonassar.vercel.app); merging it published the static Pages site and passed `verify-production` in [CI run 40964990632](https://github.com/hamedonassar95/Devobs/actions/runs/40964990632). **UNVERIFIED:** Vercel configuration, preview access controls and intended audience have not been independently inspected. | This confirms behavior for a repository documentation PR and static Pages only. It does not authorize a P01 endpoint, staging data, or customer access. See [Vercel Git integration docs](https://vercel.com/docs/git). |

### Repository publication evidence (2026-10-29)

- **VERIFIED:** PR #290 was documentation-only and merged as `837e9790ce45fbc7fa624fdf68db1c3b5b396105`. Main CI [run 40964990632](https://github.com/hamedonassar95/Devobs/actions/runs/40964990632) and separate CodeQL [run 40964990346](https://github.com/hamedonassar95/Devobs/actions/runs/40964990346) succeeded. GitHub Pages publication and production-site verification succeeded; the PR's Vercel preview is linked above.
- **Scope:** these results verify repository CI and static-site publication. No P01 service, database, provider resource, staging data transfer, paid inference, or customer data was created or used. **P01 remains NO-GO / BLOCKED.**

### Offline evidence versus live acceptance

The synthetic six-call contract is useful **offline acceptance evidence** for expected response shape and tenant-denial behavior only. Other safe preparation includes the staging-app/authentication unit tests and code review of the SQL policy. The PostgreSQL RLS integration suite requires a disposable PostgreSQL fixture (as used by CI); it is not a hosted-staging test. A passing test or CI run cannot replace live checks.

After separate authorization and provisioning, **live P01 evidence** must include: exact staged source SHA; TLS and hostname verification; readiness against the actual restricted runtime role; authenticated valid/invalid/expired-token tests; JWKS rotation and revocation behavior; the six-call sequence against the isolated staging service using synthetic identities/data; cross-tenant denial against real RLS, including same-project-name cases; denied writes; rate/request limits and redacted logs; controlled database/network failure handling; and a successful isolated backup restore with measured recovery objectives. Record exact commands, outputs, time, scope and approver without recording credentials.

## Owner-selected values and evidence required before any P01 action

The values below record owner-provided proposed selections for the bounded staging scope. They do not prove provider settings are configured or authorize provisioning. The owner-signed conditional approval below is not effective until automatic enforcement of the USD 100 combined monthly ceiling is proven; the current operational status is NO-GO / BLOCKED. Do not put credentials, DSNs, tokens, keys, or private customer data in this document. The repository-only preview and Pages entries below record the owner's standing repository instruction; they do not grant an active P01 GO.

| Decision | Owner-selected value / evidence (owner-provided proposal; configuration not verified) |
| --- | --- |
| Provider, account/workspace, service and authorized operator | Railway is the current hosting alternative under evaluation; no account, workspace, project, or service has been verified or created. Render workspace “My Workspace” (`tea-dafq4ue7bikc73d7tmig`) and Supabase organization “Devobs Staging” are earlier planning proposals only, not selected or provisioned. Operator proposal: Mohammad Nassar. |
| Region, data residency and permitted data classification | Amsterdam is accepted preliminarily for Railway only; contractual data-residency terms must be confirmed before real data. Synthetic data ONLY; no customer data and no real PII. |
| Maximum monthly spend ceiling **and enforceable provider quota/cap mechanism**; alerting and stop procedure | Owner-approved ceiling: **USD 100 total per month**, conditional on verified enforcement across every billable P01 resource. Railway's [official cost-control documentation](https://docs.railway.com/pricing/cost-control) establishes a minimum USD 10 Compute hard limit, says all workloads are taken offline at the limit, includes CPU/memory/storage/network egress in Compute, and separates Agent usage. It does **not** specify maximum delay/overrun, explicitly confirm managed databases, or explain volume/backup/PITR charges or retention after shutdown. Proposed safeguards and frozen compute-only test criteria are in [P01_RAILWAY_SPEND_ENFORCEMENT_EVIDENCE.md](P01_RAILWAY_SPEND_ENFORCEMENT_EVIDENCE.md); they are not configured or authorized. **P01 remains NO-GO / BLOCKED.** |
| PII/telemetry allowance, purpose, retention, deletion and privacy/legal approval | Owner-stated: synthetic data only; no PII; synthetic telemetry only; 30-day retention; owner deletes all staging resources on request or at end of P01. No legal/privacy approval required while no real PII or customer data is used. |
| IdP, issuer/audience/client scope, trusted JWKS source, rotation/revocation and failure behavior | Proposal: Auth0 Free as the candidate to evaluate, preferred over Supabase Auth for the current verifier's required RS256 access JWT with `iss`, strict `aud`, `sub`, `exp`, `iat`, `jti`, `client_id`, `scope` containing `devobs.read`, and lifetime at most 900 seconds. Auth0's [RFC 9068 profile](https://auth0.com/docs/secure/tokens/access-tokens/access-token-profiles) documents `client_id`, `jti`, and `scope`; its [API settings](https://auth0.com/docs/get-started/apis/api-settings) document RS256 and configurable access-token lifetime; its [OIDC discovery/JWKS documentation](https://auth0.com/docs/secure/tokens/json-web-tokens/locate-json-web-key-sets) documents the tenant discovery endpoint. Supabase's [JWT documentation](https://supabase.com/docs/guides/auth/jwts) documents short-lived Auth JWTs and JWKS, but the reviewed docs do not establish the required exact claims/defaults. Auth0 Free availability of all required features and compatibility with this verifier are **UNVERIFIED**. Issuer: `[UNVERIFIED: Auth0 tenant issuer]`; audience: `[UNVERIFIED: registered API identifier]`; client ID: `[UNVERIFIED: Auth0 application client ID]`; scope issuance: `[UNVERIFIED: devobs.read]`. Discovery URL: `https://[UNVERIFIED: Auth0 tenant domain]/.well-known/openid-configuration`; verify its issuer and same-origin HTTPS `jwks_uri` before use. Fetch metadata/JWKS only from the verified official discovery URL over TLS, rotate on provider schedule, and fail closed on discovery/JWKS failure. |
| PostgreSQL runtime identity: non-owner, non-superuser, no `BYPASSRLS`, minimum read grants; migration owner and reviewed policy evidence | Runtime role `devobs_reader`: read-only, non-owner, non-superuser, no `BYPASSRLS`, `SELECT` only; forced RLS. Migration role `devobs_migrator`: migrations only. RLS policy review evidence: Pending after provisioning. |
| TLS/CA verification and allowed network ingress/egress, including private access restrictions | Full certificate validation; HTTPS only; no public database access; network egress to the IdP and database only. |
| Backup encryption/retention and successful restore evidence; approved RPO/RTO | Encrypted backups; 7-day retention; one successful isolated restore rehearsal required before sign-off; RPO 24 hours; RTO 24 hours. Restore rehearsal evidence: Pending after provisioning. |
| Readiness/liveness semantics, smoke-test target, failure thresholds and exact staged SHA | Liveness means process is up; readiness checks the database using the runtime role; all six smoke calls must pass (100%). Published/staged SHA: Pending after provisioning. |
| Incident owner/on-call path, stop conditions, rollback procedure and resource deletion authority | Mohammad Nassar is incident owner. Stop at 80% spend, any cross-tenant leak, or readiness failure lasting over 15 minutes. Rollback means redeploying the previous SHA. Only the owner may delete resources. Incident contact: phone "Phone not published (public repository); use the email contact only."; email `hamedonassar95@outlook.sa`. |
| Independent release approver and approval mechanism; distinguish this from the implementer | None available; risk accepted by owner for synthetic-data-only staging. |
| Vercel preview visibility accepted before any push/PR? Scope and audience | The owner's standing repository instruction authorizes routine source/documentation PRs, CI, and merge; PR #290's preview was generated. Scope is limited to repository artifacts and synthetic/static content. This does not approve a P01 staging endpoint, staging data, or customer access. The Vercel access-control settings remain unverified. |
| Separate approval for any main merge that may publish GitHub Pages | The owner's standing repository instruction authorizes merge after green CI; PR #290's merge published and verified the static site. This is not approval to deploy a P01 service or create resources. |

## P01 Railway spend-control gate — current exit criteria

**Current gate: NO-GO / BLOCKED.** No support request was sent and the pre-registered test has not been run. See [the Railway evidence packet](P01_RAILWAY_SPEND_ENFORCEMENT_EVIDENCE.md) for the evidence ledger, controls, exact support request, and frozen test protocol.

Budget-control evidence may be supplied by either an official written Railway response that resolves the applicable coverage, maximum delay/overrun, and post-shutdown billing/retention questions, or a successful run of the frozen USD 10 compute-only test after explicit one-time owner authorization. A test-only pass covers only the tested ephemeral Compute workload; managed PostgreSQL, persistent storage, backups/PITR, and Amsterdam contractual residency remain blocked until written confirmation or a separately approved scope change. Passing the budget sub-gate does not itself authorize provisioning or change the owner-signed NO-GO; all P01 security, identity, recovery, and owner sign-off requirements still apply.

### Owner-signed decision record

- Decision: **NO-GO / BLOCKED at this time.** The owner conditionally approves the bounded P01 scope with a USD 100/month total ceiling, contingent on verified automatic enforcement. That condition is unmet; no resource or integration may start.
- Scope and exclusions: The conditional approval is limited to P01 staging with synthetic data only; it excludes production, customer data, commercial use, paid AI inference, and P13–P19. It does not take effect before hard-cap evidence is recorded.
- AI-9: Remains **FAIL**. This P01 decision does not change the AI-9 gate or its reported measurements.
- Owner identity: Mohammad Nassar.
- Independent approver (if applicable): None available; owner accepts this for synthetic-data-only staging. This does not waive the USD 100 automatic-enforcement prerequisite.
- UTC timestamp: 2026-10-30 02:42:05 UTC.
- Decision-time main SHA and exact required-check run: `4ec9fd138f004498827b5c3b903a78971a8e6706`; required `validate` passed in [CI run 40991673938](https://github.com/hamedonassar95/Devobs/actions/runs/40991673938).
- Evidence/approval reference: Owner's explicit USD 100/month conditional decision recorded in this Codex conversation on 2026-10-30 02:42:05 UTC. Railway documentation and remaining unknowns: [P01_RAILWAY_SPEND_ENFORCEMENT_EVIDENCE.md](P01_RAILWAY_SPEND_ENFORCEMENT_EVIDENCE.md).
- Owner signature/reference: **Mohammad Nassar — textual owner signature recorded by Codex under the explicit instruction in this conversation, 2026-10-30 02:42:05 UTC; signed decision is NO-GO pending hard-cap enforcement proof.**

This signed NO-GO records the USD 100/month ceiling and conditional P01 approval. It does not authorize resource creation, provider spend, data transfer, deployment, or inference while the enforcement condition is unmet. P01 remains **NO-GO / BLOCKED** until automatic total-spend enforcement and the remaining pre-provisioning controls are evidenced. The conditional approval is limited to the synthetic-data P01 scope above; it is not a general production release, customer-data, commercial, billing-over-cap, or AI-inference approval.

## Future AI roadmap boundary

These are future planning milestones only, not P01 requirements that activate an integration:

| Milestone | Future direction; not enabled |
| --- | --- |
| P13 | Per-tenant, minimized OpenTelemetry telemetry with data-quality checks. |
| P14 | Offline-baselined anomaly detection with measured false positives. |
| P15 | Read-only AI incident analysis and human-reviewed draft fixes. |
| P16 | Deterministic Trivy/CodeQL/OPA security gates; AI is advisory only. |
| P17 | FinOps recommendations with actual owner-approved spend limits and enforcement. |
| P18 | Least-privilege code/IaC copilots producing reviewable proposals only. |
| P19 | Auditable evaluation, feedback, prompt versioning and rollback evidence. |

The deep-research article is a **planning input**, not validation of vendor claims. GPT-6.1 Terra performance, security benchmarks, API syntax, eligibility, licensing and prices remain **UNVERIFIED** and are not used here. No model, Copilot, API, telemetry, payment, or cloud integration is activated. Preserve tenant isolation, redaction, prompt-injection defenses, provenance, cost enforcement and human approval as later-stage gates.

## Publication and P01 authorization boundary

The owner has authorized routine repository PRs, CI, and merges after green checks; PR #290 confirms that a repository preview can be generated and a merge can publish the static Pages site. This standing instruction covers repository artifacts and the existing static-site path only. It does not authorize provider spend beyond the approved ceiling, data transfer, staging endpoints, paid AI, or customer access. **The owner has signed a NO-GO / BLOCKED decision and conditionally approved P01 with a USD 100/month total ceiling; activation remains blocked until verifiable automatic enforcement and the remaining pre-provisioning controls are established for all P01 resources.** See the [current Pages release source](../.github/workflows/ci.yml) and [P00 publication boundary](P00_OWNER_DECISION.md).

## References

- [Railway spend-enforcement evidence and pre-registered test design](P01_RAILWAY_SPEND_ENFORCEMENT_EVIDENCE.md)
- [Canonical P00–P12 execution roadmap](plans/2026-10-26-devobs-production-execution-roadmap.md)
- [Offline staging acceptance](STAGING_ACCEPTANCE.md)
- [Managed staging proposal and prerequisites](RENDER_SUPABASE_STAGING.md)
- [PostgreSQL RLS implementation and limits](POSTGRES_RLS_STAGING.md)
- [Product/SaaS readiness blockers](PRODUCT_SAAS_READINESS.md)
- [PostgreSQL row security documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [OWASP API Broken Object Level Authorization guidance](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/)


## P01 offline evidence gate (review only)

The optional manual workflow `.github/workflows/p01-evidence-gate.yml` runs
`scripts/check_p01_evidence.py` against `docs/p01/evidence.json`. The tracked
sample is intentionally **NO-GO**, with all seven controls **UNVERIFIED**.
The checker rejects missing/unknown fields, unexpected state, stale timestamps,
SHA mismatch, and unsafe references; a missing control fails closed. It neither
fetches external evidence nor authenticates a reviewer, therefore even a fully
populated file is **READY_FOR_HUMAN_REVIEW**, never an authorization or runtime
proof. Do not change the owner-signed P01 NO-GO based on this checker alone.
The manual job is not wired into the static GitHub Pages release gate.

Run locally from the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_p01_evidence.py' -v
python3 scripts/check_p01_evidence.py --file docs/p01/evidence.json --expected-sha 838083fd490780ea27649a401777ad69bd767318
```

The second command intentionally exits 1 while P01 remains blocked. Attestations
must reference an actual reviewed source SHA and clean HTTPS evidence URLs, but
that structure does not verify their authenticity or provider-account settings.
Only explicit separate owner approval can authorize staging, spend, deployments,
or production actions. Never include tokens, account identifiers, or sensitive
customer evidence in this public repository.

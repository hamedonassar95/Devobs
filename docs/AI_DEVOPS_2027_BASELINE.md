# DevObs AI DevOps baseline

**Evidence date:** 2026-10-25
**Repository:** `hamedonassar95/Devobs`
**Reviewed main SHA:** `85956696df6f8722e2c8d7d1d88f7a03653c2d56`
**Evidence:** GitHub source tree, merged pull requests, ruleset, and CI run [40216497498](https://github.com/hamedonassar95/Devobs/actions/runs/40216497498).

This inventory distinguishes source and CI evidence from a deployed service. A green CI run proves only the checks executed on that commit; it does not prove production identity, tenant isolation, model quality, or service availability.

## Component inventory

| Subsystem | Main source and test evidence | Status | Boundary / remaining proof |
| --- | --- | --- | --- |
| Evidence contracts and collectors | `scripts/devobs_intelligence/contracts.py`, `collectors.py`; `tests/test_intelligence_contracts.py`, `test_intelligence_collectors.py` | VERIFIED in source and Python CI | Synthetic fixtures and fixed-origin reads; no authenticated live webhook ingestion. |
| AI adviser and deterministic policy | `adviser.py`, `policy.py`, `state_machine.py`; `tests/test_intelligence_adviser.py`, `test_intelligence_policy.py` | VERIFIED as offline proposal logic | No production model/provider is configured; approvals and execution transitions remain disabled. |
| Context, topology, incident memory and correlation | `context.py`, `correlation.py`, `incident_memory.py`; `tests/test_intelligence_context_graph.py`, `test_intelligence_correlation.py` | VERIFIED as bounded offline logic | Synthetic metadata only; no live OTLP collector or trusted production incident memory. |
| Tenant scope and signed-token API | `tenant_scope.py`, `oidc_tokens.py`, `oidc_metadata.py`, `oidc_rotation.py`, `api_app.py`; `tests/test_intelligence_tenant_scope.py`, `test_intelligence_api_security.py`, `test_intelligence_oidc_metadata.py`, `test_intelligence_oidc_rotation.py` | VERIFIED in source and Python CI | WSGI contract exists; no deployed DevObs API or independently configured IdP. |
| PostgreSQL tenant isolation | `deploy/postgres/001_tenant_rls.sql`, `postgres_store.py`; `tests/test_postgres_rls_integration.py` | VERIFIED against ephemeral PostgreSQL 17 in CI | No DevObs hosted database was identified; CI does not prove hosted identity, network, backup, or tenant isolation. |
| Local audit ledger | `audit_store.py`; `tests/test_intelligence_audit_store.py` | PARTIAL | Hash chaining is locally verifiable but not externally anchored. The current local feature branch adds serialized atomic append and a consistent single-snapshot summary; its focused 11-test suite passes, but the fixes are not in `main` and have not passed full CI/CodeQL. |
| Staging entrypoint and smoke contract | `staging_app.py`, `staging_smoke.py`; `tests/test_intelligence_staging_app.py` | PARTIAL | Code requires operator-supplied OIDC and TLS-verified PostgreSQL settings; no live DevObs staging was found or exercised. |
| Mobile/web and DevOps integration | GitHub Actions, GitHub Pages; main CI run above | PARTIAL | Main's static Pages deployment was published and verified. No Vercel project linked to this repository was returned by the connected-account lookup; no GitLab DevObs project or DevObs Supabase project was returned. |

Every source/test row above was inspected at the single exact main SHA in the header; the row-level paths and test names are therefore all pinned to that revision, while the CI run is recorded separately below.

## Exact CI evidence

Run `40216497498` tested main SHA `85956696df6f8722e2c8d7d1d88f7a03653c2d56`. Python validation, security scans, PostgreSQL RLS integration, `validate`, Pages publish, and deployed-site verification succeeded. Node tests were skipped. The active `Protect main` ruleset requires the `validate` status and a pull request, but its required approving-review count is zero. It configures a CodeQL alert threshold; the latest CodeQL analysis result was not independently verified.

On the local candidate branch, 126 targeted AI-intelligence tests pass, including the BOM inventory after the required files were added to the sparse checkout. Full `test_intelligence_*.py` discovery also ran 126 tests but could not set up the staging-app test because `psycopg` is not installed; no dependencies were installed in this disk-constrained environment. That setup error is not classified as a source regression. The 11 audit-store tests, Python AST parsing for 42 source/test files, internal links, and `git diff --check` pass. The full repository suite has not been run from a complete checkout.

## Not established

- A hosted DevObs API, tenant database, production OIDC identity provider, or live AI inference.
- A verified CodeQL analysis result for the reviewed main SHA.
- An enforced independent human review before merge.
- Externally tamper-evident audit storage, measured service SLOs, backup/restore proof, or customer-facing operations.
- A Vercel, GitLab, or Supabase DevObs deployment. The connected Supabase account lookup returned a separate Phone Repair Assistant project; its data and settings were not inspected.

## Release interpretation

`production-release` runs only after a successful `validate` job on a push to `main`; pull requests receive checks and a temporary downloadable artifact instead. `one-click-deploy` is a separate manually dispatched production-capable workflow guarded by candidate validation, a confirmation input, rollback release validation, and quality CI. A staging or release workflow definition is not proof that its external service is configured or that a deployment succeeded.

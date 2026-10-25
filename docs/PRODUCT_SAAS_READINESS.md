# DevObs Enterprise commercial readiness gate

**Not yet sellable as a multi-tenant AI DevOps SaaS.** Current capability: protected GitHub repository, existing CI/CD and static site, read-only evidence collection, deterministic review-only recommendations, and local sample-data demonstration.

## Proposed service architecture, not deployed

- API Gateway -> SSO/OIDC identity provider -> tenant-aware RBAC/ABAC authorization -> project-scoped REST API (OpenAPI contract) -> queued workers -> SQL database with tenant row-level restrictions -> bounded evidence adapters -> policy/adviser/audit.
- External provider credentials stored in a managed secret store scoped per tenant. No API keys in source code, configuration samples, test outputs or public logs.
- Tenant data isolation must be proven by integration tests for read, write, list, search, audit export, model retrieval and background workers, including deliberate cross-tenant attempts.
- Hosted dashboard must show evidence age, policy decision, CI state, approval actor and historical incident provenance without granting model outputs admin privileges.
- API keys must be hashed, revocable, restricted by tenant/project/operation, rotated, rate-limited and bound to an authenticated principal. Authentication and RBAC are **not implemented**.
- Stripe billing and metering **not configured**. Before charging customers: reviewed legal/tax eligibility, actual processor availability, webhook signature validation, idempotent invoice events, plan quotas, reconciliation, refunds/disputes and access after cancellation.
- Integrations (email, Slack, Teams): notifications only after opted-in tenant authorization and message privacy review. None is active.

## Onboarding acceptance flow (target)

1. Sign in through verified identity provider and create a tenant.
2. Consent to privacy/retention policy and connect one read-only GitHub/GitLab project.
3. Inspect minimum scopes and prove fetch of the exact project commit and read-only CI status.
4. Run a zero-cost, synthetic demo to show advisory evidence and policy gates.
5. Review audit trace and choose support/alert preferences.
6. Introduce optional paid inference only after clear consent, limit and billing authorization.

## Example commercial plans — DRAFT, no pricing claims

| Plan | Intended scope | Metering proposal |
| --- | --- | --- |
| Sandbox | Offline demo and 1 sample project | Fixed included requests, no live credentials |
| Team | Scoped CI insights and manual triage | Per connected repo plus analyzed incident cap |
| Enterprise | SSO, tenant isolation, approvals, audit exports | Contracted usage/quota and support terms |

Prices, currencies, entitlements, subscription signup and availability must be validated before any public sales page or invoice. No billing system exists.

## SLA template fields (not an offer)

Covered services; supported regions; measured service availability window; exclusions; maintenance notices; response priority and on-call hours; allowed credit/remedy terms; data retention and deletion; security incident reporting route; backup RPO/RTO supported by actual drills; termination, migration and dispute process. Obtain legal review before publication.

## Privacy/terms drafting checklist (not legal advice)

Controller/processor identity, data collected, service purpose, lawful basis/consent, AI vendor disclosures, cross-border processors, DPA/subprocessors, log/model data exclusions, deletion/export timelines, breach response, access controls, retention by plan, prohibited uses, age/legal eligibility, refund/dispute and governing law. No finished privacy policy, terms or DPA has been legally approved.

## Licensing audit: review required before commercial resale

Observed direct Python development tools: `bandit==1.9.4`, `pip-audit==2.10.1`. Existing `THIRD_PARTY_NOTICES.md` and `licenses/` need license/attribution reconciliation against the dependency tree and all Actions/reused upstream modules; **this work did not establish commercial clearance**. Future container image base layers, model provider output licenses, cloud services and copied runbooks need separate review. A commercial resale blocker exists if any dependency forbids the intended distribution, has unmet source/attribution obligations or cannot be licensed.

## Go/no-go criteria

No external customer onboarding until: verified identity+tenant isolation, signature-bound approvals, legal/privacy documents, encrypted storage, tested backup restore, support and security response procedures, observed SLO metrics, measured evaluation/cost, compliant software inventory and proof of authorization for any paid services. Mark every current unmet criterion **BLOCKED**.

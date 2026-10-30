# Devobs control plane and separate experiment projects — owner architecture choice

**Decision date: 2026-10-31.** Owner clarified that **Devobs AI Intelligence** is the original central product; other projects are experiments for verifying how its automation and AI services operate. **Architecture authorized; no external deployment, transfer of data, new account or paid action has occurred.** P01 is **NO-GO**.

## Ownership and isolation

- **Core:** `hamedonassar95/Devobs` is the canonical control-plane codebase for future tenant-aware services, AI workflows, release safeguards, evidence, audit, finance policy, and customer-facing SaaS. Existing `main` stays protected and unchanged until a reviewed PR is approved.
- **PHONE REPAIR ASSISTANT:** experimental client/use case for mobile-repair diagnostics. Its existing Supabase project remains **separate and untouched**. Its data, secrets and users are not imported to the Devobs database.
- **AL-DALA MOBILE:** experimental commercial/storefront client. Keep storefront hosting, credentials, commerce records and customer data independent; no live Devobs integration is currently verified.
- **Further projects:** treat as independent tenant-scoped integrations only after specific owner approval, scoped API contracts, issuer/audience/JWKS verification, row-level authorization tests and budget guards.

The conceptual relation is **Devobs services → approved experiment-specific integration**. An experiment is *not* a privileged Devobs administrator; no experiment can deploy `main`, invoke metered AI or access another project's database. Feedback/diagnostic events used during initial testing must be entirely synthetic and non-personal.

## Selected separate Supabase boundary

| Field | Owner architecture decision | Actual provider status |
| --- | --- | --- |
| Target organization | **Devobs AI Intelligence** | **NOT CREATED / NOT VERIFIED** |
| Plan | **Free** initial synthetic-only evaluation | Account eligibility **UNVERIFIED** |
| Proposed project | `devobs-p01-staging` | **NOT CREATED** |
| Region | Frankfurt `eu-central-1` | Proposal only; owner has not authorized a new provider create |
| Data | Synthetic, no real customer records | No data transfer authorized |
| Existing project | PHONE REPAIR ASSISTANT remains in its existing Free organization | No reads of its tables or changes |
| Later commercial setup | Review Pro organization billing, RLS, independent restoration and OIDC | **P01 NO-GO** |

Supabase documents **two active Free projects across all organizations where the owner is admin/owner**, and that **each organization has separate billing**, so an independent Free organization with one Devobs test project is the appropriate *candidate* (not a guarantee of eligibility). References: https://supabase.com/docs/guides/platform/billing-on-supabase and https://supabase.com/kb/troubleshooting/keeping-free-projects-after-pro-upgrade-Kf9Xm2.

**Tool limitation:** the connected Supabase tool supports listing organizations and creating a project under an existing organization, **not creating a new organization**. Do not bypass this by placing Devobs inside the Phone Repair Assistant organization. Owner action required: from the official Supabase Dashboard organization dropdown choose **New organization** and create a dedicated **Free** organization named `Devobs AI Intelligence`. The official link is https://supabase.com/dashboard/new. **Do not create the project yet**; first report the new org and use account-specific cost quotation, plus separately confirm any nonzero charge before a create action.

## Technical integration sequence, gated

1. **Devobs central runtime (P01):** isolated PostgreSQL service, restricted non-BYPASSRLS database identity, OIDC verifier with issuer/audience/JWKS, and observability. Keep cloud service undeployed pending owner request.
2. **Experiment contract (offline):** minimal versioned payload carrying `tenant_id`, `project_id`, trust level, source, bounded synthetic event and correlation ID; reject unknown tenants, mismatched project scope and unsigned external event sources. Only ingest after a trusted identity layer exists.
3. **AI intelligence (offline first):** run AI-1–AI-7 deterministic synthetic simulations and separate AI-9 quality evaluation; no self-deploy or paid inference without explicit approval.
4. **Pilot:** read-only advice to designated experiment actor, with audit and measurement. No cross-project database reads or direct changes to actual phones/storefront.
5. **Commercial:** only after P01–P12 release gates, real RLS/restore tests, business/legal readiness, and cost reviews.

## Verifiable local policy

The [control-plane manifest](devobs_experiment_policy.json), [validator](../../scripts/check_devobs_experiment_policy.py), and [negative tests](../../tests/test_devobs_experiment_policy.py) enforce the **proposal-only** architecture. Validating the policy proves neither a connected Supabase organization nor tenant SaaS readiness.

```sh
python3 scripts/check_devobs_experiment_policy.py
python3 -m unittest discover -s tests -p 'test_devobs_experiment_policy.py' -v
```

**Spend boundary:** the owner's $100/month operating target remains planning-only. No provider project creation or subscription activation is authorized by this architecture decision.

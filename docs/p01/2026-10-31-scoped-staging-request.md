# P01 — account inspection and scoped staging authorization packet

> **New owner screenshot supersedes the earlier inventory snapshot (2026-10-31):** separate **Devobs AI Intelligence Free** organization **and one project** are visible in Supabase UI; both linked API aliases still return only the old organization. Project identity and region are **unknown**. The original findings and `DRAFT_ONLY_NO_GO` request below are historical and **must not be used to create another Devobs project**. Reconcile the existing project first. [Detailed evidence](2026-10-31-supabase-owner-ui-evidence.md).

**Observed:** 2026-10-31. **Owner authorization:** read-only plan/resource/cost investigation and preparation of this scoped packet, **not** cloud provisioning or spending. **Status:** `DRAFT_ONLY / P01 NO-GO`.

**Inspected source:** Protected Devobs `main` at `e1e4223ff9853109b66972e7ba997a81240f9639` and the separate consolidated review branch. No provider settings, secrets, deployments, customer data or payment methods were changed, nor was a cloud resource created. No service/deployment can be inferred from a provider project alone.

## Sanitized observations from connected accounts

| Provider / scope | VERIFIED via connector | UNVERIFIED / consequence |
| --- | --- | --- |
| Render | One connected `My Workspace` is visible. Postgres and Key Value list endpoints reported no resources. `list_services(includePreviews=true)` returned `null`. | `null` is indeterminate (not zero services). Workspace plan, active compute/egress/build billing, payment-method presence, outstanding charges and commercial eligibility cannot be read by current connector. **No new Render service approved.** |
| Supabase | One organization currently reports plan `free`, tier `tier_free`. One existing active project belongs to **Phone Repair Assistant v2**, in region `ap-south-1`. | No Devobs database. Do not inspect or repurpose unrelated project data. Subscription renewal, other billing charges, eligibility for another Free project, and authorization to create a new organization/project are unknown. |
| Vercel | One connected team has **seven listed projects**, including `devobs` and `devobs-staging`. Both project detail APIs report latest deployment `READY`. | READY means a Vercel deployment record succeeded; it does **not** prove the required hosted API, RLS isolation or production SLA. Team plan and account invoice remain unknown. October billing-aggregates endpoint returned `404 costs_not_found` (not a zero-dollar bill). Leave all Vercel deployments unchanged; Hobby is non-commercial. |
| Auth0 | No account connector was available to inspect. | Identity tenant, region, Free-plan entitlement, JWKS issuer and any account-specific charges remain entirely UNKNOWN. |

No account IDs, email addresses, project IDs, secret values, payment instruments, live logs or customer data are reproduced here. These are evidence-limited read-only observations, not contract quotes.

## Public tariff research — NOT account-specific quotes

| Item | USD/month published base | Conditions |
| --- | ---: | --- |
| Synthetic-only Render Free web | $0 compute | Not production suitable; idles after 15 minutes, build/bandwidth limitations; initial creation/deploy can be public-facing |
| Synthetic-only separate Supabase Free DB | $0 plan | Another standalone project/organization requires explicit approval, quota eligibility, specific Frankfurt `eu-central-1` and synthetic-only data; Free lacks managed backups |
| Commercial Render Starter web | $7 compute | One 0.5 GB web instance at list price; capacity and SLA unmeasured |
| Render Hobby/Pro workspace | $0 / $25 | Actual connected workspace plan UNKNOWN; Pro relevant to production-grade operations |
| Commercial Supabase Pro DB-only first Micro project | $25 | In its own separate Pro organization; includes eligible Micro compute credits; extra project compute and overages charge separately |
| Auth0 Free | $0 if eligible | Free listing up to 25k monthly active users; no connected Auth0 tenant/entitlement verified; some features may need verification/billing |
| Vercel currently connected projects | unknown | No measured billing, do not include them as zero or assume commercial-use rights |
| Paid AI inference | $0 **only when disabled** | No OpenAI/Vertex/Claude metered calls are authorized in P01 |
| Backup, domain, egress/build, taxes, other add-ons | unknown | Must obtain actual account-specific costs before new paid commitments |

**Illustrative commercial recurring base excluding unknown Vercel, backup, overages, identity upgrades, tax and AI:**
- Render Hobby workspace + Starter web + separate new Supabase Pro organization/one Micro database + Auth0 Free: `$0+$7+$25+$0 = $32/month`.
- Render Pro workspace + Starter web + Supabase Pro + Auth0 Free: `$25+$7+$25+$0 = $57/month`.

**Only the second case is the preferred candidate for a production-grade workspace,** subject to proving its additional services fit the approved planning allocation of $60 core / $20 metered / $20 reserve. A $57 base leaves only $3 in the core allocation; **do not buy** backup add-ons or other subscriptions based on this nominal headroom. The owner-approved *target* is **$100/month total**, not a binding invoice ceiling. Any actual expense needs separate precise authorization.

## Sequential proposal — no execution authorization in this packet

1. **P01-A completed (read-only):** connected account inventory and tariff sources, with all unknowns preserved. Existing Vercel projects and Phone Repair Assistant v2 remain untouched.
2. **P01-B outstanding:** operator verifies Render workspace subscription, upcoming invoice and any paid add-ons; Supabase Free account eligibility and the price of a **new dedicated Devobs organization/project**; existing Vercel plan/usage/charges; Auth0 tenant availability and paid feature requirements. Do not read or transmit payment instrument details or secrets. Without full billing totals, keep paid activity blocked.
3. **P01-C separate approval required:** choose the exact new Devobs project/provider account, `Frankfurt / eu-central-1`, spending category (Free **synthetic only** or a specified paid SKU), service name, potential public exposure, expected total, and rollback/deletion path. Initial Render creation may deploy immediately. Creation is NOT included in the owner's read-only consent.
4. **P01-D after scoped approval:** create a separate synthetic-only Devobs database (never the repair project); configure least-privilege DSN `sslmode=verify-full`, an OIDC issuer/JWKS under approved tenant, RLS denied-cross-tenant integration, encrypted offsite backup and isolated restore. No production data.
5. **P01-E independently verified:** record OIDC issuer/audience, restricted role, RLS tests, 24h RPO/RTO restore, telemetry, contractual data region, operation costs and signed owner GO before production staging. P02–P12 and paid AI still require separate gates.

## Formal owner authorization required for any next write

**Only after account-specific costs become visible**, request an explicit choice of *one resource/action* with a verified account/region, Free or paid plan, actual monthly/fixed cost, fee/tax uncertainty and public-network consequences. The owner may approve one synthetic-only resource while rejecting others. An approval to review a plan is **not** an approval to create a project, upgrade a subscription or enable a deployment.

## Official provider references (current as inspected)

- Render service limitations: https://render.com/docs/free
- Render compute and workspace subscription pricing: https://render.com/pricing
- Supabase pricing: https://supabase.com/pricing
- Supabase billing separation across organizations: https://supabase.com/docs/guides/platform/billing-on-supabase
- Supabase precise Frankfurt region: https://supabase.com/docs/guides/platform/regions
- Supabase cost-control exclusions: https://supabase.com/docs/guides/platform/cost-control
- Auth0 plan listing: https://auth0.com/pricing
- Vercel Hobby non-commercial limitations: https://vercel.com/docs/plans/hobby

**Final decision:** P01 stays **NO-GO / PREPARATION ONLY**. No external resources, payment changes, migrations, secrets or metered AI were provisioned for this packet.

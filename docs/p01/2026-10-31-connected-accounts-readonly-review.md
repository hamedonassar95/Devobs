# P01 — connected-account billing and plan review (sanitized)

**Observed:** 2026-10-31 (review session). **Decision:** **NO-GO / BLOCKED**.
**Repository baseline:** `e1e4223ff9853109b66972e7ba997a81240f9639`; separate review branch: `feat/p01-free-only-budget-guard-20261031`.
**Scope:** read-only observations from the currently linked Render and Supabase connectors and available plugin discovery. No account billing method, secret, project data, invoices, cloud consoles, keys, database SQL, service logs, or production resources were read or changed. Do not treat this as a signed provider statement or live staging proof.

## Evidence and limits

| Provider | Current account observations (sanitized) | What remains unverified |
| --- | --- | --- |
| Render | Both available connector aliases returned the same workspace metadata. The service-list response was `null` (indeterminate, **not** evidence that zero services exist); the PostgreSQL list said no instances found, and Key Value list said no instances found. | Workspace **plan**, payment-method presence, remaining usage, supplementary charges, invoices, billed add-ons, suspended services and total-invoice cap. No billable-scope guarantee is established. |
| Supabase | Both connected aliases resolved to the same organization. Its organization details reported **plan `free`** and **tier `tier_free`**. Project listing returned **one existing active project** unrelated to the planned Devobs staging. | Payment-method presence, unsettled charges, add-ons, other billing obligations, room for another Free project, and separately approved region/isolation. Existing unrelated project must **not** be repurposed. |
| Auth0 | No Auth0 connector is exposed among the currently available connected tools; plugin directory query for Auth0 returned no match. **No account inspection occurred.** | Whether an Auth0 account exists, its Free-tier eligibility, paid features/trials, payment obligations, tenant region, identity/JWKS configuration and issuance behavior. |

The results above are **verified connector observations**, not independently authenticated provider invoices or contractual commitments. Listing an account's plan is not sufficient to establish a total monthly invoice ceiling.

## Published terms — reference only, not account attestation

- [Render Free instances](https://render.com/docs/free) explain included quotas and service suspension without a payment method; [Render FAQ](https://render.com/docs/faq) explicitly warns that Free instances can incur charges when a payment method is attached. The workspace plan and its service compute plan are separate decisions.
- [Supabase Free pricing](https://supabase.com/pricing) advertises a Free plan, a maximum of two active Free projects and pausing inactive Free projects; its paid tiers have managed backups. No account-specific bill or guarantee is established here.
- [Auth0 pricing](https://auth0.com/pricing) documents a public Free offer; no authenticated account evidence is available.

## P01 acceptance matrix after this review

| Required gate | State | Reason |
| --- | --- | --- |
| Complete USD 100/month invoice enforcement | **BLOCKED** | Render billing and add-ons unknown; Supabase Free confirmed at org-plan level only; Auth0 not connected. No verifiable combined ceiling covers fees/taxes/overruns. |
| Provider/account and region approval | **BLOCKED** | No owner-approved dedicated P01 provider set, region, data terms or staging account selection. |
| OIDC issuer/JWKS and token lifecycle | **BLOCKED** | Auth0 account unverified; offline code is not proof of live identity. |
| Live PostgreSQL RLS and cross-tenant denial | **BLOCKED** | Only existing disposable CI fixtures are evidenced; do not reuse unrelated Supabase data. |
| Backup and isolated restore | **BLOCKED** | No approved P01 backup, restore transcript or measured RPO/RTO. |
| Owner decision / independent release gate | **BLOCKED** | Prior owner-signed conditional NO-GO is unchanged; no staging GO was given. |

`docs/p01/zero_bill_candidate.json` must remain unchanged: its payment-method, add-on, outstanding-charge and auto-upgrade flags stay `null` until the intended operator verifies each item via appropriate account-level evidence. The existing checker deliberately fails closed.

**Single next owner action:** confirm or provide *non-sensitive yes/no status only* for the Render workspace plan, whether any payment method/paid add-on/pending charge is present, and Auth0 account Free-plan eligibility (if that account exists). Do **not** share payment numbers, screenshots of cards, billing addresses, private account IDs, tokens, or credentials. Even all-positive self-reported answers are a *review input*, **not** an enforceable USD 100 invoice guarantee or permission to create resources.

**No changes:** This report adds no provider resources, no billing actions and no modification to `main`, CI security settings, application functionality or the owner-signed P01 decision. A GitHub push to this documentation branch may trigger existing CI and Vercel preview automatically; its success does not certify production SaaS readiness.

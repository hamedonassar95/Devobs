# P01 budget blocker: zero-bill staging candidate — not an approval

**Status: P01 NO-GO / BLOCKED.** Snapshot tied to main SHA e1e4223ff9853109b66972e7ba997a81240f9639 (2026-10-30 UTC). No accounts, billing consoles, provider services, payment methods, secrets or production data were accessed. This is a non-deploying architectural alternative, **not** confirmation that Devobs has a zero invoice or a provider-guaranteed USD 100 all-in hard cap.

## Decision and official evidence

The owner conditionally authorized **at most USD 100 for the entire monthly P01 invoice**, not simply a compute-usage threshold. The signed P01 NO-GO, Railway evidence, P00–P12 roadmap and STATE remain authoritative. Budget alerts, application rate limiting and GitHub CI **cannot** enforce a cloud-provider invoice ceiling.

| Candidate | Official evidence | Safety limitations and unknowns |
| --- | --- | --- |
| **Render Free** web service | [Free services](https://render.com/docs/free) and [billing FAQ](https://render.com/docs/faq): without a payment method, included-bandwidth exhaustion suspends Free services and exhausted build minutes disable new builds instead of incurring specified supplemental fees. | Verify actual workspace plan, absence of a payment method, custom domains, add-ons, historic charges and other obligations. Free services sleep, have ephemeral storage, can be suspended for outbound traffic and are **not production-ready**. |
| **Supabase Free** managed PostgreSQL | [Official cost control](https://supabase.com/docs/guides/platform/cost-control) states that the Free Plan does not charge; [billing FAQ](https://supabase.com/docs/guides/platform/billing-faq) describes Free quota restrictions. | Verify actual organization plan, no paid organizations/resources/add-ons/balance and account-specific terms. Free projects may pause and **do not supply automated managed backups**. |
| **Auth0 Free** identity provider | [Official pricing](https://auth0.com/pricing) documents a Free tier with quota-limited identities and machine-to-machine authentication. | Confirm free account and eligible RS256/OIDC token profile, claims, tenant region and JWKS lifecycle; paid feature and trial constraints are unverified. |

**Why the previous options do not meet the condition:** Railway publishes [separate Compute/Agent limits](https://docs.railway.com/pricing/cost-control); the repository-recorded support reply reports continuing storage/backup charges and no maximum overrun. AWS [limits pre-tax project costs](https://docs.aws.amazon.com/accounts/latest/reference/create-spend-limit.html), not necessarily the entire invoice. Neither is a proven all-in USD 100 invoice cap for Devobs.

**Free-only architectural option:** Use only the three Free-tier services for **synthetic-data-only staging**. Before even considering activation, separately verify each account has **no payment method, no paid addons, no automatic paid upgrade, no pending charges, no other billable services**, and confirm applicable provider terms. Lack of a card is **not necessarily** a legally enforceable all-in cap. The owner must still approve independently adequate cost evidence and every other P01 requirement.

## Conservative offline guard

- The versioned `docs/p01/zero_bill_candidate.json` deliberately stores null for *every* account/billing assertion. Never change it to true based only on marketing or a generic Free plan. Never commit account details or invoices.
- `scripts/check_p01_zero_bill_candidate.py` rejects non-Free plan, wrong SHA, missing account, paid addons, payment method, auto-upgrades, unresolved historic charges, and external billable services.
- A fixture with every flag true produces **REVIEW_ONLY / NO-GO**, not independent billing verification or deployment authorization. Current fixture returns exit code 1 (fail-closed).
- This offline script is not connected to production deployments and does not modify `scripts/check_p01_evidence.py` or the required security checks.

## Remaining acceptance matrix

| Gate | Outcome and required proof |
| --- | --- |
| Combined <= USD 100/month | **BLOCKED:** no account-level billing evidence or complete-invoice guarantee. |
| Provider and region | **BLOCKED:** Render/Supabase/Auth0 are candidates, not chosen accounts; confirm regions and processing agreements. |
| OIDC/JWKS | **BLOCKED:** require real verified issuer, claims, trusted JWKS, expired-token rejection, key rotation/revocation. |
| PostgreSQL RLS | **BLOCKED:** disposable-CI tests cannot prove hosted non-owner/non-BYPASSRLS role, FORCE RLS and cross-tenant rejection. |
| Recovery | **BLOCKED:** Supabase Free has no automatic managed backup. Require encrypted, off-site daily logical exports retained 7 days and isolated restore evidence (RPO <= 24h, RTO <= 24h); see [Supabase backup guidance](https://supabase.com/docs/guides/platform/backups). Never store dumps or credentials in Git. |
| Owner/release | **BLOCKED:** existing owner P01 NO-GO stands until an exact-scope signed decision based on independently checked evidence. |

**Single next owner decision:** Whether to authorize evaluating the Free-only synthetic staging candidate (Render Free + Supabase Free + Auth0 Free), with **read-only plan/billing checks only** and **no resource creation**, no payment method, no paid upgrades, no deployments and no data transfers. Approval to evaluate **is not** P01 GO.

## Reproducible offline checks

Run at the repository root:

- `python3 -m unittest discover -s tests -p 'test_p01_zero_bill_candidate.py' -v`
- `python3 -m compileall -q scripts/check_p01_zero_bill_candidate.py tests/test_p01_zero_bill_candidate.py`
- `python3 scripts/check_p01_zero_bill_candidate.py --file docs/p01/zero_bill_candidate.json --expected-sha e1e4223ff9853109b66972e7ba997a81240f9639` (expected exit **1**, NO-GO).

These checks do not query any provider or prove an account guarantee.

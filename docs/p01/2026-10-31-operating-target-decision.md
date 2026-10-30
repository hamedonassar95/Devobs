# P01 financial-policy revision — owner-directed operating target

**Recorded: 2026-10-31. Source: owner's explicit selection in ChatGPT conversation; GitHub owner signature/approval has NOT been collected.** This note records the user's financial planning choice. It supersedes only the **earlier demand for a provider-guaranteed USD 100 monthly all-in invoice cap**, *not* the rest of the P01 NO-GO or P00–P12 gates. This document is a proposal/review record, **not a provider contract or P01 GO**.

## Approved policy choice vs actions NOT approved

| Aspect | Current authority |
| --- | --- |
| Financial policy | **TARGET** USD 100/month across *all* planned providers, workspace subscriptions, compute, database, identity, paid AI, storage/backup, egress/build, fees and taxes. Actual invoices **may exceed** target. |
| Owner consent in conversation | **Budget policy selection accepted**. No explicit paid resource/service/account consent, no financial instrument, and no production release approval. |
| Target allocation | Up to **USD 60** planned core recurring services, **USD 20** planned metered activity, **USD 20** unallocated reserve. **Allocation is not consent to charge** any part of it. |
| Internal alerts (future configuration) | Monitor forecast at **50%, 75%, 90%, 100%** of $100; require human review before new paid commitments at **$75 forecast**; recommend pausing avoidable metered usage at **$80 forecast**. These are policy-advisory levels, not live integrated controls or a hard provider spending stop. |
| Unverified costs | Missing estimates, failed billing evidence or unknown active accounts **fail closed** for additional paid activity, including paid AI. |
| Current branch vs main | Protected main SHA snapshot `e1e4223ff9853109b66972e7ba997a81240f9639`; improvements remain only in independent review branch until formally merged. |
| Phase status | **P01 NO-GO / BLOCKED**; no account, region, hosted identity, PostgreSQL RLS deployment, backup restore, or SaaS launch has been verified. |

## Why this policy is necessary

- [Render billing](https://render.com/docs/faq): paid instances, storage, build-pipeline minutes, and outbound bandwidth are billed separately; [Render 2026 workspace plans](https://render.com/changelog/updated-plans-for-render-workspaces) distinguish Hobby/Pro subscription fees from compute. Account-specific subscription remains UNKNOWN.
- [Supabase official Spend Cap](https://supabase.com/docs/guides/platform/cost-control) applies only to selected usage categories and excludes compute/PITR and several add-ons. It cannot enforce the full Devobs budget.
- [OpenAI prepaid API billing](https://help.openai.com/en/articles/8264644-setting-up-and-managing-prepaid-api-billing) explains that a negative balance may occur before the cutoff completes; auto-recharge limits are not absolute inference caps. All paid AI remains disabled unless separately approved.
- [GitHub budgets](https://docs.github.com/en/billing/how-tos/set-up-budgets) can offer provider-side stop-usage on supported meter types when selected, but an alert-only budget does not stop spend. No account configuration has been changed.

## Next transition — planning to controlled P01 staging

1. **Account pricing and location** (read-only): identify eligible Render web/workspace plans, standalone Devobs Supabase project/region and IdP plan and region, plus every billable usage class. Existing Supabase Phone Repair Assistant v2 remains separate and untouched.
2. **Pre-purchase estimate & separate scoped authorization:** owner reviews actual month-one expected recurring charges, backup service cost, maximum feasible metered usage, data terms, and risk of overshoot. If the proposed recurring base exceeds $60, revise allocation with a fresh owner decision. **No spending is authorized by this document.**
3. **Hosted synthetic P01 tests after explicit create permission:** OIDC issuer/audience/JWKS, a restricted non-BYPASSRLS PostgreSQL service role and cross-tenant-denial tests; encrypted offsite backup and isolated restore proving RPO/RTO 24h; operational kill-switch and spend-alert checks; no customer data.
4. **New P01 signoff with exact evidence** before P02 or production; commercial SaaS requires later independent gates.

## Machine-verifiable, not bill-certified

`operating_budget_policy.json` is the agreed *non-spending* policy record. `scripts/check_p01_operating_budget.py` reports advisory threshold actions from explicitly supplied untrusted numeric estimates. It never contacts providers or authorizes activity, and always returns a nonzero status even for positive claims.

```sh
python3 -m unittest discover -s tests -p 'test_p01_operating_budget.py' -v
python3 scripts/check_p01_operating_budget.py --expected-main-sha e1e4223ff9853109b66972e7ba997a81240f9639
# Expected exit 1; NO-GO.
```

**Boundaries remain:** historical owner-approved conditions, decision packets, source SHAs and original support notes are preserved unchanged for audit. This document explicitly supersedes only the hard-ceiling *policy choice*, not historical facts. Approval to spend, create, deploy or operate production must be independent and recorded at the time of that action.

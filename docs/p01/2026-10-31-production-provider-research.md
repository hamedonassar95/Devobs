# Devobs P01 → commercial pilot: provider and AI cost review

**Evidence snapshot:** 2026-10-31. **Decision: NO-GO / BLOCKED.** Inspected protected `main` = `e1e4223ff9853109b66972e7ba997a81240f9639`; the GitHub Pages static site and passing CI **do not prove a live tenant-isolated SaaS**. Official public pages are *policy research*, not provider/account invoices. No new account, billing instrument, secret, resource, AI API invocation or deployment was created.

## Recommendation

**Use two explicit environments rather than an unverified one-size-fits-all free stack.**

1. **P01 synthetic only:** the existing Render Free + a **new separate** Supabase Free PostgreSQL project + independently configured OIDC may be evaluated *after separate approval* of account, region, billing, restoration and creation. Existing Phone Repair Assistant v2 Supabase data must not be reused. Render Free is explicitly **not for production**. An unapproved account or unavailable Auth0 tenant is still a blocker.
2. **Commercial pilot candidate (not selected or purchased):** Render Starter + Supabase Pro PostgreSQL + Free-eligible OIDC and **deterministic, no-paid-model default**. Published starting prices are **USD 7 Render web compute + USD 25 Supabase Pro = USD 32/month** *if a Render Hobby workspace is appropriate for this workload*. Render also publishes a **USD 25/month Pro workspace** for teams deploying production-grade apps, making the indicative combined base **USD 57/month** when it is needed. The user's actual Render workspace plan and commercial eligibility remain **UNVERIFIED**. Both figures are *before* usage, taxes, extra providers, AI inference, extra compute, storage, backups, and other services. This is a base-price estimate only, **not** an enforceable total monthly ceiling. Confirm Supabase Micro compute credit, number of projects, Render workspace plan, data-processing terms, invoice details and restoration RPO/RTO before any P01 GO.
3. **AI inference:** keep AI-1–AI-7 deterministic/local and AI-9 experimental. Do not enable OpenAI/Vertex/Claude/Copilot metered calls automatically merely because a token is configured. Paid AI must have separate per-tenant quotas, caller authorization, human approval and an independently validated total-invoice budget. **OpenAI prepaid credit cutoff is not instantaneous**, and turning off auto-recharge is only one safeguard.
4. **Cloudflare experimental branch only:** Workers Free and Workers AI Free have quota-exhaustion behavior useful for a narrow, degradable function. D1 uses **SQLite**, not PostgreSQL; porting the existing PostgreSQL RLS schema is a major redesign and should not displace the tested P01 database design.
5. **Vercel deployment control:** Vercel **Hobby is non-commercial** under its published policy. Any existing Vercel preview success is *not* SaaS commercial-use authorization. Do not make Vercel Hobby the commercial launch target.

## 2026-10-31 provider source register (official)

| Fact | URL | Consequence |
| --- | --- | --- |
| Render Free explicitly not for production; web sleeps; its free Postgres expires after 30 days and has no backups | https://render.com/docs/free | NO-GO for commercial runtime on Render Free |
| Render Hobby workspace $0 plus compute, Pro workspace $25 plus compute; small web compute starts at $7 | https://render.com/pricing | Price assumptions must include workspace and service separately |
| Supabase Free = $0 plan, projects may pause; Pro starts at $25 and includes 7 daily backups | https://supabase.com/pricing | Commercial Postgres candidate subject to controlled restore |
| Supabase Pro spend cap excludes compute, domains, PITR, add-ons and other separately charged items | https://supabase.com/docs/guides/platform/cost-control | No all-in invoice guarantee |
| Supabase separate paid organizations, Free projects quota across owner organizations | https://supabase.com/docs/guides/platform/billing-on-supabase | Check account-level cost and distinct project identity |
| Supabase select explicit Frankfurt `eu-central-1` rather than ambiguous Europe grouping | https://supabase.com/docs/guides/platform/regions | Region proposal only; verify data terms |
| Vercel Hobby is only for non-commercial use | https://vercel.com/docs/limits/fair-use-guidelines | Block commercial deployment there |
| Cloudflare D1 Free fails closed when over quota; uses SQLite | https://developers.cloudflare.com/d1/reference/faq/ and https://developers.cloudflare.com/d1/ | Not drop-in PostgreSQL/RLS |
| Workers Free 100,000 requests/day; Workers AI Free 10,000 neurons/day; exceeding quota fails | https://developers.cloudflare.com/workers/platform/limits/ and https://developers.cloudflare.com/workers-ai/platform/pricing/ | Possible separate AI experimentation; no SLA |
| OpenAI prepaid auto-reload is on by default during setup; credit exhaustion can temporarily run negative | https://help.openai.com/en/articles/8264644-setting-up-and-managing-prepaid-api-billing | Never count prepaid balance as instantaneous cap |

## Conservative eligibility model

- `commercial_pilot_candidate.json` is a **proposed** architecture, not a real configured deployment. All ten invoice components and six live controls are `null`; owner production signoff is `false`.
- `scripts/check_p01_commercial_pilot.py` rejects incomplete/unknown suppliers, prohibits fake owner signoff, rejects Render Free, Vercel Hobby, Supabase Free managed-backup assumptions, D1-for-PostgreSQL substitutions, and AI prepaid hard-cap assumptions. It **always exits nonzero and says NO-GO**, even if someone submits positive assertions; only an independent provider contract, account-specific billing review, signed owner approval and runtime tests can clear P01.
- `python3 -m unittest discover -s tests -p 'test_p01_commercial_pilot.py' -v` exercises the guard.
- `python3 scripts/check_p01_commercial_pilot.py --file docs/p01/commercial_pilot_candidate.json --expected-sha e1e4223ff9853109b66972e7ba997a81240f9639` returns 1 (expected NO-GO).

## Required next gates

**G1 financial**: owner/account-level all-in USD 100/month enforceable cap **including** web compute, Render workspace subscription, DB/identity/AI, egress/build, backups/storage, optional services, taxes/fees and delay/overrun risk. If impossible, owner must expressly revise the hard condition before *any* expense (alerts alone cannot meet it).

**G2 isolation**: independent Devobs database in approved EU region; non-owner/non-BYPASSRLS role, FORCE RLS and adversarial cross-tenant tests on staging; do not repurpose another project's DB.

**G3 identity**: live OIDC metadata/JWKS/audience/issuer/key rotation and denial of malformed/expired tokens using an approved IdP. No raw provider key in repo.

**G4 recovery**: encrypted offsite daily backups, 7-day retention and isolated restore proving RPO ≤24h and RTO ≤24h, including storage objects if any.

**G5 AI**: measure AI-9 on independently preserved acceptance set (current detector fails required gate); no paid model fallback or self-modifying deployment before human approval.

**G6 operations and owner**: monitoring, incident on-call, release rollback, commercial terms/privacy and explicit human P01 GO; later P02–P12 signoffs separate.

**Decision now:** continue offline validation and financial/provider due diligence. **Do not** create external resources or run metered AI/deploy until independently authorized and evidenced.

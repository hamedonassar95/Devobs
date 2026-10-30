# P01 — one review entrypoint (consolidated, non-deploying)

**New owner-supplied Supabase screenshot evidence (2026-10-31):** the Supabase organizations UI shows **Devobs AI Intelligence — Free Plan — 1 project**, separate from the original Free organization (also 1 project). Both connected Supabase aliases still list **only** the old organization and its Phone Repair Assistant project. This is a connector-vs-UI conflict, **not** permission to recreate a Devobs project. The project's **region is now visible as `us-east-1` from the owner's project-list screenshot**, while its full name, operational status and actual billing remain **UNVERIFIED** by the connected API. This conflicts with the proposed `eu-central-1` (Frankfurt) region; no migration or new project is authorized. A later dashboard screenshot now confirms **Healthy / Nano / no GitHub repository connected / no backups** as owner-UI facts, not live tenant isolation or recovery evidence. The connected Supabase API **denied access** to the Devobs project reference. See [the detailed screenshot reconciliation](2026-10-31-supabase-owner-ui-evidence.md). See [evidence reconciliation](2026-10-31-supabase-owner-ui-evidence.md). P01 remains NO-GO.

**Current decision: NO-GO / BLOCKED.** No setup, spending, production access, secrets, customer data, or resource creation is authorized here. Do not rebuild or delete the working Devobs repository. Use the protected `main` as source of truth and review branch changes under normal PR controls. The exact inspected main snapshot was `e1e4223ff9853109b66972e7ba997a81240f9639`; refresh the SHA and CI before any later owner decision.

## Existing evidence consolidated (not new provider proof)

| Need | Evidence/source | Actual status |
| --- | --- | --- |
| P00/P01 authority | [P01 owner decision](../P01_ACTIVATION_READINESS.md) and [roadmap](../plans/2026-10-26-devobs-production-execution-roadmap.md) | P00 GO only; P01 NO-GO; no staging activation |
| Exact-main NO-GO decision | [Seven-control acceptance matrix](2026-10-31-e1e4223-acceptance-matrix.json), [decision packet](2026-10-31-e1e4223-no-go-decision.md) | 7/7 controls blocked, historical main-SHA observation only |
| Connected accounts, sanitized | [Read-only provider inspection](2026-10-31-connected-accounts-readonly-review.md) | Supabase organization Free confirmed; Render billing unknown; Auth0 connection unavailable |
| Local free-only alternative | [Free-only candidate](2026-10-31-free-only-budget-candidate.md), [unknown-by-default fixture](zero_bill_candidate.json) | UNVERIFIED; all account-level billing assertions remain null; script never authorizes GO |
| Advisory review integrity | [Evidence gate script](../../scripts/check_p01_evidence.py), [exact-checkout guard](../../scripts/verify_p01_checkout.py) | Fail closed unless reviewed SHA matches checkout; evidence authenticity and real provider spend not verified |
| Live acceptance | [RLS evidence](../POSTGRES_RLS_STAGING.md) and [staging acceptance](../STAGING_ACCEPTANCE.md) | CI/local synthetic only; no live OIDC, managed RLS, restore or all-in hard cap proof |

**Updated financial policy:** the owner accepted **USD 100/month as an operating target**, *not* a provider-guaranteed all-in invoice ceiling. This supersedes the historical hard-ceiling *for prospective financial planning only*. It does **not** authorize spending, a new subscription, resource creation or P01 activation. See [owner-directed policy](2026-10-31-operating-target-decision.md) and [offline operating budget guard](../../scripts/check_p01_operating_budget.py). Render's connected workspace subscription remains UNKNOWN, and the complete invoice is not verified. The old hard-cap analysis remains in the historical matrix and reports for audit.

A single [Combined preflight](LOCAL_PREFLIGHT.md) produces a machine-readable NO-GO matrix from both source and budget evidence files. Its nonzero exit status is intentional; no completeness check grants deployment approval.

## Core platform and experimental clients (owner decision 2026-10-31)

Devobs AI Intelligence remains the **canonical central control-plane repository**; PHONE REPAIR ASSISTANT and AL-DALA MOBILE are **independent experiment projects**, not shared databases, admin credentials, or automatic deploy targets. The [architecture decision](../architecture/DEVOBS_CORE_EXPERIMENTS.md), [proposed manifest](../architecture/devobs_experiment_policy.json), and [offline invariant checker](../../scripts/check_devobs_experiment_policy.py) document this boundary. The target **new separate Supabase Free organization** has **not** been created. The existing phone-repair project must never be reused for Devobs. Production/publishing and paid AI remain unauthorized.

## Scoped provider approval packet (2026-10-31)

The [sanitized account review and scoped staging request](2026-10-31-scoped-staging-request.md) records connected Render/Supabase/Vercel observations, the 404 (not zero) Vercel billing result, published cost examples and the exact **independent owner authorization required before any create/deploy**. Its [machine-readable request](p01-staging-authorization-request.json) remains `DRAFT_ONLY_NO_GO`. Run `python3 -m unittest discover -s tests -p 'test_p01_staging_request.py' -v` to verify that read-only consent never becomes spend permission.

## Current commercial-provider evidence

[October 31 provider/AI cost research](2026-10-31-production-provider-research.md) documents current official restrictions and a conservative commercial candidate. The [offline commercial target manifest](commercial_pilot_candidate.json) remains NO-GO with invoice and live-runtime proof unknown. `python3 -m unittest discover -s tests -p 'test_p01_commercial_pilot.py' -v` tests the guard, and `python3 scripts/check_p01_commercial_pilot.py --expected-sha e1e4223ff9853109b66972e7ba997a81240f9639` must exit 1 and report NO-GO, without provider actions.

## Offline verification (safe, no credentials)

For the new operating target, use `python3 -m unittest discover -s tests -p 'test_p01_operating_budget.py' -v` and `python3 scripts/check_p01_operating_budget.py --expected-main-sha e1e4223ff9853109b66972e7ba997a81240f9639` (expected exit 1 / NO-GO). These checks evaluate internal policy only, not the provider bill.

```sh
python3 -m unittest discover -s tests -p 'test_p01_evidence.py' -v
python3 -m unittest discover -s tests -p 'test_p01_checkout.py' -v
python3 -m unittest discover -s tests -p 'test_p01_decision_packet.py' -v
python3 -m unittest discover -s tests -p 'test_p01_zero_bill_candidate.py' -v
python3 -m compileall -q scripts/verify_p01_checkout.py scripts/check_p01_evidence.py scripts/check_p01_zero_bill_candidate.py
```

Both these **expected fail-closed** data checks must exit with code 1 while the claims are unverified:

```sh
python3 scripts/check_p01_evidence.py --file docs/p01/evidence.json --expected-sha e1e4223ff9853109b66972e7ba997a81240f9639
python3 scripts/check_p01_zero_bill_candidate.py --file docs/p01/zero_bill_candidate.json --expected-sha e1e4223ff9853109b66972e7ba997a81240f9639
```

**Next controlled stage:** obtain non-secret, account-specific provider/region, recurring-price and billing evidence under the new *target* policy; secure explicit scope-limited approval for any paid resources or staging creation, then prove OIDC/JWKS, tenant RLS and encrypted restore in a separately authorized synthetic staging environment. The [operating-target decision](2026-10-31-operating-target-decision.md) does not itself create a GO or justify spending.

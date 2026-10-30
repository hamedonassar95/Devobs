# P01 — one review entrypoint (consolidated, non-deploying)

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

**Hard blocker:** the owner's **USD 100/month complete-invoice ceiling** includes all services, storage/backups, recurring fees, taxes and possible overrun. Railway cannot meet the requirement based on the repository-recorded support answer; AWS project limits apply pre-tax; an assertion that a provider offers a Free plan is **not** a guaranteed billing cap. The connected Render tools do not expose the workspace subscription. Do not guess Hobby/Pro or require the owner to know it.

A single [Combined preflight](LOCAL_PREFLIGHT.md) produces a machine-readable NO-GO matrix from both source and budget evidence files. Its nonzero exit status is intentional; no completeness check grants deployment approval.

## Offline verification (safe, no credentials)

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

**Next owner decision, only after new evidence:** choose an eligible provider/region and accept a proven combined all-in billing mechanism. Until then keep `main` healthy and prepare only offline security, identity and recovery tests. No production/paid action is justified by this packet.

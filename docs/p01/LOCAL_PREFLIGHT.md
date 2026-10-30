# P01 offline combined preflight

This local, read-only command combines the two existing P01 structural assessments. It **never authorizes P01**, even if the supplied JSON claims all checks are VERIFIED. Its output is machine-readable JSON with seven P01 controls and Free-only budget-claim gaps. The owner-signed NO-GO and USD 100 combined monthly invoice condition remain authoritative.

Run from a checkout of this branch:



```sh
python3 -m unittest discover -s tests -p 'test_p01_local_preflight.py' -v
python3 scripts/p01_local_preflight.py --expected-sha e1e4223ff9853109b66972e7ba997a81240f9639 > p01-status.json
# Above returns 1 (expected NO-GO); malformed evidence returns 2.
```

**Snapshot limitation:** The SHA above identifies the historical main evidence baseline, **not** this branch's checkout SHA. This tool does not query GitHub or authenticate evidence owners. Use the separate exact-main-checkout guard in the optional manual workflow for checkout binding, and independently verify the provider/billing/runtime facts before any GO decision.

Expected current results: 7 blocked gates, at least 16 unresolved Free-only billing assertions, a historical evidence source-SHA mismatch, and `resource_creation_authorized=false`. In a report where all JSON fields *claim* VERIFIED, each control becomes `CLAIM_ONLY_UNTRUSTED`, **not GO**. Never commit credentials, invoices, payment methods, or real user data in these fixtures.

After provider and billing evidence is obtained through separately approved read-only means, owner must approve the precise scope and region, and staging still requires live identity, RLS and isolated restore evidence. Do not modify main, provider resources or deployment settings as part of this offline preflight.

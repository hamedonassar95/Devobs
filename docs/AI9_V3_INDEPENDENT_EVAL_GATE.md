# AI-9 v3 — Post-merge status and independent-evaluation decision gate

**Evidence reviewed:** 2026-10-31 UTC. This is an **offline preparation/approval document**, not a command to execute new seeds, a production release or an AI-9 PASS.

## Merged implementation

- [PR #327](https://github.com/hamedonassar95/Devobs/pull/327) merged into `main` at `5982bd239f7fc083163ce99e24f9bc3e20e75f5d`; reviewed PR head `fa87cdb547f927beb82377e112432f62644f4a10`.
- [Required PR CI run 41148812810](https://github.com/hamedonassar95/Devobs/actions/runs/41148812810) passed `validate`, Node, Python, PostgreSQL RLS, Terraform, security and container scan.
- [Stored replay results](AI9_COHERENT_ONSET_V3_REPLAY_RESULTS.md) on **previously consumed** synthetic seed `20270201`: TP=73, FP=8, FN=17, TN=45142, window Precision=90.1235%, Recall=81.1111%, FPR=0.0177%.
- [PR #326](https://github.com/hamedonassar95/Devobs/pull/326), containing the evidence ledger and CI contract, also merged, at `1357cc6b2a4520511fa098bb6c9248be7a2e9172`.
- The `main` CI run, CodeQL and static Pages checks are distinct from the PR CI. Their exact status must be refreshed before operational claims. Green checks never certify production AI-9 or SaaS.

## Frozen independent synthetic holdout

[The original preregistration](AI9_COHERENT_ONSET_V3_PREREGISTRATION.md) requires the **unconsumed** seed set `20270601`, `20270602`, `20270603`, `20270604` to be run once, in order, **only after a separate owner authorization**. The user's PR merge is not treated as permission to consume the holdout.

Before running any holdout:
1. Confirm current `main` and exact commit, PR merge, required `validate`, CodeQL and source integrity. Freeze the v3 algorithm, comparator, generator, score thresholds and per-seed dataset contract. **Do not tune** after looking at holdout results.
2. Verify all four seed identifiers are collision-free against current and historical GitHub source and previous evaluation artifacts. A collision invalidates this trial, not just that seed; do not substitute another seed.
3. Implement and independently review an **explicit manual-only evaluator** in a separate PR if not already present. It must reject other seeds, fail closed on digest/shape/count errors, avoid unapproved network and secret access, and ensure ordinary CI/unit tests cannot consume holdout seeds.
4. Secure **separate explicit owner authorization** for that single run, listing the exact four seed IDs, evaluated HEAD SHA and deterministic no-fee local runtime. Until approved, do not run the evaluator.
5. On the authorized one-time run, report separately per seed: canonical input SHA256, 56 services, three metrics each, 45,240 scored metric windows (90 positives, 45,150 negatives), TP/FP/FN/TN, Precision, Recall, FPR, first positive delay and missing detections. Preserve complete failure cases as evidence, not raw private data.
6. Every seed must independently meet Precision >=80%, Recall >=80% and FPR <=5% to describe an independent **synthetic-only** pass. Do not pool results to hide failed seeds or run again based on results.
7. Even after a synthetic pass, the AI-9 release gate stays **BLOCKED** pending labelled real incidents, provenance and privacy permission, authenticated tenant boundaries, resource budget, drift/alert-burden analysis and an explicit production decision. P01 stays **NO-GO / BLOCKED**.

## Research-informed supplementary checks

- A [2026 study on event-level evaluation](https://www.mdpi.com/2076-3417/16/11/5450) warns that point-adjusted metrics can overstate incident-level utility. Keep frozen window gates authoritative, and later add event-level latency/coverage as *descriptive* metrics rather than retroactive replacement of required gates.
- The [TAB unified time-series anomaly detection benchmark](https://doi.org/10.14778/3746405.3746407) emphasizes evaluation consistency across multiple datasets. Consider external open datasets only in a **separate** experiment, without borrowing them for or changing the sealed v3 holdout.
- Untrusted input and false confidence in a CI-only result are not sufficient grounds to enable automated remediation or production actions.

## Owner decision needed for the next restricted step

No model, repository workflow or automation can authorize this decision. Explicitly approve **the one-time offline holdout on the exact seed set** after manual-only evaluator review; otherwise continue with read-only exploration, evaluator design and tests on hand-crafted or already-consumed fixtures.

**Current final state:** `AI-9 = FAIL / NOT AUTHORIZED`, `P01 = NO-GO / BLOCKED`. No live model, cloud resource, paid service or tenant database has been activated by this work.

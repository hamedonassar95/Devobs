# AI-9 v3 — Post-merge status and independent-evaluation decision gate

**Evidence reviewed:** updated 2026-11-01 UTC. This is an **offline evidence and decision document**, not a production release or an AI-9 production PASS.

## Frozen holdout execution — completed once

- **VERIFIED:** The owner authorized the exact one-time, no-fee synthetic run on PR [#357](https://github.com/hamedonassar95/Devobs/pull/357), bound to evaluated `main` SHA `80dbcb3466c1368662190736a442d1082e7f2b54`, registration `ai9-coherent-onset-v3`, and seeds `20270601`–`20270604`. Each reserved seed was consumed once, in registered order; do not rerun or substitute seeds.
- **VERIFIED:** The stored evaluator record is [`AI9_V3_FROZEN_HOLDOUT_RESULTS.json`](AI9_V3_FROZEN_HOLDOUT_RESULTS.json), with result `ALL_FROZEN_WINDOW_GATES_PASS`. All four seeds independently passed the frozen window gates (Precision >=80%, Recall >=80%, FPR <=5%). Candidate v3 results:

  | Seed | TP / FP / FN / TN | Precision | Recall | FPR | Missing detections | Maximum delay |
  | --- | --- | ---: | ---: | ---: | ---: | ---: |
  | 20270601 | 75 / 4 / 15 / 45,146 | 94.9367% | 83.3333% | 0.008859% | 0 | 0 windows |
  | 20270602 | 77 / 5 / 13 / 45,145 | 93.9024% | 85.5556% | 0.011074% | 0 | 0 windows |
  | 20270603 | 76 / 8 / 14 / 45,142 | 90.4762% | 84.4444% | 0.017719% | 0 | 0 windows |
  | 20270604 | 75 / 0 / 15 / 45,150 | 100.0000% | 83.3333% | 0.000000% | 0 | 1 window |

- **VERIFIED, repository CI only:** PR #358 records this evidence. Its required PR CI [run 41359194103](https://github.com/hamedonassar95/Devobs/actions/runs/41359194103), CodeQL [run 41359222608](https://github.com/hamedonassar95/Devobs/actions/runs/41359222608), and GitHub Advanced Security [run 41359229242](https://github.com/hamedonassar95/Devobs/actions/runs/41359229242) succeeded. On merge SHA `3eb987a85c2d85071ad760b205e6f5c84a3ab586`, main CI [run 41359551458](https://github.com/hamedonassar95/Devobs/actions/runs/41359551458) succeeded, including `validate`, Pages publish and `verify-production`; its docs-only path condition skipped Python and Node tests. Main CodeQL [run 41359550746](https://github.com/hamedonassar95/Devobs/actions/runs/41359550746) and Vercel status succeeded.
- **Limits:** This evaluates four draws from the existing synthetic generator, not independently sourced real incident labels or real-world generalization. It does not change the production detector or establish live tenant isolation, drift behavior, alert burden, operating cost, or production safety. **Official AI-9 remains FAIL / NOT AUTHORIZED; P01 remains NO-GO / BLOCKED.** No live resource, customer data or paid inference was used.

## Merged implementation

- [PR #327](https://github.com/hamedonassar95/Devobs/pull/327) merged into `main` at `5982bd239f7fc083163ce99e24f9bc3e20e75f5d`; reviewed PR head `fa87cdb547f927beb82377e112432f62644f4a10`.
- [Required PR CI run 41148812810](https://github.com/hamedonassar95/Devobs/actions/runs/41148812810) passed `validate`, Node, Python, PostgreSQL RLS, Terraform, security and container scan.
- [Stored replay results](AI9_COHERENT_ONSET_V3_REPLAY_RESULTS.md) on **previously consumed** synthetic seed `20270201`: TP=73, FP=8, FN=17, TN=45142, window Precision=90.1235%, Recall=81.1111%, FPR=0.0177%.
- [PR #326](https://github.com/hamedonassar95/Devobs/pull/326), containing the evidence ledger and CI contract, also merged, at `1357cc6b2a4520511fa098bb6c9248be7a2e9172`.
- The `main` CI run, CodeQL and static Pages checks are distinct from the PR CI. Their exact status must be refreshed before operational claims. Green checks never certify production AI-9 or SaaS.

## Historical pre-run protocol and approval gate

The requirements below describe the controls that were completed for the one-time run recorded above. They are retained as protocol evidence; they are no longer pending actions.

[The original preregistration](AI9_COHERENT_ONSET_V3_PREREGISTRATION.md) required the seed set `20270601`, `20270602`, `20270603`, `20270604` to be run once, in order, after separate owner authorization. The exact authorization and resulting run are documented above.

Before running any holdout:
1. Confirm current `main` and exact commit, PR merge, required `validate`, CodeQL and source integrity. Freeze the v3 algorithm, comparator, generator, score thresholds and per-seed dataset contract. **Do not tune** after looking at holdout results.
2. Verify all four seed identifiers are collision-free against current and historical GitHub source and previous evaluation artifacts. A collision invalidates this trial, not just that seed; do not substitute another seed.
3. Implement and independently review an **explicit manual-only evaluator** in a separate PR if not already present. It must reject other seeds, fail closed on digest/shape/count errors, avoid unapproved network and secret access, and ensure ordinary CI/unit tests cannot consume holdout seeds.
4. The owner gave separate explicit authorization for the single run, listing the exact four seed IDs, evaluated HEAD SHA and deterministic no-fee local runtime. The authorization has been consumed; it does not authorize any additional evaluation.
5. On the authorized one-time run, report separately per seed: canonical input SHA256, 56 services, three metrics each, 45,240 scored metric windows (90 positives, 45,150 negatives), TP/FP/FN/TN, Precision, Recall, FPR, first positive delay and missing detections. Preserve complete failure cases as evidence, not raw private data.
6. Every seed must independently meet Precision >=80%, Recall >=80% and FPR <=5% to describe an independent **synthetic-only** pass. Do not pool results to hide failed seeds or run again based on results.
7. Even after a synthetic pass, the AI-9 release gate stays **BLOCKED** pending labelled real incidents, provenance and privacy permission, authenticated tenant boundaries, resource budget, drift/alert-burden analysis and an explicit production decision. P01 stays **NO-GO / BLOCKED**.

## Research-informed supplementary checks

- A [2026 study on event-level evaluation](https://www.mdpi.com/2076-3417/16/11/5450) warns that point-adjusted metrics can overstate incident-level utility. Keep frozen window gates authoritative, and later add event-level latency/coverage as *descriptive* metrics rather than retroactive replacement of required gates.
- The [TAB unified time-series anomaly detection benchmark](https://doi.org/10.14778/3746405.3746407) emphasizes evaluation consistency across multiple datasets. Consider external open datasets only in a **separate** experiment, without borrowing them for or changing the sealed v3 holdout.
- Untrusted input and false confidence in a CI-only result are not sufficient grounds to enable automated remediation or production actions.

## Remaining release decision and blockers

The one-time synthetic holdout is complete and its seeds are closed. No model, repository workflow or automation can approve production. A future AI-9 release decision requires independently sourced, privacy/provenance-reviewed labeled incident evidence, authenticated tenant-boundary evidence, drift/alert-burden analysis, and explicit owner approval. P01 separately remains blocked on its spend-enforcement and live staging controls.

**Current final state:** `AI-9 = FAIL / NOT AUTHORIZED`, `P01 = NO-GO / BLOCKED`. No live model, cloud resource, paid service or tenant database has been activated by this work.

# AI-9 Precision gap — frozen synthetic evidence

**Classification:** development-only, offline arithmetic. **Decision:** AI-9 **FAIL**, P01 **NO-GO / BLOCKED**. No gate, detector, source dataset, provider, account or deployment changed.

## Inputs and reproducibility

- Existing preregistration: [AI-9 multimetric confirmation v1](AI9_MULTIMETRIC_CONFIRMATION_V1_PREREGISTRATION.md).
- Existing frozen report: [AI9_MULTIMETRIC_CONFIRMATION_V1_RESULTS.json](AI9_MULTIMETRIC_CONFIRMATION_V1_RESULTS.json).
- Integrity preflight: `scripts/check_ai9_multimetric_evidence.py` recomputes the frozen report's per-seed counts and summaries **internally**, but it cannot independently authenticate the underlying raw events.
- Run: `python3 scripts/check_ai9_precision_gap.py` from the repository root. **Exit 1 is expected** on this historical quality FAIL; exit 2 means invalid evidence. Exit 0 on a hypothetical passing synthetic input would **not** authorize production.
- Focused test: `python3 -m unittest discover -s tests -p 'test_ai9_precision_gap.py' -v`.
- Both scripts are offline and read-only. No estimator, tuned detector, regenerated synthetic input or new holdout was executed.

## Exact fixed-TP arithmetic

The owner-approved window-level Precision gate remains **80%**, Recall **80%**, and FPR **5%**. For each seed:

`Precision = TP / (TP + FP) >= 0.8` implies `FP <= floor(TP / 4)`.

This is integer arithmetic: the allowable FP budget is calculated **separately per seed**, not by imposing a potentially misleading pooled precision gate.

| Observed statistic across all 20 frozen seeds | Value |
| --- | ---: |
| Scored windows | 904,800 |
| Positive windows | 1,800 |
| True positives after confirmation | 1,524 |
| False positives after confirmation | 23,203 |
| Sum of per-seed FP budgets, keeping each TP fixed | 374 |
| Minimum false positives to eliminate, with each TP fixed | 22,829 |
| Reduction from current FP, keeping each TP fixed | 98.3881% |
| Frozen Precision pass count | 0/20 |
| Frozen Recall pass count | 20/20 |
| Frozen FPR pass count | 20/20 |

**Interpretation:** current FPR compliance does not imply adequate Precision when the synthetic base rate is low. Merely reducing false positives by filtering signals may also remove true positives and fail Recall. The fixed-TP assumption is a mathematical scenario **not a validated attainable performance result**. No threshold or production setting should be relaxed to hide this gap.

## Next evidence-first development path

1. Perform **post-hoc exploratory** FP segmentation on the existing already-consumed synthetic fixtures: source family, metric, signal channel, coincidence/persistence reason and boundary windows. Track denominators, overlap and false negatives; do not regard reused seeds as a fresh holdout.
2. Register and freeze a single narrow candidate change **before** running any new independent synthetic seeds. Retain the existing 80% / 80% / 5% window gates and report all metrics, including recall and latency.
3. Keep real telemetry **blocked** until data provenance, privacy/retention authority, service identity and an independently reviewed labeling protocol are approved. Any holdout using real customer data needs separate authorization.
4. Require independent evaluation and an explicit owner decision before a detector rollout. The code and this document are diagnostic only, never an AI-9 PASS or P01 GO.

**Verification limitations:** This calculation validates an algebraic constraint against previously tracked aggregate counts. It neither verifies raw-event authenticity nor establishes detection improvements, operational service readiness or SaaS readiness.

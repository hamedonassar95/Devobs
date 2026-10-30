# AI-9 Z-score / Moving-Average and Grouping Candidate v1 — Preregistration

| Field | Value |
| --- | --- |
| Registration | `ai9-zma-2of3-alert-grouping-v1` |
| Registered | 2026-10-30 11:09:11 UTC |
| Status | REGISTERED — NOT RUN |
| Source snapshot | `e129a8d` on `feature/ai9-synthetic-eval-v2` |
| Comparison policies | production baseline; `ai9-ewma-noise-candidate-v1`; this candidate |

This is a development-only comparison on synthetic data. It does not restore or reproduce the historical AI-9 evaluator. AI-9 remains **FAIL** and P01 remains **NO-GO / BLOCKED**.

## Seed reuse and scope

- Use exactly seeds `20261201` through `20261220`, in ascending order, as requested. These seeds were already used in the prior baseline/v1 comparison. Reusing them permits a paired comparison on identical inputs but is post-selection development evidence, **not an independent holdout or generalization test**.
- For each seed, use the same fixed 56-scenario generator, 15,080 scored windows, 30 positive and 15,050 negative labels, scenario order, PRNG, metric-value rules, timestamps, and schema bounds from [`AI9_SYNTHETIC_EVALUATION_V2_PREREGISTRATION.md`](AI9_SYNTHETIC_EVALUATION_V2_PREREGISTRATION.md). Do not change seed or scenario recipes.
- Compare three predictions on each exact input: (1) the production baseline detector, (2) current `ai9-ewma-noise-candidate-v1`, and (3) the candidate defined below. The run must stop if recomputed baseline/v1 per-seed counts differ from the saved [`AI9_SYNTHETIC_MULTI_SEED_V1_RESULTS.json`](AI9_SYNTHETIC_MULTI_SEED_V1_RESULTS.json).

## Frozen candidate: `ai9-zma-2of3-alert-grouping-v1`

- Keep the EWMA channel exactly as current candidate v1: causal trailing median width 3, alpha `0.3`, baseline 30.
- Keep the production error-rate-spike channel unchanged.
- For each metric series, collect the original production `z_score` and `moving_average` boolean flags at each scored window. A candidate v1.1 `z_score` (respectively `moving_average`) flag is true only if that same channel was true in at least 2 of the current and previous 2 **scored** windows. At series startup, use only scored flags already observed; missing history counts as false. Do not change channel thresholds or the underlying flags.
- Candidate v1.1 window prediction is the OR of confirmed `z_score`, confirmed `moving_average`, current candidate-v1 EWMA, and unchanged production `error_rate_spike`.
- For descriptive alert grouping, merge predicted alert windows for the same metric series when the gap between successive predicted windows is at most 120 seconds. Do not fill quiet windows or alter any per-window prediction. The grouped episode closes after two consecutive observed quiet windows; an open tail remains ineligible. Grouping is reported descriptively and does **not** change window Precision or create an incident gate.

## Frozen assumptions, gates, and summaries

- Keep cadence 60 seconds, baseline 30 points, `before=0s`, `after=120s`, and two observed quiet windows to close.
- Apply the unchanged per-seed window gates to all three versions: Precision `>=0.80`, Recall `>=0.80`, FPR `<=0.05`. Report each version's gate outcomes per seed and counts out of 20. No aggregate acceptance rule is added. Incident-level Precision is not a gate.
- Report TP/FP/FN/TN and seed-level Precision, Recall, FPR. For Precision and FPR report arithmetic mean and population variance over the 20 seed-level proportions; variance is expressed in percentage-points squared. Undefined Precision fails that seed and invalidates the aggregate Precision mean/variance; do not omit it.
- Report grouped alert-episode counts and open-tail counts descriptively using the same closure rule; do not use them to change window gates.
- Record all 20 input digests. Emit aggregate counts/rates only; never print metric series or raw values. Do not use real data, services, network, official evaluation seeds, or locked holdouts.
- Freeze this candidate and run once. No post-result threshold, confirmation-rule, grouping-window, or gate changes. Any later candidate requires a separate preregistration.

## Decision boundary

The 20 seeds are reused development inputs. Even if the new candidate improves the paired means, that is not independent evidence or production authorization. Precision remains window-level as decided by the owner. No candidate is connected to production; no changes here can set AI-9 to PASS or P01 to GO.

**At registration time:** the candidate has not been implemented or scored.

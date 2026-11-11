# AI-9 Synthetic Multi-Seed Evaluation v1 — Preregistration

| Field | Value |
| --- | --- |
| Registration | `ai9-synthetic-multiseed-v1` |
| Registered | 2026-10-30 10:57:32 UTC |
| Status | REGISTERED — NOT RUN |
| Source snapshot | `d75ca5c` on `feature/ai9-synthetic-eval-v2` |
| Prior protocol | `ai9-synthetic-window-evaluation-v2` |

This is a development-only stability check for the existing baseline and candidate on new synthetic draws. It is not the missing historical evaluator, not a real-data validation, and cannot change AI-9 (**FAIL**) or P01 (**NO-GO / BLOCKED**).

## Frozen run plan

- Use exactly these 20 previously unused seeds, once each and in ascending order: `20261201`, `20261202`, `20261203`, `20261204`, `20261205`, `20261206`, `20261207`, `20261208`, `20261209`, `20261210`, `20261211`, `20261212`, `20261213`, `20261214`, `20261215`, `20261216`, `20261217`, `20261218`, `20261219`, `20261220`.
- For each seed, generate the same frozen 56-scenario recipe and 15,080 scored windows from [`AI9_SYNTHETIC_EVALUATION_V2_PREREGISTRATION.md`](AI9_SYNTHETIC_EVALUATION_V2_PREREGISTRATION.md): 30 positive and 15,050 negative windows, same scenario order, metric values, labels, timestamps, and event-schema bounds. Only the seed changes. The two detectors are paired on the exact same generated input for each seed.
- Keep assumptions unchanged: cadence 60 seconds; baseline 30 observed points; `before=0s`; `after=120s`; episode closes after two consecutive observed quiet windows; no synthetic padding.
- Keep detector policies unchanged: production baseline detector and `ai9-ewma-noise-candidate-v1` (causal width-three median for EWMA only, alpha 0.3, preserving the other three detector channels).
- Keep gates unchanged for each seed: Precision `>=0.80`, Recall `>=0.80`, FPR `<=0.05`. Report per-seed gate outcomes and the number of seeds passing each gate out of 20. Do not define a new aggregate acceptance rule from the mean.
- Score and compare window-level Precision and FPR independently for each detector and seed. Also calculate the arithmetic mean and **population variance** across the 20 seed-level proportions; `variance = sum((x - mean)^2) / 20`. Report proportions as percentages, variance in percentage-points squared, and standard deviation in percentage points for interpretation.
- If any seed yields undefined Precision (zero predicted windows), mark that seed's Precision gate FAIL and report the aggregate Precision mean/variance as undefined; do not omit that seed. FPR with no negative windows is an evaluator error, not a value to omit.
- Record each seed's input digest and TP/FP/FN/TN. Emit aggregate reports only; do not emit metric series or raw values. No real data, services, external APIs, locked holdouts, or official evaluation seeds.
- Do not alter recipes, model logic, assumptions, gates, or seed list after any of the 20 results are observed. A later detector change requires a separate preregistration and unused seeds.

## Interpretation boundary

This is one fixed synthetic family with 20 deterministic random draws, not 20 independent real-world populations. Means and variance describe sensitivity to the registered generator only. They do not demonstrate generalization or production readiness. The existing single-seed run at `20261105` is excluded from this aggregate. A successful summary cannot promote AI-9 to PASS or P01 to GO.

**At registration time:** no seed in this list has been generated or scored, and no multi-seed result is available.

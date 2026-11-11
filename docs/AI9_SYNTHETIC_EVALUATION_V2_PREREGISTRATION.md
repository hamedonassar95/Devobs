# AI-9 Synthetic Candidate Evaluation v2 — Preregistration

| Field | Value |
| --- | --- |
| Registration | `ai9-synthetic-window-evaluation-v2` |
| Registered | 2026-10-30 03:57:44 UTC |
| Status | REGISTERED — NOT RUN |
| Source snapshot | `4d20a9c0d6dd3c57c7ca72f4bb6d9948b428a386` |

This is a new, development-only synthetic evaluation. It is not the missing historical AI-9 evaluator, does not reproduce the historical dataset, and cannot establish production quality. The historical AI-9 result remains **FAIL** and P01 remains **NO-GO / BLOCKED**.

## Frozen policies and scope

- Candidate policy: `ai9-ewma-noise-candidate-v1`.
- Evaluation policy: `ai9-synthetic-window-evaluation-v2`.
- Fixed EWMA alpha: `0.3`; baseline: 30 observed points; cadence: 60 seconds.
- Candidate: causal trailing median of width 3 for the EWMA channel only. The existing production detector's z-score, moving-average, and error-rate channels remain unchanged in the local evaluator.
- Synthetic timing assumptions: `before=0s`, `after=120s`, and close a predicted episode after two consecutive observed quiet windows. No padding or fabricated quiet points.
- Frozen selected gates: Precision `>=0.80`, Recall `>=0.80`, FPR `<=0.05`. They are copied unchanged from the recorded AI-9 gates. This run does not evaluate delay, RCA, or the full historical episode gate.
- No real data, provider calls, official evaluation/holdout seed, `episode_holdout`, or production service.

## Frozen synthetic input

- Seed: `20261105`; one deterministic generation, held in memory.
- 56 independent metric-series scenarios; 30 baseline points per scenario.
- Scored sample count: 15,080 windows: 40 scenarios with 269 scored windows and 16 with 270.
- Labels: 50 fault-free controlled-factor scenarios and six injected-fault scenarios. Each injected fault lasts exactly five consecutive 60-second windows, giving 30 positive windows and 15,050 negative windows. The rate is intentionally rare and is recorded before scoring.
- The 50 normal scenarios use exact control-group counts: 8 flat, 9 noise-only, 8 seasonality-only, 8 linear-drift-only, 8 seasonality-plus-noise, and 9 seasonality-plus-noise-plus-drift. Controls use `cpu_percent`, unit `percent`, baseline 34. Noise is uniform on `[-0.7,+0.7]`; the daily-season term is `7*sin(2*pi*(index mod 1440)/1440 - pi/3)`; total linear drift is `10*index/(scenario_length-1)`. Factors add to the baseline. The global PRNG is seeded once with `20261105` and consumed in scenario/sample order. These recipes reuse the owner-provided factor definitions with a new seed; the shortened scenario window does not establish a full-day seasonal result.
- The six fault scenarios, in fixed order after the 50 controls, each use uniform `[-0.7,+0.7]` noise and a five-window step at sample indices 150–154 inclusive, returning to baseline at index 155: `latency_ms` baseline 100 milliseconds, `+120`; `cpu_percent` baseline 34 percent, `+18`; `disk_percent` baseline 34 percent, `+25`; `error_rate` baseline 0.5 percent, `+4`; `request_rate` baseline 34 per second, `-18`; `memory_percent` baseline 34 percent, `+15`. The fault scenarios have no seasonality or drift. Fault magnitudes, units, indices, and durations are fixed before scoring.
- Scenario indices 0–39 have 299 samples (269 scored); indices 40–55 have 300 samples (270 scored). Thus the exact scored-window total is `40*269 + 16*270 = 15,080`. The fault scenarios occupy indices 50–55. Both detectors consume the same observations and labels.
- The evaluator records a SHA-256 digest of the canonical in-memory input and aggregate counts only; it does not write or print raw metric series.

## Frozen scoring

For each scored window, `predicted=true` if any active detector channel flags that window. For the candidate, only the EWMA channel is replaced by the median-filtered candidate result; the other three production channels are preserved.

- `TP`: predicted window with an injected-fault label.
- `FP`: predicted window without an injected-fault label.
- `FN`: injected-fault window without a prediction.
- `TN`: non-fault window without a prediction.
- Precision = `TP / (TP + FP)`; if there are no predictions, report `null` and fail the gate.
- Recall = `TP / (TP + FN)`; FPR = `FP / (FP + TN)`.
- Report numerator, denominator, and counts for both baseline and candidate. Do not tune the detector, filter width, seed, scenarios, labels, or thresholds after seeing results.

The episode check is separate from the window metrics: a predicted alarm can match a fault only from its onset through 120 seconds after onset (onset window, +60 seconds, or +120 seconds), with no pre-onset credit. Predicted episodes close only after two observed quiet windows. An episode still open at the series end is marked ineligible; the evaluator does not append data. Because this protocol is new and synthetic, these episode results do not replace the missing historical evaluator's eligibility decision.

## One-run rule and interpretation

Run the evaluator once after its implementation and contract tests are fixed. Publish the candidate and baseline results together, including `TP/FP/FN/TN`, the input digest, policy versions, and episode eligibility. No result from this protocol can set AI-9 to PASS or P01 to GO. A failure requires a separately preregistered experiment; do not revise this protocol after observing the run.

**At registration time:** no metrics have been computed, and the candidate has not been scored on these scenarios.

## Pre-execution implementation addendum

Registered before implementation scoring on 2026-10-30. This addendum resolves implementation details without changing the seed, scenarios, labels, gates, or assumptions above:

- Use the same deterministic 32-bit generator as `ai9_factor_ablation.mjs`: add `0x6D2B79F5` to unsigned state; apply its existing `Math.imul` xor/mix sequence; return the unsigned result divided by `2^32`. Initialize once with seed `20261105`; consume exactly one draw per sample in scenario order, including recipes whose noise amplitude is zero. Noise equals `(draw*2-1)*amplitude`.
- Compute each value as base plus seasonality, drift, noise, and any fault step; clamp to the event schema's numeric range (`0–100` for percent units, `>=0` for other units), then round with `Number(value.toFixed(4))`. Event timestamps start at `2026-10-29T00:00:00.000Z`; each subsequent sample is 60 seconds later, and each scenario starts `10,000,000,000` milliseconds after the preceding scenario's start.
- Baseline predictions use the current production `analyzeMetricEvents` function. Candidate predictions preserve that result's `z_score`, `moving_average`, and `error_rate_spike` flags and replace only its EWMA flag with `scoreEwmaNoiseCandidate` at alpha `0.3`, baseline `30`, and the event unit. At sample index `i`, candidate input is the raw metric history from `max(0,i-32)` through `i` inclusive (at most 33 observations), so the causal width-three filter has the required preceding observations whenever available. Both versions score indices 30 through the final sample.
- A ground-truth positive window is exactly sample index 150, 151, 152, 153, or 154 in the six fault scenarios. The 120-second detection-match interval is exactly indices 150–152 inclusive. Report the first predicted index and whether it falls in that interval; do not convert an alarm after index 152 into a match.
- For episode summaries, consecutive predicted windows belong to one episode until two observed false windows close it. Count every episode that remains open at sample end as ineligible. Report counts only; episode summaries do not add a gate to this selected window-metric run.

No scoring command has been run as of this addendum.

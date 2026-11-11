# AI-9 Synthetic False-Positive, Episode, and Precision-Unit Analysis

**Classification:** post-hoc decomposition of the already-consumed synthetic seed `20261105`. It is not an independent performance result and is excluded from the registered 20-seed summary. AI-9 remains **FAIL**; P01 remains **NO-GO / BLOCKED**.

## Reconciliation and false positives by series type

The diagnostic regenerated the v2 synthetic input and verified the original canonical digest `1e4211cf0e21371cbbbc8fa3849db1fa0c859e44dab5d02e6c63bc5b33d5852b`. It reconciled the baseline's 1,710 and candidate's 794 false-positive windows. The groups below use the original negative labels; fault-background rows are negative-labelled windows before or after the five injected positive windows in each same fault series.

| Series type | Negative windows | Baseline FP | Candidate FP | Candidate FPR | Candidate FP signal pattern |
| --- | ---: | ---: | ---: | ---: | --- |
| Flat control | 2,152 | 0 | 0 | 0% | — |
| Noise only | 2,421 | 634 | 188 | 7.7654% | EWMA 188 |
| Seasonality only | 2,152 | 0 | 0 | 0% | — |
| Linear drift only | 2,152 | 0 | 0 | 0% | — |
| Seasonality + noise | 2,153 | 423 | 212 | 9.8467% | EWMA 206; Z-score 5; Z-score + EWMA 1 |
| Seasonality + noise + drift | 2,430 | 215 | 127 | 5.2263% | EWMA 117; Z-score 9; Z-score + EWMA 1 |
| Fault-series CPU background | 265 | 65 | 31 | 11.6981% | EWMA 31 |
| Fault-series disk background | 265 | 70 | 21 | 7.9245% | EWMA 21 |
| Fault-series error-rate background | 265 | 106 | 90 | 33.9623% | Moving average 65; EWMA 12; moving average + EWMA 13 |
| Fault-series latency background | 265 | 67 | 47 | 17.7358% | EWMA 47 |
| Fault-series memory background | 265 | 59 | 28 | 10.5660% | EWMA 28 |
| Fault-series request-rate background | 265 | 71 | 50 | 18.8679% | EWMA 50 |
| **Total** | **15,050** | **1,710** | **794** | **5.2757%** | — |

The candidate reduced false positives in every noisy control group and every fault-series background, but the remaining errors cluster in noise-bearing recipes and negative windows around injected-fault series. Flat, seasonal-only, and drift-only controls produced no false positives in this particular seed. These are recipe-level observations, not general causal claims.

## Detector attribution and noise patterns

The candidate's 794 false-positive windows partition by exact active-channel combination as follows:

| Active candidate signal(s) | False-positive windows |
| --- | ---: |
| EWMA only | 700 |
| Moving average only | 65 |
| Z-score only | 14 |
| Moving average + EWMA | 13 |
| Z-score + EWMA | 2 |
| **Total** | **794** |

EWMA was active in 715/794 windows; 79 were emitted without EWMA, through unchanged moving-average or Z-score rules. The error-rate-spike rule did not appear in any of these false-positive channel combinations. Channel counts are exact attribution to rules that fired, not proof of a real-world cause.

The candidate's width-three causal median filters only the EWMA input. Its remaining synthetic failure modes are:

- **Multi-window noise excursions:** the output contains 132 consecutive two-window false-positive runs, 29 runs of three to four windows, and 2 runs of five or more. A three-point median can suppress a single raw impulse, but short bursts and correlated excursions survive it.
- **Noisy recipes with additional structure:** 212 false positives occurred under seasonality plus noise, and 127 under seasonality, noise, and drift. Seasonality or drift alone caused none in this seed, so these numbers only show the tested combinations.
- **Signals outside the modified channel:** 79 false-positive windows came from unchanged Z-score/moving-average channels without an EWMA signal. An EWMA-only filter cannot remove these by construction.
- **Metric and boundary sensitivity:** the fault-series error-rate background produced 90/265 false positives; 65 were moving-average only and 25 involved EWMA. The generator clips negative percentages at zero to satisfy the metric schema, so this high rate is tied to a synthetic boundary effect and should not be generalized to operational error-rate data.

There were 431 false-positive windows with no immediately adjacent false-positive window and 363 adjacent to at least one other such window. These counts describe the temporal arrangement of flagged windows; “isolated” here does not mean the underlying raw noise sample was proven to be a single impulse.

## Open episodes at the end of the sample

The registered closure rule requires two observed consecutive quiet windows. The candidate ended with two open episodes; neither overlaps an injected-fault label:

| Synthetic series | Type | Episode starts at sample | Last observed sample | Quiet windows observed after last signal | Result |
| --- | --- | ---: | ---: | ---: | --- |
| `control_seasonality_plus_noise_07` | Seasonality + noise control | 297 | 298 | 1 | Open; ineligible |
| `control_seasonality_noise_and_drift_04` | Seasonality + noise + drift control | 299 | 299 | 0 | Open; ineligible |

The baseline had 10 open episodes at EOF. These are right-censored by the sample boundary: closure is unconfirmed, and the alert could continue or later receive two quiet observations. The evaluator does not append fabricated observations. Both candidate episodes are false-labelled control alerts, but their episode end times remain unknown; this leaves the episode summary **ineligible** under the frozen assumptions.

## Window precision versus descriptive incident precision

Window precision remains the only registered Precision gate. For a separate descriptive view on this one seed, incident-level precision is defined as matched predicted episodes divided by all predicted episodes. Each injected fault may match at most one predicted episode whose start is from onset through +120 seconds; all other episodes, including open episodes, count as false incident alerts.

| Version | Window TP / FP | Window precision | Matched episodes / predicted episodes | Descriptive incident precision | Matched injected faults / 6 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline | 30 / 1,710 | 1.7241% | 4 / 1,052 | 0.3802% | 4/6 (66.6667%) |
| Candidate | 30 / 794 | 3.6408% | 5 / 519 | 0.9634% | 5/6 (83.3333%) |

Episode precision is lower because hundreds of predicted alert episodes are counted separately, while only four or five start within the registered incident match window. This alternative unit has **no acceptance gate in this analysis**. Applying the existing 80% threshold to incident precision, replacing window precision, or adding a second gate would be a policy decision; no such decision or change is made here.

## Evidence and scope

- Diagnostic command: `node scripts/ai_intelligence/diagnose_ai9_synthetic_fp_v2.mjs`.
- Input digest and exact aggregate/cross-tab output: [`AI9_SYNTHETIC_FP_DIAGNOSTIC_V2.json`](AI9_SYNTHETIC_FP_DIAGNOSTIC_V2.json).
- Diagnostic implementation: [`diagnose_ai9_synthetic_fp_v2.mjs`](../scripts/ai_intelligence/diagnose_ai9_synthetic_fp_v2.mjs).
- The diagnostic reprocessed only the consumed seed `20261105` to decompose recorded counts. It was not used to tune a candidate, change thresholds, choose seeds, or update production. The registered 20-seed sample remained untouched and excludes this seed.
- No raw metric series are emitted or stored; no production detector, threshold, metric gate, or P01 decision was changed.

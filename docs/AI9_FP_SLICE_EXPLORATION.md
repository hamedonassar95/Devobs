# AI-9 False-Positive Slice Exploration (post hoc)

**Status:** development-only diagnostic. **AI-9 FAIL, P01 NO-GO / BLOCKED.**

## Purpose

Explain *where* the already observed synthetic false positives occur, without retraining, tuning, deploying, lowering existing gates, or reporting a new holdout result. This is a **descriptive, post-hoc replay** of the original frozen generator and detector/confirmation layer. The registered 20270201–20270220 seeds have already been used in prior evaluation. They cannot be treated as independent new evaluation data.

## Read-only workflow

- `node scripts/ai_intelligence/ai9_fp_slice_exploration.mjs` prints a JSON summary for **previously consumed seed 20270201**. It does not accept external events, raw logs, accounts or customer data. It makes no network calls and writes no files.
- `node --test tests/ai9_fp_slice_exploration.test.mjs` compares the replayed confusion counts and input digest with the existing [frozen JSON report](AI9_MULTIMETRIC_CONFIRMATION_V1_RESULTS.json). Mismatches must fail.
- The CI Node job syntax-checks the new module and runs the new test. The existing production detector and its policy remain unchanged.

## Outputs and interpretation

Output includes TP, FP, FN and TN for the selected seed, plus mutually exclusive counts grouped by existing synthetic control/fault recipe and metric name. These counts must sum back to the frozen confusion matrix.

Two additional fields show **overlapping associations**, not causes:
- `overlapping_current_window_channels`: signals present in the current raw detector window when a false positive was reported. Persistent confirmations can be influenced by *previous* windows.
- `overlapping_confirmation_reasons`: persistence and cross-metric reasons. A single false positive can have both.

Do **not** sum overlapping channel/reason counts as unique false positives or interpret a flagged channel as a causal explanation. No raw measurements, per-service identifiers, token data, external requests or live incidents are included in output.

## Product decision boundary

This exploratory result may justify a **new preregistered candidate** that specifically addresses an observed false-positive slice. All original owner decisions remain: window Precision >=80%, Recall >=80%, FPR <=5%. A candidate must be frozen **before** evaluation on truly new independent seeds, then independently reviewed. Any new real dataset must first pass privacy/provenance authorization. Replaying already-consumed seeds is **not** evidence of an AI-9 PASS, tenant isolation in a live service, or P01 readiness.

## Observed post-hoc slice evidence (one reused synthetic seed)

**VERIFIED from GitHub Actions Node test:** [push run 41132376680, Node job 124326288532](https://github.com/hamedonassar95/Devobs/actions/runs/41132376680/job/124326288532) emitted `AI9_POSTHOC_FP_SLICES` for seed `20270201`. Its output agrees with the frozen reference: **TP=76, FP=1,126, FN=14, TN=44,024**. This is an exploratory breakdown for **one previously used synthetic seed**, not an independent acceptance measurement.

| Synthetic group | False-positive windows |
| --- | ---: |
| `control_noise_only` | 424 |
| `control_seasonality_plus_noise` | 279 |
| `control_seasonality_noise_and_drift` | 91 |
| `injected_fault` (outside labeled positive windows) | 332 |
| `control_flat`, `control_linear_drift_only`, `control_seasonality_only` | 0 |
| **Total** | **1,126** |

The three control recipes containing noise account for **794/1,126 (70.5151%)** FPs in this replay. The remaining **332/1,126 (29.4849%)** occur during *negative* windows associated with synthetic fault scenarios. These are descriptive labels rather than proven root causes.

| Metric | False-positive windows |
| --- | ---: |
| `latency_ms` | 703 |
| `cpu_percent` | 357 |
| `request_rate` | 28 |
| `memory_percent` | 16 |
| `disk_percent` | 15 |
| `error_rate` | 7 |

Current-window channel associations: `ewma=1119`, `z_score=9`. Confirmation reasons: `persistent_same_channel_2_of_3=745`, `cross_metric_coincidence_within_120s=595`. **These fields overlap:** they must not be added to derive unique FP counts and cannot establish which component caused an alert. A confirmation can depend on previous windows.

**Next candidate focus (recommendation, NOT APPROVED):** investigate EWMA persistence in noisy synthetic controls, especially `latency_ms` and `cpu_percent`, while measuring the effect on TP/FN and Recall. Freeze a narrow candidate and a genuinely new untouched holdout **before** evaluating it. Do not simply suppress the noisy channels or change the owner's gates.

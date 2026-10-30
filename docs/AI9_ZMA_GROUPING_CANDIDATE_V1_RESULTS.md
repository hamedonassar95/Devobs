# AI-9 Z-score / Moving-Average and Grouping Candidate v1 — Results

**Decision unchanged:** AI-9 **FAIL**; P01 **NO-GO / BLOCKED**. This is a paired synthetic development comparison on seeds already used for baseline/v1, not independent validation.

## Run evidence

- Preregistration: [`AI9_ZMA_GROUPING_CANDIDATE_V1_PREREGISTRATION.md`](AI9_ZMA_GROUPING_CANDIDATE_V1_PREREGISTRATION.md).
- Candidate: `ai9-zma-2of3-alert-grouping-v1`; it adds two-of-three scored-window confirmation for Z-score and moving average, retains candidate-v1 EWMA and unchanged error-rate spike, and reports 120-second alert groups descriptively.
- Command, run once: `node scripts/ai_intelligence/ai9_zma_grouping_candidate_v1.mjs`.
- Code commit run: `7fe1b7e` on `feature/ai9-synthetic-eval-v2`.
- Seeds: `20261201`–`20261220`, paired across all three versions, 56 scenarios and 15,080 windows per seed.
- The runner verified every input digest and baseline/current-candidate TP/FP/FN/TN count against the previously saved 20-seed report before accepting the new candidate results.
- Exact per-seed counts, rates, gates, episode summaries, and input digests: [`AI9_ZMA_GROUPING_CANDIDATE_V1_RESULTS.json`](AI9_ZMA_GROUPING_CANDIDATE_V1_RESULTS.json).

## Window Precision and FPR summary

Means and population variances use each seed's window-level rate; variance units are percentage-points squared. Gates remain the unchanged per-seed gates: Precision `>=80%`, Recall `>=80%`, FPR `<=5%`.

| Version | Mean Precision | Precision variance (pp²) | Mean FPR | FPR variance (pp²) | Precision passes | Recall passes | FPR passes | All gates pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Production baseline | 1.6649% | 0.0005081 | 11.7757% | 0.0261140 | 0/20 | 20/20 | 0/20 | 0/20 |
| Current candidate v1 | 3.4973% | 0.0165009 | 5.5080% | 0.0436793 | 0/20 | 20/20 | 0/20 | 0/20 |
| New Z-score/moving-average v1 | 3.1960% | 0.0397525 | 5.3445% | 0.0479521 | 0/20 | 20/20 | 1/20 | 0/20 |

The new candidate lowered mean FPR by 0.1635 percentage points relative to current v1, but lowered mean Precision by 0.3014 percentage points. It missed 2–5 of the 30 positive windows per seed (mean Recall 88.3333%, range 83.3333%–93.3333%). Only seed `20261219` passed FPR, at 4.9834%; its Precision still failed. The Precision gate failed on every seed for all versions.

## Descriptive alert grouping

The existing 120-second gap and two-observed-quiet-window rule groups timestamps without filling missing windows. Episode counts do not enter the window gates and do not create an incident gate.

| Version | Grouped predicted episodes | Closed after quiet observations | Open at sample end | Seeds with at least one open episode | Fault scenarios matched within frozen interval |
| --- | ---: | ---: | ---: | ---: | ---: |
| Production baseline | 21,291 | 21,057 | 234 | 20/20 | 59/120 |
| Current candidate v1 | 11,135 | 11,026 | 109 | 20/20 | 88/120 |
| New Z-score/moving-average v1 | 10,809 | 10,705 | 104 | 20/20 | 101/120 |

These totals are descriptive summaries over the 20 synthetic draws. Grouping reduces duplicate episode count slightly versus current v1, but all seeds still end with open alert episodes.

## Interpretation and limits

- The new candidate's two-of-three filter reduced false alerts a little more than v1, but the paired mean Precision fell and FPR passed in only one seed. It does not meet the frozen release gates.
- The seeds were already consumed for baseline/v1 selection and evaluation. Reuse supports exact paired comparison, not an unbiased independent estimate. No independent holdout result was generated.
- The gate remains window Precision as the owner decided. Grouping is descriptive only. No production detector, thresholds, gate definitions, or P01 decision changed.
- No push, PR, merge, deployment, real data, service, or locked holdout was used.

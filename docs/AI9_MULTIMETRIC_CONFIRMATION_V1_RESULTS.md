# AI-9 Multi-Metric Confirmation v1 — Results

**Decision unchanged:** AI-9 **FAIL**; P01 **NO-GO / BLOCKED**. This is a synthetic development evaluation of an isolated post-detector layer. It is not a replay of the historical AI-9 evaluation, an estimate from real incidents, or production evidence. No production detector, gate, or threshold changed.

## Frozen run evidence

- Preregistration: [`AI9_MULTIMETRIC_CONFIRMATION_V1_PREREGISTRATION.md`](AI9_MULTIMETRIC_CONFIRMATION_V1_PREREGISTRATION.md), registration `ai9-multimetric-confirmation-v1`; registered before implementation and before any registered seed was generated.
- Frozen versions: baseline detector; `ai9-ewma-noise-candidate-v1`; and that candidate followed by `ai9-post-detector-confirmation-v1`. Window gates stayed at Precision `≥80%`, Recall `≥80%`, and FPR `≤5%`.
- Frozen seeds: `20270201`–`20270220`, exactly once each. Each seed has 56 synthetic service traces with three synchronous metrics: 45,240 scored metric-windows, 90 positive and 45,150 negative. Across 20 seeds: 904,800 scored windows, 1,800 positive and 903,000 negative. Seed-level canonical input digests and confusion counts are recorded in [`AI9_MULTIMETRIC_CONFIRMATION_V1_RESULTS.json`](AI9_MULTIMETRIC_CONFIRMATION_V1_RESULTS.json); its SHA-256 is `7f3c2e68b9ff2ecb6bca712b5d7b99b609e2cf8972ab39251143d7ef571d2d0c`.
- The generator, evaluator, gates, rules, and tests were frozen before the registered data generation. The one-time command was `node scripts/ai_intelligence/evaluate_ai9_multimetric_confirmation_v1.mjs`; it emitted aggregate and per-seed confusion metrics and digests, not raw event series.
- Frozen implementation commits: preregistration `e81ea735b15c50bdff573b5216f5ebdcda408616`; generator `fa381822c21c093bea7187e1ebf18415cad39e50`; evaluator `eafa438f2b56516c9fa966cd68ab79b57b787157`; policy guard `d25a24e3a19ebbfcdf15bae432a5fc9840dee901`.
- Variance below is population variance across the 20 per-seed percentages, in percentage-points squared (pp²). Missed windows are total false negatives over 1,800 positives. Missed fault services are descriptive; they are not another gate.

## Window-level comparison

| Version | Precision mean (variance) | Recall mean (variance) | FPR mean (variance) | Missed positive windows | Missed fault services | Precision / Recall / FPR passes | All gates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline detector | 1.9997% (0.002073 pp²) | 82.5556% (2.851852 pp²) | 8.0656% (0.007603 pp²) | 314 / 1,800 | 2 / 120 | 0 / 20 · 20 / 20 · 0 / 20 | 0 / 20 |
| `ai9-ewma-noise-candidate-v1` | 3.5644% (0.008287 pp²) | 84.6667% (2.666667 pp²) | 4.5673% (0.004712 pp²) | 276 / 1,800 | 0 / 120 | 0 / 20 · 20 / 20 · 20 / 20 | 0 / 20 |
| Candidate + `ai9-post-detector-confirmation-v1` | 6.1670% (0.039099 pp²) | 84.6667% (2.666667 pp²) | 2.5695% (0.004222 pp²) | 276 / 1,800 | 0 / 120 | 0 / 20 · 20 / 20 · 20 / 20 | 0 / 20 |

Precision failed in all 20 seeds for every version. The confirmation layer passed the existing Recall and FPR gates in 20/20 seeds, but did not approach the Precision gate. The preregistration defines no aggregate acceptance gate; aggregate gate decision is therefore `NOT_DEFINED_BY_PREREGISTRATION`.

### Context against the earlier recorded FAIL

The earlier owner-provided reference was TP=30, FP=925, FN=0, TN=14,125: Precision **3.1414%**, Recall **100%**, FPR **6.1462%**. The new multi-metric layer mean is Precision **6.1670%**, Recall **84.6667%**, FPR **2.5695%**. These are **not a direct before/after comparison**: they come from different synthetic inputs and protocols. The new run does not reproduce the old evaluation or prove a general improvement. The earlier reference and this limitation are also recorded in [`AI9_SYNTHETIC_EVALUATION_V2_RESULTS.md`](AI9_SYNTHETIC_EVALUATION_V2_RESULTS.md).

### Recall cost for the Precision gain

Paired against the current EWMA candidate, the layer increased mean Precision by **2.6027 percentage points** (3.5644% → 6.1670%). Mean Recall loss was **0.0000 percentage points** (84.6667% → 84.6667%): there were **0 additional false-negative windows**, and no seed lost Recall. The measured Recall loss per Precision point gained is **0** for this synthetic run. FPR fell by **1.9978 percentage points** (4.5673% → 2.5695%). This observed tradeoff applies only to this frozen synthetic generator family; it does not predict real service behavior.

### Confirmation reasons and incident tails

The layer attributed **16,315** confirmed metric-windows to same-channel persistence and **14,239** to cross-metric coincidence within 120 seconds. The reasons overlapped on **5,827** windows, so the two counts are not disjoint and must not be added as unique confirmed windows.

| Version | Incidents started/grouped | Closed after two observed quiet windows | Open at sample end | Seeds with open incidents |
| --- | ---: | ---: | ---: | ---: |
| Baseline detector | 43,810 | 43,306 | 504 | 20 / 20 |
| Current EWMA candidate | 25,942 | 25,670 | 272 | 20 / 20 |
| Candidate + confirmation layer | 14,902 | 14,752 | 150 | 20 / 20 |

The 150 layer incidents remained open at EOF across all seeds. No quiet samples were appended, so these tails were not marked closed. Incident totals remain descriptive; the owner selected window-level Precision and did not authorize a new incident-level gate.

## Prevalence and theoretical Precision ceiling

Synthetic prevalence is `90 / 45,240` = **0.198939% positive**. Assuming perfect Recall, the maximum theoretical Precision at selected FPR values is:

| FPR | Maximum theoretical Precision |
| ---: | ---: |
| 5% | 3.8339% |
| 1% | 16.6205% |
| 0.1% | 66.5927% |
| 0.05% | 79.9467% |
| 0.01% | 95.2230% |
| 0% | 100% |

This calculation explains why the existing FPR allowance alone cannot guarantee the Precision target under this synthetic class balance. It does not justify changing either gate.

## Real-data evidence and integration gaps

- **VERIFIED (repository evidence):** [`AI_EVALUATION_DATASETS.md`](AI_EVALUATION_DATASETS.md) describes tracked evaluation fixtures as synthetic and unreviewed. The repository does not contain a representative, authorized, expert-labeled time-series corpus of operational incidents and control periods. Real incident prevalence is therefore **unknown**; it cannot be estimated from the available repository fixtures.
- **VERIFIED (synthetic run):** cross-metric behavior was exercised across three aligned metrics for each synthetic service. The scenario ID was supplied to the layer out of band because the production event schema has no stable service identity. This does not validate a production metric-to-service mapping or real cross-metric correlations.
- **UNVERIFIED / not exercised:** durable state and restart recovery, duplicate delivery and idempotency, out-of-order replay, bounded retention, multiple concurrent workers, real missing-sample cadence, alert routing and deduplication, audit records, or incident runbooks. The prototype is not ready for operational integration.
- **Required before integration:** an owner-reviewed stable service/metric mapping; a runtime adapter with explicit ordering, gap, and recovery contracts; durable/idempotent state tests; routing, audit and runbook design; and an authorized representative labeled dataset with a preregistered holdout. The existing frozen window gates must be evaluated on that evidence without post-result changes.
- These results are **not numerically comparable** to prior single-metric confirmation results: this benchmark has three synchronized metrics per service and a different frozen synthetic population. It does not replace the historical AI-9 failure measurement.

## Recommendation and status

Keep the layer isolated as a development prototype. First obtain a representative, authorized labeled incident/control dataset and define the production service identity and durable-state contract; then preregister a separate evaluation before any real-data use. Do not integrate the layer into the production detector based on this result.

AI-9 remains **FAIL** because Precision passed in **0/20** seeds; P01 remains **NO-GO / BLOCKED**. The technical model score and production state are unchanged.

Local verification before measurement: focused tests **2/2**; `node --test tests/*.test.*` **104/104**, 0 failed, 0 skipped; syntax checks and `git diff --check` passed. The one-time evaluation command completed; it was not rerun while preparing this report. No real data, service, cloud resource, production change, push, PR, or merge was used in the measurement itself.

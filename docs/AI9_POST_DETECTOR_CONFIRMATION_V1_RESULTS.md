# AI-9 Post-Detector Confirmation Layer v1 — Results

**Decision unchanged:** AI-9 **FAIL**; P01 **NO-GO / BLOCKED**. This is one synthetic development evaluation; it is not the historical AI-9 evaluation, a real-incident estimate, or production evidence.

## Frozen run evidence

- Protocol: [`AI9_POST_DETECTOR_CONFIRMATION_V1_PREREGISTRATION.md`](AI9_POST_DETECTOR_CONFIRMATION_V1_PREREGISTRATION.md), registered before implementation and seed generation.
- Registration/policy version: `ai9-post-detector-confirmation-v1`; comparison candidate: `ai9-ewma-noise-candidate-v1`.
- Implementation was frozen locally in commits `0956853` (confirmation layer and contract tests) and `6420c03` (evaluation runner and its preregistration contract test) before the evaluation.
- Command, run once: `node scripts/ai_intelligence/evaluate_ai9_post_confirmation_v1.mjs`.
- Seeds: `20270101`–`20270120`, exactly once each. Each seed contains 56 scenarios and 15,080 scored windows: 30 positive and 15,050 negative. Total: 301,600 windows, including 600 positive windows.
- The generator family, labels, cadence, 30-point baseline, `before=0s`, `after=120s`, two observed quiet windows, and gates were unchanged. Only the seed varied. Every seed's canonical input digest is in [`AI9_POST_DETECTOR_CONFIRMATION_V1_RESULTS.json`](AI9_POST_DETECTOR_CONFIRMATION_V1_RESULTS.json), SHA-256 `52d7d952b1345645220e24a42c9a18d7eda7014db7c859ab52972be48854d2ba`.
- The layer confirms the same channel in at least 2 of 3 observed windows, or two distinct metric names for one service with signals within 120 seconds. Multiple detector channels on one metric do not count as independent. It groups confirmed windows and closes an incident after two observed quiet windows. The benchmark has one metric per synthetic service, so it exercised persistence only; cross-metric coincidence was exercised by contract tests, not by this benchmark.

## Window metrics across 20 seeds

Values are the mean of per-seed proportions. Variance is population variance in percentage-points squared (pp²). `Missed windows` is total FN over 600 positive windows. The last column counts injected-fault scenarios without an incident start during onset through onset + 120 seconds; it is descriptive, not a new gate.

| Version | Precision mean (variance) | Recall mean (variance) | FPR mean (variance) | Missed positive windows | Missed fault scenarios | P / R / FPR gate passes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Current production baseline in v2 harness | 1.6594% (0.000987 pp²) | 100.0000% (0) | 11.8176% (0.051984 pp²) | 0 / 600 | 56 / 120 | 0 / 20 · 20 / 20 · 0 / 20 |
| `ai9-ewma-noise-candidate-v1` | 3.4172% (0.010515 pp²) | 100.0000% (0) | 5.6392% (0.030106 pp²) | 0 / 600 | 24 / 120 | 0 / 20 · 20 / 20 · 0 / 20 |
| Candidate + post-detector confirmation layer | 8.4783% (0.241187 pp²) | 82.0000% (2.666667 pp²) | 1.7708% (0.013291 pp²) | 108 / 600 | 6 / 120 | 0 / 20 · 20 / 20 · 20 / 20 |

The gates remain Precision `≥80%`, Recall `≥80%`, and FPR `≤5%`. No version passed all three in any seed. The layer passed Recall and FPR in 20/20 seeds, but Precision in 0/20; AI-9 therefore remains **FAIL**. This v2 baseline/candidate table is not numerically interchangeable with the separate historical failure report (about 3.14% Precision and 6.15% FPR), which used a different evaluation record.

### Recall cost of the Precision gain

Against the current EWMA candidate, mean Precision increased by **5.0611 percentage points** (3.4172% → 8.4783%), while mean Recall fell by **18.0000 percentage points** (100% → 82%). That is **3.56 Recall percentage points lost per 1 Precision point gained** on the paired seed means. The layer added **108 missed positive windows** across the 20 seeds, or 5.4 per seed. Per-seed Recall ranged from 80.0% to 83.3333%, so every seed remained at or above the existing Recall gate.

FPR fell from 5.6392% to 1.7708%. At the injected-fault episode level, missed scenarios fell from 24/120 for the current candidate to 6/120 for the layer. The window-level gate remains authoritative; the episode counts are diagnostic only.

## Grouped incidents and open tails

| Version | Started/grouped incidents | Closed after observed quiet windows | Still open at sample end |
| --- | ---: | ---: | ---: |
| Baseline | 21,188 | 20,960 | 228 |
| Current EWMA candidate | 11,387 | 11,296 | 91 |
| Candidate + layer | 3,832 | 3,805 | 27 |

The layer still ended with 27 open incidents across 14 of 20 seeds. No synthetic quiet windows were appended, and the open incidents were not treated as closed. Incident counts do not create an additional acceptance gate.

## Prevalence and theoretical Precision ceiling

The synthetic window prevalence is `30 / 15,080` = **0.198939% positive** and **99.801061% negative**. Assuming perfect Recall, the fixed prevalence gives:

| FPR | Maximum theoretical Precision |
| ---: | ---: |
| 5% | 3.8339% |
| 1% | 16.6205% |
| 0.1% | 66.5927% |
| 0.05% | 79.9467% |
| 0.01% | 95.2230% |
| 0% | 100% |

Lower Recall yields lower Precision at the same FPR. With only 30 positive windows, an empirical Precision of at least 80% allows at most 7 false positives, corresponding to FPR `7 / 15,050` = **0.0465%**. Thus the unchanged 5% FPR limit alone is far too loose to guarantee the Precision gate under this synthetic prevalence.

## Real incident data and integration gaps

- **VERIFIED in the tracked repository:** [`AI_EVALUATION_DATASETS.md`](AI_EVALUATION_DATASETS.md) describes the evaluation fixtures as synthetic and unreviewed. The Decisions fixture has 28 rows, all marked `synthetic_unreviewed`. The incident-investigator fixture has 10 report examples (the document describes one historical report and nine synthetic cases); it is not a labeled time-series corpus with positive/negative monitoring windows. No representative operational incident-and-control telemetry corpus was found. **Real incident prevalence is therefore unknown and cannot be estimated from this repository.**
- The current metric event schema does not provide a stable service identifier. Integration needs an owner-reviewed metric-to-service mapping so cross-metric confirmation cannot combine unrelated services.
- The benchmark has one metric per service scenario and therefore does not measure real cross-metric correlation. It also uses one synthetic recipe family; the 20 seeds do not represent 20 independent real-world populations.
- The component's state is in memory. Durable state/restart semantics, duplicate delivery/idempotency, replay ordering, bounded state/retention, concurrent workers, and failure recovery need a runtime design and tests.
- Real telemetry cadence, missing-sample behavior, alert delivery/routing, incident ownership, auditability, and operational runbooks remain unverified. Integration also needs a reviewed adapter, end-to-end tests with service identity, and an authorized expert-labeled, representative holdout with negative windows.

## Recommendation

Keep this layer as an isolated synthetic prototype. Before integration, build and test a service-aware adapter against a representative, authorized, expert-labeled telemetry set, preregister the evaluation, and require the existing window gates to pass. Do not change production or any gate from this result.

Local verification: focused contract tests **14/14**; full Node suite `node --test tests/*.test.*` **102/102**, 0 failed, 0 skipped; syntax checks and `git diff --check` passed before measurement. No hosted CI, push, PR, merge, detector change, threshold change, real data, or production integration was used.

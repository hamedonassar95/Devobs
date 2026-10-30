# AI-9 Synthetic Multi-Seed v1 — Results

**Status remains:** AI-9 **FAIL**; P01 **NO-GO / BLOCKED**. This is a synthetic development stability check, not the historical evaluator or production evidence.

## Run evidence

- Preregistration: [`AI9_SYNTHETIC_MULTI_SEED_V1_PREREGISTRATION.md`](AI9_SYNTHETIC_MULTI_SEED_V1_PREREGISTRATION.md), committed before seed generation.
- Evaluation policy: `ai9-synthetic-window-evaluation-v2`; candidate: `ai9-ewma-noise-candidate-v1`.
- Code commit run: `a5db0d1` on `feature/ai9-synthetic-eval-v2`.
- Command, run once across the registered set: `node scripts/ai_intelligence/ai9_synthetic_multiseed_v1.mjs`.
- Completion recorded: 2026-10-30 11:01:48 UTC.
- Seeds: `20261201`–`20261220`, 20 total. Each produced 56 scenarios and 15,080 scored windows (30 positive, 15,050 negative). Both detectors used the same input for each seed.
- Exact per-seed counts, rates, gate results, and input digests: [`AI9_SYNTHETIC_MULTI_SEED_V1_RESULTS.json`](AI9_SYNTHETIC_MULTI_SEED_V1_RESULTS.json).

## Mean and population variance across seeds

Each seed's metric was computed first; the table reports the arithmetic mean and population variance across those 20 proportions. Variance is expressed in percentage-points squared; the standard deviation is included to make its scale readable.

| Detector | Metric | Mean | Population variance (pp²) | Standard deviation (pp) | Seeds passing original gate |
| --- | --- | ---: | ---: | ---: | ---: |
| Baseline | Precision (≥80%) | 1.6649% | 0.0005081 | 0.0225 | 0/20 |
| Candidate | Precision (≥80%) | 3.4973% | 0.0165009 | 0.1285 | 0/20 |
| Baseline | FPR (≤5%) | 11.7757% | 0.0261140 | 0.1616 | 0/20 |
| Candidate | FPR (≤5%) | 5.5080% | 0.0436793 | 0.2090 | 0/20 |

Recall was 100% and passed its unchanged ≥80% gate in all 20 seeds for both detectors. No seed passed all three selected gates. The candidate's mean Precision exceeded the baseline by 1.8324 percentage points and mean FPR was lower by 6.2678 percentage points; this summarizes only the registered synthetic generator. No aggregate acceptance rule was added.

## Per-seed results

Counts are TP/FP/FN/TN. Rates are percentages. Every seed had Recall=100%; Precision and FPR gates failed for both versions on every seed.

| Seed | Baseline counts | Baseline P | Baseline FPR | Candidate counts | Candidate P | Candidate FPR |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| 20261201 | 30/1792/0/13258 | 1.6465% | 11.9070% | 30/852/0/14198 | 3.4014% | 5.6611% |
| 20261202 | 30/1800/0/13250 | 1.6393% | 11.9601% | 30/847/0/14203 | 3.4208% | 5.6279% |
| 20261203 | 30/1750/0/13300 | 1.6854% | 11.6279% | 30/866/0/14184 | 3.3482% | 5.7542% |
| 20261204 | 30/1801/0/13249 | 1.6384% | 11.9668% | 30/792/0/14258 | 3.6496% | 5.2625% |
| 20261205 | 30/1773/0/13277 | 1.6639% | 11.7807% | 30/789/0/14261 | 3.6630% | 5.2425% |
| 20261206 | 30/1763/0/13287 | 1.6732% | 11.7143% | 30/853/0/14197 | 3.3975% | 5.6678% |
| 20261207 | 30/1768/0/13282 | 1.6685% | 11.7475% | 30/857/0/14193 | 3.3822% | 5.6944% |
| 20261208 | 30/1771/0/13279 | 1.6657% | 11.7674% | 30/860/0/14190 | 3.3708% | 5.7143% |
| 20261209 | 30/1760/0/13290 | 1.6760% | 11.6944% | 30/787/0/14263 | 3.6720% | 5.2292% |
| 20261210 | 30/1727/0/13323 | 1.7075% | 11.4751% | 30/812/0/14238 | 3.5629% | 5.3953% |
| 20261211 | 30/1791/0/13259 | 1.6474% | 11.9003% | 30/826/0/14224 | 3.5047% | 5.4884% |
| 20261212 | 30/1797/0/13253 | 1.6420% | 11.9402% | 30/856/0/14194 | 3.3860% | 5.6877% |
| 20261213 | 30/1759/0/13291 | 1.6769% | 11.6877% | 30/794/0/14256 | 3.6408% | 5.2757% |
| 20261214 | 30/1816/0/13234 | 1.6251% | 12.0664% | 30/884/0/14166 | 3.2823% | 5.8738% |
| 20261215 | 30/1784/0/13266 | 1.6538% | 11.8538% | 30/799/0/14251 | 3.6188% | 5.3090% |
| 20261216 | 30/1769/0/13281 | 1.6676% | 11.7542% | 30/841/0/14209 | 3.4443% | 5.5880% |
| 20261217 | 30/1759/0/13291 | 1.6769% | 11.6877% | 30/803/0/14247 | 3.6014% | 5.3355% |
| 20261218 | 30/1742/0/13308 | 1.6930% | 11.5748% | 30/862/0/14188 | 3.3632% | 5.7276% |
| 20261219 | 30/1797/0/13253 | 1.6420% | 11.9402% | 30/781/0/14269 | 3.6991% | 5.1894% |
| 20261220 | 30/1726/0/13324 | 1.7084% | 11.4684% | 30/818/0/14232 | 3.5377% | 5.4352% |

## Interpretation limits

- The candidate reduced false alarms in every seed, but FPR remained above 5% in every seed and Precision remained far below 80% in every seed.
- The seeds are deterministic draws from one synthetic family, not independent real-world populations. The mean and variance do not establish generalization.
- The old seed `20261105` and the owner-provided historical reference are excluded from these statistics.
- No detector, threshold, assumption, gate, or production file was changed. This result does not set AI-9 to PASS or P01 to GO.

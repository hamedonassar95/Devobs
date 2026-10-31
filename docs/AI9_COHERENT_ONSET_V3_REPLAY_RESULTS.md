# AI-9 Coherent Onset v3 — historical replay results (NOT independent validation)

**Run date:** 2026-10-31 UTC  
**PR:** [#327](https://github.com/hamedonassar95/Devobs/pull/327)  
**Source under test:** `a5bcb586bc566859790068efb2dee4436ce8ec6c` (feature head after merging updated main)  
**CI evidence:** [GitHub Actions run 41148631232](https://github.com/hamedonassar95/Devobs/actions/runs/41148631232) — Node test output `AI9_ONSET_V3_REUSED_SEED`.  
**Registered design:** [AI9_COHERENT_ONSET_V3_PREREGISTRATION.md](AI9_COHERENT_ONSET_V3_PREREGISTRATION.md).  
**Dataset:** already-consumed `20270201`, 56 synthetic services × 3 metrics, 45,240 scored metric windows, 90 positive + 45,150 negative. This seed is not an independent holdout.

## Frozen window-level results from the CI log

| Version | TP | FP | FN | TN | Precision | Recall | FPR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Joint v2 | 58 | 8 | 32 | 45142 | 87.8788% | 64.4444% | 0.0177% |
| Onset v3 | 73 | 8 | 17 | 45142 | 90.1235% | 81.1111% | 0.0177% |

- **Paired development delta:** +15 TP, -15 FN, unchanged FP=8 and TN=45,142.
- **Frozen window gates on this reused seed only:** Precision ≥80% **PASS**, Recall ≥80% **PASS**, FPR ≤5% **PASS**.
- **Descriptive only:** all 18 injected-fault metric streams had at least one matched v3 signal; match does not demonstrate practical incident detection on real telemetry.
- **Model limitations:** synthetic windows are highly imbalanced, only one already-consumed seed, generator shares fault recipes with development, no independently labelled field incidents or calibration checks, and no measurement of distribution shift across real services.
- **Cost:** no API model inference, private data, network, SaaS resources, or production changes.
- **Decision:** AI-9 overall **FAIL / NOT AUTHORIZED FOR PRODUCTION**; P01 **NO-GO / BLOCKED**; no existing production thresholds or detector changed.

## Next controlled verification

The registered fresh seeds `20270601`–`20270604` have **not** been evaluated or consumed by this PR or CI. After reviewed merge and a separate explicit owner decision for the one-time independent synthetic run, perform the preregistered evaluation without threshold tuning or repeating seeds based on results. Record every seed, canonical input SHA, TP/FP/FN/TN, delay and gate result. A synthetic PASS still requires independent real-data authorization, identity, privacy and safety gates before deployment.

Independent research on time-series anomaly evaluation recommends careful separation of development/held-out data and warns against label-dependent threshold selection: https://link.springer.com/article/10.1007/s10994-026-07183-y

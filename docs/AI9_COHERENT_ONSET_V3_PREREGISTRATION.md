# AI-9 Coherent Onset v3 — Frozen Development Registration

**Registration:** `ai9-coherent-onset-v3`  
**Base main SHA:** `daa750d34003eb44bfecfe2b8bd1272859520217`  
**Classification:** synthetic development-only; NOT a production configuration.  
**Status:** REGISTERED BEFORE implementation/evaluation; AI-9 remains **FAIL**, P01 **NO-GO / BLOCKED**.

## Pre-existing evidence
Historical v2 used seed `20270201` yielded TP=58, FP=8, FN=32, TN=45142, Precision=87.8788%, Recall=64.4444% (FAIL), and FPR=0.0177%. The v2 robust 3-point median requires two changed samples to fire; an isolated strong onset sample may be missed. This is a **hypothesis**, not an observed root-cause proof. The earlier v2 four-seed holdout (20270501–20270504) is not consumed or changed by this work.

## Candidate contract — frozen before evaluation
1. Leave `ai9-joint-metric-confirmation-v2`, `robustShiftDecision`, post-detector confirmation and production anomaly detector **unchanged**. Candidate v3 operates only as a read-only suppressive filter over the same exactly-three-metric synchronous service input.
2. Compute v2 `jointMetricDecision(input)` first; propagate its fail-closed input validation and its baseline `candidate_confirmed` outcome exactly.
3. For each metric at `index >= 32`, use the same **causal 30-point reference** as robust-shift v1: `values[index-32 : index-2]`. Let `center = median(reference)` and `MAD = median(abs(reference-center))`.
4. Define one **onset** on metric `m` only when `MAD > 0`, both immediate preceding observed samples `values[index-2]` and `values[index-1]` satisfy `abs(sample-center) <= 4 * MAD`, and the **current** `values[index]` satisfies `abs(current-center) > 12 * MAD`. These constants and inequalities are frozen; do not tune after replay. Require exactly 60-second timestamps on the existing validated 33-point window.
5. Define `coherent_onset = count(distinct metrics with onset) >= 2` at the **same service and timestamp**. A third metric cannot borrow another service's evidence.
6. For each metric, `candidate_confirmed_v3 = existing_confirmed && (v2.coherent_service_shift || coherent_onset)`. A candidate **cannot create an alert** unless post-detector confirmation is already true.
7. No labels, fault groups, future values, seeds or metric identifiers change the algorithm; only the three synchronous streams and preexisting confirmation booleans are read. Invalid, missing, non-finite or inconsistent input fails closed; `MAD=0` cannot authorize an onset. No persistent state, networking or paid inference.

## Scoring/holdout discipline
- Before running any fresh seeds, verify with hand-authored behavior tests for one/two onset metrics, previous-sample stability, zero MAD, insufficient history, false confirmation, malformed timestamps, and service isolation.
- Replay **only already consumed** `20270201` against the **unaltered** `generateAi9MultimetricServicesV1`, post-detector baseline and v2. Require identical baseline digest `361a77e4ee44de9c10903f2045287dc86ed2b170c5da019f9880f8fe2f4962a0` and counts 76/1126/14/44024. Print full confusion counts for baseline/v2/v3; no raw series.
- **No CI job, unit test, or default command may run fresh seeds.** After registration and implementation are reviewed and merged, and only with separate owner authorization for that evaluation, perform exactly one `--fresh-once` evaluation with four new preregistered seeds `20270601,20270602,20270603,20270604`, after a no-collision check. A collision invalidates this design; do not replace a seed opportunistically.
- Keep immutable per-seed window gates Precision >= 80%, Recall >= 80%, FPR <= 5%; print TP/FP/FN/TN, false negative/onset delay, canonical data hashes, and all gate decisions, with no pooled hiding of seed failures. Any invalid condition yields INVALID rather than PASS.
- Even an independent synthetic PASS is not production approval or evidence of generalization. Real telemetry, identity, privacy, operating cost and the owner's approval require separate gates.

## External research used for hypothesis framing
- [Leakage and point-adjust pitfalls (2026)](https://link.springer.com/article/10.1007/s10994-026-07183-y)
- [Evaluation metrics must match operator alert costs (2026)](https://www.sciencedirect.com/science/article/pii/S0925231226019454)
- [Causal MAD and calibrated precision under alert budgets (2026)](https://www.sciencedirect.com/science/article/pii/S2542660526000508)

These references motivate evaluation safeguards, not a claim that this particular 12-MAD filter is research-validated.

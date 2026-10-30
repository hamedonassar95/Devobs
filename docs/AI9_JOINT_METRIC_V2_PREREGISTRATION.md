# AI-9 Joint-Metric Confirmation v2 — Frozen Preregistration

**Registration ID:** `ai9-joint-metric-confirmation-v2`. **Status:** REGISTERED / NOT RUN. **Classification:** synthetic development only. **Base:** `34173567d08fb3d1898cfe4bfd510d5acf4f9c4f`. **AI-9 FAIL / P01 NO-GO-BLOCKED** until independent approvals.

## Development evidence that motivated this hypothesis

The **previously used** synthetic seed `20270201` was replayed under preregistered robust-shift v1: the baseline had TP=76 FP=1126 FN=14 TN=44024; applying each metric's individual robust-shift gate yielded TP=59 FP=66 FN=31 TN=45084, with Precision 47.2% (FAIL), Recall 65.56% (FAIL), FPR 0.146% (PASS). This is post-hoc development evidence, not fresh validation. Version v1 remains frozen; no tuning of its `4*MAD` threshold is permitted.

## Frozen candidate definition

1. Reuse unchanged `ai9-ewma-noise-candidate-v1` channel composition, the existing `ai9-post-detector-confirmation-v1` layer and `robustShiftDecision` v1 from the merged repository. Neither the production detector nor the layer's internal incident/history state changes.
2. At a single **service** and timestamp with exactly three **distinct** metric names, compute the existing v1 robust shift flag for **each** metric using `robustShiftDecision(metric, index, true).robust_shift`; the shift is computed from values alone and does not use the existing per-metric confirmed flag.
3. Define `coherent_service_shift = count(metrics where robust_shift === true) >= 2`. A raw signal in two channels on the same metric counts as **one metric**, never two. No mixing metrics from other services, timestamps or tenants.
4. For each metric `m`, define `candidate_confirmed[m] = existing_post_detector_confirmed[m] && coherent_service_shift`. Thus the candidate cannot generate a new alert absent prior confirmation; a metric with a weak individual shift can retain an existing confirmed alert if two *other or including itself* metrics have a strong shift.
5. Strict 30-reference/3-recent/`shift > 4*MAD` v1 logic, 60-second cadence, data validity and fail-closed handling remain unchanged. Until sample index 32 there is insufficient history; output false for all metrics. Missing/nonfinite metrics, timestamps, duplicate or out-of-order events, duplicate service metric identities, non-synchronous metric timestamps, or fewer/more than three metrics invalidate the input. Do not interpolate gaps or reuse another service's state.
6. No labels, group names, fault-family identifiers, future samples or arbitrary metric-specific thresholds may influence candidate decisions. No training, threshold search, auto-remediation, network connection or external LLM.

## Frozen comparison, validation and stopping

- Compare current post-detector confirmation baseline, **prior robust-shift v1 diagnostic** and new joint-metric v2 using identical generated values and labels. The baseline source policy remains unchanged.
- Use exactly **four new unused seeds** `20270501`, `20270502`, `20270503`, `20270504`, ascending, once. GitHub repository text searches returned no occurrences of any of these four before registration. Verify no prior history collision before the one-time run; if found, mark the experiment INVALID, do not replace a seed.
- Preserve `generateAi9MultimetricServicesV1` generator, 56 services, 3 synchronous metrics, existing labels/fault windows, 30 initial baseline samples and 45,240 scored **metric** windows per seed (90 positive, 45,150 negative). Record input canonical SHA-256 for each seed.
- Score TP/FP/FN/TN, Precision, Recall and FPR separately for **each seed and version** using frozen gate semantics: Precision ≥0.80, Recall ≥0.80, FPR ≤0.05. Publish FP/FN tradeoffs, descriptive matched fault metric counts and observed first-detection delays; absent detections are missing, not latency=0. No new episode gate or RCA claim.
- Before touching any fresh seed, focused behavioral tests must pass and a replay of the **already used** seed `20270201` must match frozen baseline digest `361a77e4ee44de9c10903f2045287dc86ed2b170c5da019f9880f8fe2f4962a0` and TP/FP/FN/TN=76/1126/14/44024. Include tests for distinct metrics, one vs two robust shifts, weak third metric, confirmation-false, flat/noise, onset/recovery, missing samples, duplicate timestamps, and isolation across services.
- **One-time fresh evaluation** occurs only after this registration is merged and the separate implementation PR passes CI/CodeQL and human review. Ordinary unit tests and push/PR CI must **not** generate these four fresh seeds. No early stop, seed replacement, threshold change or second run after inspecting results.
- Any invalid data, baseline mismatch or execution failure is an INVALID experiment, **not PASS**. All four per-seed gate triplets must pass to describe an *independent synthetic-only candidate pass*. No pooled aggregate may hide a seed failure.

## Decision boundary

Even successful independent synthetic results **cannot** change official AI-9 FAIL or P01 NO-GO/BLOCKED. A live production decision requires separately authorized, independently labeled real incident data, privacy/source provenance review, tested tenant identity and RLS isolation, spending controls and explicit owner signoff. No production change or paid service is authorized by this study.

Implementation will be isolated to new modules/tests, with ordinary CI executing only fixed hand-authored fixtures plus the already consumed seed. The new-seed evaluator shall be an explicit offline command and report its version, exact revision and all denominators. [GitHub Actions workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) governs any later workflow addition; no automatic holdout workflow is authorized by this registration.

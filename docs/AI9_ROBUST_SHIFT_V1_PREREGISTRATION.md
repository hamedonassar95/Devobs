# AI-9 Robust Shift Candidate v1 — Frozen Preregistration

**Policy ID:** `ai9-robust-shift-confirmation-v1`. **Classification:** synthetic development only. **Status:** REGISTERED / NOT RUN. **Baseline snapshot:** `df3c0758fc66546f6674c68bf47c14eee71bee56`. **Owner quality gates unchanged:** window Precision ≥80%, window Recall ≥80%, window FPR ≤5%.

**Decision before this study:** AI-9 **FAIL**, P01 **NO-GO / BLOCKED**. No production detector, provider resource, customer data, paid AI inference, rollout, secrets, environment or deployment configuration may be altered under this registration.

## Why this candidate

Previous already-consumed seed `20270201` yielded TP=76, FP=1,126, FN=14, TN=44,024 after confirmation; 794 false positives occurred in noisy synthetic control recipes, and EWMA was associated with 1,119 false-positive windows. These are **post-hoc descriptive associations**, not proof of causality or a new holdout. The existing window-level policy requires ≥80% Precision, not an incident-level surrogate.

## Exact frozen algorithm (no tuning after holdout)

The frozen baseline for the comparison is the existing `ai9-ewma-noise-candidate-v1`, with preserved other channels, followed by `ai9-post-detector-confirmation-v1`. The **only** candidate change is an additional per-metric *causal robust-shift* decision applied **after** the existing confirmation output; keep all existing raw channels and confirmation state evolution unmodified.

For each metric at sample index `i >= 32`, use exactly 33 consecutive finite values ending at `i`. Define:
- `reference = values[i-32 ... i-3]` (30 observations, excluding current three);
- `recent = values[i-2 ... i]` (three observations);
- `center = median(reference)`, with even-length median the mean of the middle two ordered values;
- `mad = median(abs(x-center) for each reference x)`;
- `shift = abs(median(recent) - center)`;
- `robust_shift = (shift > 4 * mad)`, strict `>` (not `>=`). No fitted offset, hidden metric-specific threshold, min floor, data-specific parameter or future observation is allowed.
- `candidate_confirmed = existing_confirmed && robust_shift`. When `existing_confirmed` is false, candidate is false. Do **not** use labels or group identifiers in candidate decisions, and do not modify the existing detector or confirmation component.

Invalid / missing / nonfinite data, inconsistent metric cadence, duplicate or out-of-order event timestamps or unavailable history **fail closed** (no positive signal, diagnostic error/invalid sample recorded). The existing confirmation layer retains its own idempotency/gap behavior; this offline evaluator must not fabricate samples. For deterministic evaluation, use the existing generator's fully populated finite 30-point baseline, 60-second cadence, per-service metric triplets, and distinct per-service confirmation state.

## Frozen fresh evaluation

- **Exactly four** previously unconsumed synthetic seeds: `20270401, 20270402, 20270403, 20270404`, ascending, once each. A repository text search before registration found no use of `20270401` or `20270404`; verify that all four are absent from earlier evaluator and diagnostic seed sets before the one-time run. If overlapping, report **INVALID / NO RESULT**, do not silently replace the seeds.
- Retain `generateAi9MultimetricServicesV1` and its unchanged generator policy, population, labels, sampling, fault windows and canonical input digest calculation. Exactly 56 services × 3 metrics, 45,240 scored windows per seed (90 positive, 45,150 negative), with 30 historical baseline observations and the same fault onset/duration. No new generator parameters.
- Compare the *existing post-confirmation baseline* against the robust-shift post-confirmation candidate on **identical** generated data. Score both with `scoreAi9Confusion`, report TP, FP, FN, TN, Precision, Recall, FPR and corresponding frozen per-seed threshold statuses. Record exact input SHA-256 per seed, policy IDs, source commit of implementation, and complete reproducible command.
- Describe per-seed fault detection delay in observed windows where measurable. Missing detections are **missing**, not zero delay. Report false-negative difference and FP difference per seed. Episode/RCA claims are outside the frozen gate scope.
- **No early stopping**, cherry-picking, threshold adjustment, rerun after observing outcomes, or use of prior used seeds as evidence of fresh performance. A failed test, invalid input digest, or mismatched baseline is an invalid experiment that must be reported rather than interpreted as PASS.
- One-time execution is separate from ordinary CI, only after the preregistration commit is merged and deterministic unit tests pass. Do **not** run the fresh four seeds in any ordinary unit test or test-on-push workflow.

## Required tests before first evaluation

Use tiny hand-constructed arrays (not new holdout seeds) for unchanged reference, noisy sub-threshold values, one-sample spikes, sustained shifts, fault onset/recovery, finite input contract, incomplete history, duplicate/out-of-order timestamp and state restart/independent service isolation. Include a replay sanity check only on **previously used seed 20270201**, matching its exact frozen baseline confusion counts and canonical input hash; any mismatch blocks fresh evaluation.

## Results and authorization

The preregistered window gates are unchanged: Precision ≥0.8, Recall ≥0.8, FPR ≤0.05 **for each seed**. Report every threshold separately; no aggregate gate substitution. Even if all four synthetic seeds pass, the study is **synthetic-only** and **does not authorize AI-9 production PASS or P01 GO**; expert-labeled independent real data, privacy approval, full operational security and human release approval are separate requirements. No real customer telemetry or external credentials may be used.

GitHub Actions behavior and job permissions are documented in [GitHub Actions documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax); no changes to Actions or cloud deployment are authorized by this preregistration alone.

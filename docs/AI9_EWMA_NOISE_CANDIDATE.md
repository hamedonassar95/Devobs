# AI-9 EWMA Noise Candidate — development only

**Status:** isolated development candidate; not a production change, official evaluation, or readiness claim. AI-9 remains **FAIL** and P01 remains **NO-GO / BLOCKED**.

## Provenance and scope

- This is a new local branch from `origin/main` at `4ec9fd138f004498827b5c3b903a78971a8e6706`, created after the historical AI-9 branch and commit proved unavailable in this workspace. It is not a restoration of that branch.
- The factor-ablation recipe and its generator contract were supplied by the owner in this conversation. `ai9_alpha_detector.mjs` is a development-only copy of the `origin/main` detector logic, with EWMA alpha made explicit; the production `anomaly_detector.mjs` is unchanged.
- `ai9_ewma_noise_candidate.mjs` adds a causal trailing median of three values before the existing EWMA calculation. It changes no production detector, threshold, evaluator, or CI gate.
- The candidate is not connected to the application, report command, or official evaluator. The factor-ablation evaluator is present for future development-only use and was not run in this task.

## Frozen candidate policy

Policy version: `ai9-ewma-noise-candidate-v1`.

| Setting | Candidate value | Status |
| --- | --- | --- |
| Filter | Causal trailing median, width 3 | Candidate choice; not validated on AI-9 gates |
| EWMA alpha | 0.3 by default; 0.5 accepted for isolated diagnostics | Existing alpha values only |
| Baseline | 30 points | Held fixed |
| `before` | 0 seconds | Synthetic assumption only |
| `after` | 120 seconds | Synthetic assumption only |
| Episode close | Two observed quiet windows | Synthetic assumption only |
| Gate requirements | Precision ≥80%, Recall ≥80%, FPR ≤5%, median delay ≤2 windows, RCA Top-3 ≥70% | Unchanged; no result produced |

These timing values are **synthetic assumptions**, not official recommendations. The policy version accompanies every candidate score. The candidate score reports only EWMA fields; it does not calculate Precision, Recall, FPR, episode eligibility, or RCA.

## Expected trade-off and limits

The median filter suppresses an isolated one-window excursion and can pass a sustained level shift after two changed samples in the included unit fixture. That is an implementation behavior, not evidence that AI-9 Recall is preserved. A real one-window fault may also be suppressed. Precision, Recall, FPR, delay, and RCA have **not** been measured for this candidate.

The factor-ablation generator uses development seed `20261104`, six fault-free synthetic recipes, and a 30-point baseline. Its measurements are not rerun here; the seed is already consumed for development and cannot establish independent quality. No official evaluation seed, holdout episode data, real data, or production service was used.

## Next evidence required

Any future performance run needs a new, pre-registered synthetic development protocol and policy version. Keep its results separate from official/real data. Do not select a winner or modify production from the generator tests or the historical owner-provided results. AI-9 stays **FAIL** unless the unchanged official evaluator provides verifiable passing results under an authorized protocol.

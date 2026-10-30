# AI-9 Robust Shift v1 — Implementation (development-only)

**Policy:** `ai9-robust-shift-confirmation-v1` from [frozen preregistration](AI9_ROBUST_SHIFT_V1_PREREGISTRATION.md), merged in PR #321 **before** implementation or fresh-seed evaluation.

## Source boundary

- `scripts/ai_intelligence/ai9_robust_shift_candidate.mjs` implements the exact 30-reference, 3-recent, strict `shift > 4 * medianAbsoluteDeviation(reference)` rule. It receives the existing confirmation boolean; it cannot generate positives when the current confirmation is false.
- `scripts/ai_intelligence/ai9_robust_shift_evaluation_v1.mjs` reuses the frozen generator, existing detector/confirmation layer and metric-window scoring. CLI `--replay-used` executes **only** the already-consumed seed `20270201`. CLI `--fresh-once` is reserved for a **separately authorized single evaluation** of the four preregistered seeds `20270401`–`20270404`; ordinary CI **never** invokes it.
- `tests/ai9_robust_shift_candidate.test.mjs` checks fault onset/absence/recovery, noise/drift, replay determinism, finite values and chronological cadence errors.
- `tests/ai9_robust_shift_evaluation_v1.test.mjs` compares the previous historical baseline TP/FP/FN/TN and canonical input SHA-256 with the **previously published** frozen report; new seeds are intentionally not touched.
- The existing source and policy of `anomaly_detector.mjs`, `post_detector_confirmation.mjs`, and all production services remain unchanged.

## Evidence ladder

1. **Red / VERIFIED:** The original stub generated six `robust_shift_not_implemented` test failures in GitHub Actions CI run [41133572106](https://github.com/hamedonassar95/Devobs/actions/runs/41133572106). This is deliberate TDD test evidence, not a release.
2. **Green / VERIFIED:** Replacing the stub with the frozen candidate produced six passing focused tests in the Node job from [CI 41133698364](https://github.com/hamedonassar95/Devobs/actions/runs/41133698364). Those tests do not establish detector quality.
3. **Historical replay / PENDING until CI completed:** New test verifies the old `20270201` baseline digest/counts, then records exploratory candidate changes without treating them as fresh results.
4. **Fresh one-time synthetic test / NOT RUN:** The frozen four new seeds may be evaluated **once** only after full contract tests, PR review, merge and explicit tracking of the source SHA. Any misaligned input or failed historical replay invalidates the test. Passing synthetic metrics alone never grants production GO.
5. **Real-world evaluation / BLOCKED:** Requires independently reviewed incident labels, secure service identity and permissions, data retention/privacy approvals, and explicit owner signoff.

## Local/reproduction commands

```sh
node --test tests/ai9_robust_shift_candidate.test.mjs
node --test tests/ai9_robust_shift_evaluation_v1.test.mjs
node scripts/ai_intelligence/ai9_robust_shift_evaluation_v1.mjs --replay-used
```

The one-time holdout command `--fresh-once` is **not** part of CI or automated deployment and is deliberately not run in this change.

**Decision remains:** AI-9 **FAIL**, P01 **NO-GO / BLOCKED**, no cloud, payment, data transfer, secrets or tenant activation.

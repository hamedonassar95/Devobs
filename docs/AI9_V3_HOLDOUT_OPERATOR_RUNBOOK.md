# AI-9 v3 — one-time independent synthetic holdout operator procedure

**Registration:** [AI9_COHERENT_ONSET_V3_PREREGISTRATION.md](AI9_COHERENT_ONSET_V3_PREREGISTRATION.md) (registered before v3 code).  
**Owner consent:** The owner explicitly consented in the current ChatGPT conversation to a **single offline evaluation of 20270601–20270604 after the evaluator has been prepared and reviewed**. This prose is **not** an authenticated GitHub approval or a waiver of review/merge gates.  
**State of this PR:** Evaluator preparation and non-consuming contract tests only. **No independent seed has been generated or evaluated by this PR.**

## Separation of concerns

- The standalone `scripts/ai_intelligence/ai9_v3_frozen_holdout_once.mjs` is **not** imported into any server or app, and its scoring function runs **only** with explicit `--fresh-once --approved-sha <full-main-sha>`.
- CI runs a syntax check and hand-authored contract tests only; it MUST NOT run the one-time evaluation command, import a live holdout evaluation function, or create holdout artifacts.
- Node's module import does not run the evaluator; its top-level CLI guard rejects unspecified switches.
- No model API, real telemetry, secrets, SaaS deployment, production detector change, or paid resource is used.
- Outputs are summarized per-seed statistics and input digests, not raw time series. The results are only independent **seed draws on the existing synthetic generator**, not independent real-world validation.

## Mandatory review gate, before any fresh evaluation

1. Review and merge this evaluator PR **only with the repository owner's explicit approval for that reviewed SHA**. Check the exact PR head's `validate`, security, Node contract and CodeQL checks. The merged revision is the evaluation candidate; confirm no unreviewed code or generator/threshold changes.
2. Confirm `main` is clean, checked out locally, fully fetched (non-shallow), and at its latest merged SHA. Review every occurrence of `20270601`, `20270602`, `20270603`, `20270604` in GitHub **history and prior result artifacts**. Preregistration/documentation mentions are expected; an earlier scored result, leaked holdout metrics, or previously consumed seed invalidates this registered experiment. Automated preflight also checks historical `docs/*RESULTS.json` changes; it is a fail-closed screen, **not a substitute for human history review**.
3. Check that both `docs/AI9_V3_FROZEN_HOLDOUT_LOCK.json` and `docs/AI9_V3_FROZEN_HOLDOUT_RESULTS.json` are absent from main and all remote refs, and that no uncommitted local run has already started.
4. Review the operator's **existing specific consent for exactly this four-seed, single, no-fee offline evaluation** and record the approved **exact main SHA** in a signed/attributable owner decision on GitHub. Do not infer this approval solely from a passed CI or AI advisory.
5. Run the script exactly **once** from a clean local checkout of `main` with Node.js, using:

```bash
git fetch --all --tags
git checkout main
git pull --ff-only
git rev-parse HEAD
git rev-parse --is-shallow-repository
git status --porcelain
node scripts/ai_intelligence/ai9_v3_frozen_holdout_once.mjs --fresh-once --approved-sha <owner-approved-main-40-character-sha>
```

The script rejects mismatched SHA, non-main branch, shallow/dirty checkout, existing lock/results and structured historical result-artifact seed collisions. It first replays the previously used `20270201` for reference integrity. **Only then** does it write a one-time lock before generating any reserved seed. If the run fails after locking, it writes INVALID and refuses automatic retries. **Do not delete the lock, change the seed set, rerun selectively, or cherry-pick results.**

6. Commit both lock and result artifacts (including failure/INVALID) in a **separate reviewable PR** with the evaluated SHA and CI/test evidence. Do not merge or re-run because of an undesired result. No secrets or raw customer data are recorded.

## Frozen acceptance, no threshold search

Four independent seed draws: `20270601`–`20270604`; each contains exactly 56 services × three synchronous metric streams, 45,240 scored metric windows, 90 positive and 45,150 negative. Report for **each seed** the canonical input SHA256, baseline/v2/v3 TP/FP/FN/TN and all window Precision, Recall, FPR, detection-delay/missing counts. Every individual v3 seed must meet:

- Precision ≥ 80%.
- Recall ≥ 80%.
- FPR ≤ 5%.

If any seed misses a threshold the result is **FROZEN_WINDOW_GATES_FAIL**, not an excuse to tune, re-seed, aggregate or repeat. A valid synthetic-only PASS does **not** authorize the production detector or change `AI-9 FAIL / NOT AUTHORIZED`; `P01 NO-GO/BLOCKED` remains. Independent labelled incident data, privacy/provenance, auth/RLS, alerts, live reliability and a new explicit release decision are separate.

## Rollback and safety

Closing this PR before merge changes nothing on main. Reverting the evaluator code after a future merge does not invalidate previously recorded evidence or permit another run. The dry/unit tests prove **contract behavior only**, not the independent holdout or production readiness.

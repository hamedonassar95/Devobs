# AI-9 Detector-to-Confirmation Adapter v1 — Implementation Record

**Status:** local composition prototype. AI-9 remains **FAIL** and P01 remains **NO-GO / BLOCKED**. No production detector, threshold, gate, evaluator, or live resource changed.

## API and data flow

`createDetectorConfirmationAdapter({ confirmationLayer })` exposes asynchronous `processEventWindow({ serviceId, occurredAt, events })`. It runs the repository's existing `analyzeMetricEvents` detector over stored server-metric events, validates that each metric's latest observation is aligned to the canonical UTC window timestamp, and forwards only `{ metric, channels }` plus the caller-provided service ID to the injected confirmation layer or local journal.

The adapter rejects non-metric events, empty/oversized/duplicate event batches, duplicate metric names, inconsistent detector results, non-canonical timestamps, and misaligned latest observations before calling confirmation. Its output contains the adapter and confirmation policy versions plus the confirmation implementation's output; raw metric values and detector result details are not copied into the output. The adapter propagates fixed error codes and does not print or persist input.

The service ID is passed through from the caller. The event schema has no authenticated service identity, so this adapter **does not** authenticate the caller, establish tenant scope, prove that events map to the supplied ID, or establish source provenance. An upstream identity mapping and authenticated boundary are required before any real integration.

## Verification

- Preregistration was committed before implementation in [`AI9_DETECTOR_CONFIRMATION_ADAPTER_V1_PREREGISTRATION.md`](AI9_DETECTOR_CONFIRMATION_ADAPTER_V1_PREREGISTRATION.md), based on `origin/main` `498e629dcd0c2d915226444e736c30aff8e97b69`.
- Focused end-to-end contract: `node --test tests/post_detector_confirmation_adapter.test.mjs` — **6/6 passed**. Tests use only synthetic metric histories and a disposable private directory.
- Full Node suite: `node --test tests/*.test.*` — **127/127 passed**, 0 failures, 0 skipped.
- `python3 -m unittest discover -s tests -p 'test_ci_trigger_contract.py' -v` — **2/2 passed**.
- `python3 -m unittest discover -s tests -p 'test_ci_release_gate.py' -v` — **1/1 passed**.
- `python3 scripts/check_action_pins.py` — **39 workflow/template files passed**.
- `python3 scripts/check_agent_spec.py` and `python3 scripts/check_site.py` — **PASS**.
- `node --check` for the adapter and its test, plus `git diff --check` — **PASS**.
- A full local Python suite was attempted and did not complete: 534 tests ran, 18 skipped, and the staging-app test setup errored because `psycopg` is not installed in this workspace. This feature changes no Python source; this is a local environment limitation, not a passing local Python result.
- CI workflow now syntax-checks and runs the adapter contract in the existing Node job. On implementation head `ca4d744037a6f2694d85a52a82c8d71d7dc5839e`, PR #303 CI run [`41067497186`](https://github.com/hamedonassar95/Devobs/actions/runs/41067497186) passed, including hosted Python validation, and CodeQL run [`41067491831`](https://github.com/hamedonassar95/Devobs/actions/runs/41067491831) passed; Vercel Preview also succeeded. Those runs predate this evidence-only documentation update; the final PR head must pass its own required checks before merge. No main-branch result is claimed here.

## Limits and gate status

This is a behavior-composition test and prototype, not a detector-quality measurement. It did not calculate Precision, Recall, FPR, prevalence, or any AI-9 gate; it did not generate or consume evaluation seeds or holdout data. It did not connect to a network, alert provider, API, hosted database, or live service. The local journal still provides local single-writer persistence only. Service mapping, authentication, tenant enforcement, delivery/retry operations, and a production storage/retention design remain unresolved.

The step does not change AI-9 **FAIL**, P01 **NO-GO / BLOCKED**, the existing gate definitions, detector behavior, or thresholds.

# AI-9 Synthetic Evaluation v2 — Results

**Classification:** development-only synthetic measurement; not the historical AI-9 evaluation and not production evidence. The recorded AI-9 state remains **FAIL** and P01 remains **NO-GO / BLOCKED**.

## Protocol and run

- Frozen protocol: [`AI9_SYNTHETIC_EVALUATION_V2_PREREGISTRATION.md`](AI9_SYNTHETIC_EVALUATION_V2_PREREGISTRATION.md), registered before measurement.
- Evaluation policy: `ai9-synthetic-window-evaluation-v2`.
- Candidate policy: `ai9-ewma-noise-candidate-v1`.
- Assumptions: `before=0s`, `after=120s`, close after two observed quiet windows.
- Run time: 2026-10-30 04:03:05 UTC.
- Code snapshot scored: `71e5e53` (`feat(ai9): add isolated synthetic evaluator v2`), based on `origin/main` at `4d20a9c0d6dd3c57c7ca72f4bb6d9948b428a386`.
- Command, run once: `node scripts/ai_intelligence/ai9_synthetic_evaluation_v2.mjs`.
- Input SHA-256 (canonical in-memory input): `1e4211cf0e21371cbbbc8fa3849db1fa0c859e44dab5d02e6c63bc5b33d5852b`.
- Dataset: 56 synthetic series; 15,080 scored windows; 30 positive and 15,050 negative windows. No real data or service was used.

## Window metrics

| Version | TP | FP | FN | TN | Precision (gate ≥80%) | Recall (gate ≥80%) | FPR (gate ≤5%) | Selected gates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline production detector | 30 | 1,710 | 0 | 13,340 | 1.7241% **FAIL** | 100% PASS | 11.3621% **FAIL** | **FAIL** |
| EWMA noise candidate v1 | 30 | 794 | 0 | 14,256 | 3.6408% **FAIL** | 100% PASS | 5.2757% **FAIL** | **FAIL** |

On this new synthetic input, the candidate reduced false positives by 916 (53.57%) and FPR by 6.0864 percentage points while measured window Recall stayed at 100%. It still missed the FPR gate by 0.2757 percentage points and missed the Precision gate substantially. With 30 true positives, the frozen 80% Precision gate allows at most 7 false positives; this candidate produced 794.

## Episode summary under the registered assumptions

| Version | Fault scenarios detected by an episode beginning from onset through +120s | Predicted episodes | Closed after two quiet windows | Still open at sample end | Episode summary eligible |
| --- | ---: | ---: | ---: | ---: | --- |
| Baseline production detector | 4/6 | 1,052 | 1,042 | 10 | No |
| EWMA noise candidate v1 | 5/6 | 519 | 517 | 2 | No |

These are aggregate summaries of this synthetic run. No quiet observations were appended. Episode eligibility here does not replace the historical evaluator's episode decision; no RCA Top-3 or full official episode evaluation was run.

## Historical reference (not a paired comparison)

The owner-provided earlier FAIL reference was TP=30, FP=925, FN=0, TN=14,125: Precision 3.1414%, Recall 100%, FPR 6.1462%. The new candidate measured Precision 3.6408%, Recall 100%, and FPR 5.2757%. Although both summaries have 30 positives and 15,050 negatives, they use different synthetic inputs and protocols; the difference is descriptive only and is not an independent improvement claim or a reproduction of the earlier run.

## Aggregate command output

```json
{"classification":"synthetic_development_only","registration_id":"ai9-synthetic-window-evaluation-v2","seed":20261105,"input_canonical_sha256":"1e4211cf0e21371cbbbc8fa3849db1fa0c859e44dab5d02e6c63bc5b33d5852b","candidate_policy_version":"ai9-ewma-noise-candidate-v1","evaluation_policy_version":"ai9-synthetic-window-evaluation-v2","synthetic_assumptions":{"before_seconds":0,"after_seconds":120,"quiet_windows_to_close":2},"scenario_count":56,"fault_scenario_count":6,"scored_windows":15080,"label_counts":{"positive":30,"negative":15050},"frozen_gates":{"precision":0.8,"recall":0.8,"fpr":0.05},"baseline":{"window_metrics":{"tp":30,"fp":1710,"fn":0,"tn":13340,"windows":15080,"precision":0.017241379310344827,"recall":1,"fpr":0.11362126245847176,"gate_status":{"precision":"FAIL","recall":"PASS","fpr":"FAIL"}},"episode_summary":{"fault_scenarios":6,"predicted_episodes":1052,"closed_episodes":1042,"open_episodes_at_end":10,"eligible":false,"fault_scenarios_detected_in_frozen_match_window":4}},"candidate":{"window_metrics":{"tp":30,"fp":794,"fn":0,"tn":14256,"windows":15080,"precision":0.03640776699029126,"recall":1,"fpr":0.052757475083056476,"gate_status":{"precision":"FAIL","recall":"PASS","fpr":"FAIL"}},"episode_summary":{"fault_scenarios":6,"predicted_episodes":519,"closed_episodes":517,"open_episodes_at_end":2,"eligible":false,"fault_scenarios_detected_in_frozen_match_window":5}},"selected_window_gate_assessment":"FAIL","interpretation":"Development-only synthetic comparison. This assessment does not change the recorded AI-9 FAIL or P01 NO-GO / BLOCKED states."}
```

## Verification and limits

- Focused contract tests, run before measurement: `node --test tests/ai9_synthetic_evaluation_v2.test.mjs` — 4/4 passed.
- Syntax checks for the evaluator and its focused test passed before measurement.
- The evaluator imports the production detector for the baseline and preserves its non-EWMA channels for the candidate; only the EWMA flag is substituted with the candidate result.
- This new protocol does not reconstruct the missing historical evaluator, inspect locked holdouts, alter official thresholds, or change production behavior. No push, PR, merge, deployment, or production connection occurred.
- No result from this synthetic run authorizes AI-9 PASS or P01 GO. Both remain blocked by the existing gates and by missing live/service evidence.

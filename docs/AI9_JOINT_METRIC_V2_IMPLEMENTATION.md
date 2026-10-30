# AI-9 Joint-Metric Confirmation v2 — Isolated Implementation and Development Replay

**Classification:** synthetic development only. **Official state:** AI-9 **FAIL**, P01 **NO-GO / BLOCKED**. **Preregistration** was merged in PR #323 before new code or seed measurement: [AI9_JOINT_METRIC_V2_PREREGISTRATION.md](AI9_JOINT_METRIC_V2_PREREGISTRATION.md).

## Implemented boundary

- `scripts/ai_intelligence/ai9_joint_metric_v2.mjs`: exactly three distinct, synchronous metrics per service, with independently computed, unchanged v1 robust-shift flags. Consensus requires 2 of 3. Alerts are the existing per-metric confirmation AND consensus; no new alert is created by the proposed filter.
- `scripts/ai_intelligence/ai9_joint_metric_evaluation_v2.mjs`: offline comparison of baseline post-confirmation, rejected individual robust-shift v1 and v2 joint-metric, using the frozen existing generator and confusion-matrix scorer. `--replay-used` uses already-consumed seed 20270201. `--fresh-once` is **not invoked in CI or this phase**.
- `tests/ai9_joint_metric_v2.test.mjs`: six behavior tests including distinct-metric count, weak third metric, service/time isolation and rejection of malformed inputs.
- `tests/ai9_joint_metric_evaluation_v2.test.mjs`: exact historical canonical input digest and baseline count comparison with frozen JSON. The new seeds 20270501–20270504 are **NOT RUN**.
- Existing detector, post-confirmation implementation, threshold values, RLS, secrets and deployments were not changed.

## Verified evidence

- **TDD RED:** CI run [41134679960](https://github.com/hamedonassar95/Devobs/actions/runs/41134679960), 6 failures with `joint_metric_not_implemented` prior to algorithm code.
- **TDD GREEN:** CI run [41134909863](https://github.com/hamedonassar95/Devobs/actions/runs/41134909863), six focused tests passed, zero failed.
- **Historical replay:** CI run [41135137190](https://github.com/hamedonassar95/Devobs/actions/runs/41135137190), Node job output `AI9_JOINT_V2_REUSED_SEED` matched the frozen canonical input digest and baseline counts for `20270201`.

| Window metric | Frozen baseline | Rejected v1 | Joint v2 (post-hoc) | Frozen gate |
| --- | ---: | ---: | ---: | --- |
| TP | 76 | 59 | 58 | — |
| FP | 1,126 | 66 | 8 | — |
| FN | 14 | 31 | 32 | — |
| TN | 44,024 | 45,084 | 45,142 | — |
| Precision | 6.3228% FAIL | 47.2000% FAIL | **87.8788% PASS** | ≥80% |
| Recall | 84.4444% PASS | 65.5556% FAIL | **64.4444% FAIL** | ≥80% |
| FPR | 2.4939% PASS | 0.1462% PASS | **0.0177% PASS** | ≤5% |

**Quality decision:** v2 is **NOT ELIGIBLE FOR PROMOTION** because Recall fails on the already-consumed development seed. No fresh independent performance claim can be made. The precise source of missed fault windows remains exploratory; no threshold change or deployment is justified.

## Next safe experiment

A possible **new v3** study is a first-observation exception for sufficiently large, independently confirmed changes, paired with existing cross-metric confirmation, to recover onset windows while controlling FP. This is only a hypothesis; it needs a **new preregistered algorithm and untouched seed set**, complete TP/FP/FN/TN counts, latency and slice evidence, and a human decision. No v3 is implemented here.

## Verification commands

```sh
node --test tests/ai9_joint_metric_v2.test.mjs
node --test tests/ai9_joint_metric_evaluation_v2.test.mjs
node scripts/ai_intelligence/ai9_joint_metric_evaluation_v2.mjs --replay-used
```

Do not run the `--fresh-once` command as part of ordinary CI. No cloud resource, customer data, paid inference or production authorization is involved.

# AI-9 Multi-Metric Confirmation v1 — Preregistration

| Field | Value |
| --- | --- |
| Registration | `ai9-multimetric-confirmation-v1` |
| Registered | 2026-10-30 11:39:49 UTC |
| Status | REGISTERED — NOT RUN |
| Base commit | `1bcd04e0e3d8271a50d14c2761d3ce1f4bcad270` on `main` |
| Evaluation unit | Window-level Precision, Recall and FPR |

This is a new synthetic development experiment to exercise cross-metric confirmation for the same synthetic service. It is not real telemetry, the historical AI-9 evaluation, or a production test. AI-9 remains **FAIL** and P01 remains **NO-GO / BLOCKED**.

## Frozen seeds and metric population

- Use exactly seeds `20270201` through `20270220`, ascending and once each. A read-only search of the checked-out repository found no prior occurrences. Do not substitute or add seeds.
- Each service has three time-synchronous metrics. Control services use `cpu_percent`, `latency_ms`, and `error_rate`; fault services use the metric names shown in the fault-delta table below. Metric configurations (baseline, scale, unit) are: `cpu_percent=(34,1,percent)`, `disk_percent=(34,1,percent)`, `memory_percent=(34,1,percent)`, `latency_ms=(100,2,milliseconds)`, `error_rate=(3,0.25,percent)`, and `request_rate=(34,1,per_second)`.
- Each service and metric stream has its own deterministic Mulberry32 stream initialized with `(seed XOR imul(service_index+1, 0x9E3779B1) XOR imul(metric_index+1, 0x85EBCA6B)) >>> 0`. The generator advances state by `state=(state+0x6D2B79F5)>>>0`, then applies the standard Mulberry32 integer mix `z=imul(z XOR (z>>>15), z OR 1); z=z XOR (z+imul(z XOR (z>>>7), z OR 61)); output=(z XOR (z>>>14))>>>0`, divided by `4,294,967,296`. Consume one uniform draw per observation; never share streams between metrics.
- For control groups, derive factors only from the existing group name: `seasonality=7` when the group includes `seasonality`, `drift=10` when it includes `drift`, and `noise=0.7` when it includes `noise`; otherwise each is zero. For each metric scale `s`, generate `baseline + seasonality*s*sin(2π*(i mod 1440)/1440 - π/3) + drift*s*i/(length-1) + Uniform(-noise*s, noise*s)`.
- Fault-service metric sets and fixed deltas (in their native unit) are: `fault_latency_step`: latency `+120ms`, CPU `+10pp`, error rate `+0.5pp`; `fault_cpu_step`: CPU `+18pp`, latency `+60ms`, error rate `+0.375pp`; `fault_disk_step`: disk `+25pp`, latency `+90ms`, error rate `+0.625pp`; `fault_error_rate_step`: error rate `+1pp`, latency `+100ms`, CPU `+12pp`; `fault_request_rate_drop`: request rate `-18/s`, latency `+80ms`, error rate `+0.5pp`; `fault_memory_step`: memory `+15pp`, latency `+70ms`, CPU `+12pp`. Fault streams use independent noise with amplitude `0.7*scale` and no seasonal/drift component, matching the fault-family background. Bound percent values to `[0,100]` and other metric values to nonnegative; round to four decimal places before event normalization.
- Every fault service's three metric windows are labeled positive during its existing five-window fault interval beginning at sample 150. Controls remain negative.
- Score after the existing 30-point baseline. This creates 45,240 scored metric windows per seed, exactly 90 positive and 45,150 negative windows. Fixed prevalence remains `90 / 45,240 = 30 / 15,080`; labels and denominators are identical for all three versions.
- Preserve each event's existing service-scenario timestamp. `serviceId` is the existing scenario ID supplied to the confirmation component; do not add a service identifier to the production event schema in this experiment.

## Frozen comparison and confirmation rules

Compare three versions on the same generated event values and labels:

1. The current production detector evaluated per metric.
2. `ai9-ewma-noise-candidate-v1` evaluated per metric with its current preserved-channel composition.
3. The same candidate's channel outputs passed together for all three metrics at each service timestamp through `ai9-post-detector-confirmation-v1`.

The confirmation layer remains frozen: confirm a metric window if it has a raw signal and either the same channel occurs in at least 2 of the current and previous 2 observed windows, or at least 2 distinct metrics for the same service have raw channel signals in the inclusive 120-second interval including the current window. Multiple channels on one metric are not independent evidence. Group confirmed metric windows into incidents per service+metric; close after two observed quiet windows. Gaps, ordering and missing-sample behavior remain exactly as in the already committed component.

Record confirmed windows attributed to persistence and cross-metric coincidence. Count a fault service as episode-matched when at least one layer incident starts for any of its three metrics during `[fault onset, onset+120s]`. Episode outcomes stay descriptive; no incident-level gate is introduced.

## Frozen metrics and stopping rules

- Use the existing per-seed gates unchanged: Precision `>=0.80`, Recall `>=0.80`, FPR `<=0.05`. No aggregate acceptance gate is added.
- Record per seed/version TP, FP, FN, TN, Precision, Recall, FPR, false-negative windows, and fault-service scenarios without a matching confirmed incident start.
- Report arithmetic mean and population variance over the 20 per-seed proportions for Precision, Recall and FPR. Variance units are percentage-points squared. Also report per-seed gate pass counts and mean paired Precision gain/Recall loss versus current candidate, total additional FN windows, and Recall loss per Precision point gained when the gain is positive.
- Report grouped, closed, open-at-end and interrupted incident totals, plus separate counts of confirmed metric windows attributed to each confirmation rule. These are descriptive only.
- Report prevalence and theoretical `Pmax = prevalence / (prevalence + (1-prevalence)*FPR)` at FPR `5%, 1%, 0.1%, 0.05%, 0.01%, 0%`, assuming perfect Recall. Lower Recall lowers Precision at fixed FPR.
- Record each seed's canonical input digest. Emit aggregate/per-seed confusion metrics and digests only; never emit raw series values.
- Freeze generator, evaluator, and contract tests before generating any registered seed. Run once. Do not edit assumptions, labels, rules, gates, or seeds after viewing any result. On any mismatch, stop and report it without changing the preregistration.

## Limits and integration boundary

This design intentionally adds three metric streams to a synthetic service and defines correlated fault effects. Twenty seeds vary noise realizations within one frozen synthetic family; they are not twenty independent real-world populations. The repository's current event schema does not carry a service identity; this replay supplies the existing scenario ID out of band to exercise the layer only. It does not validate a live metric-to-service mapping, real cross-metric correlation, durable state, delivery ordering, alert routing, or real incident prevalence.

No production detector, thresholds, gate definitions, service, secrets, real data, official/locked holdout, cloud provider, or AI inference is involved. Passing this experiment cannot change AI-9 FAIL or P01 NO-GO / BLOCKED.

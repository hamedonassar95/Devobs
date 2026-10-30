# AI-9 Post-Detector Confirmation Layer v1 — Preregistration

| Field | Value |
| --- | --- |
| Registration | `ai9-post-detector-confirmation-v1` |
| Registered | 2026-10-30 11:21:28 UTC |
| Status | REGISTERED — NOT RUN |
| Source snapshot | `e5e254c` on `feature/ai9-synthetic-eval-v2` |
| Evaluation unit | Window-level Precision, Recall, and FPR |

This is a standalone synthetic development experiment. It does not reproduce the historical AI-9 evaluator. The owner decided that Precision remains a window-level gate and that no incident-level gate is added. AI-9 remains **FAIL**; P01 remains **NO-GO / BLOCKED**.

## Frozen comparison and new seeds

- Compare the current production baseline, current `ai9-ewma-noise-candidate-v1`, and that same candidate followed by the independent confirmation layer defined below.
- Use exactly the new seeds `20270101` through `20270120`, in ascending order, once each. A read-only search of the current workspace found no prior references to these seeds; do not use other seeds. The prior `20261201`–`20261220` and `20261105` seeds are excluded.
- For each seed, use the fixed v2 generator unchanged: 56 scenarios, 15,080 scored windows, 30 positives, 15,050 negatives, same scenario order, values, labels, timestamps, PRNG, and event bounds. Only the seed varies. Both references and the layered candidate consume the same observations and labels per seed.
- The candidate input is the v1 detector's channel output, not raw metric data. Map channel names to `z_score`, `moving_average`, `ewma`, and `error_rate_spike`. The layer never changes detector thresholds or raw predictions.

## Frozen confirmation component

Implement an independent stateful component with a narrow interface: `processServiceWindow({ serviceId, occurredAt, metrics: [{ metric, channels }] })` plus a read-only snapshot method. `channels` contains the distinct detector channels that flagged that metric at that observed window. The component returns per-metric `confirmed`, confirmation reasons, incident ID/state, and closure or interruption status. It does not import or mutate the production detector.

An initial warning becomes a confirmed window alert only when the current metric has at least one raw channel signal **and** either of these rules is satisfied:

1. **Persistence:** the same channel is active in at least 2 of the current and previous 2 observed windows for the same service and metric.
2. **Cross-metric coincidence:** at least 2 distinct metric names in the same service have emitted a channel signal within the inclusive 120-second window, including a current signal for the metric being confirmed.

Distinct detector channels on one metric are not treated as statistically independent. Cross-metric coincidence is supported by the component contract, but the frozen v2 benchmark has one metric per synthetic service; therefore only the persistence route can activate in that benchmark. Unit contract tests will exercise the cross-metric route separately.

Confirmed alert windows for the same service and metric are grouped into one incident when the gap between consecutive confirmed windows is at most 120 seconds. The incident closes only after two consecutive **observed** quiet windows. Do not fill missing windows or append synthetic quiet observations. A metric absent from a service window is missing, not quiet. Reject duplicate/out-of-order timestamps. If the observed service cadence has a gap greater than 60 seconds, clear confirmation history and mark any active incident interrupted/ineligible; do not infer quietness across a gap.

Window-level gate predictions are the component's `confirmed` booleans. Incident grouping is descriptive only and does not change window labels, add an incident Precision gate, or replace the existing gates.

## Frozen metric policy

- Keep cadence 60 seconds, baseline 30 points, `before=0s`, `after=120s`, and two observed quiet windows for incident closure.
- Keep the per-seed gates unchanged for all three versions: Precision `>=0.80`, Recall `>=0.80`, FPR `<=0.05`.
- For every seed/version record TP, FP, FN, TN, Precision, Recall, FPR, the number of false-negative windows, and the number of injected fault scenarios with no confirmed incident start in `[fault onset, onset+120s]`.
- Report arithmetic means and population variances over the 20 per-seed proportions for Precision, Recall, and FPR. Variance units are percentage-points squared. Report per-seed gate pass counts; add no aggregate acceptance rule.
- Report paired mean Precision gain vs. current v1, paired mean Recall loss vs. current v1, absolute increase in missed positive windows, and `Recall loss / Precision gain` when Precision gain is positive. If there is no positive Precision gain, label the ratio `not applicable`; do not divide by zero or claim a tradeoff.
- Report descriptive grouped-incident totals and open/interrupted counts. They are not quality gates.
- Report the fixed synthetic prevalence `30 / 15,080` and theoretical maximum window Precision at FPR `5%, 1%, 0.1%, 0.05%, 0.01%, 0%`, assuming perfect Recall: `Pmax = prevalence / (prevalence + (1-prevalence)*FPR)`. State that lower Recall gives lower Precision at the same FPR.
- Do not emit raw metric values. Record each seed's canonical input digest. Do not use real data, external services, production systems, prior seeds, or official/locked holdouts.
- Freeze implementation and contract tests before generating any of the 20 seeds. Run the comparison once. Do not change confirmation rules, cadence, gates, labels, or seed list after seeing results.

## Integration and evidence boundaries

The v2 synthetic generator uses one metric per scenario, so this experiment measures persistence confirmation and not real cross-metric service correlation. The repository's current metric event schema has metric name/value/unit but no service identity. This component's contract accepts a service ID, but the actual service-to-metric mapping, durable state/restart behavior, real telemetry cadence, idempotency, backpressure, alert routing, and labeled real incident prevalence remain unverified. Repository AI evaluation fixtures are marked synthetic/unreviewed; they are not evidence of operational incident prevalence.

Passing synthetic tests or results cannot set AI-9 to PASS or P01 to GO. No production wiring, detector change, threshold change, publication, push, PR, or merge is authorized.

**At registration time:** no component implementation, contract test, or scoring run for this policy exists.

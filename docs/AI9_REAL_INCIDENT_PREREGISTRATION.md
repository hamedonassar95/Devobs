# AI-9 Natural-Incident Evaluation — Preregistration Protocol

**Protocol checked:** 2026-11-13. **Classification:** future-study design; not a
dataset registration, evaluation authorization, result, or release decision.
**Current status:** no qualifying natural-incident corpus has been identified or
approved in this repository; no evaluation was executed for this protocol.
AI-9 remains **BLOCKED** and P01 remains **NO-GO**.

This protocol defines the evidence that must be frozen before an independent
natural-incident evaluation can be considered. It does not select or download a
dataset, alter the detector, evaluator, comparator, thresholds, seeds, or CI, or
authorize data access. A future study is not preregistered until a reviewed
registration binds the exact eligible dataset, rights, label rubric, code, and
immutable manifest. Public-source assessments already completed are summarized
in [AI-9 External Dataset Assessment](AI9_EXTERNAL_DATASET_ASSESSMENT.md); this
document does not repeat those studies.

## 1. Admission criteria for a natural-incident corpus

Every requirement below must be evidenced before data are admitted to the final
holdout. A missing or unsupported requirement makes the affected metric or
corpus **NOT_EVALUABLE**; it is not an invitation to infer labels, alter the
production contract, or silently omit a gate.

1. **Lawful provenance and rights.** Record the data controller and source,
   collection context, lawful basis, applicable contract/license, permitted
   evaluation and derived-label uses, retention and reporting rights, and any
   commercial-use restrictions. A code or repository license does not grant
   rights to its telemetry, logs, incident reports, or personal data. If rights
   are unclear, mark them **UNVERIFIED** and exclude the source.
2. **Naturally occurring incidents.** Include unplanned incidents observed in
   the intended operating environment. Exclude injected, simulated, staged,
   synthetic, benchmark-generated, planned-maintenance, and test failures from
   the natural-incident cohort. Production-derived telemetry with injected
   failures is still not a natural incident. Record a reason for every
   exclusion before predictions are revealed.
3. **Independent labels.** Two qualified reviewers independently label whether
   an incident occurred, its onset and end, affected services, and root cause.
   Reviewers must be blinded to detector output and must not be the model or
   detector authors. Use source postmortems, tickets, or equivalent evidence;
   record source type, rubric/version, confidence, and inter-rater agreement.
   A third qualified reviewer adjudicates disagreements under the frozen rubric.
   Do not infer ground truth from a detector alert or model-generated RCA.
4. **Time and service mapping.** Store pseudonymous incident IDs, UTC onset/end
   timestamps, affected-service identifiers, the service-registry version,
   source time zone and clock assumptions, and evidence connecting the root cause
   to the affected service. Freeze a deterministic metric-to-service mapping,
   metric names, units, schema, and transformation provenance before scoring.
   Keep root-cause service distinct from downstream affected services.
5. **Cadence and missing observations.** Record native sampling cadence,
   timestamp precision, duplicates, gaps, and missingness by service and metric.
   The current AI-9 v3 input contract requires the existing synchronous
   60-second window. Do not interpolate, downsample, backfill, pad quiet periods,
   or otherwise convert an incompatible source for this protocol. A source that
   cannot be evaluated through the already-approved, production-identical input
   and scoring contract is **NOT_EVALUABLE**. Missing values remain missing;
   report their count and gap distribution. Freeze exclusions and eligibility
   rules before predictions are unblinded.
6. **Privacy and retention approval.** Obtain written data-owner and privacy/legal
   approval for the stated purpose, data minimization, pseudonymization,
   controlled access, encryption, retention period, deletion date, and allowed
   outputs. Keep private telemetry and incident narratives out of Git, PRs,
   public artifacts, and third-party services. This repository task neither
   accesses nor uploads private logs.
7. **Immutable version and checksums.** Before scoring, create a manifest of
   source URI/record and immutable version, exact selected files, byte sizes,
   SHA-256 digests, label and service-map versions, preprocessing/evaluator
   identifiers, and exclusions. Hash the canonical manifest and preserve it in
   an approved restricted evidence location; publish only an appropriately
   redacted manifest/hash. Do not commit raw data. Mutable branch names alone
   are not immutable versions.
8. **Sample-size and sampling-frame justification.** Before looking at model
   results, specify the target population and sampling frame, incident and
   negative-control denominators, expected prevalence, anticipated clustering,
   desired uncertainty or power, and handling of missing/withdrawn records.
   Justify counts separately for incident recall, precision, false-positive
   rate, latency, RCA, and planned service/class slices. A convenience or
   case-control sample cannot estimate population precision or FPR without a
   defensible representative negative frame or valid sampling weights. Do not
   treat correlated windows from one incident as independent incidents. The
   approximately 30 cases noted in issue #224 are an initial-review milestone,
   not evidence of adequate power for this protocol. Use a documented power or
   precision calculation; for simple proportions, a conservative planning
   approximation is `n ≈ z² × 0.25 / d²` (for 95% confidence and ±10 percentage
   points, about 97 independent units). This is an illustration, not a minimum,
   acceptance criterion, or replacement for exact/cluster-aware analysis.

## 2. Frozen evaluation method and reported metrics

Use only the existing AI-9 candidate, production detector path, preprocessing,
comparator, and evaluator identified by exact revision in the future
registration. Do not tune, recalibrate, retrain, change labels, or change
thresholds against the holdout. Window-level definitions and gates in the
currently approved AI-9 registration remain authoritative. The existing
external assessment records window Precision ≥80%, Recall ≥80%, FPR ≤5%, median
detection delay ≤2 windows, and RCA Top-3 ≥70% where applicable; this protocol
does not redefine them. If an authoritative current contract differs, resolve
that discrepancy in review before registration, not after scoring.

Report, with numerators, denominators, and applicable uncertainty intervals:

- **Precision, recall, and false-positive rate:** calculate using the existing
  AI-9 window-level evaluator and its frozen label/window rules. Show TP, FP,
  FN, TN and the negative-window denominator. Do not substitute point-adjusted
  or event-adjusted scores for the frozen window gates. Report incident-level
  event coverage separately as a descriptive measure.
- **Incident detection latency:** for each independently labeled incident,
  measure elapsed time from adjudicated UTC onset to the first eligible alert
  under the existing scoring rule. Report seconds and 60-second windows,
  medians and distributions; a missed event remains a miss and must not be
  dropped from latency reporting. Preserve the current latency criterion where
  applicable; do not add or relax a threshold here.
- **Root-cause ranking:** report Top-1 and Top-3 against the independently
  adjudicated root-cause service, with eligible case counts. Count an abstention
  as incorrect for Top-1 and Top-3, and report abstention/coverage rate
  separately. If the frozen AI-9 candidate does not emit a compatible ranking,
  RCA metrics are **NOT_EVALUABLE**; do not add a ranker for this evaluation.
- **Slices:** report each supported service and preregistered incident class
  separately, including positive/negative denominators, missingness, abstentions,
  and uncertainty. Identify unsupported slices as **NOT_EVALUABLE**. Do not
  create post-hoc classes or pool a failing slice into a pass.
- **Negative-control burden:** report false alerts as windows and alerts per
  eligible service-day, with the exposure denominator. These are descriptive
  operational measures unless an existing approved gate specifies otherwise.
- **Failure and uncertainty reporting:** include all registered metrics,
  counts, excluded/invalid cases and reasons, label disagreements, misses,
  abstentions, failed strata, and deviations. Use exact binomial intervals for
  independent binomial units when appropriate; use a preregistered cluster
  bootstrap over whole incident/outage or service-time blocks for correlated
  observations. State interval method, confidence level, resampling unit,
  seed, and iteration count before unblinding. Small-sample uncertainty must
  remain visible. Intervals describe uncertainty; they do not create or change
  a pass threshold.

## 3. Holdout isolation and one-time authorization

Before any holdout labels or outputs are exposed to the evaluator:

1. Separate development data from the final holdout by parent incident/outage,
   recurring incident family, and any linked service/time block. Document the
   grouping rule and prove there is no entity or derived-window overlap.
2. Have an independent custodian retain the final labels and holdout manifest.
   Freeze and record the dataset manifest hash, label rubric, detector and
   evaluator commit SHAs, preprocessing, comparator, metric definitions,
   exclusions, analysis code, and output schema before unblinding.
3. Obtain independent scientific review of the sampling plan, labels, analysis,
   and uncertainty method; separate privacy/legal and data-owner approval for
   access and use. Reviewers must disclose conflicts and be independent of the
   implementation authors. Preserve reviewer decision and evidence references
   without exposing private data.
4. Obtain a **separate, one-time owner authorization** bound to the exact
   dataset/manifest SHA-256, code SHA, purpose, local execution command, resource
   and cost limits, output location, and retention/deletion date. Approval of
   this protocol or a PR is not approval to access data or execute an evaluation.
   Prior authorization for synthetic seeds is consumed and does not carry over.
5. After all approvals, execute once in the approved isolated environment. Do
   not call paid inference, upload data, access live infrastructure, select a
   favorable subset, or rerun because a result is undesirable. Preserve the
   complete result, including invalid/failure outcomes, and reconcile it to the
   frozen hashes. Any deviation invalidates the affected study and requires a
   newly reviewed registration and authorization before another run.

This PR does none of these actions. It does not authorize a run, change an AI-9
gate, or imply that current human approval for repository work covers private
data use or future evaluation.

## 4. Current source disposition

The official source metadata and repository documentation below were checked
2026-11-13. These are source-inspection findings only; no new dataset files were
downloaded or scored for this protocol. **NOT_EVALUABLE** means unsuitable as
the natural-incident AI-9 holdout under the criteria above, not that a source is
invalid for every research question.

| Source and checked snapshot | Rights/source status | Natural-incident AI-9 disposition |
| --- | --- | --- |
| [Microsoft Cloud Monitoring Dataset](https://github.com/microsoft/cloud-monitoring-dataset/tree/6a07a53c2fac495fb6831811df4c980d6c04bd10), `master` snapshot `6a07a53c2fac495fb6831811df4c980d6c04bd10`; repository archived; MIT declaration | Production-derived time series and expert point-anomaly labels; license applies subject to its terms. | **NOT_EVALUABLE:** point labels do not provide independently adjudicated incident identity, affected-service/root-cause labels, or the complete AI-9 contract. |
| [IBM Cloud Console dataset](https://zenodo.org/records/14062900), DOI `10.5281/zenodo.14062900`, v1.0, published 2024-11-10; CC BY 4.0 | Official record declares the dataset license. Existing assessment inspected only the small label CSV; the telemetry Parquet files were not downloaded. | **NOT_EVALUABLE:** five-minute cadence, global event windows, and no affected-service/root-cause labels; current detector input requires 60-second cadence. |
| [RCAEval](https://huggingface.co/datasets/phamquiluan/RCAEval/tree/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e), snapshot `afeacb11bcc94dadfd1c8f483ee4377b2b8b614e`; MIT declared on dataset card | Existing pinned RE1-OB research slice contains injected testbed failures; prior supplemental baseline work is recorded in the assessment. | **NOT_EVALUABLE:** injected failures are not naturally occurring incidents; prior result is not a Devobs production-detector evaluation. Do not repeat it here. |
| [OpenRCA 2.0 Lite](https://huggingface.co/datasets/anon-ops/ops-lite/tree/581eba39d0bfd2d397eded6cd7cbe3303255521a), snapshot `581eba39d0bfd2d397eded6cd7cbe3303255521a`; Apache-2.0 declared for the dataset card | Underlying testbed components may have separate terms. | **NOT_EVALUABLE:** fault-injected testbed cases, not natural incidents; component rights must be reviewed separately for any other use. |
| [AIOps Challenge 2020](https://github.com/AIOps-Lab-NKU/AIOps-Challenge-2020-Data/tree/05dcea9688794f3787a9b7e4a8931c6e70fa0ec78), snapshot `05dcea9688794f3787a9b7e4a8931c6e70fa0ec78`; README describes non-commercial research/teaching terms | No SPDX license identified in the checked repository snapshot; commercial rights are **UNVERIFIED**. | **NOT_EVALUABLE:** published study describes injected failures; exact archive mapping and cadence also remain **UNVERIFIED**. |
| [AIOpsArena dataset](https://github.com/AIOpsArena/dataset/tree/7c73e77d5a5109d30461417757c1c6ba3c234534), snapshot `7c73e77d5a5109d30461417757c1c6ba3c234534` | No license declaration identified in checked repository; reuse rights **UNVERIFIED**. | **NOT_EVALUABLE:** documented ground truth is for injected faults, not natural incidents. |
| [ChronoGraph](https://github.com/bit-ml/ChronoGraph/tree/51a16b9b29a0ecb1b6f17d672ca1da97de9da99a), repository snapshot `51a16b9b29a0ecb1b6f17d672ca1da97de9da99a`; source paper [arXiv v2](https://arxiv.org/abs/2509.04449v2), checked 2026-11-13 | The repository declares Apache-2.0, but explicit rights for the production telemetry payload are **UNVERIFIED**. Paper describes incident-report-derived event annotations; independent double review/adjudication is not established. | **NOT_EVALUABLE:** the paper reports 30-minute sampling and 17 labeled anomaly segments, not a sample-size justification for AI-9; root-cause labels are not documented, and the 30-minute cadence violates the unchanged 60-second AI-9 input contract. |
| Devobs synthetic fixtures and consumed AI-9 v3 holdout ([frozen results](AI9_V3_FROZEN_HOLDOUT_RESULTS.json)) | Internal synthetic fixtures; the v3 seeds `20270601`–`20270604` have already been consumed once. | **NOT_EVALUABLE:** synthetic/injected evidence cannot establish natural-incident generalization; do not rerun or reuse consumed seeds. |
| Owner-authorized, independently labeled natural incident corpus | No qualifying owner-owned or licensed corpus, data manifest, independent label set, or privacy/retention approval is present in the reviewed repository evidence. | **UNVERIFIED / NOT_EVALUABLE:** no corpus has been identified and approved for this protocol. |

For details on existing RCAEval, IBM, Microsoft, and synthetic work, see the
[external dataset assessment](AI9_EXTERNAL_DATASET_ASSESSMENT.md). This protocol
does not reproduce their findings or claim that a candidate now meets the
admission requirements.

## 5. Evidence references and limits

Research and methodology references checked 2026-11-13:

- NIST, [AI Risk Management Framework 1.0](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf), January 2023; and [AI RMF core: Measure](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/). Use as governance and validity guidance, not as a Devobs acceptance standard.
- NIST/SEMATECH, [exact binomial confidence intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm), accessed 2026-11-13. Small-sample interval methods must be stated; no NIST result certifies this detector.
- Google SRE Workbook, [postmortem analysis](https://sre.google/workbook/postmortem-analysis/) and [postmortem culture](https://sre.google/workbook/postmortem-culture/), accessed 2026-11-13; supports evidence-based timelines and root-cause review, not dataset permission.
- Microsoft, [dataset README at pinned commit](https://github.com/microsoft/cloud-monitoring-dataset/blob/6a07a53c2fac495fb6831811df4c980d6c04bd10/README.md) and [license at the same commit](https://github.com/microsoft/cloud-monitoring-dataset/blob/6a07a53c2fac495fb6831811df4c980d6c04bd10/LICENSE).
- IBM, [Zenodo record 14062900](https://zenodo.org/records/14062900), version and license metadata.
- RCAEval, [pinned Hugging Face dataset snapshot](https://huggingface.co/datasets/phamquiluan/RCAEval/tree/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e), including its dataset card and declared license.
- OpenRCA, [pinned OpenRCA 2.0 Lite snapshot](https://huggingface.co/datasets/anon-ops/ops-lite/tree/581eba39d0bfd2d397eded6cd7cbe3303255521a), including dataset card and declared license.
- AIOps Challenge, [pinned data repository snapshot](https://github.com/AIOps-Lab-NKU/AIOps-Challenge-2020-Data/tree/05dcea9688794f3787a9b7e4a8931c6e70fa0ec78); and [paper describing dataset C](https://arxiv.org/html/2208.03938v1). The archive's exact shape and rights beyond the README terms are **UNVERIFIED**.
- AIOpsArena, [pinned dataset repository snapshot](https://github.com/AIOpsArena/dataset/tree/7c73e77d5a5109d30461417757c1c6ba3c234534). License and any broader reuse rights are **UNVERIFIED**.
- ChronoGraph, [pinned repository README](https://github.com/bit-ml/ChronoGraph/blob/51a16b9b29a0ecb1b6f17d672ca1da97de9da99a/README.md), [pinned repository license](https://github.com/bit-ml/ChronoGraph/blob/51a16b9b29a0ecb1b6f17d672ca1da97de9da99a/LICENSE), and [arXiv paper v2](https://arxiv.org/abs/2509.04449v2). The paper's reported cadence and event count do not satisfy the AI-9 input and evidence requirements; telemetry-payload rights and independent adjudication remain **UNVERIFIED**.
- Existing Devobs contracts and results: [AI-9 v3 independent-evaluation gate](AI9_V3_INDEPENDENT_EVAL_GATE.md), [frozen synthetic results](AI9_V3_FROZEN_HOLDOUT_RESULTS.json), [issue #320](https://github.com/hamedonassar95/Devobs/issues/320), and [issue #224](https://github.com/hamedonassar95/Devobs/issues/224).

Repository state and dataset rights can change. Recheck all official sources,
licenses, immutable versions, and the current AI-9 contract when a specific
corpus is proposed. Do not infer an account's permissions or a dataset owner's
consent from public availability. Current AI-9 remains **BLOCKED**, P01 remains
**NO-GO**, and no evaluation was run as part of this protocol.

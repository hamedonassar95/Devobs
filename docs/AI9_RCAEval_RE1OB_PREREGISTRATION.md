# RCAEval RE1-OB controlled root-cause ranking check — preregistration

**Registration ID:** `ai9-rcaeval-re1ob-shift-baseline-v1`
**Registered:** 2026-11-09 UTC, before any ranking score was computed
**Classification:** supplemental, offline, injected-fault benchmark; **not** the AI-9 release evaluation.
**Repository implementation reviewed:** `67df7dc0060a9aa11f1837f75e6fe278fec5cfd7`.

## Question and limits

This one-time check asks whether a fixed, generic metric-shift baseline can rank the injected root-cause service in RCAEval's RE1 Online Boutique slice. It does not invoke or evaluate Devobs' production detector, establish natural-incident accuracy, or change any release gate. Even a favorable result cannot set AI-9 to PASS or P01 to GO.

The owner authorized downloading the public data and completing the locally feasible work. This registration narrows that authorization to one no-fee, local-only descriptive run on the data snapshot below. No raw files will be uploaded, committed, or sent to an external model or service. No thresholds or production code will change.

## Frozen source and input

- Dataset: [RCAEval on Hugging Face](https://huggingface.co/datasets/phamquiluan/RCAEval), revision `afeacb11bcc94dadfd1c8f483ee4377b2b8b614e`.
- License: the dataset card and README declare MIT. Only the dataset files are used; no baseline code is imported. The publisher's dataset notice, rather than the mixed-license baseline-code tree, governs this data-only use.
- Slice: all 125 `RE1-OB` cases, with `cases.parquet`, `metrics.parquet`, and `inject_time.txt`; 251 files, 31,866,704 bytes. No other suites are included.
- Download verification: each Parquet/LFS file is checked against its published SHA-256, and each text file against its Git blob SHA-1 and byte count. Canonical sorted input-manifest SHA-256: `aa2e61a8cb507fdd8819dd75c6d13f761f2f86a369c07f12378a5faf78bb41c6`.
- Source metadata inspection found one-second samples and 15 metric-schema variants. Exactly 123 of 125 cases contain complete 60-sample pre-injection and post-injection windows; the two cases without both windows remain `NOT EVALUABLE` and will not be silently dropped from coverage reporting.

The publisher describes RE1 as metric-only data from injected failures in microservice testbeds, and identifies each case's injected root service. This is controlled testbed evidence, not naturally occurring production incident data.

## Frozen procedure

1. Consider every indexed RE1-OB case once. Use `inject_time` as published; do not change labels or select cases based on telemetry outcomes.
2. Require exactly 60 one-second samples in each interval: `[inject_time - 60, inject_time)` for baseline and `[inject_time, inject_time + 60)` for the fault window. If either is incomplete, report the case `NOT EVALUABLE`.
3. Use numeric finite columns only. Parse feature names according to the publisher's documented `{service}_{metric}` layout by matching the final metric suffix. Do not use the root-cause label, fault label, or repetition number when computing rankings.
4. For each feature with 60 finite observations in both windows and nonzero baseline median absolute deviation (MAD), compute `abs(median(fault) - median(baseline)) / (1.4826 * MAD(baseline))`. Ignore a feature with zero baseline MAD; do not add an epsilon or tune a floor.
5. A service score is the maximum eligible feature score for that service. Sort descending by score, breaking ties by ascending service name. If no feature is eligible, abstain. This is a deliberately simple, fixed comparator, not Devobs' deployed ranker.
6. After freezing rankings, compare them with `root_cause_service` from the index. Report Top-1 and Top-3, abstention, and coverage overall and by fault/root-service strata. Include abstentions as misses in eligible-case denominators. The two pre-identified cases without complete windows are listed separately.
7. Report descriptive values only. No pass threshold, pooling rule, model selection, tuning, second run, or production promotion is defined by this registration.

## Prohibited conclusions and unchanged gates

- A result is **not** an AI-9 PASS, production validation, natural-incident evidence, or proof of Devobs detector behavior.
- Do not change detector behavior, thresholds, sealed synthetic seeds, the AI-9 gate, P01 controls, workflows, deployment, or services based on this experiment.
- AI-9 remains blocked pending the independently sourced, privacy/provenance-reviewed natural-incident evidence and operational checks required by [the release gate](AI9_V3_INDEPENDENT_EVAL_GATE.md). P01 remains blocked pending verified spend enforcement, identity/OIDC, tenant isolation, network/TLS, backup/restore, and independent approval evidence.

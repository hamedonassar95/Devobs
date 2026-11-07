# IBM Cloud Anomaly Dataset — Research-Only Review

**Review date:** 2026-11-07  
**Repository:** `hamedonassar95/Devobs`  
**Disposition:** RESEARCH_REFERENCE_ONLY — NOT APPROVED FOR AI-9 SCORING OR RELEASE EVIDENCE

## Decision

The Zenodo dataset record may be tracked as an auxiliary research reference for cloud telemetry anomaly-detection work. It must not be treated as evidence that Devobs AI-9 passes, as production validation, or as proof of root-cause diagnosis quality.

This is a documentation-only decision. No dataset files are committed, no evaluation is run, and no application, workflow, threshold, metric, or release gate is changed.

## Verified source metadata

Primary record: https://zenodo.org/records/14062900  
DOI: https://doi.org/10.5281/zenodo.14062900  
Related paper: https://arxiv.org/abs/2411.09047

The record describes IBM Cloud Console telemetry collected over approximately 4.5 months:
- 39,365 entries at 5-minute intervals.
- 117,448 described features/attributes.
- Labeled anomaly windows with sources including Issue Tracker, Instant Messenger, and Test Log.
- Data-center planned/unplanned downtime metadata.

Published file inventory:
| File | Published size | Published MD5 |
|---|---:|---|
| `anomaly_windows.csv` | 1.5 kB | `d87f9add1d127c66dbe6158ae56c2a64` |
| `location_downtime.csv` | 6.1 kB | `64ea8969d1158aca34f54cc5a20d87e7` |
| `demo.ipynb` | 13.4 kB | `3e6974c149ca5ef56fb83cc14ea2e33f` |
| `demo.html` | 296.0 kB | `d5986896bcac642441a744ce7f725805` |
| `pivoted_data_all.parquet` | 2.7 GB | `d2b515002dadd0a339f682f4b53c6ba1` |
| `unpivoted_data.parquet` | 2.7 GB | `e4805ad9a870696771e0453c8763a026` |

Source: Zenodo record, Files and Description sections. These are publisher-declared metadata values; they have not yet been independently verified against downloaded files.

## License and reuse status

**BLOCKED / UNVERIFIED:** The record's Rights section displays the License field without a license value. Zenodo's terms state that users must respect the license conditions attached to each record; open availability alone does not grant reuse rights.

Until the dataset owner or record metadata provides a clear license or written permission:
- Do not redistribute, mirror, commit, or package dataset contents.
- Do not use the data in a commercial product or public demo.
- Restrict this entry to bibliographic/reference tracking and metadata-level research planning.

Zenodo references:
- Record: https://zenodo.org/records/14062900
- Terms: https://about.zenodo.org/terms/
- License guidance: https://support.zenodo.org/help/en-gb/2-content/21-can-i-get-permission-to-use-a-specific-record

## Relevance to Devobs

**INFERRED:** The dataset may be useful for exploring time-series anomaly detection, telemetry features, event-window labeling, and evaluation methodology for cloud-service monitoring.

**NOT ESTABLISHED:** It does not by itself validate:
- AI-9 incident-investigator correctness or root-cause explanations.
- Production behavior, tenant isolation, or authorization.
- Independent holdout performance.
- P01 production readiness or commercial release readiness.

AI-9 remains **FAIL / BLOCKED** and P01 remains **NO-GO / BLOCKED**. This note does not alter either gate.

## Pending verification checklist

1. Obtain a clear dataset license or written reuse permission from the rights holder.
2. When the local file-inspection tool is available, download only the small CSV and notebook files first.
3. Verify each downloaded file against the MD5 published by Zenodo.
4. Inspect schemas, row counts, timestamp coverage, labels, missingness, and notebook references.
5. Record a separate data-quality and relevance assessment.
6. Seek separate explicit approval before downloading either 2.7 GB Parquet file.
7. Seek separate explicit approval before any AI-9 evaluation. The reserved AI-9 holdout remains out of scope.

## Execution record

- Zenodo record metadata reviewed online: **VERIFIED**.
- License for dataset contents: **UNVERIFIED / BLOCKED**.
- Local downloads and checksum verification: **NOT RUN**.
- Dataset schema/content inspection: **NOT RUN**.
- AI-9 evaluation: **NOT RUN**.
- Dataset upload or commit: **NOT DONE**.
- Main branch, deployments, paid services, secrets, and release gates: **UNCHANGED**.


## Related research implementation — static source review

Reviewed read-only at public repository:
https://github.com/msi-ru-cs/icse-seip2025-anomaly-detector-public
Reviewed source revision: `b9240359275cfadf2be3e9098bc872b4ef09017d`

Relevant source files:
- `README.md`
- `Dockerfile`
- `requirements.txt`
- `conf/config.yaml`
- `src/run_experiment__multi_models_GRU_ANN.py`
- `src/preprocessing.py`
- `src/anomaly_likelihood.py`
- `src/nab_scoring.py`

### What the reference implementation does

- Uses HTTP 5XX telemetry features from the pivoted Parquet data.
- Uses ANN or GRU autoencoders, reconstruction error and a likelihood calculation.
- Uses labeled anomaly windows and a window-based NAB-style score.
- The README describes Python 3.11 and pinned TensorFlow/Keras, pandas, NumPy, scikit-learn and Parquet dependencies.

### Static-review findings

1. **The checked-in configuration uses a fixed chronological split:** training from 2024-01-26 through 2024-02-29 and testing from 2024-03-01 through 2024-05-31. This is a documented experiment configuration, not proof of independent validation for Devobs.
2. **The apparent grid search is currently a single configuration:** the active arrays contain one threshold (0.9996), one long window (30), and one short window (2). The code therefore evaluates one parameter combination in this revision, despite the function name.
3. **The configured GRU sequence length is one:** the training and inference paths pass `time_steps=1`. This provides no multi-interval sequence context in that configured path, so it should not be described as demonstrated long-sequence temporal learning.
4. **The model-selection/evaluation path uses the test period's labeled anomaly windows to calculate and report its score.** The inspected code does not establish a separate untouched validation set for choosing or confirming settings. Treat reported test-period scores as experiment-specific, not as an independent estimate of production performance.
5. **The Dockerfile downloads the Parquet dataset during image build and starts the experiment as its container command.** Do not run `docker build` or the container as a lightweight inspection step: the build downloads a multi-gigabyte dataset, installs the ML stack, and the default command starts model training/evaluation.
6. **The repository's Apache-2.0 LICENSE applies to the software repository's code as published there.** It does not grant rights to the separate Zenodo dataset. Dataset rights remain unresolved until the dataset record's own license or written permission is confirmed.

These are static observations from the cited source revision; no code was executed and no model metrics were reproduced.

### Devobs applicability

**Potentially useful research patterns:** telemetry feature extraction, chronological train/test separation, anomaly-window labeling, reconstruction-error signals, and event-timing-aware scoring.

**Not suitable for direct adoption as AI-9 acceptance evidence:** this implementation is a batch anomaly-detection experiment over a specific IBM 5XX telemetry dataset. It does not validate Devobs incident reasoning, root-cause attribution, multi-tenant authorization, security controls, or production operations.

### Updated execution record

- Public reference implementation inspected at a pinned source revision: **VERIFIED — STATIC REVIEW ONLY**.
- Software repository LICENSE observed as Apache-2.0: **VERIFIED FOR THAT CODE REPOSITORY ONLY**.
- Zenodo dataset license: **UNVERIFIED / BLOCKED**.
- Docker build, dataset download, training, or experiment execution: **NOT RUN**.
- Dataset content/schema/checksum inspection: **NOT RUN**.
- AI-9 scoring or holdout: **NOT RUN**.
- Devobs application, workflows, thresholds, metrics, and release gates: **UNCHANGED**.

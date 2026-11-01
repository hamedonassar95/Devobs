# AI-9 External Dataset Assessment — No Run Performed

**Assessment date:** 2026-11-01. **Decision:** candidate-source research only. AI-9 remains **FAIL / BLOCKED**; P01 remains **NO-GO / BLOCKED**. No dataset files were downloaded, no detector or evaluator was run, no thresholds changed, and no production path was touched.

## Candidate sources

| Dataset | Verified source evidence | Fit for Devobs AI-9 | Limits / rights notes |
| --- | --- | --- | --- |
| [Microsoft Cloud Monitoring Dataset](https://github.com/microsoft/cloud-monitoring-dataset) | The Microsoft repository README says the 67 time series come from production Microsoft service/client telemetry and that experts manually labeled anomalous time points. The format is timestamp, metric value, and point label. The repository exposes an [MIT license](https://raw.githubusercontent.com/microsoft/cloud-monitoring-dataset/master/LICENSE). | Small, straightforward candidate for an independent, window-level telemetry check; no external service or paid inference is needed to analyze downloaded public files locally. | Labels are point anomalies, not incident IDs or root-cause labels. It is 67 mostly univariate series, so it does not directly validate Devobs's same-service multimetric confirmation or RCA Top-3. The repository is archived. Confirm data-file notices before any redistribution; the planned use is local evaluation only. |
| [IBM Cloud Console anomaly dataset, Zenodo 14062900](https://zenodo.org/records/14062900) | The Zenodo record describes about 4.5 months of IBM Cloud Console production telemetry, 39,365 five-minute rows and 117,448 features. It lists `anomaly_windows.csv` as ground-truth windows categorized by Issue Tracker, Instant Messenger, and Test Log. The official record identifies [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and exposes two Parquet files of about 2.7 GB each. The [associated paper](https://arxiv.org/abs/2411.09047) says the Issue Tracker covers customer-impacting events and often has root-cause analysis. | Stronger candidate for a separate incident-oriented evaluation because it links real production telemetry with time windows and identifies label sources. Zenodo's license allows reuse with attribution, subject to its terms. | Labels are mixed-source and must be filtered under a pre-registered rule; test-log/IM labels are not automatically production incidents. The large data files and five-minute cadence require a carefully frozen adapter. Mapping features to Devobs services/metrics and RCA labels is not established. |

## Recommendation

Use the IBM dataset as the **first candidate for a separately reported external validation**, subject to the owner's approval of the exact one-time local download and evaluation. Keep Microsoft as a lighter supplementary anomaly-point dataset. Neither source is a substitute for Devobs's production acceptance, and no result may be described as an AI-9 PASS until every existing gate and the gate's provenance requirements are met.

Before scoring anything, prepare and review a separate registration that freezes:

1. Exact Zenodo record/version, attribution, files and cryptographic hashes.
2. Which annotation sources count as positive labels (for example, Issue Tracker only) and how overlapping, planned, test, or ambiguous windows are treated.
3. A deterministic feature/service mapping based only on source documentation, the five-minute evaluation-window semantics, timestamp gaps, missing-data handling, and whether the source can supply all required labels.
4. The unchanged detector, baseline, comparator, and existing gates: window Precision >=80%, Recall >=80%, FPR <=5%, median delay <=2 windows, and RCA Top-3 >=70%. A gate that the dataset cannot support is `NOT EVALUABLE`/invalid for that run; it is not skipped or replaced.
5. One run only, with per-source/per-series results, prevalence, confusion counts, missing detections, delay, and input/output hashes; no pooled result may hide a failed subset. No tuning or threshold changes after scoring.

Schema and provenance inspection must be separated from detector outcomes. Do not use previous AI-9 synthetic seeds, alter the sealed synthetic registration, or commit raw dataset files. After registration, run only in a local environment with no network or paid services. Owner authorization for that exact run is still required by the existing AI-9 gate.

## Gate state

- **VERIFIED:** two public sources with official repository/record metadata, label descriptions, and published reuse licenses have been identified.
- **UNVERIFIED:** exact row-level provenance/quality for selected files, a deterministic mapping to Devobs service/metric contracts, and whether any dataset supports all existing RCA/episode gates.
- **BLOCKED:** the owner has not approved the exact external dataset run; no files have been downloaded and no preregistered external evaluation exists. AI-9 remains **FAIL / BLOCKED**.

## References

- [Microsoft dataset README](https://github.com/microsoft/cloud-monitoring-dataset/blob/master/README.md)
- [Microsoft dataset license](https://raw.githubusercontent.com/microsoft/cloud-monitoring-dataset/master/LICENSE)
- [IBM Zenodo record and license](https://zenodo.org/records/14062900)
- [IBM dataset paper and annotation process](https://arxiv.org/abs/2411.09047)
- [AI-9 v3 independent-evaluation gate](AI9_V3_INDEPENDENT_EVAL_GATE.md)

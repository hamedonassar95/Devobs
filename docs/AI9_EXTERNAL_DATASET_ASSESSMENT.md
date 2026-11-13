# AI-9 External Dataset Assessment — Source Inspection and Supplemental Results

**Assessment date:** 2026-11-09. **Decision:** IBM metadata/labels were inspected; the RCAEval RE1-OB slice was downloaded, verified, preregistered and evaluated once as a supplemental testbed benchmark. No Devobs production detector was run. AI-9 remains **FAIL / BLOCKED**; P01 remains **NO-GO / BLOCKED**. The owner authorized local work without uploading raw data. No raw dataset files were committed, no threshold changed, and no production path was touched.

## Candidate sources

| Dataset | Verified source evidence | Fit for Devobs AI-9 | Limits / rights notes |
| --- | --- | --- | --- |
| [Microsoft Cloud Monitoring Dataset](https://github.com/microsoft/cloud-monitoring-dataset) | The Microsoft repository README says the 67 time series come from production Microsoft service/client telemetry and that experts manually labeled anomalous time points. The format is timestamp, metric value, and point label. The repository exposes an [MIT license](https://raw.githubusercontent.com/microsoft/cloud-monitoring-dataset/master/LICENSE). | Small, straightforward candidate for an independent, window-level telemetry check; no external service or paid inference is needed to analyze downloaded public files locally. | Labels are point anomalies, not incident IDs or root-cause labels. It is 67 mostly univariate series, so it does not directly validate Devobs's same-service multimetric confirmation or RCA Top-3. The repository is archived. Confirm data-file notices before any redistribution; the planned use is local evaluation only. |
| [IBM Cloud Console anomaly dataset, Zenodo 14062900](https://zenodo.org/records/14062900), v1.0 (`10.5281/zenodo.14062900`) | The official record identifies [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), 39,365 five-minute rows, 117,448 telemetry features, and two Parquet files of about 2.7 GB each. `anomaly_windows.csv` contains 25 global event windows. Its official MD5 is `d87f9add1d127c66dbe6158ae56c2a64`; the locally inspected file's SHA-256 is recorded below. | Useful as a candidate for supplementary system-level event-detection research on real production telemetry. | The labels do not name affected services or root causes. Only three labels are Issue Tracker; the other 22 are Instant Messenger or Test Log. The source is five-minute cadence, while Devobs AI-9 v3 requires exactly 60-second spacing and is marked `synthetic_development_only`. The detector cannot be run directly on this source without changing its contract. Therefore this source does not support the complete AI-9 gate, particularly service-level mapping and RCA Top-3. |
| [RCAEval](https://github.com/phamquiluan/RCAEval) / [Hugging Face data](https://huggingface.co/datasets/phamquiluan/RCAEval) | The dataset card/README declare MIT and describe 735 cases across three testbed systems. The RE1-OB slice has 125 root-service-labeled cases, 49–59 metric series per case, and one-second timestamps. | One preregistered research baseline run achieved 99/123 Top-1 and 114/123 Top-3 on eligible cases. This checks a fixed generic post-injection ranker on one controlled slice, not Devobs' production implementation. | These are injected testbed failures, not natural production incidents. The result cannot close AI-9. No baseline code was imported; other RCAEval suites and mixed-license baseline code were not used. See the [registration](AI9_RCAEval_RE1OB_PREREGISTRATION.md) and [results](AI9_RCAEval_RE1OB_RESULTS.md). |
| [OpenRCA 2.0 Lite](https://huggingface.co/datasets/anon-ops/ops-lite) | The dataset card declares Apache-2.0 and describes 455 cases with root-cause services and verified propagation graphs. | Potential supplementary benchmark for service-level RCA ranking and propagation evaluation. | The cases are fault injections in testbeds, not incidents observed in production. The underlying TrainTicket, Hotel Reservation/DeathStarBench, and OpenTelemetry Demo testbeds retain their own licenses. This cannot replace real production evidence for AI-9; no files were downloaded. |
| [AIOps Challenge 2020 dataset](https://github.com/AIOps-Lab-NKU/AIOps-Challenge-2020-Data) | Its README says the failure summary includes time, fault type, and fault location with business/infrastructure metrics and traces. The associated research paper says dataset C uses telemetry from a production ISP system and contains 169 injected failures with ground-truth times and root components. | Potential supplementary controlled validation on production-derived telemetry, with external fault-time and root-component labels. | Failures were injected, not naturally occurring production incidents. The README limits use to non-commercial research/teaching; this is not an unrestricted open-source license and cannot substantiate commercial product readiness. Exact cadence, archive size, and mapping to Devobs services remain unverified; no files were downloaded. Treat as research-only unless rights and scope are clarified. |
| [AIOpsArena dataset](https://github.com/AIOpsArena/dataset) | Its README describes three days of platform data, 60-second metrics, logs/traces, and ground truth for injected faults. | Potential controlled smoke test for the detector's 60-second input contract and fault-localization plumbing. | It is fault-injection/testbed evidence, not production-incident validation. The visible repository file list has no license file, so rights are unverified; no data or code was downloaded. Do not use until an applicable license is supplied. |

## 2026-11-09 source inspection

- **VERIFIED:** Zenodo API metadata identifies record v1.0, DOI `10.5281/zenodo.14062900`, and license `CC BY 4.0`. Only `anomaly_windows.csv` was fetched locally. Its size is 1,465 bytes, official MD5 is `d87f9add1d127c66dbe6158ae56c2a64`, and observed SHA-256 is `7b8a038ef9bb9a443d57191abd3a1fc9669153245f82568f93b9383d4d7f29f5`.
- **VERIFIED:** source codes in the CSV are `1=Issue Tracker` (3 windows), `2=Instant Messenger` (11), and `3=Test Log` (11), as mapped by the [associated paper](https://arxiv.org/html/2411.09047). The inspected labels include one zero-duration window and three overlapping pairs. The CSV contains only event identifier, start/end times, and source code; it has no service identity or root-cause answer.
- **VERIFIED:** the paper describes 5-minute aggregates whose feature names encode datacenter, client/server role, component, method, HTTP status code, endpoint, and statistic. Its demo reports 91.06% missing values in the pivoted dataset. The two telemetry Parquet files were not downloaded, so their row-level contents remain uninspected.
- **VERIFIED:** `scripts/ai_intelligence/ai9_coherent_onset_v3.mjs` rejects non-60-second spacing and classifies the candidate as `synthetic_development_only`. Adapting timestamps, interpolating values, or assigning global incident windows to every service would change the evaluation contract or invent labels; none was done.
- **Decision:** no detector/evaluator run is valid for the full AI-9 gate on this source as currently defined. IBM may still support a separately preregistered, clearly labeled supplementary event-detection study after a compatible cadence/feature protocol is reviewed. That study cannot be reported as an AI-9 PASS and cannot assess RCA Top-3 from this CSV.

## Additional source search — no data downloaded

- **VERIFIED:** the AIOps Challenge 2020 README says its failure summary includes time, fault type, and fault location and links business/infrastructure metrics and traces. The associated paper describes dataset C as telemetry from a production ISP system but explicitly says the 169 failures were injected. Its dataset terms restrict use to non-commercial purposes such as research or teaching. This is a possible research-only controlled evaluation, not natural-incident or unrestricted product-readiness evidence.
- **UNVERIFIED:** the AIOps 2020 archive's exact size, cadence, and correspondence between labels and Devobs service-level AI-9 targets. The primary download host returned “Link does not exist” in browser inspection; the alternate Google Drive link exposed no file metadata. No attempt was made to download it.
- **VERIFIED:** AIOpsArena documents a 60-second cadence and injected-fault ground truth, but its visible repository file listing has no license file. It is testbed evidence, and its usage rights remain unclear; it was not downloaded.
- **VERIFIED:** RCAEval's dataset card and README declare MIT. From the exact snapshot `afeacb11bcc94dadfd1c8f483ee4377b2b8b614e`, 125 RE1-OB cases plus `cases.parquet` were downloaded locally (251 files, 31,866,704 bytes). Every file's size and published SHA-256 LFS or Git blob SHA-1 matched; the canonical manifest SHA-256 is `aa2e61a8cb507fdd8819dd75c6d13f761f2f86a369c07f12378a5faf78bb41c6`. The slice has one-second samples and 15 metric-schema variants. Two cases lack complete preregistered windows.
- **VERIFIED:** After committing the preregistration before scoring, a fixed generic metric-shift baseline produced Top-1 `99/123` (80.49%) and Top-3 `114/123` (92.68%); fault-injected loss cases were weaker (Top-1 `10/24`, Top-3 `17/24`). This baseline uses the published injection time and is not Devobs' production detector. The full method and limitations are in the [registration](AI9_RCAEval_RE1OB_PREREGISTRATION.md) and [results](AI9_RCAEval_RE1OB_RESULTS.md).
- **Decision:** RCAEval adds controlled service-RCA evidence, but no public source reviewed so far supplies naturally occurring production incidents with independently reviewed service/root-cause labels under a compatible Devobs production evaluation contract. Keep AI-9 blocked; do not report injected-fault results as production evidence.

## Recommendation

RCAEval RE1-OB has been evaluated once as a supplemental injected-fault RCA baseline; keep it for research comparison only. Use OpenRCA 2.0 Lite as another independent fault-injection RCA comparison only after its data and testbed terms are reviewed. IBM and Microsoft may support separately registered anomaly-detection studies if their cadence and feature mapping are defensible. Consider AIOps Challenge 2020 only for non-commercial research after confirming exact archive terms and shape; it cannot substantiate commercial readiness. AIOpsArena may support a 60-second controlled smoke test only after its license is clarified. No candidate alone currently supports every unchanged AI-9 gate, and no result may be described as an AI-9 PASS until all evidence and release requirements are met.

Before scoring anything, prepare and review a separate registration that freezes:

1. Exact dataset source and version (for example, a Zenodo DOI/version or repository commit), attribution, applicable license, selected files and cryptographic hashes.
2. Which source annotations count as labels for the chosen task and how overlapping, injected, planned, test, or ambiguous cases are treated.
3. A deterministic telemetry-to-service/metric mapping based only on source documentation, native sampling and any resampling rule, evaluation windows, timestamp gaps, missing-data handling, and whether the source supports each required label.
4. The unchanged detector, baseline, comparator, and existing gates: window Precision >=80%, Recall >=80%, FPR <=5%, median delay <=2 windows, and RCA Top-3 >=70%. A gate that the dataset cannot support is `NOT EVALUABLE`/invalid for that run; it is not skipped or replaced.
5. For any future external evaluation, preregister one run with per-source/per-series results, prevalence, confusion counts, missing detections, delay, and input/output hashes; no pooled result may hide a failed subset. No tuning or threshold changes after scoring.

Schema and provenance inspection must be separated from detector outcomes. Do not use previous AI-9 synthetic seeds, alter the sealed synthetic registration, or commit raw dataset files. Future registered runs must be local, use no paid services, and receive the exact owner authorization required by the AI-9 gate.

## Gate state

- **VERIFIED:** four candidates have publisher/repository license declarations that permit some reuse subject to their terms: Microsoft Cloud Monitoring (MIT), RCAEval code/data (MIT per its README), IBM Cloud Console data (CC BY 4.0), and OpenRCA 2.0 Lite (Apache-2.0 card; underlying testbed licenses remain separate). AIOps Challenge 2020 is research-only under its published terms; AIOpsArena's license is not stated in its visible repository listing.
- **VERIFIED:** the owner authorized local inspection of IBM Zenodo record v1.0 with no raw-data upload. The small label CSV was inspected and hashed; no telemetry Parquet was downloaded and no detector score was computed.
- **VERIFIED:** the owner authorized local RCAEval inspection/evaluation; the preregistration preceded its one-time score. A supplemental generic-baseline result exists for RE1-OB only; Devobs' production detector was not run.
- **UNVERIFIED:** a deterministic feature/service mapping for IBM; exact AIOps 2020 archive shape/size/cadence and rights-holder permission beyond non-commercial research; AIOpsArena reuse rights; production suitability of testbed datasets; and whether a preregistered combination can support every AI-9 gate.
- **BLOCKED:** full AI-9 scoring on IBM is invalid under the current detector cadence and label contract. RCAEval's testbed baseline is not a production-detector or natural-incident evaluation. No complete external evaluation for AI-9 exists; AI-9 remains **FAIL / BLOCKED**.

## Natural-incident preregistration update — 2026-11-13

The [AI-9 Natural-Incident Evaluation preregistration](AI9_REAL_INCIDENT_PREREGISTRATION.md)
sets admission, independent-label, privacy, sampling, holdout, metric, uncertainty,
and one-time authorization requirements for a future natural-incident study. It
is a design protocol only: no qualifying corpus has been identified or approved,
no new data were downloaded or scored, and no AI-9 gate or threshold changed.

Official source metadata and pinned snapshots were rechecked on 2026-11-13 for
Microsoft Cloud Monitoring, IBM Zenodo 14062900, RCAEval, OpenRCA 2.0 Lite,
AIOps Challenge 2020, and AIOpsArena. Existing assessments and results for
RCAEval, IBM, Microsoft, and Devobs synthetic holdouts remain the detailed
record; this update does not repeat or rerun those studies. Each source remains
**NOT_EVALUABLE** for the complete natural-incident AI-9 gate because labels,
cadence, injected-failure status, or usage rights do not meet all admission
requirements. No owner-approved natural-incident manifest or independent label
set is present in the reviewed evidence. Rights or source claims not confirmed
by the pinned publisher documentation remain **UNVERIFIED**. AI-9 remains
**FAIL / BLOCKED**; P01 remains **NO-GO / BLOCKED**.

## References

- [Microsoft dataset README](https://github.com/microsoft/cloud-monitoring-dataset/blob/master/README.md)
- [Microsoft dataset license](https://raw.githubusercontent.com/microsoft/cloud-monitoring-dataset/master/LICENSE)
- [IBM Zenodo record and license](https://zenodo.org/records/14062900)
- [IBM dataset paper and annotation process](https://arxiv.org/abs/2411.09047)
- [RCAEval repository, dataset description and licensing](https://github.com/phamquiluan/RCAEval)
- [RCAEval dataset snapshot](https://huggingface.co/datasets/phamquiluan/RCAEval/tree/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e)
- [RCAEval research paper](https://arxiv.org/abs/2412.17015v5)
- [RCAEval RE1-OB preregistration](AI9_RCAEval_RE1OB_PREREGISTRATION.md) and [results](AI9_RCAEval_RE1OB_RESULTS.md)
- [AIOps Challenge 2020 published dataset and use terms](https://github.com/AIOps-Lab-NKU/AIOps-Challenge-2020-Data)
- [Research paper describing AIOps Challenge dataset C and its injected failures](https://arxiv.org/html/2208.03938v1)
- [AIOpsArena dataset and sampling/ground-truth description](https://github.com/AIOpsArena/dataset)
- [OpenRCA 2.0 Lite dataset card and license](https://huggingface.co/datasets/anon-ops/ops-lite)
- [AI-9 v3 independent-evaluation gate](AI9_V3_INDEPENDENT_EVAL_GATE.md)

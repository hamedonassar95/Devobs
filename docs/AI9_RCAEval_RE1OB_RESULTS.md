# RCAEval RE1-OB controlled root-cause ranking check — results

**Registration:** [frozen protocol](AI9_RCAEval_RE1OB_PREREGISTRATION.md), registered at commit `9a03b3a9b22a1d24ae1e43c3810450c01b4f9089` before this score was computed.
**Classification:** one-time, supplemental, offline, injected-fault benchmark. **This does not evaluate Devobs' production detector and does not open AI-9 or P01.**

## Verified run

- Source revision: [RCAEval Hugging Face snapshot](https://huggingface.co/datasets/phamquiluan/RCAEval/tree/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e), declared MIT by its dataset card/README.
- Scope: all 125 RE1 Online Boutique cases, 251 data/index files, 31,866,704 bytes. No baseline source code or other suite was downloaded.
- Integrity: all 251 files were rechecked against their published LFS SHA-256 or Git blob SHA-1 and byte size. Canonical input-manifest SHA-256: `aa2e61a8cb507fdd8819dd75c6d13f761f2f86a369c07f12378a5faf78bb41c6`.
- Runtime: Python 3.12 with PyArrow 26.0.1 installed in a temporary directory; no repository dependency was added. Computation read local files only and called no hosted model or service.
- Coverage: 123 cases had complete 60-sample baseline and post-injection windows. Two cases had no complete windows and were reported `NOT EVALUABLE` as preregistered. The eligible set had no abstentions.

## Descriptive result

| Measure | Result |
| --- | ---: |
| Evaluated cases | 123 / 125 |
| Root-service Top-1 | 99 / 123 (80.49%) |
| Root-service Top-3 | 114 / 123 (92.68%) |
| Abstentions among eligible cases | 0 / 123 |
| Cases without the preregistered windows | 2 / 125 |

The fixed score is a maximum absolute robust metric shift per service, evaluated during the first minute **after the known injection timestamp**. It is a post-injection localization baseline, not an incident detector, not a latency measurement, and not the algorithm used by Devobs in production.

Top-1 / Top-3 counts by injected fault:

| Fault | Eligible cases | Top-1 | Top-3 |
| --- | ---: | ---: | ---: |
| CPU | 24 | 19 (79.17%) | 22 (91.67%) |
| Delay | 25 | 23 (92.00%) | 25 (100.00%) |
| Disk | 25 | 24 (96.00%) | 25 (100.00%) |
| Loss | 24 | 10 (41.67%) | 17 (70.83%) |
| Memory | 25 | 23 (92.00%) | 25 (100.00%) |

Loss-injection cases were notably weaker. The aggregate score must not hide this gap; the run defines no pass threshold and no model or parameter was selected from the result.

## Interpretation and gate state

RCAEval confirms that one simple, fixed post-injection metric-shift baseline can rank injected root services on this testbed slice. It does **not** show that Devobs' current detector attains these scores: that detector was not invoked. All 123 scored cases are fault-injected testbed data, with an injection timestamp available to the evaluator. The result therefore cannot establish detection before an incident, natural production incident accuracy, false-positive burden, operational drift, tenant isolation, or safety in live use.

- **AI-9 remains `FAIL / BLOCKED`.** The experiment is useful supplementary RCA research, but it is not independent evidence from naturally occurring, provenance-reviewed production incidents and does not validate the production detector.
- **P01 remains `NO-GO / BLOCKED`.** No provider-enforced spend cap, identity, tenant-isolation, network, backup/restore, or staging evidence was created or verified here.
- No detector, threshold, workflow, secret, service, deployment, production setting, or gate status changed. Raw dataset files remain outside the repository.

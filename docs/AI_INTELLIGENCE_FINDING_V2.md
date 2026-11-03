# AI Intelligence — incident finding wire contract v2 (historical)

Superseded by [incident finding wire contract v3](AI_INTELLIGENCE_FINDING_V3.md), which adds bounded declared dependency paths for impacted services.

**Scope:** local, offline serialization of deterministic incident-correlation results. This is a P03 building block only; it is not an API endpoint, a trusted signature, or a readiness-gate change.

## Record contract

`IncidentFinding.to_record()` emits an exact JSON-compatible schema-version-2 object. `IncidentFinding.from_record(...)` rejects unknown or missing fields, unsupported versions, invalid scope, malformed or duplicate evidence, inconsistent ranking evidence, invalid status/category combinations, inconsistent topology or memory provenance, and a mismatched finding digest. Version 1 records are not accepted by this strict parser.

The v2 record adds `ranking_interpretation` and `ranked_service_evidence`. The interpretation is always `fixed_heuristic_not_causal`. Each top-three service includes its stable rank, integer score, and the triggered signal reason codes, points, and exact evidence digest for each contribution. The fixed rules are:

- `failed_checks_positive`: +3 when failed checks are greater than zero.
- `error_rate_threshold_met`: +2 when error rate is at least 5 percent.
- `capacity_threshold_met`: +1 when capacity is at least 85 percent.

Services are sorted by descending score, then service ID. The record omits raw metric values. The strict parser checks that every signal maps to the fixed metric and point rule, references a digest in the finding, contributes to the recorded score, and agrees with the ordered service list and top category.

The record also carries tenant and project scope, status, category, impacted services, evidence digests, runbook IDs, source SHA, model/calibration flags, optional topology snapshot digest and capture time, and bounded memory provenance. A finding with `INSUFFICIENT_EVIDENCE` has no ranked or impacted services or ranking evidence. A finding with `PENDING_HUMAN_APPROVAL` remains a proposal for human review.

The `finding_digest` is SHA-256 over the canonical JSON payload without the digest field (sorted keys, compact separators, UTF-8, non-finite numbers rejected). It detects accidental or unsynchronized edits only; anyone can recompute it. It does not authenticate a producer, preserve a signature, authorize an action, or prove that supplied evidence is true.

When the record contains memory provenance, it includes the incident-record digest, source SHA and timestamp, plus the curator approval ID, approver ID and approval digest. Snapshot-based correlation includes only records with a verified, currently active approval. This wire contract does not re-verify the original Ed25519 signature or key trust map; downstream callers must preserve the verified result and must not treat this record digest as a signature.

## Limits

- No network endpoint, database, durable storage, model inference, or production action is added.
- No real incidents, customer data, or external data are included.
- The ranking is a fixed heuristic, not causal proof, calibrated confidence, or measured detection quality.
- A source digest binds the explanation to the supplied evidence identifier, not to the truth of the underlying telemetry.
- Consumers must re-check tenant authorization and human-approval requirements; parsing a record is not authorization.
- This contract does not change AI quality evaluation or operational-readiness status.

Focused offline checks:

```bash
python3 -m unittest discover -s tests -p 'test_intelligence_correlation.py' -v
python3 -m unittest discover -s tests -p 'test_intelligence_finding_contract.py' -v
```

# AI Intelligence — offline topology snapshot contract v1

**Scope:** local, deterministic input contract for dependency-topology reasoning. This is P03 preparation only. It does not satisfy P02's live-signal entry condition, P03's release gate, or any AI-9/P01 gate.

## Interface

`scripts/devobs_intelligence/context.py` exposes `ServiceTopologySnapshot`. A snapshot binds:

- exact tenant and project identifiers;
- a 40- or 64-character lowercase source commit SHA;
- an ISO-8601 timezone-aware capture time normalized to UTC;
- a bounded, validated service list and dependency-edge list; and
- a canonical SHA-256 content digest over those fields.

`affected_by(tenant, project, service, now=..., max_age_seconds=900, depth=3)` requires the caller to provide the expected scope and an aware current time. It rejects scope mismatch, a future or stale snapshot, invalid freshness limits, and unknown services with fixed error codes. Graph size/depth limits and cycle-safe traversal are inherited from `ServiceTopology`.

`scripts/devobs_intelligence/correlation.py` accepts either the existing in-memory `ServiceTopology` or a `ServiceTopologySnapshot`. For a snapshot, `correlate(...)` rebuilds and checks the canonical digest, validates tenant/project scope and freshness, and requires the snapshot source SHA to equal the telemetry source SHA. It uses the snapshot's bounded `affected_by` traversal and returns `topology_snapshot_digest` plus `topology_captured_at` with the finding, including an `INSUFFICIENT_EVIDENCE` result. Existing `ServiceTopology` callers remain supported and have no snapshot provenance fields.

`ServiceTopologySnapshot.to_record()` emits a detached, JSON-compatible schema-v1 record. `from_record(...)` accepts only the exact v1 fields, reconstructs the bounded graph, and verifies the supplied digest before returning a snapshot. Unknown schema versions, extra or missing fields, malformed graph arrays, and content/digest mismatches fail closed with fixed error codes. This defines a local interchange contract only; it does not add a file loader, network endpoint, persistence, or trusted producer.

## What the contract proves

- In-memory snapshot fields have the accepted shape and bounds.
- Equivalent service/edge ordering produces the same canonical digest.
- A change to the source SHA or capture time changes the digest.
- Queries cannot use the snapshot under another tenant/project scope or after its freshness window.
- The offline incident correlator cannot mix telemetry with a stale, cross-scope, altered, or differently sourced topology snapshot.
- Correlation output carries the snapshot digest and capture time so a reviewer can identify the exact topology context used.
- A JSON encode/decode round trip preserves the canonical snapshot, while unsupported versions and altered records are rejected.
- No network, storage, model, or cloud operation is performed.

## Signed-envelope verification (offline T22 preparation)

`scripts/devobs_intelligence/topology_attestation.py` verifies an exact schema-v1 Ed25519 envelope. The signed payload uses a domain separator and binds the signer key ID to the full canonical snapshot record. The caller supplies the trusted raw public-key map, expected tenant/project, expected source SHA, current time and freshness limit. Verification returns the validated snapshot plus a digest of the signed envelope; it never returns the signature or key material.

This checks a signature against the caller's trust input. It does not enroll or protect keys, prove that a signer observed the real source commit, ingest live metadata, prevent all replays, or persist an audit trail. Only generated test keys and synthetic topology are used here. T22 remains open until an authorized source and protected key-enrollment process are approved and exercised.

## Limits and next gate

The digest detects accidental content changes; it is **not** a signature, identity assertion, collector attestation, or proof that the topology came from the named commit. The caller still supplies tenant, project, source SHA, capture time, and graph. The schema-v1 record and correlator integration remain local contracts; they do not authenticate a producer, ingest live topology, or prove operational quality. The separate [topology drift report](AI_INTELLIGENCE_TOPOLOGY_DRIFT_V1.md) compares two offline snapshots but does not establish whether declared edges are true or complete. Further work still needs an approved source, reviewed provenance, poisoned/stale-memory controls, retention/privacy decisions, and hosted evidence. No readiness decision changes from this implementation.

Focused contract checks:

```bash
python3 -m unittest discover -s tests -p 'test_intelligence_topology_snapshot.py' -v
python3 -m unittest discover -s tests -p 'test_intelligence_context_graph.py' -v
```

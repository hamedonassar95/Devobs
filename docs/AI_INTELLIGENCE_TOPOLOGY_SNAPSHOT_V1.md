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

## What the contract proves

- In-memory snapshot fields have the accepted shape and bounds.
- Equivalent service/edge ordering produces the same canonical digest.
- A change to the source SHA or capture time changes the digest.
- Queries cannot use the snapshot under another tenant/project scope or after its freshness window.
- No network, storage, model, or cloud operation is performed.

## Limits and next gate

The digest detects accidental content changes; it is **not** a signature, identity assertion, collector attestation, or proof that the topology came from the named commit. The caller still supplies tenant, project, source SHA, capture time, and graph. P03 still needs an authenticated and owner-approved source, reviewed provenance, poisoned/stale-memory controls, retention/privacy decisions, integration with downstream context, and its required tests. P02 remains blocked on P01 live staging and privacy approval. No readiness gate changes from this implementation.

Focused contract checks:

```bash
python3 -m unittest discover -s tests -p 'test_intelligence_topology_snapshot.py' -v
python3 -m unittest discover -s tests -p 'test_intelligence_context_graph.py' -v
```

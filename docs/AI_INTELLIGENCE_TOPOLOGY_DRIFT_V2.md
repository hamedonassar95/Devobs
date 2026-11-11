# AI Intelligence — offline topology drift report v2

**Scope:** deterministic, local comparison of two bounded `ServiceTopologySnapshot` records. This is a P03 building block only. It does not ingest topology, authenticate a live producer, or alter incident rankings or execution policy.

## Behavior

`scripts/devobs_intelligence/topology_drift.py` exposes `compare_topology_snapshots(before, after)`. It reconstructs both inputs through the strict snapshot v1 parser, requires identical tenant and project scope, and rejects a non-increasing capture time.

The schema-v2 report includes sorted added/removed services and dependency edges, introduced/resolved strongly connected cycle groups, newly isolated/reconnected services, and a digest over the full canonical record. It also lists every edge in the after snapshot under `unverifiable_edges`, with status `UNVERIFIABLE` and reason `per_edge_source_metadata_absent`. The report does this because snapshot v1 has no edge-level source evidence. A valid signed envelope can authenticate the exact bytes and signer assertion, but it does not prove that a declared dependency is true or complete.

Cycle discovery uses strongly connected components. Existing snapshot limits cap input at 100 services and 500 edges. Isolated means a service has no incoming or outgoing edge.

## Verified behavior

- Snapshot scope, schema and content digests are revalidated before comparison.
- Cross-tenant/project comparisons and equal or reversed capture times fail closed.
- Reordered equivalent snapshots produce the same report and digest.
- Added/removed edges and services, cycle changes and isolated-service changes are explicit.
- All current edges without edge-level source evidence are explicitly marked unverifiable.
- An empty current edge set produces an empty unverifiable-edge list.
- Output records and nested edge arrays are detached from the report object.
- The local audit chain records the report digest, not service names or graph contents.

## Limits

This report describes declared graph differences only. It cannot prove that an edge is real or complete, establish source-to-runtime correspondence, or infer causality. A cycle, isolated service, or unverifiable edge is a review signal, not proof of an incident. No collector, persistent topology store, hosted endpoint, model inference, or automated action is added. T23 remains partial; no readiness gate is closed by this offline report.

Focused checks:

```bash
python3 -m unittest discover -s tests -p 'test_intelligence_topology_drift.py' -v
python3 -m unittest discover -s tests -p 'test_intelligence_audit_store.py' -v
```

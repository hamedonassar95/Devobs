# AI Intelligence — offline topology drift report v1

**Scope:** deterministic, local comparison of two `ServiceTopologySnapshot` records. This is an offline P03 building block. It does not ingest topology, authenticate a producer, or alter incident rankings or execution policy.

## Behavior

`scripts/devobs_intelligence/topology_drift.py` exposes `compare_topology_snapshots(before, after)`. It reconstructs both inputs through the strict snapshot v1 parser before use, requires identical tenant and project scope, and rejects a non-increasing capture time. It then returns a detached schema-v1 report with sorted added/removed services and dependency edges, introduced/resolved strongly connected cycle groups, and newly isolated/reconnected services. The report digest binds the complete canonical output.

Cycle discovery uses strongly connected components and is bounded by the existing topology limits of 100 services and 500 edges. Isolated means a service has no incoming or outgoing edge. A dependency edge is still only a declared relationship; the current contract has no per-edge source or verification metadata.

The synthetic CLI demo compares a fixed prior graph with its current synthetic graph, includes the report in its JSON output, and records only its digest in the existing local audit chain. The demo makes no network call and changes no production state.

## Verified behavior

- Snapshot scope, schema and content digests are revalidated before comparison.
- Cross-tenant/project comparisons and equal or reversed capture times fail closed.
- Reordered equivalent snapshots produce the same report and digest.
- Added/removed edges and services, cycle changes and isolated-service changes are explicit.
- The output record is detached; editing it does not alter a later comparison.

## Limits

The report describes declared graph differences only. It cannot prove that an edge is real or complete, identify a trusted producer, establish source-to-runtime correspondence, or infer causality. A cycle or isolated service is a review signal, not proof of an incident. The audit chain records only the digest; it is local and can be rewritten by a privileged database writer. No collector, persistent topology store, hosted endpoint, model inference, or automated action is added.

Focused checks:

```bash
python3 -m unittest discover -s tests -p 'test_intelligence_topology_drift.py' -v
python3 -m unittest discover -s tests -p 'test_intelligence_demo.py' -v
```

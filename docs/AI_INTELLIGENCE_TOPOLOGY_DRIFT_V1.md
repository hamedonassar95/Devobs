# AI Intelligence — offline topology drift report v1 (historical)

This report contract is superseded by [topology drift report v2](AI_INTELLIGENCE_TOPOLOGY_DRIFT_V2.md), which explicitly marks edges lacking edge-level source evidence as unverifiable.

The v1 report compared two bounded, same-tenant/project ServiceTopologySnapshot objects and included declared added/removed services and edges, cycle changes, isolated/reconnected services, source SHAs, capture times, and a digest over its record. It did not include per-edge source or verification metadata. A v1 report therefore could not distinguish a declared dependency from a source-verified dependency.

The current offline test suite remains:

```bash
python3 -m unittest discover -s tests -p 'test_intelligence_topology_drift.py' -v
```

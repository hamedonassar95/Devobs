# AI Intelligence — incident finding wire contract v3

**Scope:** local, offline serialization of deterministic incident-correlation results. This is a P03 building block only; it is not an API endpoint, a trusted signature, or a readiness-gate change.

## Record contract

`IncidentFinding.to_record()` emits an exact JSON-compatible schema-version-3 object. `IncidentFinding.from_record(...)` rejects unknown or missing fields, unsupported versions, invalid scope, malformed evidence, inconsistent ranking evidence, malformed impact paths, invalid status/category combinations, inconsistent topology or memory provenance, and a mismatched finding digest. Version 1 and 2 records are not accepted by this strict parser.

Version 3 retains the v2 deterministic top-three score explanation and adds `impact_path_interpretation` and `impact_paths`. The interpretation is always `declared_edges_not_causal`. For each impacted service, `path_services` lists a shortest declared dependency route from that service to the top-ranked service. The root has a one-node path. Routes are bounded to three edges and ordered to match `impacted_services`; ties are resolved lexicographically.

The parser checks each path's service ID, starting service, root endpoint, length, uniqueness, and alignment with the impacted-service list. It also checks the fixed ranking reason codes and points, per-signal evidence digests, score totals, and top category. The finding digest binds all of these fields as content, but anyone can recompute it.

`validate_impact_paths_against_snapshot(record, snapshot, now_utc=...)` additionally revalidates the supplied snapshot, checks its digest, tenant, project, source SHA, capture time and freshness against the finding, and recomputes the impacted-service set and deterministic shortest paths. It rejects paths that are valid JSON but do not match the exact snapshot. This is a consistency check, not source authentication: callers must verify a snapshot's signature against their trusted key before relying on its declared edges.

`validate_attested_impact_finding(...)` composes the existing Ed25519 envelope verifier with that path check. Callers must supply expected tenant, project and source SHA from their independently trusted request context, plus a protected keyring; the returned `AttestedImpactFinding` exposes the verified key ID and attestation digest alongside the finding. This does not enroll keys or establish that a signer observed a real source. Tests use generated keys and synthetic snapshots only.

## Limits

- The path records declared topology only. The schema does not carry edge-level verification, and parsing cannot prove that any edge is real, complete, or causal. A snapshot digest binds a supplied snapshot; it does not authenticate the collector or edge truth.
- Ranking remains a fixed heuristic, not calibrated confidence or measured detection quality; per-signal digests identify supplied evidence but do not prove its truth.
- No network endpoint, database, durable storage, model inference, live topology, real incident data, or production action is added.
- The trusted-key source and its lifecycle remain the caller's responsibility; a valid signature proves only that the supplied key signed the envelope.
- Consumers must re-check tenant authorization and human-approval requirements; parsing a record is not authorization.
- This contract does not change AI-9, P01, Codex runtime, or other operational-readiness decisions.

Focused offline checks:

```bash
python3 -m unittest discover -s tests -p 'test_intelligence_correlation.py' -v
python3 -m unittest discover -s tests -p 'test_intelligence_finding_contract.py' -v
```

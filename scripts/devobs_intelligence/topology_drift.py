"""Deterministic, offline comparison of two bounded topology snapshots."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from .context import ContextError, ServiceTopologySnapshot
from .topology_attestation import (
    RotatingTopologyKeyring,
    VerifiedTopologyAttestation,
    verify_topology_attestation,
)


def _validated_snapshot(value: object) -> ServiceTopologySnapshot:
    if type(value) is not ServiceTopologySnapshot:
        raise ContextError("invalid_topology_snapshot")
    try:
        return ServiceTopologySnapshot.from_record(value.to_record())
    except (AttributeError, TypeError, ValueError, ContextError):
        raise ContextError("invalid_topology_snapshot") from None


def _cycle_components(snapshot: ServiceTopologySnapshot) -> tuple[tuple[str, ...], ...]:
    """Return strongly connected service groups, excluding acyclic singletons."""
    adjacency = {service: [] for service in snapshot.services}
    for dependent, dependency in snapshot.edges:
        adjacency[dependent].append(dependency)
    for neighbors in adjacency.values():
        neighbors.sort()

    index = 0
    indexes: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    cycles: list[tuple[str, ...]] = []

    def visit(service: str) -> None:
        nonlocal index
        indexes[service] = index
        lowlinks[service] = index
        index += 1
        stack.append(service)
        on_stack.add(service)
        for neighbor in adjacency[service]:
            if neighbor not in indexes:
                visit(neighbor)
                lowlinks[service] = min(lowlinks[service], lowlinks[neighbor])
            elif neighbor in on_stack:
                lowlinks[service] = min(lowlinks[service], indexes[neighbor])
        if lowlinks[service] != indexes[service]:
            return
        component = []
        while True:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == service:
                break
        if len(component) > 1:
            cycles.append(tuple(sorted(component)))

    for service in snapshot.services:
        if service not in indexes:
            visit(service)
    return tuple(sorted(cycles))


def _isolated_services(snapshot: ServiceTopologySnapshot) -> frozenset[str]:
    connected = {service for edge in snapshot.edges for service in edge}
    return frozenset(set(snapshot.services) - connected)


@dataclass(frozen=True)
class TopologyDriftReport:
    """Detached, versioned summary of changes between same-scope snapshots."""

    tenant: str
    project: str
    before_snapshot_digest: str
    after_snapshot_digest: str
    before_source_sha: str
    after_source_sha: str
    before_captured_at: str
    after_captured_at: str
    added_services: tuple[str, ...]
    removed_services: tuple[str, ...]
    added_edges: tuple[tuple[str, str], ...]
    removed_edges: tuple[tuple[str, str], ...]
    introduced_cycles: tuple[tuple[str, ...], ...]
    resolved_cycles: tuple[tuple[str, ...], ...]
    newly_isolated_services: tuple[str, ...]
    reconnected_services: tuple[str, ...]
    unverifiable_edges: tuple[tuple[str, str], ...]

    def to_record(self) -> dict:
        payload = {
            "schema_version": 2,
            "tenant": self.tenant,
            "project": self.project,
            "before_snapshot_digest": self.before_snapshot_digest,
            "after_snapshot_digest": self.after_snapshot_digest,
            "before_source_sha": self.before_source_sha,
            "after_source_sha": self.after_source_sha,
            "before_captured_at": self.before_captured_at,
            "after_captured_at": self.after_captured_at,
            "added_services": list(self.added_services),
            "removed_services": list(self.removed_services),
            "added_edges": [list(edge) for edge in self.added_edges],
            "removed_edges": [list(edge) for edge in self.removed_edges],
            "introduced_cycles": [list(group) for group in self.introduced_cycles],
            "resolved_cycles": [list(group) for group in self.resolved_cycles],
            "newly_isolated_services": list(self.newly_isolated_services),
            "reconnected_services": list(self.reconnected_services),
            "unverifiable_edges": [
                {
                    "edge": list(edge),
                    "status": "UNVERIFIABLE",
                    "reason": "per_edge_source_metadata_absent",
                }
                for edge in self.unverifiable_edges
            ],
        }
        digest = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        ).encode("ascii")).hexdigest()
        return {**payload, "report_digest": digest}


@dataclass(frozen=True)
class AttestedTopologyDriftReport:
    """A drift report linked to two independently verified envelopes.

    The envelope digests identify the signed inputs but do not replace those
    inputs or make the report independently verifiable. Retain both original
    envelopes and the applicable trust configuration when audit replay is
    required.
    """

    drift: TopologyDriftReport
    before_key_id: str
    after_key_id: str
    before_attestation_digest: str
    after_attestation_digest: str

    def to_record(self) -> dict:
        payload = {
            "schema_version": 1,
            "before_attestation": {
                "key_id": self.before_key_id,
                "digest": self.before_attestation_digest,
            },
            "after_attestation": {
                "key_id": self.after_key_id,
                "digest": self.after_attestation_digest,
            },
            "drift": self.drift.to_record(),
        }
        digest = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False,
        ).encode("ascii")).hexdigest()
        return {**payload, "attested_report_digest": digest}


def compare_topology_snapshots(
    before: ServiceTopologySnapshot,
    after: ServiceTopologySnapshot,
) -> TopologyDriftReport:
    """Compare validated snapshots without treating a digest as source authentication."""
    before = _validated_snapshot(before)
    after = _validated_snapshot(after)
    if (before.tenant, before.project) != (after.tenant, after.project):
        raise ContextError("topology_scope_mismatch")
    before_time = datetime.fromisoformat(before.captured_at.replace("Z", "+00:00"))
    after_time = datetime.fromisoformat(after.captured_at.replace("Z", "+00:00"))
    if after_time <= before_time:
        raise ContextError("invalid_topology_order")

    old_services, new_services = set(before.services), set(after.services)
    old_edges, new_edges = set(before.edges), set(after.edges)
    old_cycles, new_cycles = set(_cycle_components(before)), set(_cycle_components(after))
    old_isolated, new_isolated = _isolated_services(before), _isolated_services(after)
    return TopologyDriftReport(
        tenant=after.tenant,
        project=after.project,
        before_snapshot_digest=before.snapshot_digest,
        after_snapshot_digest=after.snapshot_digest,
        before_source_sha=before.source_sha,
        after_source_sha=after.source_sha,
        before_captured_at=before.captured_at,
        after_captured_at=after.captured_at,
        added_services=tuple(sorted(new_services - old_services)),
        removed_services=tuple(sorted(old_services - new_services)),
        added_edges=tuple(sorted(new_edges - old_edges)),
        removed_edges=tuple(sorted(old_edges - new_edges)),
        introduced_cycles=tuple(sorted(new_cycles - old_cycles)),
        resolved_cycles=tuple(sorted(old_cycles - new_cycles)),
        newly_isolated_services=tuple(sorted(new_isolated - old_isolated)),
        reconnected_services=tuple(sorted(
            (old_isolated & new_services) - new_isolated)),
        unverifiable_edges=tuple(sorted(new_edges)),
    )


def _verified_attestation(
    envelope: object,
    keyring: dict[tuple[str, str, str], bytes],
    *,
    tenant: str,
    project: str,
    source_sha: str,
    now: datetime,
    max_age_seconds: int,
) -> VerifiedTopologyAttestation:
    return verify_topology_attestation(
        envelope, keyring,
        expected_tenant=tenant,
        expected_project=project,
        expected_source_sha=source_sha,
        now=now,
        max_age_seconds=max_age_seconds,
    )


def compare_attested_topology_snapshots(
    before_attestation: object,
    after_attestation: object,
    trusted_public_keys: dict[tuple[str, str, str], bytes]
    | RotatingTopologyKeyring,
    *,
    expected_tenant: str,
    expected_project: str,
    expected_before_source_sha: str,
    expected_after_source_sha: str,
    now: datetime,
    max_age_seconds: int = 900,
) -> AttestedTopologyDriftReport:
    """Verify two signed snapshots under one trust view, then compare them.

    Both snapshots must independently match the requested scope, expected
    source SHA, and freshness window. Verification is completed before any
    drift values are computed. This authenticates the envelopes against the
    caller's configured trust keys; it does not establish that a signer
    observed a complete or truthful dependency graph.
    """
    try:
        if isinstance(trusted_public_keys, RotatingTopologyKeyring):
            keyring = trusted_public_keys.snapshot()
        elif type(trusted_public_keys) is dict:
            keyring = dict(trusted_public_keys)
        else:
            keyring = trusted_public_keys
    except (RuntimeError, TypeError, ValueError):
        raise ContextError("invalid_topology_keyring") from None

    before = _verified_attestation(
        before_attestation, keyring,
        tenant=expected_tenant,
        project=expected_project,
        source_sha=expected_before_source_sha,
        now=now,
        max_age_seconds=max_age_seconds,
    )
    after = _verified_attestation(
        after_attestation, keyring,
        tenant=expected_tenant,
        project=expected_project,
        source_sha=expected_after_source_sha,
        now=now,
        max_age_seconds=max_age_seconds,
    )
    drift = compare_topology_snapshots(before.snapshot, after.snapshot)
    return AttestedTopologyDriftReport(
        drift=drift,
        before_key_id=before.key_id,
        after_key_id=after.key_id,
        before_attestation_digest=before.attestation_digest,
        after_attestation_digest=after.attestation_digest,
    )

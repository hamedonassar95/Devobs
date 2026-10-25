"""OFFLINE-ONLY tenant access boundary: contracts exist; behavior not implemented."""

from dataclasses import dataclass


class AccessDenied(Exception):
    """Fixed, non-sensitive authorization failure."""


@dataclass(frozen=True)
class Membership:
    tenant_id: str
    actor_id: str
    role: str
    project_ids: tuple[str, ...]


@dataclass(frozen=True)
class ProjectSnapshot:
    tenant_id: str
    project_id: str
    source_sha: str
    ci_state: str


class OfflineTenantGate:
    def __init__(self, identity_resolver, memberships, snapshots):
        raise NotImplementedError("offline tenant boundary pending")

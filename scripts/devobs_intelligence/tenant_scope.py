"""Offline tenant/project authorization gate. NOT a live OIDC or web API verifier.

The identity resolver must be trusted, independently authenticated middleware.
This local contract rejects untrusted input and must never be published directly
as a bearer-token-authentication service. No AI recommendation grants rights.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Sequence

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_ROLES = frozenset({"viewer", "operator", "owner"})
_STATES = frozenset({
    "success", "failed", "pending", "running", "stale", "missing",
    "skipped", "canceled", "manual", "scheduled",
})


class AccessDenied(ValueError):
    """Uniform error: do not expose tenant or resource existence."""


def _valid_id(value: object) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _deny() -> None:
    raise AccessDenied("access_denied")


@dataclass(frozen=True)
class Membership:
    tenant_id: str
    actor_id: str
    role: str
    project_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (not _valid_id(self.tenant_id) or not _valid_id(self.actor_id)
                or type(self.role) is not str or self.role not in _ROLES
                or type(self.project_ids) is not tuple
                or not self.project_ids or len(self.project_ids) > 100
                or not all(_valid_id(project) for project in self.project_ids)
                or len(set(self.project_ids)) != len(self.project_ids)):
            raise ValueError("invalid_membership")


@dataclass(frozen=True)
class ProjectSnapshot:
    tenant_id: str
    project_id: str
    source_sha: str
    ci_state: str

    def __post_init__(self) -> None:
        if (not _valid_id(self.tenant_id) or not _valid_id(self.project_id)
                or type(self.source_sha) is not str
                or _SHA.fullmatch(self.source_sha) is None
                or type(self.ci_state) is not str or self.ci_state not in _STATES):
            raise ValueError("invalid_snapshot")


class OfflineTenantGate:
    """Authorize read-only responses using server-side membership and verified identity.

    The supplied resolver is an injected trusted boundary. Real signature,
    issuer/audience, expiry, replay and session checks MUST be completed by
    external identity middleware, which is deliberately not included here.
    """

    def __init__(
        self,
        identity_resolver: Callable[[str], str | None],
        memberships: Sequence[Membership],
        snapshots: Sequence[ProjectSnapshot],
    ) -> None:
        if not callable(identity_resolver):
            raise ValueError("invalid_identity_boundary")
        if type(memberships) not in (list, tuple) or type(snapshots) not in (list, tuple):
            raise ValueError("invalid_configuration")
        if len(memberships) > 1000 or len(snapshots) > 5000:
            raise ValueError("invalid_configuration")
        member_map = {}
        for membership in memberships:
            if type(membership) is not Membership:
                raise ValueError("invalid_configuration")
            key = (membership.tenant_id, membership.actor_id)
            if key in member_map:
                raise ValueError("duplicate_membership")
            member_map[key] = membership
        project_map = {}
        for snapshot in snapshots:
            if type(snapshot) is not ProjectSnapshot:
                raise ValueError("invalid_configuration")
            key = (snapshot.tenant_id, snapshot.project_id)
            if key in project_map:
                raise ValueError("duplicate_project")
            project_map[key] = snapshot
        self._identity_resolver = identity_resolver
        self._members = member_map
        self._projects = project_map

    def _authorize(self, token: str, tenant_id: str, project_id: str,
                   *, must_propose: bool = False) -> ProjectSnapshot:
        if (type(token) is not str or not 1 <= len(token) <= 4096
                or not _valid_id(tenant_id) or not _valid_id(project_id)):
            _deny()
        try:
            actor_id = self._identity_resolver(token)
        except Exception:
            _deny()
        if not _valid_id(actor_id):
            _deny()
        membership = self._members.get((tenant_id, actor_id))
        snapshot = self._projects.get((tenant_id, project_id))
        if (membership is None or snapshot is None
                or project_id not in membership.project_ids
                or (must_propose and membership.role not in {"operator", "owner"})):
            _deny()
        return snapshot

    def read_status(self, token: str, tenant_id: str, project_id: str,
                    **unexpected: object) -> dict[str, str]:
        if unexpected:
            _deny()
        snapshot = self._authorize(token, tenant_id, project_id)
        return {"ci_state": snapshot.ci_state, "source_sha": snapshot.source_sha}

    def propose_change(self, token: str, tenant_id: str, project_id: str,
                       **unexpected: object) -> dict[str, str]:
        if unexpected:
            _deny()
        snapshot = self._authorize(token, tenant_id, project_id, must_propose=True)
        return {"decision": "PROPOSE_ONLY", "source_sha": snapshot.source_sha}

    def execute(self, *_args: object, **_kwargs: object) -> None:
        # Until signed, actor+action+SHA-bound one-time human approvals exist,
        # the offline control plane has NO authority for mutations.
        _deny()

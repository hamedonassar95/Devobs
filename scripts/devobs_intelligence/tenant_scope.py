"""OFFLINE-ONLY tenant access boundary; the authenticated resolver is not implemented."""

class AccessDenied(Exception):
    """Fixed, non-sensitive authorization failure."""


class OfflineTenantGate:
    def __init__(self, identity_resolver, memberships, snapshots):
        raise NotImplementedError("offline tenant boundary pending")

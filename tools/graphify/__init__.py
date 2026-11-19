"""Local, read-only repository intelligence built on the Graphify CLI.

This package wraps the offline open-source Graphify CLI and adds Devobs-owned
adapters. The adapters are explicitly *not* Graphify features; see
``docs/architecture/graphify-integration.md``.
"""

from .repository_intelligence import (
    PINNED_GRAPHIFY_VERSION,
    PINNED_WHEEL_SHA256,
    POLICY_ID,
    GraphifyRunner,
    RepositoryIntelligenceError,
    build_report,
    cross_repo_view,
    inspect_repository,
    read_graph,
    validate_graph,
)

__all__ = [
    "PINNED_GRAPHIFY_VERSION",
    "PINNED_WHEEL_SHA256",
    "POLICY_ID",
    "GraphifyRunner",
    "RepositoryIntelligenceError",
    "build_report",
    "cross_repo_view",
    "inspect_repository",
    "read_graph",
    "validate_graph",
]

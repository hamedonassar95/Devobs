"""Shared constants, validation and small helpers for local graph tooling."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import pathlib
import re
# Required for read-only, no-shell git subprocesses with fixed argv.
import subprocess  # nosec B404
import sys
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

POLICY_ID = "devobs-repository-intelligence-v1"
PINNED_GRAPHIFY_VERSION = "0.9.113"
PINNED_WHEEL_SHA256 = "62f8483e536c9200f93665f9c61df6489436ab087432e0a0a738bd88096e0491"
MAX_GRAPH_BYTES = 512 * 1024 * 1024
MAX_ADAPTER_FILES = 10_000
MAX_WORKFLOW_BYTES = 512 * 1024
MAX_OUTPUT_CHARS = 8_000
ALLOWED_CONFIDENCE = frozenset({"EXTRACTED", "INFERRED", "AMBIGUOUS"})
PROVIDER_KEY_VARS = (
    "ANTHROPIC_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "KIMI_API_KEY",
    "MOONSHOT_API_KEY",
    "OPENAI_API_KEY",
)
DEFAULT_EXCLUDES = (
    ".env",
    ".env.*",
    "**/.env",
    "**/.env.*",
    "**/secrets/**",
    "**/credentials/**",
    "**/*credentials*.json",
    "**/service-account*.json",
    "**/terraform.tfvars*",
    "**/*.tfstate",
    "**/*.tfstate.*",
    "**/*.tfplan",
    "**/*.pem",
    "**/*.key",
    "**/*.p12",
    "**/*.pfx",
    "**/*.log",
    "**/credentials",
    "**/.aws/**",
    "**/.ssh/**",
    "**/id_rsa*",
    "**/id_ed25519*",
    "**/.npmrc",
    "**/.netrc",
    "**/.pypirc",
    "**/.git-credentials",
    "**/node_modules/**",
    "**/dist/**",
    "**/build/**",
    "**/.cache/**",
    "**/coverage/**",
    "**/.worktrees/**",
    "**/.venv/**",
    "**/venv/**",
    "**/graphify-out/**",
)
_EXCLUDED_PARTS = frozenset(
    {
        ".git",
        ".env",
        ".aws",
        ".ssh",
        "secrets",
        "credentials",
        "node_modules",
        "dist",
        "build",
        ".cache",
        "coverage",
        ".worktrees",
        ".venv",
        "venv",
        "__pycache__",
        "graphify-out",
        "site-packages",
    }
)
_EXCLUDED_NAME_PATTERNS = (
    ".env*",
    "credentials",
    "id_rsa*",
    "id_ed25519*",
    ".npmrc",
    ".netrc",
    ".pypirc",
    ".git-credentials",
    "*credentials*.json",
    "service-account*.json",
    "terraform.tfvars*",
    "*.tfstate",
    "*.tfstate.*",
    "*.tfplan",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.log",
)
_ABS_PATH_RE = re.compile(r"(?:[A-Za-z]:\\|/)[^\s\"'<>|]+")
_VERSION_RE = re.compile(r"^graphify\s+(\S+)\s*$")
_TAG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_MD_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_JOB_RE = re.compile(r"^  ([A-Za-z0-9_.-]+):\s*$")
_NEEDS_RE = re.compile(r"^\s+needs:\s*(.*)$")
_USES_RE = re.compile(r"^\s+(?:-\s+)?uses:\s*(.+)$")


class RepositoryIntelligenceError(Exception):
    """Policy, validation or I/O failure that must stop the run."""


class GraphSchemaError(RepositoryIntelligenceError):
    """A graph document does not satisfy the expected node-link schema."""


class GraphifyRunnerError(RepositoryIntelligenceError):
    """A Graphify CLI invocation failed or returned an unexpected result."""


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()


def is_within(path: pathlib.Path, parent: pathlib.Path) -> bool:
    """Return True when ``path`` is ``parent`` or lives underneath it."""
    try:
        path.resolve().relative_to(parent.resolve())
    except (OSError, ValueError):
        return False
    return True


def is_excluded(path: pathlib.Path, root: pathlib.Path) -> bool:
    """Local adapter exclusion check for secrets, builds and sensitive dirs."""
    try:
        parts = path.resolve().relative_to(root.resolve()).parts
    except (OSError, ValueError):
        return True
    if not parts or any(part in _EXCLUDED_PARTS for part in parts[:-1]):
        return True
    name = parts[-1]
    return any(fnmatch.fnmatch(name, pattern) for pattern in _EXCLUDED_NAME_PATTERNS)


def sanitize_output(text: str, replacements: Iterable[pathlib.Path | str] = ()) -> str:
    """Bound and de-path a CLI response before it is placed in a report."""
    value = text or ""
    for item in replacements:
        value = value.replace(str(item), "<path>")
    value = _ABS_PATH_RE.sub("<path>", value)
    return value[:MAX_OUTPUT_CHARS]


def sanitize_json(value: object) -> object:
    """Recursively bound and de-path JSON-shaped data before reporting it."""
    if isinstance(value, str):
        return sanitize_output(value)
    if isinstance(value, list):
        return [sanitize_json(item) for item in value[:200]]
    if isinstance(value, dict):
        return {
            str(key)[:200]: sanitize_json(item)
            for key, item in list(value.items())[:200]
        }
    return value


def run_git(repo: pathlib.Path, *args: str) -> str:
    """Run a read-only git command; never contacts a remote."""
    # Read-only git command: fixed argv, no shell, no remote operations.
    result = subprocess.run(  # nosec B603, B607
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        detail = hash_text(result.stderr or "")
        raise RepositoryIntelligenceError(
            f"git_{args[0]}_failed exit={result.returncode} stderr_sha256={detail[:16]}"
        )
    return result.stdout


@dataclass(frozen=True)
class GraphStats:
    node_count: int
    edge_count: int
    edge_key: str
    relation_counts: dict[str, int]
    confidence_counts: dict[str, int]
    relation_confidence_counts: dict[str, dict[str, int]]
    source_file_count: int
    orphan_node_ids: tuple[str, ...]
    dangling_edge_count: int
    cycle_back_edges: int
    cycle_samples: tuple[tuple[str, ...], ...]

    def as_dict(self) -> dict:
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "edge_key": self.edge_key,
            "relation_counts": dict(sorted(self.relation_counts.items())),
            "confidence_counts": dict(sorted(self.confidence_counts.items())),
            "relation_confidence_counts": {
                relation: dict(sorted(counts.items()))
                for relation, counts in sorted(self.relation_confidence_counts.items())
            },
            "source_file_count": self.source_file_count,
            "orphan_node_count": len(self.orphan_node_ids),
            "orphan_node_ids": list(self.orphan_node_ids[:25]),
            "dangling_edge_count": self.dangling_edge_count,
            "cycle_back_edges": self.cycle_back_edges,
            "cycle_samples": [list(sample) for sample in self.cycle_samples[:10]],
        }


def _cycle_scan(node_ids: Sequence[str], adjacency: dict[str, list[str]]) -> tuple[int, list[tuple[str, ...]]]:
    """Iterative DFS returning back-edge count and bounded cycle samples."""
    state = {node_id: 0 for node_id in node_ids}
    samples: list[tuple[str, ...]] = []
    back_edges = 0
    for start in node_ids:
        if state[start]:
            continue
        path: list[str] = [start]
        stack: list[tuple[str, object]] = [(start, iter(adjacency.get(start, ())))]
        state[start] = 1
        while stack:
            node_id, iterator = stack[-1]
            try:
                nxt = next(iterator)  # type: ignore[arg-type]
            except StopIteration:
                state[node_id] = 2
                stack.pop()
                path.pop()
                continue
            if nxt not in state:
                continue
            if state[nxt] == 1:
                back_edges += 1
                if len(samples) < 10 and nxt in path:
                    samples.append(tuple(path[path.index(nxt) :] + [nxt]))
            elif state[nxt] == 0:
                state[nxt] = 1
                path.append(nxt)
                stack.append((nxt, iter(adjacency.get(nxt, ()))))
    return back_edges, samples


def validate_graph(document: object) -> GraphStats:
    """Fail closed unless the document is a usable node-link graph."""
    if not isinstance(document, dict):
        raise GraphSchemaError("graph_root_must_be_object")
    nodes = document.get("nodes")
    if not isinstance(nodes, list):
        raise GraphSchemaError("graph_nodes_must_be_array")
    edge_key = "edges" if isinstance(document.get("edges"), list) else "links"
    edges = document.get(edge_key)
    if not isinstance(edges, list):
        raise GraphSchemaError("graph_edges_or_links_must_be_array")

    node_ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise GraphSchemaError("graph_node_must_be_object")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            raise GraphSchemaError("graph_node_id_must_be_nonempty_string")
        if node_id in node_ids:
            raise GraphSchemaError("graph_duplicate_node_id")
        node_ids.add(node_id)
        for key in ("label", "source_file", "source_location"):
            value = node.get(key)
            # Graphify 0.9.113 emits source_location=null for some file nodes.
            if value is not None and not isinstance(value, str):
                raise GraphSchemaError(f"graph_node_{key}_must_be_string")

    relation_counts: dict[str, int] = {}
    confidence_counts: dict[str, int] = {}
    relation_confidence: dict[str, dict[str, int]] = {}
    degrees: dict[str, int] = {node_id: 0 for node_id in node_ids}
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    dangling = 0
    for edge in edges:
        if not isinstance(edge, dict):
            raise GraphSchemaError("graph_edge_must_be_object")
        source = edge.get("source")
        target = edge.get("target")
        relation = edge.get("relation")
        confidence = edge.get("confidence")
        if not isinstance(source, str) or not isinstance(target, str):
            raise GraphSchemaError("graph_edge_endpoints_must_be_strings")
        if source not in node_ids or target not in node_ids:
            dangling += 1
            continue
        if not isinstance(relation, str) or not relation:
            raise GraphSchemaError("graph_edge_relation_must_be_nonempty_string")
        if not isinstance(confidence, str) or confidence not in ALLOWED_CONFIDENCE:
            raise GraphSchemaError("graph_edge_confidence_not_supported")
        relation_counts[relation] = relation_counts.get(relation, 0) + 1
        confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1
        relation_confidence.setdefault(relation, {})[confidence] = (
            relation_confidence.setdefault(relation, {}).get(confidence, 0) + 1
        )
        degrees[source] += 1
        degrees[target] += 1
        adjacency[source].append(target)

    if dangling:
        raise GraphSchemaError(f"graph_has_{dangling}_dangling_edges")
    ordered_ids = sorted(node_ids)
    back_edges, cycle_samples = _cycle_scan(ordered_ids, adjacency)
    source_files = {
        node.get("source_file")
        for node in nodes
        if isinstance(node, dict) and isinstance(node.get("source_file"), str)
    }
    return GraphStats(
        node_count=len(node_ids),
        edge_count=len(edges),
        edge_key=edge_key,
        relation_counts=relation_counts,
        confidence_counts=confidence_counts,
        relation_confidence_counts=relation_confidence,
        source_file_count=len(source_files),
        orphan_node_ids=tuple(node_id for node_id in ordered_ids if degrees[node_id] == 0),
        dangling_edge_count=dangling,
        cycle_back_edges=back_edges,
        cycle_samples=tuple(cycle_samples),
    )


def read_graph(path: pathlib.Path) -> tuple[dict, GraphStats, str, str]:
    """Read and validate a graph file; return document, stats, edge key, sha."""
    path = path.resolve()
    if not path.is_file():
        raise RepositoryIntelligenceError("graph_file_not_found")
    size = path.stat().st_size
    if size == 0 or size > MAX_GRAPH_BYTES:
        raise RepositoryIntelligenceError("graph_file_size_out_of_range")
    raw = path.read_bytes()
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GraphSchemaError(f"graph_json_invalid {type(exc).__name__}") from exc
    stats = validate_graph(document)
    return document, stats, stats.edge_key, hashlib.sha256(raw).hexdigest()


def snapshot_source(source: pathlib.Path) -> dict:
    """Fingerprint source state without reading file contents."""
    source = source.resolve()
    git_dir = source / ".git"
    if git_dir.exists():
        head = run_git(source, "rev-parse", "HEAD").strip()
        status = run_git(source, "status", "--porcelain", "--untracked-files=all")
        lines = [line for line in status.splitlines() if line.strip()]
        return {
            "kind": "git",
            "head": head,
            "dirty": bool(lines),
            "status_line_count": len(lines),
            "digest": hash_text("\n".join(lines)),
        }
    entries: list[str] = []
    for path in sorted(source.rglob("*")):
        if not path.is_file() or is_excluded(path, source):
            continue
        stat = path.stat()
        entries.append(f"{path.relative_to(source).as_posix()}:{stat.st_size}:{stat.st_mtime_ns}")
    return {
        "kind": "directory",
        "file_count": len(entries),
        "digest": hash_text("\n".join(entries)),
    }



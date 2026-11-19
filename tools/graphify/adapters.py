"""Devobs-owned adapters; none of these are native Graphify features."""

from __future__ import annotations

import json
import pathlib
import re
from collections.abc import Sequence

from .common import (
    MAX_ADAPTER_FILES,
    MAX_WORKFLOW_BYTES,
    RepositoryIntelligenceError,
    _JOB_RE,
    _MD_LINK_RE,
    _NEEDS_RE,
    _TAG_RE,
    _USES_RE,
    _cycle_scan,
    is_excluded,
    is_within,
    read_graph,
    run_git,
)

def _tracked_files(source: pathlib.Path) -> list[str]:
    """Return repository-relative paths from git, or a bounded directory walk."""
    if (source / ".git").exists():
        output = run_git(source, "ls-files")
        paths = [line.strip() for line in output.splitlines() if line.strip()]
    else:
        paths = [
            path.relative_to(source).as_posix()
            for path in source.rglob("*")
            if path.is_file()
        ]
    accepted: list[str] = []
    for rel in paths:
        candidate = (source / rel).resolve()
        if is_excluded(candidate, source):
            continue
        accepted.append(rel.replace("\\", "/"))
        if len(accepted) >= MAX_ADAPTER_FILES:
            break
    return sorted(set(accepted))


def tree_adapter(source: pathlib.Path) -> dict:
    source = source.resolve()
    files = _tracked_files(source)
    categories: dict[str, int] = {}
    for rel in files:
        suffix = pathlib.PurePosixPath(rel).suffix.lower()
        if suffix in {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs", ".java", ".c", ".h", ".cpp", ".cs", ".rb", ".php", ".sh"}:
            category = "code"
        elif suffix in {".md", ".rst", ".txt"}:
            category = "docs"
        elif rel.startswith(".github/workflows/"):
            category = "workflow"
        elif suffix in {".yml", ".yaml", ".json", ".toml", ".ini"}:
            category = "config"
        elif suffix in {".tf", ".tfvars", ".hcl"}:
            category = "infra"
        else:
            category = "other"
        categories[category] = categories.get(category, 0) + 1
    return {
        "adapter": "devobs_tree",
        "native_graphify_feature": False,
        "file_count": len(files),
        "categories": dict(sorted(categories.items())),
        "sample_paths": files[:100],
    }


def workflow_adapter(source: pathlib.Path) -> dict:
    """Best-effort extraction of job IDs and `needs` edges from workflow YAML.

    This is intentionally narrower than a YAML parser: it reads top-level job
    keys and their direct ``needs``/``uses`` lines. A workflow file without a
    recognizable ``jobs:`` block fails closed.
    """
    source = source.resolve()
    workflows = [
        rel
        for rel in _tracked_files(source)
        if rel.startswith(".github/workflows/") and rel.endswith((".yml", ".yaml"))
    ]
    if not workflows:
        return {
            "adapter": "devobs_workflow",
            "native_graphify_feature": False,
            "status": "no_workflows",
            "workflow_count": 0,
            "jobs": [],
            "edges": [],
        }
    jobs: set[str] = set()
    edges: set[tuple[str, str]] = set()
    uses: set[str] = set()
    for rel in workflows[:100]:
        path = source / rel
        if path.stat().st_size > MAX_WORKFLOW_BYTES:
            raise RepositoryIntelligenceError("workflow_file_too_large")
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if not any(line.strip() == "jobs:" for line in lines):
            raise RepositoryIntelligenceError(f"workflow_jobs_block_missing {rel}")
        current: str | None = None
        index = 0
        while index < len(lines):
            line = lines[index]
            if line.strip() == "jobs:":
                current = None
                index += 1
                continue
            match = _JOB_RE.match(line)
            if match:
                current = match.group(1)
                jobs.add(current)
                index += 1
                continue
            if current is None:
                index += 1
                continue
            needs_match = _NEEDS_RE.match(line)
            if needs_match:
                raw = needs_match.group(1).strip()
                if raw.startswith("[") and raw.endswith("]"):
                    values = [item.strip().strip("'\"") for item in raw[1:-1].split(",")]
                elif raw:
                    values = [raw.strip("'\"")]
                else:
                    values = []
                    base_indent = len(line) - len(line.lstrip())
                    cursor = index + 1
                    while cursor < len(lines):
                        nxt = lines[cursor]
                        if not nxt.strip():
                            cursor += 1
                            continue
                        indent = len(nxt) - len(nxt.lstrip())
                        item = nxt.strip()
                        if indent <= base_indent or not item.startswith("- "):
                            break
                        values.append(item[2:].strip().strip("'\""))
                        cursor += 1
                for value in values:
                    if value:
                        edges.add((value, current))
            uses_match = _USES_RE.match(line)
            if uses_match:
                uses.add(uses_match.group(1).strip().strip("'\""))
            index += 1
    ordered_jobs = sorted(jobs)
    ordered_edges = sorted(edges)
    adjacency = {job: [] for job in ordered_jobs}
    for source_job, target_job in ordered_edges:
        adjacency.setdefault(source_job, []).append(target_job)
    back_edges, cycles = _cycle_scan(sorted(adjacency), adjacency)
    return {
        "adapter": "devobs_workflow",
        "native_graphify_feature": False,
        "status": "ok",
        "workflow_count": len(workflows[:100]),
        "jobs": ordered_jobs,
        "edges": [{"from": a, "to": b} for a, b in ordered_edges],
        "uses": sorted(uses)[:100],
        "cycle_back_edges": back_edges,
        "cycle_samples": [list(sample) for sample in cycles[:10]],
        "limitations": ["top-level job keys only", "needs expressions are literal strings"],
    }


def branch_adapter(source: pathlib.Path) -> dict:
    source = source.resolve()
    if not (source / ".git").exists():
        return {
            "adapter": "devobs_branch",
            "native_graphify_feature": False,
            "status": "not_a_git_repository",
        }
    branches = [line.strip() for line in run_git(source, "branch", "--format=%(refname:short)").splitlines() if line.strip()]
    changed = [line.strip() for line in run_git(source, "diff", "--name-only", "HEAD").splitlines() if line.strip()]
    worktrees = run_git(source, "worktree", "list", "--porcelain")
    return {
        "adapter": "devobs_branch",
        "native_graphify_feature": False,
        "status": "ok",
        "head": run_git(source, "rev-parse", "HEAD").strip(),
        "branch": run_git(source, "rev-parse", "--abbrev-ref", "HEAD").strip(),
        "local_branches": branches[:100],
        "local_branch_count": len(branches),
        "worktree_count": len([line for line in worktrees.splitlines() if line.startswith("worktree ")]),
        "dirty": bool(run_git(source, "status", "--porcelain", "--untracked-files=all").strip()),
        "changed_files": changed[:100],
        "changed_file_count": len(changed),
        "network_calls": 0,
    }


def docs_adapter(source: pathlib.Path) -> dict:
    source = source.resolve()
    tracked = set(_tracked_files(source))
    docs = [rel for rel in sorted(tracked) if rel.lower().endswith((".md", ".rst"))]
    inbound: dict[str, int] = {}
    broken: list[dict[str, str]] = []
    for rel in docs[:MAX_ADAPTER_FILES]:
        path = source / rel
        if path.stat().st_size > MAX_WORKFLOW_BYTES:
            raise RepositoryIntelligenceError("document_too_large")
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in _MD_LINK_RE.finditer(text):
            target = match.group(1).split("#", 1)[0].strip()
            if not target or "://" in target or target.startswith(("#", "mailto:", "data:")):
                continue
            resolved = (path.parent / target).resolve()
            if not is_within(resolved, source):
                continue
            try:
                local_rel = resolved.relative_to(source).as_posix()
            except ValueError:
                continue
            if local_rel in tracked:
                inbound[local_rel] = inbound.get(local_rel, 0) + 1
            elif len(broken) < 100:
                broken.append({"file": rel, "target": target})
    return {
        "adapter": "devobs_docs_links",
        "native_graphify_feature": False,
        "document_count": len(docs),
        "inbound_link_count": sum(inbound.values()),
        "orphan_documents": [rel for rel in docs if inbound.get(rel, 0) == 0][:100],
        "broken_local_links": broken,
    }


def dependency_adapter(graph_path: pathlib.Path | None, source: pathlib.Path) -> dict:
    source = source.resolve()
    result: dict = {
        "adapter": "devobs_dependency",
        "native_graphify_feature": False,
        "status": "graph_not_requested",
    }
    if graph_path is None:
        return result
    _document, stats, _edge_key, _digest = read_graph(graph_path)
    tracked = set(_tracked_files(source))
    source_files: set[str] = set()
    document, _stats, _key, _digest = read_graph(graph_path)
    for node in document.get("nodes", []):
        if isinstance(node, dict) and isinstance(node.get("source_file"), str):
            source_files.add(node["source_file"].replace("\\", "/"))
    unmapped = sorted(source_file for source_file in source_files if source_file not in tracked)
    return {
        "adapter": "devobs_dependency",
        "native_graphify_feature": False,
        "status": "ok",
        "graph_source_file_count": stats.source_file_count,
        "tracked_file_count": len(tracked),
        "source_files_not_in_tracked_tree": unmapped[:100],
        "relation_counts": dict(sorted(stats.relation_counts.items())),
        "confidence_counts": dict(sorted(stats.confidence_counts.items())),
        "ambiguous_edge_count": stats.confidence_counts.get("AMBIGUOUS", 0),
        "cycle_back_edges": stats.cycle_back_edges,
    }


def inspect_repository(source: pathlib.Path, graph_path: pathlib.Path | None = None) -> dict:
    source = source.resolve()
    return {
        "tree": tree_adapter(source),
        "workflows": workflow_adapter(source),
        "branches": branch_adapter(source),
        "docs": docs_adapter(source),
        "dependencies": dependency_adapter(graph_path, source),
    }


def cross_repo_view(config_path: pathlib.Path) -> dict:
    """Build a bounded, locally tagged adapter view from explicit graph paths."""
    config_path = config_path.resolve()
    if not config_path.is_file():
        raise RepositoryIntelligenceError("cross_repo_config_not_found")
    if config_path.stat().st_size > 1024 * 1024:
        raise RepositoryIntelligenceError("cross_repo_config_too_large")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RepositoryIntelligenceError("cross_repo_config_invalid_json") from exc
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise RepositoryIntelligenceError("cross_repo_config_schema_version")
    repositories = config.get("repositories")
    if not isinstance(repositories, list) or not 1 <= len(repositories) <= 20:
        raise RepositoryIntelligenceError("cross_repo_config_repositories_range")
    entries: list[dict] = []
    seen_tags: set[str] = set()
    view_nodes: list[dict] = []
    view_edges: list[dict] = []
    for item in repositories:
        if not isinstance(item, dict):
            raise RepositoryIntelligenceError("cross_repo_entry_must_be_object")
        tag = item.get("tag")
        source_value = item.get("source")
        graph_value = item.get("graph")
        if not isinstance(tag, str) or not _TAG_RE.match(tag) or tag in seen_tags:
            raise RepositoryIntelligenceError("cross_repo_invalid_or_duplicate_tag")
        seen_tags.add(tag)
        if not isinstance(source_value, str) or not isinstance(graph_value, str):
            raise RepositoryIntelligenceError("cross_repo_paths_must_be_strings")
        source = pathlib.Path(source_value).resolve()
        graph = pathlib.Path(graph_value).resolve()
        if not source.is_dir() or not graph.is_file():
            raise RepositoryIntelligenceError("cross_repo_path_not_found")
        if is_within(graph, source):
            raise RepositoryIntelligenceError("cross_repo_graph_inside_source")
        document, stats, _edge_key, digest = read_graph(graph)
        entries.append(
            {
                "tag": tag,
                "source": str(source),
                "graph": str(graph),
                "graph_sha256": digest,
                "stats": stats.as_dict(),
            }
        )
        for node in document.get("nodes", []):
            if len(view_nodes) >= 100 or not isinstance(node, dict):
                break
            node_id = node.get("id")
            if isinstance(node_id, str):
                view_nodes.append(
                    {
                        "id": f"{tag}::{node_id}",
                        "repo_tag": tag,
                        "local_id": node_id,
                        "label": node.get("label", ""),
                        "source_file": node.get("source_file", ""),
                    }
                )
        edge_key = "edges" if isinstance(document.get("edges"), list) else "links"
        for edge in document.get(edge_key, []):
            if len(view_edges) >= 100 or not isinstance(edge, dict):
                break
            src, dst = edge.get("source"), edge.get("target")
            if isinstance(src, str) and isinstance(dst, str):
                view_edges.append(
                    {
                        "source": f"{tag}::{src}",
                        "target": f"{tag}::{dst}",
                        "relation": edge.get("relation", ""),
                        "confidence": edge.get("confidence", ""),
                        "repo_tag": tag,
                    }
                )
    return {
        "adapter": "devobs_cross_repo",
        "native_graphify_feature": False,
        "repositories": entries,
        "bounded_view": {"nodes": view_nodes, "edges": view_edges},
        "limits": [
            "explicit local paths only",
            "no clone, no network, no global Graphify state",
            "bounded sample; use native merge-graphs for a full file",
        ],
    }



"""Central orchestration of independent, offline per-repository Graphify indexes.

One pinned Graphify CLI installation is reused for every repository. Each
repository gets its own external index directory; failures are isolated and
reports contain logical identifiers only (no absolute local paths).
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from .common import (
    DEFAULT_EXCLUDES,
    PINNED_GRAPHIFY_VERSION,
    PINNED_WHEEL_SHA256,
    POLICY_ID,
    RepositoryIntelligenceError,
    _TAG_RE,
    hash_text,
    is_excluded,
    is_within,
    read_graph,
    sanitize_json,
    sanitize_output,
)
from .runner import GraphifyRunner

MAX_MANIFEST_BYTES = 1024 * 1024
MAX_REPOSITORIES = 25
MAX_SEARCH_TERMS = 3
MAX_EXTRA_EXCLUDES = 25
INDEXABLE_SUFFIXES = frozenset(
    {
        ".c", ".cpp", ".cs", ".css", ".go", ".gradle", ".h", ".java", ".js",
        ".jsx", ".kt", ".kts", ".mjs", ".php", ".prisma", ".py", ".rb", ".rs",
        ".sh", ".sql", ".swift", ".ts", ".tsx", ".vue",
    }
)


@dataclass(frozen=True)
class RepoSpec:
    tag: str
    github: str
    directory: str
    source_root_key: str
    enabled: bool
    reason: str
    extra_excludes: tuple[str, ...]
    search_terms: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "tag": self.tag,
            "github": self.github,
            "directory": self.directory,
            "source_root_key": self.source_root_key,
            "enabled": self.enabled,
            "reason": self.reason,
            "extra_exclude_count": len(self.extra_excludes),
            "search_terms": list(self.search_terms),
        }


def load_manifest(path: pathlib.Path) -> tuple[dict, tuple[RepoSpec, ...]]:
    """Load and strictly validate the authorized repository manifest."""
    path = path.resolve()
    if not path.is_file():
        raise RepositoryIntelligenceError("manifest_not_found")
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise RepositoryIntelligenceError("manifest_too_large")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RepositoryIntelligenceError("manifest_invalid_json") from exc
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise RepositoryIntelligenceError("manifest_schema_version")
    if document.get("policy") != POLICY_ID:
        raise RepositoryIntelligenceError("manifest_policy_mismatch")
    repositories = document.get("repositories")
    if not isinstance(repositories, list) or not 1 <= len(repositories) <= MAX_REPOSITORIES:
        raise RepositoryIntelligenceError("manifest_repositories_range")

    specs: list[RepoSpec] = []
    seen: set[str] = set()
    for item in repositories:
        if not isinstance(item, dict):
            raise RepositoryIntelligenceError("manifest_entry_must_be_object")
        tag = item.get("tag")
        if not isinstance(tag, str) or not _TAG_RE.match(tag) or tag in seen:
            raise RepositoryIntelligenceError("manifest_invalid_or_duplicate_tag")
        seen.add(tag)
        github = item.get("github")
        directory = item.get("directory")
        source_root_key = item.get("source_root", "default")
        if not isinstance(github, str) or not github or github.count("/") != 1:
            raise RepositoryIntelligenceError("manifest_invalid_github")
        if (
            not isinstance(directory, str)
            or not directory
            or directory in {".", ".."}
            or "/" in directory
            or "\\" in directory
        ):
            raise RepositoryIntelligenceError("manifest_invalid_directory")
        if not isinstance(source_root_key, str) or not _TAG_RE.match(source_root_key):
            raise RepositoryIntelligenceError("manifest_invalid_source_root")
        enabled = item.get("enabled")
        if not isinstance(enabled, bool):
            raise RepositoryIntelligenceError("manifest_enabled_must_be_boolean")
        reason = item.get("reason", "")
        if not isinstance(reason, str):
            raise RepositoryIntelligenceError("manifest_reason_must_be_string")
        excludes = item.get("extra_excludes", [])
        terms = item.get("search_terms", [])
        if (
            not isinstance(excludes, list)
            or len(excludes) > MAX_EXTRA_EXCLUDES
            or any(not isinstance(value, str) or not value for value in excludes)
        ):
            raise RepositoryIntelligenceError("manifest_invalid_extra_excludes")
        if (
            not isinstance(terms, list)
            or len(terms) > MAX_SEARCH_TERMS
            or any(not isinstance(value, str) or not value or len(value) > 200 for value in terms)
        ):
            raise RepositoryIntelligenceError("manifest_invalid_search_terms")
        specs.append(
            RepoSpec(
                tag=tag,
                github=github,
                directory=directory,
                source_root_key=source_root_key,
                enabled=enabled,
                reason=sanitize_output(reason),
                extra_excludes=tuple(excludes),
                search_terms=tuple(terms),
            )
        )
    return document, tuple(specs)


def parse_keyed_paths(items: Sequence[str], option: str) -> dict[str, pathlib.Path]:
    """Parse repeated ``key=path`` options without reading any local paths."""
    result: dict[str, pathlib.Path] = {}
    for item in items:
        if "=" not in item:
            raise RepositoryIntelligenceError(f"{option}_format")
        key, value = item.split("=", 1)
        if not key or not _TAG_RE.match(key) or not value:
            raise RepositoryIntelligenceError(f"{option}_invalid")
        if key in result:
            raise RepositoryIntelligenceError(f"{option}_duplicate_key")
        result[key] = pathlib.Path(value).resolve()
    return result


def resolve_sources(
    specs: Sequence[RepoSpec],
    source_roots: dict[str, pathlib.Path],
    overrides: dict[str, pathlib.Path],
) -> dict[str, pathlib.Path]:
    """Resolve each logical repository to one local directory, fail closed."""
    resolved: dict[str, pathlib.Path] = {}
    for spec in specs:
        if not spec.enabled:
            continue
        if spec.tag in overrides:
            source = overrides[spec.tag]
        else:
            root = source_roots.get(spec.source_root_key)
            if root is None:
                raise RepositoryIntelligenceError(f"source_root_missing {spec.source_root_key}")
            source = (root / spec.directory).resolve()
            if not is_within(source, root):
                raise RepositoryIntelligenceError("source_directory_escapes_root")
        resolved[spec.tag] = source
    return resolved


def has_indexable_source(source: pathlib.Path) -> bool:
    """Return False when the tree has no non-excluded code files to index."""
    for path in source.rglob("*"):
        if not path.is_file() or is_excluded(path, source):
            continue
        if path.suffix.lower() in INDEXABLE_SUFFIXES:
            return True
    return False


def _sensitive_source_file_count(document: dict, source: pathlib.Path) -> int:
    """Count graph nodes whose source_file is an excluded/sensitive path."""
    found = 0
    for node in document.get("nodes", []):
        if not isinstance(node, dict):
            continue
        source_file = node.get("source_file")
        # Graphify emits "" for symbol nodes that have no owning file.
        if not isinstance(source_file, str) or not source_file.strip():
            continue
        if is_excluded((source / source_file).resolve(), source):
            found += 1
    return found


def index_repository(
    spec: RepoSpec,
    source: pathlib.Path,
    index_root: pathlib.Path,
    runner: GraphifyRunner,
    with_impact: bool = True,
) -> dict:
    """Index one repository; callers isolate any exception per repository."""
    entry: dict = {
        "tag": spec.tag,
        "github": spec.github,
        "status": "blocked",
        "source_layout": {
            "source_root_key": spec.source_root_key,
            "directory": spec.directory,
        },
        "index_relative_path": f"{spec.tag}/graphify-out/graph.json",
    }
    if not source.is_dir():
        entry["reason"] = "source_directory_not_found"
        return entry

    output = (index_root / spec.tag).resolve()
    if is_within(output, source) or is_within(source, output):
        entry["reason"] = "index_root_overlaps_source"
        return entry
    if not has_indexable_source(source):
        entry["status"] = "skipped"
        entry["reason"] = "no_indexable_source"
        return entry

    excludes = tuple(DEFAULT_EXCLUDES) + spec.extra_excludes
    extraction = runner.extract(source, output, force=False, excludes=excludes)
    document, stats, _edge_key, graph_digest = read_graph(extraction.graph_path)
    sensitive_count = _sensitive_source_file_count(document, source)
    if sensitive_count:
        entry["reason"] = "sensitive_source_file_indexed"
        entry["sensitive_source_file_count"] = sensitive_count
        return entry
    if not extraction.as_dict().get("source_unchanged"):
        entry["reason"] = "source_tree_mutated_during_extract"
        return entry

    searches = []
    for term in spec.search_terms:
        result = runner.search(extraction.graph_path, "query", term)
        searches.append(
            {
                "term": term,
                "kind": result.get("kind"),
                "status": result.get("status"),
                "exit_code": result.get("exit_code"),
                "elapsed_ms": result.get("elapsed_ms"),
            }
        )

    impact: dict | None = None
    if with_impact:
        for node in document.get("nodes", []):
            if not isinstance(node, dict):
                continue
            node_id = node.get("id")
            if not isinstance(node_id, str) or not node_id:
                continue
            result = runner.search(extraction.graph_path, "affected", node_id, depth=2)
            impact = {
                "matched_node_id_sha256": hash_text(node_id),
                "status": result.get("status"),
                "exit_code": result.get("exit_code"),
                "elapsed_ms": result.get("elapsed_ms"),
            }
            break

    entry.update(
        {
            "status": "success",
            "reason": "ok",
            "graph": {
                "sha256": graph_digest,
                "bytes": extraction.graph_bytes,
                "node_count": stats.node_count,
                "edge_count": stats.edge_count,
                "source_file_count": stats.source_file_count,
                "extract_elapsed_ms": extraction.elapsed_ms,
                "tool_version": extraction.tool_version,
                "source_unchanged": True,
                "sensitive_source_file_count": 0,
            },
            "searches": searches,
            "impact": impact,
        }
    )
    return entry


def run(
    specs: Sequence[RepoSpec],
    source_roots: dict[str, pathlib.Path],
    overrides: dict[str, pathlib.Path],
    index_root: pathlib.Path,
    json_out: pathlib.Path | None,
    graphify_bin: str,
    with_impact: bool = True,
) -> dict:
    """Run all repositories independently and aggregate a path-safe report."""
    if not source_roots and not overrides:
        raise RepositoryIntelligenceError("source_root_not_provided")
    resolved = resolve_sources(specs, source_roots, overrides)
    index_root = index_root.resolve()
    if json_out is not None:
        json_out = json_out.resolve()
        for source in resolved.values():
            if is_within(json_out, source):
                raise RepositoryIntelligenceError("report_path_overlaps_source")
    for source in resolved.values():
        if is_within(index_root, source):
            raise RepositoryIntelligenceError("index_root_overlaps_source")

    runner: GraphifyRunner | None = None
    version: str | None = None
    runner_error: str | None = None
    try:
        runner = GraphifyRunner(graphify_bin)
        version = runner.verify_version()
    except RepositoryIntelligenceError as exc:
        runner_error = sanitize_output(str(exc))

    entries: list[dict] = []
    for spec in specs:
        if not spec.enabled:
            entries.append(
                {
                    "tag": spec.tag,
                    "github": spec.github,
                    "status": "skipped",
                    "reason": spec.reason or "disabled_in_manifest",
                }
            )
            continue
        entry: dict
        try:
            if runner is None:
                entry = {
                    "tag": spec.tag,
                    "github": spec.github,
                    "status": "blocked",
                    "reason": runner_error or "graphify_runner_unavailable",
                }
            else:
                entry = index_repository(
                    spec,
                    resolved[spec.tag],
                    index_root,
                    runner,
                    with_impact=with_impact,
                )
        except RepositoryIntelligenceError as exc:
            entry = {
                "tag": spec.tag,
                "github": spec.github,
                "status": "blocked",
                "reason": sanitize_output(str(exc)),
            }
        except Exception as exc:  # isolate one bad repository from the rest
            entry = {
                "tag": spec.tag,
                "github": spec.github,
                "status": "blocked",
                "reason": f"unexpected_{type(exc).__name__}",
            }
        entries.append(entry)

    summary = {
        status: sum(1 for item in entries if item["status"] == status)
        for status in ("success", "blocked", "skipped")
    }
    summary["total"] = len(entries)
    report = {
        "schema_version": 1,
        "policy": POLICY_ID,
        "product": {
            "name": "Graphify open-source CLI",
            "package": "graphifyy",
            "pinned_version": PINNED_GRAPHIFY_VERSION,
            "pypi_wheel_sha256": PINNED_WHEEL_SHA256,
            "reported_version": version,
        },
        "index_layout": "<index-root>/<tag>/graphify-out/graph.json",
        "repositories": entries,
        "summary": summary,
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    payload = json.dumps(sanitize_json(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if json_out is None:
        sys.stdout.write(payload)
    else:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(payload, encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="graphify-multi-repo",
        description="Central offline Graphify orchestration with one index per repository",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="validate a manifest without indexing")
    validate.add_argument("--manifest", required=True)

    run_parser = sub.add_parser("run", help="index every enabled repository")
    run_parser.add_argument("--manifest", required=True)
    run_parser.add_argument("--index-root", required=True)
    run_parser.add_argument(
        "--source-root",
        action="append",
        default=[],
        metavar="KEY=PATH",
        help="logical source root used by manifest entries",
    )
    run_parser.add_argument(
        "--source",
        action="append",
        default=[],
        metavar="TAG=PATH",
        help="override one repository's local source directory",
    )
    run_parser.add_argument("--graphify-bin", default="graphify")
    run_parser.add_argument("--json-out")
    run_parser.add_argument("--no-impact", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _document, specs = load_manifest(pathlib.Path(args.manifest))
        if args.command == "validate":
            sys.stdout.write(
                json.dumps(
                    {
                        "schema_version": 1,
                        "policy": POLICY_ID,
                        "repositories": [spec.as_dict() for spec in specs],
                    },
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                )
                + "\n"
            )
            return 0
        source_roots = parse_keyed_paths(args.source_root, "--source-root")
        overrides = parse_keyed_paths(args.source, "--source")
        report = run(
            specs,
            source_roots,
            overrides,
            pathlib.Path(args.index_root),
            pathlib.Path(args.json_out) if args.json_out else None,
            args.graphify_bin,
            with_impact=not args.no_impact,
        )
        return 0 if report["summary"]["blocked"] == 0 else 3
    except RepositoryIntelligenceError as exc:
        print(f"FAIL {sanitize_output(str(exc))}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

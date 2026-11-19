"""Read-only local repository intelligence built on the Graphify CLI.

The implementation is split across ``common``, ``runner`` and ``adapters``;
this module keeps the stable public surface and the CLI entry point.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import subprocess
import sys
from collections.abc import Iterable, Sequence

from .adapters import (
    branch_adapter,
    cross_repo_view,
    dependency_adapter,
    docs_adapter,
    inspect_repository,
    tree_adapter,
    workflow_adapter,
)
from .common import (
    DEFAULT_EXCLUDES,
    PINNED_GRAPHIFY_VERSION,
    PINNED_WHEEL_SHA256,
    POLICY_ID,
    PROVIDER_KEY_VARS,
    GraphSchemaError,
    GraphifyRunnerError,
    GraphStats,
    RepositoryIntelligenceError,
    is_within,
    read_graph,
    validate_graph,
)
from .runner import ExtractResult, GraphifyRunner

def build_report(
    source: pathlib.Path,
    output_root: pathlib.Path,
    graphify_bin: str = "graphify",
    force: bool = False,
) -> dict:
    """Verify the CLI, extract a graph and assemble the local report."""
    runner = GraphifyRunner(graphify_bin)
    version = runner.verify_version()
    extraction = runner.extract(source, output_root, force=force)
    return {
        "schema_version": 1,
        "policy": POLICY_ID,
        "product": {
            "name": "Graphify open-source CLI",
            "package": "graphifyy",
            "pinned_version": PINNED_GRAPHIFY_VERSION,
            "pypi_wheel_sha256": PINNED_WHEEL_SHA256,
            "reported_version": version,
        },
        "source": {"path": str(source.resolve())},
        "graph": extraction.as_dict(),
        "adapters": inspect_repository(source, extraction.graph_path),
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def write_report(report: dict, output: pathlib.Path | None) -> None:
    """Write JSON only to an explicit path outside protected inputs."""
    payload = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if output is None:
        sys.stdout.write(payload)
        return
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")


def _require_outside_output(output: pathlib.Path, sources: Iterable[pathlib.Path]) -> None:
    output = output.resolve()
    for source in sources:
        if is_within(output, source.resolve()) or is_within(source.resolve(), output):
            raise RepositoryIntelligenceError("report_path_overlaps_source")


def _add_common(parser: argparse.ArgumentParser, with_graph: bool = False) -> None:
    parser.add_argument("--graphify-bin", default="graphify", help="pinned Graphify CLI executable")
    if with_graph:
        parser.add_argument("--graph", required=True, help="path to graph.json or merged graph.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repository-intelligence",
        description="Read-only local repository graphs and Devobs adapters",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="extract a pinned Graphify graph and report")
    build.add_argument("--source", default=".")
    build.add_argument("--output-root", required=True)
    build.add_argument("--force", action="store_true", help="full re-scan instead of incremental")
    build.add_argument("--json-out")
    _add_common(build)

    inspect = sub.add_parser("inspect", help="run local adapters without extraction")
    inspect.add_argument("--source", default=".")
    inspect.add_argument("--graph")
    inspect.add_argument("--json-out")

    search = sub.add_parser("search", help="run a read-only Graphify query")
    _add_common(search, with_graph=True)
    search.add_argument("--kind", required=True, choices=("query", "path", "explain", "affected", "god-nodes", "diagnose"))
    search.add_argument("--term")
    search.add_argument("--term2")
    search.add_argument("--depth", type=int, default=2)
    search.add_argument("--json-out")

    impact = sub.add_parser("impact", help="map changed files to reverse Graphify impact")
    _add_common(impact, with_graph=True)
    impact.add_argument("--changed-file", action="append", default=[])
    impact.add_argument("--depth", type=int, default=2)
    impact.add_argument("--json-out")

    cross = sub.add_parser("cross-repo", help="bounded local cross-repo adapter view")
    _add_common(cross)
    cross.add_argument("--config", required=True)
    cross.add_argument("--merge-out", help="optional native Graphify merge output (external path)")
    cross.add_argument("--json-out")

    bench = sub.add_parser("benchmark", help="measure extraction and search latency")
    _add_common(bench)
    bench.add_argument("--source", default=".")
    bench.add_argument("--output-root", required=True)
    bench.add_argument("--iterations", type=int, default=2)
    bench.add_argument("--search-term", action="append", default=[])
    bench.add_argument("--force-first", action="store_true")
    bench.add_argument("--json-out")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "build":
            source = pathlib.Path(args.source).resolve()
            output = pathlib.Path(args.json_out).resolve() if args.json_out else None
            if output is not None:
                _require_outside_output(output, [source])
            write_report(build_report(source, pathlib.Path(args.output_root), args.graphify_bin, args.force), output)
            return 0

        if args.command == "inspect":
            source = pathlib.Path(args.source).resolve()
            output = pathlib.Path(args.json_out).resolve() if args.json_out else None
            if output is not None:
                _require_outside_output(output, [source])
            graph = pathlib.Path(args.graph).resolve() if args.graph else None
            write_report(inspect_repository(source, graph), output)
            return 0

        if args.command == "search":
            runner = GraphifyRunner(args.graphify_bin)
            runner.verify_version()
            result = runner.search(
                pathlib.Path(args.graph),
                args.kind,
                args.term,
                args.term2,
                args.depth,
            )
            write_report(result, pathlib.Path(args.json_out).resolve() if args.json_out else None)
            return 0

        if args.command == "impact":
            graph = pathlib.Path(args.graph)
            document, _stats, edge_key, _digest = read_graph(graph)
            nodes = document.get("nodes", [])
            selected: list[str] = []
            for changed in args.changed_file:
                normalized = changed.replace("\\", "/")
                for node in nodes:
                    if not isinstance(node, dict):
                        continue
                    source_file = str(node.get("source_file", "")).replace("\\", "/")
                    node_id = node.get("id")
                    if isinstance(node_id, str) and source_file.endswith(normalized):
                        selected.append(node_id)
            selected = sorted(set(selected))[:25]
            runner = GraphifyRunner(args.graphify_bin)
            runner.verify_version()
            results = [
                runner.search(graph, "affected", node_id, depth=args.depth)
                for node_id in selected
            ]
            write_report(
                {
                    "adapter": "devobs_impact",
                    "native_graphify_feature": False,
                    "graph_commands": "graphify affected",
                    "edge_key": edge_key,
                    "changed_file_count": len(args.changed_file),
                    "matched_node_ids": selected,
                    "results": results,
                },
                pathlib.Path(args.json_out).resolve() if args.json_out else None,
            )
            return 0

        if args.command == "cross-repo":
            config = pathlib.Path(args.config).resolve()
            view = cross_repo_view(config)
            try:
                config_doc = json.loads(config.read_text(encoding="utf-8"))
                sources = [pathlib.Path(item["source"]) for item in config_doc["repositories"]]
            except (KeyError, TypeError, json.JSONDecodeError) as exc:
                raise RepositoryIntelligenceError("cross_repo_config_unreadable") from exc
            if args.merge_out:
                output = pathlib.Path(args.merge_out).resolve()
                _require_outside_output(output, sources)
                graphs = [pathlib.Path(item["graph"]) for item in config_doc["repositories"]]
                runner = GraphifyRunner(args.graphify_bin)
                runner.verify_version()
                view["native_merge"] = runner.merge_graphs(graphs, output)
            write_report(view, pathlib.Path(args.json_out).resolve() if args.json_out else None)
            return 0

        if args.command == "benchmark":
            source = pathlib.Path(args.source).resolve()
            output_root = pathlib.Path(args.output_root).resolve()
            runner = GraphifyRunner(args.graphify_bin)
            version = runner.verify_version()
            runs = []
            for index in range(max(1, args.iterations)):
                extraction = runner.extract(source, output_root, force=args.force_first and index == 0)
                runs.append(
                    {
                        "iteration": index,
                        "elapsed_ms": extraction.elapsed_ms,
                        "node_count": extraction.stats.node_count,
                        "edge_count": extraction.stats.edge_count,
                        "graph_bytes": extraction.graph_bytes,
                    }
                )
            searches = [
                runner.search(output_root / "graphify-out" / "graph.json", "query", term)
                for term in args.search_term
            ]
            write_report(
                {
                    "schema_version": 1,
                    "policy": POLICY_ID,
                    "graphify_version": version,
                    "source": str(source),
                    "output_root": str(output_root),
                    "runs": runs,
                    "searches": searches,
                },
                pathlib.Path(args.json_out).resolve() if args.json_out else None,
            )
            return 0
    except RepositoryIntelligenceError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 2
    return 2

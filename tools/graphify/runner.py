"""Pinned, offline subprocess wrapper for the Graphify CLI."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass

from .common import (
    DEFAULT_EXCLUDES,
    MAX_GRAPH_BYTES,
    PINNED_GRAPHIFY_VERSION,
    PROVIDER_KEY_VARS,
    GraphSchemaError,
    GraphStats,
    GraphifyRunnerError,
    RepositoryIntelligenceError,
    _VERSION_RE,
    hash_text,
    is_within,
    read_graph,
    sanitize_output,
    snapshot_source,
    validate_graph,
)

@dataclass(frozen=True)
class ExtractResult:
    graph_path: pathlib.Path
    graph_sha256: str
    graph_bytes: int
    stats: GraphStats
    elapsed_ms: int
    tool_version: str
    source_before: dict
    source_after: dict
    argv: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "graph_path": str(self.graph_path),
            "graph_sha256": self.graph_sha256,
            "graph_bytes": self.graph_bytes,
            "stats": self.stats.as_dict(),
            "elapsed_ms": self.elapsed_ms,
            "tool_version": self.tool_version,
            "source_before": self.source_before,
            "source_after": self.source_after,
            "source_unchanged": self.source_before == self.source_after,
            "argv": list(self.argv),
        }



class GraphifyRunner:
    """Thin, fail-closed subprocess wrapper around the pinned Graphify CLI."""

    def __init__(
        self,
        binary: str = "graphify",
        version: str = PINNED_GRAPHIFY_VERSION,
        timeout: int = 900,
    ) -> None:
        if not binary or shutil.which(binary) is None:
            raise GraphifyRunnerError("graphify_binary_not_found")
        self.binary = binary
        self.version = version
        self.timeout = timeout

    @staticmethod
    def offline_env() -> dict[str, str]:
        """Child environment with no LLM backend and no usable network path."""
        env = os.environ.copy()
        for key in PROVIDER_KEY_VARS:
            env[key] = ""
        env["GRAPHIFY_BACKEND"] = "none"
        env["GRAPHIFY_QUERY_LOG_DISABLE"] = "1"
        env["HTTP_PROXY"] = "http://127.0.0.1:9"
        env["HTTPS_PROXY"] = "http://127.0.0.1:9"
        env["ALL_PROXY"] = "http://127.0.0.1:9"
        env["http_proxy"] = "http://127.0.0.1:9"
        env["https_proxy"] = "http://127.0.0.1:9"
        env["NO_PROXY"] = ""
        env["no_proxy"] = ""
        return env

    def _run(
        self,
        args: Sequence[str],
        allowed_codes: frozenset[int] = frozenset({0}),
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        argv = [self.binary, *args]
        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                check=False,
                env=env if env is not None else self.offline_env(),
            )
        except subprocess.TimeoutExpired as exc:
            raise GraphifyRunnerError(f"graphify_{args[0]}_timeout") from exc
        except OSError as exc:
            raise GraphifyRunnerError(f"graphify_{args[0]}_spawn_failed {type(exc).__name__}") from exc
        if result.returncode not in allowed_codes:
            raise GraphifyRunnerError(
                f"graphify_{args[0]}_failed exit={result.returncode} "
                f"stderr_sha256={hash_text(result.stderr or '')[:16]}"
            )
        return result

    def verify_version(self) -> str:
        result = self._run(["--version"])
        match = _VERSION_RE.match((result.stdout or "").strip())
        if not match:
            raise GraphifyRunnerError("graphify_version_parse_failed")
        reported = match.group(1)
        if reported != self.version:
            raise GraphifyRunnerError(f"graphify_version_mismatch reported={reported}")
        return reported

    def extract(
        self,
        source: pathlib.Path,
        output_root: pathlib.Path,
        force: bool = False,
        excludes: Sequence[str] = DEFAULT_EXCLUDES,
    ) -> ExtractResult:
        source = source.resolve()
        output_root = output_root.resolve()
        if not source.is_dir():
            raise RepositoryIntelligenceError("source_directory_not_found")
        if is_within(output_root, source) or is_within(source, output_root):
            raise RepositoryIntelligenceError("output_root_overlaps_source")
        if output_root.exists() and not output_root.is_dir():
            raise RepositoryIntelligenceError("output_root_is_not_directory")

        before = snapshot_source(source)
        args = [
            "extract",
            str(source),
            "--code-only",
            "--no-cluster",
            "--out",
            str(output_root),
        ]
        for pattern in excludes:
            args.extend(["--exclude", pattern])
        if force:
            args.append("--force")
        started = time.perf_counter()
        result = self._run(args, env=self.offline_env())
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        graph_path = output_root / "graphify-out" / "graph.json"
        if not graph_path.is_file():
            raise GraphifyRunnerError("graph_json_not_written")
        with graph_path.open("rb") as handle:
            raw = handle.read()
        if not raw or len(raw) > MAX_GRAPH_BYTES:
            raise GraphSchemaError("graph_json_size_out_of_range")
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GraphSchemaError(f"graph_json_invalid {type(exc).__name__}") from exc
        stats = validate_graph(document)

        after = snapshot_source(source)
        if before != after:
            raise RepositoryIntelligenceError("source_tree_mutated_during_extract")
        if (source / "graphify-out").exists():
            raise RepositoryIntelligenceError("graphify_out_created_in_source")

        return ExtractResult(
            graph_path=graph_path,
            graph_sha256=hashlib.sha256(raw).hexdigest(),
            graph_bytes=len(raw),
            stats=stats,
            elapsed_ms=elapsed_ms,
            tool_version=self.version,
            source_before=before,
            source_after=after,
            argv=tuple([self.binary, *args]),
        )

    def search(
        self,
        graph_path: pathlib.Path,
        kind: str,
        term: str | None = None,
        term2: str | None = None,
        depth: int = 2,
    ) -> dict:
        """Run a read-only Graphify query; statuses 3/4 are non-fatal."""
        path = graph_path.resolve()
        if not path.is_file():
            raise RepositoryIntelligenceError("graph_file_not_found")
        if not 1 <= depth <= 6:
            raise RepositoryIntelligenceError("depth_out_of_range")
        if kind == "query":
            args = ["query", term or "", "--graph", str(path), "--budget", "2000"]
        elif kind == "path":
            args = ["path", term or "", term2 or "", "--graph", str(path)]
        elif kind == "explain":
            args = ["explain", term or "", "--graph", str(path)]
        elif kind == "affected":
            args = ["affected", term or "", "--graph", str(path), "--depth", str(depth)]
        elif kind == "god-nodes":
            args = ["god-nodes", "--json", "--graph", str(path)]
        elif kind == "diagnose":
            args = ["diagnose", "multigraph", "--json", "--graph", str(path)]
        else:
            raise RepositoryIntelligenceError("unsupported_search_kind")
        started = time.perf_counter()
        result = self._run(args, allowed_codes=frozenset({0, 3, 4}))
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        status = {0: "ok", 3: "ambiguous", 4: "no_match"}[result.returncode]
        payload: dict = {
            "kind": kind,
            "term": term,
            "term2": term2,
            "depth": depth,
            "status": status,
            "exit_code": result.returncode,
            "elapsed_ms": elapsed_ms,
        }
        if kind in {"god-nodes", "diagnose"}:
            try:
                payload["result"] = json.loads(result.stdout)
            except json.JSONDecodeError as exc:
                raise GraphifyRunnerError(f"graphify_{kind}_json_invalid") from exc
        else:
            payload["result"] = sanitize_output(result.stdout, [str(path.parent), path.parent.as_posix()])
        return payload

    def merge_graphs(self, graph_paths: Sequence[pathlib.Path], output_path: pathlib.Path) -> dict:
        """Native Graphify cross-repo merge into an explicit external file."""
        paths = [path.resolve() for path in graph_paths]
        if len(paths) < 2:
            raise RepositoryIntelligenceError("merge_requires_two_graphs")
        for path in paths:
            if not path.is_file():
                raise RepositoryIntelligenceError("merge_input_graph_not_found")
        output_path = output_path.resolve()
        if output_path in paths:
            raise RepositoryIntelligenceError("merge_output_overwrites_input")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        args = ["merge-graphs", *(str(path) for path in paths), "--out", str(output_path)]
        self._run(args)
        document, stats, _edge_key, digest = read_graph(output_path)
        return {
            "native_graphify_feature": True,
            "output_path": str(output_path),
            "graph_sha256": digest,
            "nodes": len(document.get("nodes", [])),
            "stats": stats.as_dict(),
        }



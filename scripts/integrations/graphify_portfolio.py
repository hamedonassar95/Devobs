"""LEGACY Graphify portfolio CLI adapter (canonical implementation: tools/graphify).

This file preserves the original import path, flags, exit codes, report schema,
dry-run default and 0.9.112 version check. All behavior lives in
``tools.graphify.portfolio`` and ``tools.graphify.portfolio_execution`` under an
explicit legacy contract; this adapter contains no orchestration or subprocess
implementation.
"""

from __future__ import annotations

import pathlib
import subprocess  # nosec B404 - retained for the public default argument only
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.graphify import portfolio as _portfolio  # noqa: E402
from tools.graphify import portfolio_execution as _execution  # noqa: E402

CONTRACT = _portfolio.LEGACY_PORTFOLIO_CONTRACT

POLICY = CONTRACT.policy
PINNED_GRAPHIFY_VERSION = CONTRACT.pinned_version
CANONICAL_IMPLEMENTATION = CONTRACT.canonical["implementation"]
CANONICAL_CLI = CONTRACT.canonical["cli"]
CANONICAL_PINNED_VERSION = CONTRACT.canonical["pinned_version"]
CANONICAL_MIGRATION_DOC = CONTRACT.canonical["migration_doc"]
LEGACY_NOTICE = CONTRACT.notice
AUTHORIZED_OWNER = CONTRACT.authorized_owner
ROLLOUT_BRANCHES = CONTRACT.rollout_branches
DEFAULT_TIMEOUT_SECONDS = CONTRACT.default_timeout_seconds
PROVIDER_KEY_VARS = CONTRACT.provider_key_vars

PortfolioError = _portfolio.PortfolioError
Repository = _portfolio.Repository

parse_github_remote = _portfolio.parse_github_remote
is_within = _portfolio.is_within
_git = _portfolio._git
_run = _execution._run
graphify_version = _execution.graphify_version
_tail = _execution._tail


def inspect_repository(path: pathlib.Path) -> Repository:
    return _portfolio.inspect_repository(path, contract=CONTRACT)


def discover(root: pathlib.Path, extra_paths=None):
    return _portfolio.discover(root, extra_paths, contract=CONTRACT)


def validate_output_root(output_root: pathlib.Path, repositories) -> pathlib.Path:
    return _portfolio.validate_output_root(output_root, repositories)


def plan(repositories, output_root: pathlib.Path, selected):
    return _portfolio.plan(repositories, output_root, selected)


def build_environment(base=None):
    return _execution.build_environment(base, contract=CONTRACT)


def execute_repository(
    repository: Repository,
    output_root: pathlib.Path,
    binary: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    run=subprocess.run,
):
    return _execution.execute_repository(
        repository,
        output_root,
        binary,
        timeout=timeout,
        run=run,
        contract=CONTRACT,
    )


def _build_parser():
    return _execution.build_parser(contract=CONTRACT)


def main(argv=None) -> int:
    return _execution.main(argv, contract=CONTRACT)


if __name__ == "__main__":
    sys.exit(main())

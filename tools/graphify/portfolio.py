"""Canonical implementation of the backward-compatible portfolio CLI.

The legacy ``scripts/integrations/graphify_portfolio.py`` entry point is a thin
adapter over this module. Two contracts are kept explicit:

* ``LEGACY_PORTFOLIO_CONTRACT`` preserves the original review-only 0.9.112 CLI,
  report schema, absolute-path evidence and dry-run default.
* ``CANONICAL_PORTFOLIO_CONTRACT`` identifies the supported 0.9.113 stack.

No function here downloads, installs, uploads, deploys or changes Graphify global
state. Git access is read-only and restricted to a fixed command allowlist.
"""

from __future__ import annotations

import dataclasses
import pathlib
import re
import shutil
import subprocess  # nosec B404 - fixed-argv Git and pinned local Graphify only
from collections.abc import Sequence
from dataclasses import dataclass, field

from .common import (
    PINNED_GRAPHIFY_VERSION,
    POLICY_ID,
    PROVIDER_KEY_VARS,
    RepositoryIntelligenceError,
    is_within as _path_within,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
LEGACY_NOTICE = (
    "DEPRECATED: scripts/integrations/graphify_portfolio.py is the legacy "
    "Graphify portfolio orchestrator; use scripts/graphify/multi_repo.py "
    "(tools/graphify, pinned 0.9.113) for new work."
)
CANONICAL_IMPLEMENTATION = "tools/graphify"
CANONICAL_CLI = "scripts/graphify/multi_repo.py"
CANONICAL_MIGRATION_DOC = "docs/architecture/GRAPHIFY_CONSOLIDATION_PLAN.md"
COMMAND_TEMPLATE = "graphify extract <path> --code-only --out <external-dir>"

_REMOTE_PATTERNS = (
    re.compile(
        r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<name>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
    ),
    re.compile(
        r"^git@github\.com:(?P<owner>[A-Za-z0-9_.-]+)/(?P<name>[A-Za-z0-9_.-]+?)(?:\.git)?$"
    ),
    re.compile(
        r"^ssh://git@github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<name>[A-Za-z0-9_.-]+?)(?:\.git)?$"
    ),
)


class PortfolioError(RepositoryIntelligenceError):
    """A policy, preflight or validation refusal that must stop the run."""


@dataclass(frozen=True)
class PortfolioContract:
    """Observable policy and report contract for one portfolio CLI surface."""

    policy: str
    pinned_version: str
    notice: str
    description: str
    canonical: dict
    legacy: bool
    authorized_owner: str = "hamedonassar95"
    rollout_branches: tuple[str, ...] = ("main", "master")
    default_timeout_seconds: int = 900
    provider_key_vars: tuple[str, ...] = PROVIDER_KEY_VARS
    default_root: pathlib.Path = field(default_factory=lambda: REPO_ROOT.parent)
    default_out_root: pathlib.Path = field(
        default_factory=lambda: pathlib.Path.home() / ".devobs" / "graphify-portfolio"
    )
    command_template: str = COMMAND_TEMPLATE


def _canonical_metadata(pinned_version: str) -> dict:
    return {
        "implementation": CANONICAL_IMPLEMENTATION,
        "cli": CANONICAL_CLI,
        "pinned_version": pinned_version,
        "migration_doc": CANONICAL_MIGRATION_DOC,
    }


LEGACY_PORTFOLIO_CONTRACT = PortfolioContract(
    policy="devobs-graphify-portfolio-v1",
    pinned_version="0.9.112",
    notice=LEGACY_NOTICE,
    description="LEGACY Graphify portfolio orchestrator (canonical: tools/graphify).",
    canonical=_canonical_metadata(PINNED_GRAPHIFY_VERSION),
    legacy=True,
)

CANONICAL_PORTFOLIO_CONTRACT = PortfolioContract(
    policy=POLICY_ID,
    pinned_version=PINNED_GRAPHIFY_VERSION,
    notice="",
    description="Canonical Graphify portfolio compatibility surface (tools/graphify).",
    canonical=_canonical_metadata(PINNED_GRAPHIFY_VERSION),
    legacy=False,
    default_root=REPO_ROOT,
)


@dataclasses.dataclass(frozen=True)
class Repository:
    name: str
    path: pathlib.Path
    remote: str
    owner: str | None
    remote_name: str | None
    branch: str | None
    head: str | None
    dirty: bool
    reasons: tuple[str, ...]

    @property
    def authorized(self) -> bool:
        return self.owner == LEGACY_PORTFOLIO_CONTRACT.authorized_owner

    @property
    def eligible(self) -> bool:
        return not self.reasons

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "path": str(self.path),
            "remote": self.remote,
            "owner": self.owner,
            "remote_name": self.remote_name,
            "branch": self.branch,
            "head": self.head,
            "dirty": self.dirty,
            "authorized": self.authorized,
            "eligible": self.eligible,
            "blocked_reasons": list(self.reasons),
        }


def parse_github_remote(url: str) -> tuple[str, str] | None:
    """Return ``(owner, name)`` for a github.com remote, else ``None``."""
    value = (url or "").strip()
    for pattern in _REMOTE_PATTERNS:
        match = pattern.match(value)
        if match:
            owner = match.group("owner")
            name = match.group("name")
            if name.endswith(".git"):
                name = name[: -len(".git")]
            return owner, name
    return None


def is_within(path: pathlib.Path, parent: pathlib.Path) -> bool:
    """True when *path* is *parent* or lives underneath it."""
    return _path_within(path, parent)


def _git(repo: pathlib.Path, *args: str) -> str:
    allowed = {
        ("config", "--get", "remote.origin.url"),
        ("rev-parse", "--abbrev-ref", "HEAD"),
        ("rev-parse", "HEAD"),
        ("status", "--porcelain", "--untracked-files=all"),
    }
    if tuple(args) not in allowed:
        raise PortfolioError("unsupported Git inspection command")
    git_executable = shutil.which("git")
    if not git_executable or not pathlib.Path(git_executable).is_absolute():
        raise PortfolioError("trusted Git executable not found")
    result = subprocess.run(  # nosec B603 - audited fixed Git argv, no shell
        [git_executable, "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if result.returncode != 0:
        raise PortfolioError("Git inspection command failed")
    return result.stdout


def inspect_repository(
    path: pathlib.Path,
    contract: PortfolioContract = LEGACY_PORTFOLIO_CONTRACT,
) -> Repository:
    """Read local git metadata only; never contacts the remote."""
    path = path.resolve()
    reasons: list[str] = []
    if not (path / ".git").exists():
        raise PortfolioError(f"{path} is not a git checkout")

    remote = ""
    try:
        remote = _git(path, "config", "--get", "remote.origin.url").strip()
    except PortfolioError:
        reasons.append("no origin remote")
    parsed = parse_github_remote(remote)
    owner = parsed[0] if parsed else None
    remote_name = parsed[1] if parsed else None

    branch = _git(path, "rev-parse", "--abbrev-ref", "HEAD").strip() or None
    head = _git(path, "rev-parse", "HEAD").strip() or None
    dirty = bool(_git(path, "status", "--porcelain", "--untracked-files=all").strip())

    if parsed is None:
        reasons.append("origin is not a supported github.com remote")
    elif owner != contract.authorized_owner:
        reasons.append(f"origin owner '{owner}' is not {contract.authorized_owner}")

    if branch not in contract.rollout_branches:
        reasons.append(f"branch '{branch}' is not one of {', '.join(contract.rollout_branches)}")
    if dirty:
        reasons.append("working tree has uncommitted changes")

    return Repository(
        name=path.name,
        path=path,
        remote=remote,
        owner=owner,
        remote_name=remote_name,
        branch=branch,
        head=head,
        dirty=dirty,
        reasons=tuple(reasons),
    )


def discover(
    root: pathlib.Path,
    extra_paths: Sequence[pathlib.Path] | None = None,
    contract: PortfolioContract = LEGACY_PORTFOLIO_CONTRACT,
) -> tuple[list[Repository], list[dict]]:
    """Discover candidate checkouts under *root* plus explicit extra paths.

    Linked worktrees (``.git`` is a file) are skipped with a recorded reason so a
    worktree of the same repository is not reported as a second project.
    """
    if not root.exists() or not root.is_dir():
        raise PortfolioError(f"scan root does not exist or is not a directory: {root}")
    found: list[Repository] = []
    skipped: list[dict] = []
    seen: set[pathlib.Path] = set()
    names: dict[str, pathlib.Path] = {}

    def register(repository: Repository) -> None:
        if repository.name in names:
            raise PortfolioError(
                f"duplicate repository name '{repository.name}' for "
                f"{names[repository.name]} and {repository.path}"
            )
        names[repository.name] = repository.path
        found.append(repository)
        seen.add(repository.path)

    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        marker = child / ".git"
        if not marker.exists():
            continue
        if marker.is_file():
            skipped.append(
                {"name": child.name, "path": str(child), "reason": "linked worktree or submodule"}
            )
            continue
        try:
            repository = inspect_repository(child, contract=contract)
        except PortfolioError as exc:
            skipped.append({"name": child.name, "path": str(child), "reason": str(exc)})
            continue
        register(repository)

    for extra in extra_paths or []:
        path = extra.resolve()
        if path in seen:
            continue
        register(inspect_repository(path, contract=contract))

    return found, skipped


def validate_output_root(output_root: pathlib.Path, repositories: Sequence[Repository]) -> pathlib.Path:
    """Refuse an output root that could write into a source repository."""
    resolved = output_root.expanduser().resolve()
    for repository in repositories:
        if is_within(resolved, repository.path) or is_within(repository.path, resolved):
            raise PortfolioError(
                f"output root {resolved} overlaps the source repository {repository.path}"
            )
    return resolved


def plan(
    repositories: Sequence[Repository],
    output_root: pathlib.Path,
    selected: Sequence[str],
) -> list[dict]:
    """Build a side-effect-free plan for the requested repositories."""
    by_name = {repository.name: repository for repository in repositories}
    unknown = [name for name in selected if name not in by_name]
    if unknown:
        raise PortfolioError(f"unknown repository selection: {', '.join(sorted(unknown))}")
    chosen = [by_name[name] for name in selected] if selected else list(repositories)

    actions = []
    for repository in chosen:
        out_dir = output_root / repository.name / (repository.head or "unknown")
        actions.append(
            {
                "repository": repository,
                "output_dir": out_dir,
                "would_execute": repository.eligible and bool(selected),
                "eligible": repository.eligible,
                "blocked_reasons": list(repository.reasons),
                "existing_output": out_dir.exists(),
            }
        )
    return actions

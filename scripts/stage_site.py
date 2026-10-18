"""Stage the validated static site without copying repository-only files."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile


SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


def _validate_assets_symlinks(assets: Path) -> None:
    if assets.is_symlink():
        raise ValueError("assets/ must not be a symlink")
    if not assets.exists():
        return
    for current, directories, files in os.walk(assets, followlinks=False):
        current_path = Path(current)
        for name in (*directories, *files):
            candidate = current_path / name
            if candidate.is_symlink():
                raise ValueError(f"Symlinks are not allowed under assets/: {candidate}")


def resolve_source_dir(source_dir: Path, workspace_dir: Path) -> Path:
    """Resolve a candidate source directory safely under the GitHub workspace."""
    workspace_input = Path(workspace_dir)
    if workspace_input.is_symlink():
        raise ValueError("GITHUB_WORKSPACE must not be a symlink")
    workspace = workspace_input.resolve(strict=True)
    if not workspace.is_dir():
        raise ValueError("GITHUB_WORKSPACE must be a directory")

    candidate_input = Path(source_dir)
    if ".." in candidate_input.parts:
        raise ValueError("source directory must not contain parent-directory segments")
    if not candidate_input.is_absolute():
        candidate_input = Path.cwd() / candidate_input
    # Normalize dot segments without resolving symlinks, so symlinks in any
    # component can be rejected before following them.
    candidate_lexical = Path(os.path.abspath(candidate_input))
    try:
        relative = candidate_lexical.relative_to(workspace)
    except ValueError as exc:
        raise ValueError("source directory must resolve inside GITHUB_WORKSPACE") from exc

    current = workspace
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise ValueError(f"source directory path contains a symlink: {current}")

    candidate = candidate_lexical.resolve(strict=True)
    if candidate != workspace and workspace not in candidate.parents:
        raise ValueError("source directory must resolve inside GITHUB_WORKSPACE")
    if not candidate.is_dir():
        raise ValueError("source directory must be a directory")
    return candidate


def stage_site(source_dir: Path, output_dir: Path, source_sha: str) -> Path:
    """Copy index.html and visible assets into output_dir and stamp the SHA."""
    if not isinstance(source_sha, str) or not SHA_PATTERN.fullmatch(source_sha):
        raise ValueError("source SHA must be exactly 40 hexadecimal characters")

    source = Path(source_dir).resolve()
    output_input = Path(output_dir)
    if output_input.is_symlink():
        raise ValueError("output directory must not be a symlink")
    output = output_input.resolve()
    if not source.is_dir():
        raise ValueError(f"source directory does not exist: {source}")
    if output == source or output in source.parents:
        raise ValueError("output directory must not contain or replace the source directory")
    if source in output.parents and output != source / "_site":
        raise ValueError("a staged output inside the source tree must use the _site directory")

    index = source / "index.html"
    if index.is_symlink() or not index.is_file():
        raise ValueError("source directory must contain a regular index.html file")
    if index.stat().st_size == 0:
        raise ValueError("source index.html must not be empty")
    assets = source / "assets"
    _validate_assets_symlinks(assets)

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not output.is_dir():
        raise ValueError("output path exists and is not a directory")

    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    try:
        shutil.copy2(index, temporary / "index.html")
        if assets.is_dir():
            shutil.copytree(
                assets,
                temporary / "assets",
                ignore=shutil.ignore_patterns(".*"),
            )
        (temporary / "deployment.json").write_text(
            json.dumps({"schema_version": 1, "source_sha": source_sha.lower()}) + "\n",
            encoding="utf-8",
        )
        if output.exists():
            shutil.rmtree(output)
        temporary.rename(output)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="candidate directory (or SITE_SOURCE_DIR); explicit paths must be inside GITHUB_WORKSPACE",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--source-sha", default=None)
    args = parser.parse_args()

    source_setting = args.source_dir or os.environ.get("SITE_SOURCE_DIR")
    if source_setting:
        workspace_setting = os.environ.get("GITHUB_WORKSPACE")
        if workspace_setting is None and args.source_dir is None and source_setting == ".":
            # With no candidate override, the build root itself is the only allowed fallback.
            source = Path.cwd().resolve()
        elif not workspace_setting:
            print("Site staging failed: GITHUB_WORKSPACE is required for an explicit source directory.", file=sys.stderr)
            return 2
        else:
            try:
                source = resolve_source_dir(Path(source_setting), Path(workspace_setting))
            except (OSError, ValueError) as exc:
                print(f"Site staging failed: {exc}", file=sys.stderr)
                return 2
    else:
        source = Path.cwd().resolve()
    output = args.output_dir or (source / "_site")
    if args.source_sha is not None:
        sha = args.source_sha
    else:
        sha = (
            os.environ.get("SITE_SOURCE_SHA")
            or os.environ.get("SOURCE_SHA")
            or os.environ.get("VERCEL_GIT_COMMIT_SHA")
            or os.environ.get("GITHUB_SHA")
        )
    if not sha:
        print(
            "Unable to determine source SHA: pass --source-sha or set SITE_SOURCE_SHA, SOURCE_SHA, VERCEL_GIT_COMMIT_SHA, or GITHUB_SHA.",
            file=sys.stderr,
        )
        return 2

    try:
        staged = stage_site(source, output, sha)
    except (OSError, ValueError) as exc:
        print(f"Site staging failed: {exc}", file=sys.stderr)
        return 2
    print(f"Staged static site at {staged} for {sha.lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate a Trivy CycloneDX SBOM and write bounded image evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

REVISION_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
IMAGE_ID_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
VERSION_PATTERN = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\Z")
SPEC_VERSION_PATTERN = re.compile(r"[0-9]+\.[0-9]+\Z")
EXPECTED_IMAGE_PATTERN = re.compile(r"devobs-web:([0-9a-f]{40})\Z")
MAX_SBOM_BYTES = 32 * 1024 * 1024
MAX_COMPONENTS = 100_000
COMPONENT_TYPES = frozenset({
    "application",
    "container",
    "device",
    "device-driver",
    "file",
    "firmware",
    "framework",
    "library",
    "machine-learning-model",
    "operating-system",
    "platform",
})


class InvalidSbom(ValueError):
    """Raised when the SBOM does not meet the supported output contract."""


def evaluate_sbom(sbom: Any) -> tuple[str, int]:
    """Return CycloneDX version and package count, rejecting incomplete output."""
    if not isinstance(sbom, dict) or sbom.get("bomFormat") != "CycloneDX":
        raise InvalidSbom

    spec_version = sbom.get("specVersion")
    if not isinstance(spec_version, str) or not SPEC_VERSION_PATTERN.fullmatch(spec_version):
        raise InvalidSbom

    components = sbom.get("components")
    if not isinstance(components, list) or not components or len(components) > MAX_COMPONENTS:
        raise InvalidSbom
    for component in components:
        if not isinstance(component, dict):
            raise InvalidSbom
        kind = component.get("type")
        name = component.get("name")
        if (
            not isinstance(kind, str)
            or kind not in COMPONENT_TYPES
            or not isinstance(name, str)
            or not name.strip()
        ):
            raise InvalidSbom
        if "version" in component and (
            not isinstance(component["version"], str) or not component["version"].strip()
        ):
            raise InvalidSbom

    return spec_version, len(components)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON keys so later values cannot hide malformed fields."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidSbom
        result[key] = value
    return result


def _read_sbom(sbom_path: Path) -> tuple[bytes, Any]:
    try:
        with sbom_path.open("rb") as source:
            raw = source.read(MAX_SBOM_BYTES + 1)
    except OSError as exc:
        raise InvalidSbom from exc
    if not raw or len(raw) > MAX_SBOM_BYTES:
        raise InvalidSbom
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, InvalidSbom) as exc:
        raise InvalidSbom from exc
    evaluate_sbom(document)
    return raw, document


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(payload, temporary, ensure_ascii=False, sort_keys=True, indent=2)
            temporary.write("\n")
        os.replace(temporary_path, path)
    except OSError:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def _append_summary(path: Path, evidence: dict[str, Any]) -> None:
    sbom = evidence["sbom"]
    lines = [
        "## Container image SBOM",
        "",
        f"Source revision: {evidence['sourceRevision']}",
        f"Local image tag: {evidence['image']['tag']}",
        f"Local image ID: {evidence['image']['id']}",
        (
            f"CycloneDX {sbom['specVersion']}: {sbom['componentCount']} components; "
            f"SHA-256 {sbom['sha256']}."
        ),
        f"Generator: Trivy {evidence['generator']['version']}.",
        "",
        (
            "Unsigned inventory only. It records this CI build; it is not a signed "
            "provenance attestation, release image, or proof of deployment."
        ),
        "",
    ]
    with path.open("a", encoding="utf-8") as summary:
        summary.write("\n".join(lines))


def _validate_context(
    revision: str,
    expected_image: str,
    image_id: str,
    trivy_version: str,
) -> bool:
    match = EXPECTED_IMAGE_PATTERN.fullmatch(expected_image)
    return (
        bool(REVISION_PATTERN.fullmatch(revision))
        and bool(match)
        and match.group(1) == revision
        and bool(IMAGE_ID_PATTERN.fullmatch(image_id))
        and bool(VERSION_PATTERN.fullmatch(trivy_version))
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sbom", required=True, type=Path, help="CycloneDX JSON file")
    parser.add_argument("--evidence", required=True, type=Path, help="Evidence JSON output path")
    parser.add_argument(
        "--summary",
        type=Path,
        default=os.environ.get("GITHUB_STEP_SUMMARY"),
        help="GitHub Actions summary file",
    )
    parser.add_argument("--revision", required=True, help="Full checked-out Git SHA")
    parser.add_argument("--expected-image", required=True, help="Exact checked-out image tag")
    parser.add_argument("--image-id", required=True, help="Full local Docker image ID")
    parser.add_argument("--trivy-version", required=True, help="Pinned Trivy version")
    args = parser.parse_args(argv)

    if not _validate_context(args.revision, args.expected_image, args.image_id, args.trivy_version):
        print("ERROR: invalid SBOM image identity or tool version", file=sys.stderr)
        return 2
    if not isinstance(args.summary, Path):
        print("ERROR: unable to write SBOM evidence summary", file=sys.stderr)
        return 2

    try:
        raw, document = _read_sbom(args.sbom)
        spec_version, component_count = evaluate_sbom(document)
    except InvalidSbom:
        print("ERROR: missing, malformed, or unsupported CycloneDX SBOM", file=sys.stderr)
        return 2

    evidence = {
        "schemaVersion": 1,
        "sourceRevision": args.revision,
        "image": {
            "tag": args.expected_image,
            "id": args.image_id,
        },
        "sbom": {
            "format": "CycloneDX",
            "specVersion": spec_version,
            "componentCount": component_count,
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
        "generator": {
            "name": "Trivy",
            "version": args.trivy_version,
        },
        "limitations": "Unsigned CI inventory; not a release, provenance attestation, or deployment proof.",
    }

    try:
        _append_summary(args.summary, evidence)
        _atomic_json_write(args.evidence, evidence)
    except OSError:
        print("ERROR: unable to write SBOM evidence summary", file=sys.stderr)
        return 2

    print(
        f"PASS: CycloneDX {spec_version} components={component_count} "
        f"revision={args.revision[:12]} sha256={evidence['sbom']['sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

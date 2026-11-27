#!/usr/bin/env python3
"""Validate a bounded, local KI-1 manifest containing synthetic bytes only."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

try:
    from scripts.check_knowledge_source_policy import PolicyValidationError, validate_policy
except ModuleNotFoundError:  # Direct `python3 scripts/check_knowledge_source_manifest.py` invocation.
    from check_knowledge_source_policy import PolicyValidationError, validate_policy

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "knowledge-source-manifest.schema.json"
SCHEMA_VERSION = 1
MAX_INPUT_BYTES = 1_048_576
MAX_SCHEMA_BYTES = 65_536
MAX_POLICIES = MAX_SOURCES = 100
MAX_VERSIONS = 500
MAX_CHUNKS = 5_000
MAX_CONTENT_BYTES = 65_536
MAX_DEPTH = 32

SOURCE_FIELDS = frozenset({
    "schema_version", "source_id", "source_type", "tenant_id", "repository_id",
    "policy_reference", "provenance", "source_status",
})
VERSION_FIELDS = frozenset({
    "document_id", "source_id", "version_id", "document_key", "content_sha256",
    "content_type", "byte_size", "created_at", "previous_version_id",
})
CHUNK_FIELDS = frozenset({
    "chunk_id", "document_id", "version_id", "chunk_index", "content_sha256",
    "start_offset", "end_offset", "offset_unit", "tenant_id", "repository_id",
})
TOP_FIELDS = frozenset({
    "schema_version", "manifest_mode", "policies", "sources", "document_versions", "chunks",
})
ID_RE = re.compile(r"(?:src|doc|ver|chunk)_[0-9a-f]{64}\Z")
SOURCE_REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
SCOPE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
REPOSITORY_RE = re.compile(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}\Z")
DOCUMENT_KEY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z")
CONTENT_TYPES = frozenset({
    "text/plain; charset=utf-8", "text/markdown; charset=utf-8", "application/json",
})
SOURCE_TYPES = frozenset({
    "synthetic_fixture", "public_document", "public_repository_file", "internal_document",
    "confidential_document", "restricted_document",
})
SOURCE_STATUSES = frozenset({"ACTIVE", "REVOKED", "PENDING", "UNKNOWN"})


class ManifestValidationError(ValueError):
    """A fixed validation code that never includes caller-supplied content."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _fail(code: str) -> None:
    raise ManifestValidationError(code)


def _pairs_no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    _fail("invalid_json_constant")


def _parse(raw: bytes, limit: int) -> object:
    if len(raw) > limit:
        _fail("input_too_large")
    try:
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_pairs_no_duplicates,
                           parse_constant=_reject_constant)
    except ManifestValidationError:
        raise
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError):
        _fail("malformed_json")
    _check_depth(value)
    return value


def _check_depth(value: object) -> None:
    stack = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_DEPTH:
            _fail("nesting_too_deep")
        if type(current) is dict:
            stack.extend((child, depth + 1) for child in current.values())
        elif type(current) is list:
            stack.extend((child, depth + 1) for child in current)


def canonical_json_bytes(value: object) -> bytes:
    """Canonical object encoding: UTF-8, sorted keys, compact separators, no NaN."""
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                          allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        _fail("canonicalization_failed")


def canonical_manifest_bytes(manifest: dict[str, object]) -> bytes:
    """Serialize record arrays in their specified canonical order."""
    try:
        ordered = dict(manifest)
        ordered["policies"] = sorted(manifest["policies"], key=lambda item: item["source_id"])
        ordered["sources"] = sorted(manifest["sources"], key=lambda item: item["source_id"])
        ordered["document_versions"] = sorted(
            manifest["document_versions"],
            key=lambda item: (item["document_id"], item["created_at"], item["version_id"]),
        )
        ordered["chunks"] = sorted(manifest["chunks"], key=lambda item: (item["version_id"], item["chunk_index"]))
        return canonical_json_bytes(ordered)
    except (KeyError, TypeError):
        _fail("invalid_manifest_fields")


def deterministic_id(prefix: str, identity: dict[str, object]) -> str:
    """Return `<prefix>_<sha256(canonical identity)>`; prefix is a fixed domain separator."""
    if prefix not in {"src", "doc", "ver", "chunk"}:
        _fail("invalid_identifier_prefix")
    return f"{prefix}_{hashlib.sha256(canonical_json_bytes(identity)).hexdigest()}"


def _schema_contract() -> None:
    try:
        info = SCHEMA_PATH.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SCHEMA_BYTES:
            _fail("schema_unavailable")
        with SCHEMA_PATH.open("rb") as stream:
            schema = _parse(stream.read(MAX_SCHEMA_BYTES + 1), MAX_SCHEMA_BYTES)
    except ManifestValidationError:
        raise
    except OSError:
        _fail("schema_unavailable")
    if (type(schema) is not dict or type(schema.get("required")) is not list
            or any(type(item) is not str for item in schema["required"])
            or type(schema.get("properties")) is not dict or type(schema.get("$defs")) is not dict
            or any(type(item) is not dict for item in schema["$defs"].values())
            or schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
            or schema.get("title") != "Devobs Knowledge Source Manifest v1"
            or schema.get("type") != "object" or schema.get("additionalProperties") is not False
            or set(schema.get("required", [])) != TOP_FIELDS
            or len(schema["required"]) != len(set(schema["required"]))
            or set(schema.get("properties", {})) != TOP_FIELDS
            or set(schema["$defs"]) != {"policy", "source", "documentVersion", "chunk"}):
        _fail("schema_invalid")
    properties = schema["properties"]
    if (type(properties.get("schema_version")) is not dict
            or type(properties["schema_version"].get("const")) is not int
            or properties["schema_version"].get("const") != SCHEMA_VERSION
            or properties.get("manifest_mode") != {"const": "SYNTHETIC_OFFLINE"}):
        _fail("schema_invalid")
    for key, fields, maximum in (
        ("sources", SOURCE_FIELDS, MAX_SOURCES),
        ("document_versions", VERSION_FIELDS, MAX_VERSIONS),
        ("chunks", CHUNK_FIELDS, MAX_CHUNKS),
    ):
        array = schema["properties"].get(key)
        ref = "#/$defs/" + {"sources": "source", "document_versions": "documentVersion", "chunks": "chunk"}[key]
        definition = schema["$defs"][ref.rsplit("/", 1)[1]]
        properties = fields | ({"synthetic_content"} if key == "document_versions" else set())
        required = definition.get("required")
        definition_properties = definition.get("properties")
        if (type(array) is not dict or array.get("type") != "array"
                or type(array.get("minItems")) is not int or array.get("minItems") != 1
                or array.get("maxItems") != maximum or array.get("items") != {"$ref": ref}
                or definition.get("type") != "object" or definition.get("additionalProperties") is not False
                or type(required) is not list or any(type(item) is not str for item in required)
                or type(definition_properties) is not dict
                or len(required) != len(set(required)) or set(required) != fields
                or set(definition_properties) != properties):
            _fail("schema_invalid")
    policies = schema["properties"].get("policies")
    if (type(policies) is not dict or policies.get("type") != "array"
            or type(policies.get("minItems")) is not int or policies.get("minItems") != 1
            or policies.get("maxItems") != MAX_POLICIES or policies.get("items") != {"$ref": "#/$defs/policy"}
            or schema["$defs"]["policy"].get("type") != "object"):
        _fail("schema_invalid")
    if schema["$defs"]["policy"].get("description") is None:
        _fail("schema_invalid")
    if any(type(item) is not str or not item.startswith("#/") for item in _refs(schema)):
        _fail("schema_invalid")


def _refs(value: object) -> list[object]:
    if type(value) is dict:
        return ([value["$ref"]] if "$ref" in value else []) + [ref for child in value.values() for ref in _refs(child)]
    if type(value) is list:
        return [ref for child in value for ref in _refs(child)]
    return []


def _exact_object(value: object, fields: frozenset[str], code: str,
                  optional: frozenset[str] = frozenset()) -> dict[str, object]:
    if type(value) is not dict or not fields <= set(value) or not set(value) <= fields | optional:
        _fail(code)
    return value


def _text(value: object, pattern: re.Pattern[str], code: str) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        _fail(code)
    return value


def _date(value: object) -> datetime:
    if type(value) is not str or not 1 <= len(value) <= 35 or DATE_RE.fullmatch(value) is None:
        _fail("invalid_created_at")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None or result.utcoffset() is None:
            raise ValueError
        return result
    except (ValueError, OverflowError):
        _fail("invalid_created_at")


def _identity_id(prefix: str, **fields: object) -> str:
    return deterministic_id(prefix, {"schema_version": SCHEMA_VERSION, **fields})


def _check_policy_records(records: list[object]) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for raw in records:
        if type(raw) is not dict:
            _fail("source_policy_invalid")
        try:
            validate_policy(raw)
        except PolicyValidationError:
            _fail("source_policy_invalid")
        ref = raw.get("source_id")
        if ref in result:
            _fail("duplicate_policy_reference")
        result[ref] = raw
    return result


def validate_manifest(manifest: object) -> dict[str, object]:
    """Check structure, cross-references and exact synthetic UTF-8 fixture bytes."""
    _schema_contract()
    if type(manifest) is not dict or set(manifest) != TOP_FIELDS:
        _fail("invalid_manifest_fields")
    if len(canonical_json_bytes(manifest)) > MAX_INPUT_BYTES:
        _fail("input_too_large")
    _check_depth(manifest)
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != SCHEMA_VERSION:
        _fail("unsupported_schema")
    if manifest["manifest_mode"] != "SYNTHETIC_OFFLINE":
        _fail("unsupported_manifest_mode")
    arrays = {
        "policies": (MAX_POLICIES, "empty_manifest"),
        "sources": (MAX_SOURCES, "empty_manifest"),
        "document_versions": (MAX_VERSIONS, "empty_manifest"),
        "chunks": (MAX_CHUNKS, "empty_manifest"),
    }
    for key, (limit, empty_code) in arrays.items():
        if type(manifest[key]) is not list:
            _fail("invalid_record_collection")
        if not manifest[key]:
            _fail(empty_code)
        if len(manifest[key]) > limit:
            _fail("record_limit_exceeded")

    policy_by_ref = _check_policy_records(manifest["policies"])
    content_integrity = True
    sources: dict[str, dict[str, object]] = {}
    for raw in manifest["sources"]:
        source = _exact_object(raw, SOURCE_FIELDS, "invalid_source_fields")
        if type(source["schema_version"]) is not int or source["schema_version"] != SCHEMA_VERSION:
            _fail("unsupported_schema")
        source_id = _text(source["source_id"], ID_RE, "invalid_source_id")
        if not source_id.startswith("src_"):
            _fail("invalid_source_id")
        if source_id in sources:
            _fail("duplicate_source_id")
        ref = _text(source["policy_reference"], SOURCE_REF_RE, "invalid_policy_reference")
        policy = policy_by_ref.get(ref)
        if policy is None:
            _fail("missing_policy_reference")
        tenant = _text(source["tenant_id"], SCOPE_RE, "invalid_tenant_scope")
        repository = _text(source["repository_id"], REPOSITORY_RE, "invalid_repository_scope")
        if (type(source["source_type"]) is not str or source["source_type"] not in SOURCE_TYPES
                or source["source_type"] != policy["source_type"]):
            _fail("source_policy_mismatch")
        if source["source_type"] != "synthetic_fixture":
            _fail("non_synthetic_source_not_supported")
        if tenant != policy["tenant_id"]:
            _fail("tenant_scope_mismatch")
        if repository != policy["repository_id"]:
            _fail("repository_scope_mismatch")
        if source["provenance"] != policy["provenance"]:
            _fail("provenance_mismatch")
        if type(source["source_status"]) is not str or source["source_status"] not in SOURCE_STATUSES:
            _fail("unknown_source_status")
        if source["source_status"] != "ACTIVE":
            _fail("source_not_active")
        expected = _identity_id("src", policy_reference=ref, tenant_id=tenant, repository_id=repository)
        if source_id != expected:
            _fail("source_id_mismatch")
        sources[source_id] = source

    versions: dict[str, dict[str, object]] = {}
    doc_identities: dict[str, tuple[str, str]] = {}
    version_dates: dict[str, datetime] = {}
    for raw in manifest["document_versions"]:
        version = _exact_object(raw, VERSION_FIELDS, "invalid_document_version_fields",
                                frozenset({"synthetic_content"}))
        source_id = _text(version["source_id"], ID_RE, "invalid_source_id")
        source = sources.get(source_id)
        if source is None:
            _fail("missing_source_reference")
        document_id = _text(version["document_id"], ID_RE, "invalid_document_id")
        if not document_id.startswith("doc_"):
            _fail("invalid_document_id")
        key = _text(version["document_key"], DOCUMENT_KEY_RE, "invalid_document_key")
        identity = (source_id, key)
        if document_id in doc_identities and doc_identities[document_id] != identity:
            _fail("duplicate_document_id")
        doc_identities[document_id] = identity
        tenant, repository = source["tenant_id"], source["repository_id"]
        if document_id != _identity_id("doc", source_id=source_id, tenant_id=tenant,
                                       repository_id=repository, document_key=key):
            _fail("document_id_mismatch")
        version_id = _text(version["version_id"], ID_RE, "invalid_version_id")
        if not version_id.startswith("ver_"):
            _fail("invalid_version_id")
        if version_id in versions:
            _fail("duplicate_version_id")
        digest = _text(version["content_sha256"], SHA256_RE, "invalid_content_sha256")
        content_type = version["content_type"]
        if type(content_type) is not str or content_type not in CONTENT_TYPES:
            _fail("invalid_content_type")
        if type(version["byte_size"]) is not int or not 1 <= version["byte_size"] <= MAX_CONTENT_BYTES:
            _fail("invalid_byte_size")
        if "synthetic_content" in version:
            content = version["synthetic_content"]
            if type(content) is not str:
                _fail("invalid_synthetic_content")
            raw_content = content.encode("utf-8")
            if not raw_content or len(raw_content) > MAX_CONTENT_BYTES:
                _fail("content_size_limit_exceeded")
            if version["byte_size"] != len(raw_content):
                _fail("byte_size_mismatch")
            if hashlib.sha256(raw_content).hexdigest() != digest:
                _fail("content_hash_mismatch")
        else:
            content_integrity = False
        created = _date(version["created_at"])
        previous = version["previous_version_id"]
        if previous is not None and (type(previous) is not str or ID_RE.fullmatch(previous) is None
                                     or not previous.startswith("ver_")):
            _fail("invalid_previous_version_id")
        expected = _identity_id("ver", document_id=document_id, content_sha256=digest,
                                 content_type=content_type)
        if version_id != expected:
            _fail("version_id_mismatch")
        versions[version_id] = version
        version_dates[version_id] = created

    for version in versions.values():
        previous = version["previous_version_id"]
        if previous is not None and previous not in versions:
            _fail("missing_previous_version")
        if previous is not None and versions[previous]["document_id"] != version["document_id"]:
            _fail("version_relationship_mismatch")
    successors: dict[str, str] = {}
    for version_id, version in versions.items():
        previous = version["previous_version_id"]
        if previous is not None:
            if previous in successors:
                _fail("branched_version_history")
            successors[previous] = version_id
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(version_id: str) -> None:
        if version_id in visiting:
            _fail("cyclic_version_relationship")
        if version_id in visited:
            return
        visiting.add(version_id)
        previous = versions[version_id]["previous_version_id"]
        if previous is not None:
            visit(previous)
            if version_dates[previous] >= version_dates[version_id]:
                _fail("invalid_version_order")
        visiting.remove(version_id)
        visited.add(version_id)

    for version_id in versions:
        visit(version_id)
    roots: dict[str, dict[str, object]] = {}
    for version in versions.values():
        if version["previous_version_id"] is None:
            doc_id = version["document_id"]
            if doc_id in roots:
                _fail("invalid_version_relationship")
            roots[doc_id] = version
    if set(roots) != set(doc_identities):
        _fail("invalid_version_relationship")
    source_documents: dict[str, set[str]] = {}
    for version in versions.values():
        source_documents.setdefault(version["source_id"], set()).add(version["document_id"])
    if any(len(document_ids) != 1 for document_ids in source_documents.values()):
        _fail("source_multiple_documents")
    for source_id, document_ids in source_documents.items():
        source = sources[source_id]
        policy = policy_by_ref[source["policy_reference"]]
        document_id = next(iter(document_ids))
        if policy["content_sha256"] != roots[document_id]["content_sha256"]:
            _fail("policy_content_hash_mismatch")

    chunks_by_version: dict[str, list[dict[str, object]]] = {}
    seen_chunks: set[str] = set()
    seen_positions: set[tuple[str, int]] = set()
    for raw in manifest["chunks"]:
        chunk = _exact_object(raw, CHUNK_FIELDS, "invalid_chunk_fields")
        chunk_id = _text(chunk["chunk_id"], ID_RE, "invalid_chunk_id")
        if not chunk_id.startswith("chunk_"):
            _fail("invalid_chunk_id")
        if chunk_id in seen_chunks:
            _fail("duplicate_chunk_id")
        seen_chunks.add(chunk_id)
        version_id = _text(chunk["version_id"], ID_RE, "invalid_version_id")
        version = versions.get(version_id)
        if version is None:
            _fail("missing_version_reference")
        document_id = _text(chunk["document_id"], ID_RE, "invalid_document_id")
        if document_id not in doc_identities:
            _fail("missing_document_reference")
        if document_id != version["document_id"]:
            _fail("document_version_mismatch")
        source = sources[version["source_id"]]
        if chunk["tenant_id"] != source["tenant_id"]:
            _fail("tenant_scope_mismatch")
        if chunk["repository_id"] != source["repository_id"]:
            _fail("repository_scope_mismatch")
        index = chunk["chunk_index"]
        if type(index) is not int or not 0 <= index < MAX_CHUNKS:
            _fail("invalid_chunk_index")
        position = (version_id, index)
        if position in seen_positions:
            _fail("duplicate_chunk_position")
        seen_positions.add(position)
        if chunk["offset_unit"] != "UTF8_BYTE":
            _fail("invalid_offset_unit")
        start, end = chunk["start_offset"], chunk["end_offset"]
        if (type(start) is not int or type(end) is not int or start < 0 or end <= start
                or end > version["byte_size"]):
            _fail("invalid_chunk_boundaries")
        content_hash = _text(chunk["content_sha256"], SHA256_RE, "invalid_chunk_content_sha256")
        if "synthetic_content" in version:
            raw_content = version["synthetic_content"].encode("utf-8")
            try:
                segment = raw_content[start:end]
                segment.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                _fail("invalid_utf8_boundary")
            if hashlib.sha256(segment).hexdigest() != content_hash:
                _fail("chunk_hash_mismatch")
        expected = _identity_id("chunk", version_id=version_id, chunk_index=index,
                                 start_offset=start, end_offset=end, offset_unit="UTF8_BYTE",
                                 content_sha256=content_hash)
        if chunk_id != expected:
            _fail("chunk_id_mismatch")
        chunks_by_version.setdefault(version_id, []).append(chunk)

    for version_id, version in versions.items():
        chunks = chunks_by_version.get(version_id, [])
        if not chunks:
            _fail("missing_version_chunks")
        chunks.sort(key=lambda item: item["chunk_index"])
        if [item["chunk_index"] for item in chunks] != list(range(len(chunks))):
            _fail("invalid_chunk_order")
        end = 0
        for chunk in chunks:
            if chunk["start_offset"] < end:
                _fail("overlapping_chunk_boundaries")
            end = chunk["end_offset"]
    used_sources = {version["source_id"] for version in versions.values()}
    if used_sources != set(sources):
        _fail("orphan_source")
    used_policies = {source["policy_reference"] for source in sources.values()}
    if used_policies != set(policy_by_ref):
        _fail("orphan_policy")

    canonical = canonical_manifest_bytes(manifest)
    return {
        "assurance": "STRUCTURE_AND_SYNTHETIC_CONTENT",
        "authorization_assurance": "STRUCTURE_ONLY",
        "content_integrity": "VERIFIED_SYNTHETIC_BYTES" if content_integrity else "UNVERIFIED_NO_CONTENT_BYTES",
        "decision": "PASS",
        "manifest_sha256": hashlib.sha256(canonical).hexdigest(),
        "schema_version": SCHEMA_VERSION,
        "counts": {"policies": len(policy_by_ref), "sources": len(sources),
                   "document_versions": len(versions), "chunks": len(seen_chunks)},
    }


def _read_manifest(path: Path) -> object:
    try:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            _fail("input_not_regular_file")
        if info.st_size > MAX_INPUT_BYTES:
            _fail("input_too_large")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                _fail("input_not_regular_file")
            raw = stream.read(MAX_INPUT_BYTES + 1)
    except ManifestValidationError:
        raise
    except OSError:
        _fail("input_unreadable")
    return _parse(raw, MAX_INPUT_BYTES)


def load_and_validate(path: Path) -> dict[str, object]:
    return validate_manifest(_read_manifest(Path(path)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="local synthetic JSON manifest")
    args = parser.parse_args(argv)
    try:
        report = load_and_validate(args.input)
    except ManifestValidationError as error:
        report = {"assurance": "STRUCTURE_AND_SYNTHETIC_CONTENT", "decision": "FAIL",
                  "errors": [error.code], "schema_version": SCHEMA_VERSION}
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())

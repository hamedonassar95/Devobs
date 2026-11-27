#!/usr/bin/env python3
"""Build deterministic KI-1 manifests from explicit synthetic UTF-8 inputs.

The command is offline and dry-run only. It reads only paths supplied by the
caller, emits metadata to stdout, and never persists source document bytes.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import statistics
import stat
import sys
import time
import tracemalloc
from typing import Any

try:
    from scripts.check_knowledge_source_policy import (
        MAX_INPUT_BYTES as KI0_MAX_POLICY_BYTES,
        PolicyValidationError,
        validate_policy,
    )
    from scripts.check_knowledge_source_manifest import (
        CONTENT_TYPES,
        MAX_CHUNKS as KI1_MAX_CHUNKS,
        MAX_CONTENT_BYTES as KI1_MAX_CONTENT_BYTES,
        MAX_INPUT_BYTES as KI1_MAX_MANIFEST_BYTES,
        MAX_VERSIONS as KI1_MAX_VERSIONS,
        ManifestValidationError,
        canonical_manifest_bytes,
        deterministic_id,
        validate_manifest,
    )
except ModuleNotFoundError:  # Direct `python3 scripts/knowledge_ingestion.py` invocation.
    from check_knowledge_source_policy import (
        MAX_INPUT_BYTES as KI0_MAX_POLICY_BYTES,
        PolicyValidationError,
        validate_policy,
    )
    from check_knowledge_source_manifest import (
        CONTENT_TYPES,
        MAX_CHUNKS as KI1_MAX_CHUNKS,
        MAX_CONTENT_BYTES as KI1_MAX_CONTENT_BYTES,
        MAX_INPUT_BYTES as KI1_MAX_MANIFEST_BYTES,
        MAX_VERSIONS as KI1_MAX_VERSIONS,
        ManifestValidationError,
        canonical_manifest_bytes,
        deterministic_id,
        validate_manifest,
    )


SCHEMA_VERSION = 1
MAX_DOCUMENT_BYTES = KI1_MAX_CONTENT_BYTES
MAX_CHUNKS = min(2048, KI1_MAX_CHUNKS)
MAX_CHUNK_TARGET_BYTES = 16_384
MAX_REQUEST_BYTES = 32_768
MAX_BENCHMARK_BYTES = 1_048_576
MAX_BENCHMARK_REPETITIONS = 20
DEFAULT_BENCHMARK_SIZES = (1024, 10_240, 102_400, 1_048_576)
MAX_BENCHMARK_SIZES = len(DEFAULT_BENCHMARK_SIZES)
MAX_ENGINE_DOCUMENTS = 100
DOCUMENT_KEY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z"
)
REQUEST_FIELDS = frozenset({
    "schema_version", "source_policy", "source_version", "document_key",
    "tenant_id", "repository_id", "content_type", "created_at", "chunking",
})
CHUNKING_FIELDS = frozenset({"target_chunk_bytes", "overlap_bytes", "max_chunks"})


class IngestionError(ValueError):
    """A bounded fixed error code; untrusted input is never included."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _fail(code: str) -> None:
    raise IngestionError(code)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    _fail("invalid_json_constant")


def _json_depth(value: object, maximum: int = 32) -> None:
    stack = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > maximum:
            _fail("input_too_deep")
        if type(current) is dict:
            stack.extend((item, depth + 1) for item in current.values())
        elif type(current) is list:
            stack.extend((item, depth + 1) for item in current)


def _parse_json(raw: bytes, maximum: int) -> object:
    if len(raw) > maximum:
        _fail("input_too_large")
    try:
        parsed = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except IngestionError:
        raise
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError):
        _fail("malformed_json")
    _json_depth(parsed)
    return parsed


def _canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        _fail("serialization_failed")


def canonical_result_bytes(result: "IngestionResult | dict[str, object]") -> bytes:
    """Serialize the content-free result deterministically as UTF-8 JSON."""
    value = result.to_dict() if isinstance(result, IngestionResult) else result
    return _canonical_json(value)


@dataclass(frozen=True)
class ChunkingConfig:
    """UTF-8 byte chunk limits compatible with the non-overlap KI-1 v1 schema."""

    target_chunk_bytes: int = 1024
    overlap_bytes: int = 0
    max_chunks: int = 2048

    def __post_init__(self) -> None:
        if (type(self.target_chunk_bytes) is not int
                or not 4 <= self.target_chunk_bytes <= MAX_CHUNK_TARGET_BYTES
                or type(self.overlap_bytes) is not int or self.overlap_bytes < 0
                or type(self.max_chunks) is not int or not 1 <= self.max_chunks <= MAX_CHUNKS):
            _fail("invalid_chunk_config")
        if self.overlap_bytes != 0:
            _fail("overlap_not_supported_by_ki1_v1")


@dataclass(frozen=True)
class IngestionResult:
    manifest: dict[str, object]
    report: dict[str, object]
    dry_run: bool = True

    def to_dict(self) -> dict[str, object]:
        return {"dry_run": self.dry_run, "manifest": self.manifest, "report": self.report}


def _timestamp(value: object) -> datetime:
    if type(value) is not str or len(value) > 35 or TIMESTAMP_RE.fullmatch(value) is None:
        _fail("invalid_created_at")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
        return parsed
    except (ValueError, OverflowError):
        _fail("invalid_created_at")


def _validate_request_fields(
    source_policy: object,
    document_bytes: object,
    source_version: object,
    document_key: object,
    tenant_id: object,
    repository_id: object,
    content_type: object,
    created_at: object,
    chunking: ChunkingConfig,
) -> tuple[dict[str, object], bytes, str, str, str, str, str, datetime]:
    if type(document_bytes) is not bytes:
        _fail("invalid_document_bytes")
    if not document_bytes:
        _fail("empty_document")
    if len(document_bytes) > MAX_DOCUMENT_BYTES:
        _fail("document_too_large")
    try:
        document_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        _fail("invalid_utf8")
    if type(content_type) is not str or content_type not in CONTENT_TYPES:
        _fail("unsupported_content_type")
    if type(document_key) is not str or DOCUMENT_KEY_RE.fullmatch(document_key) is None:
        _fail("invalid_document_key")
    if type(source_version) is not str or not 1 <= len(source_version) <= 128:
        _fail("invalid_source_version")
    if type(tenant_id) is not str or not tenant_id or len(tenant_id) > 128:
        _fail("invalid_tenant_scope")
    if type(repository_id) is not str or not repository_id or len(repository_id) > 201:
        _fail("invalid_repository_scope")
    if not isinstance(chunking, ChunkingConfig):
        _fail("invalid_chunk_config")
    try:
        validate_policy(source_policy)
    except PolicyValidationError:
        _fail("source_policy_invalid")
    if type(source_policy) is not dict:
        _fail("source_policy_invalid")
    if source_policy.get("source_type") != "synthetic_fixture":
        _fail("non_synthetic_source_not_supported")
    if source_policy.get("source_version") != source_version:
        _fail("source_version_mismatch")
    if source_policy.get("tenant_id") != tenant_id:
        _fail("tenant_scope_mismatch")
    if source_policy.get("repository_id") != repository_id:
        _fail("repository_scope_mismatch")
    timestamp = _timestamp(created_at)
    return (
        source_policy, document_bytes, source_version, document_key,
        tenant_id, repository_id, content_type, timestamp,
    )


def _chunk_document(content: bytes, config: ChunkingConfig) -> list[dict[str, object]]:
    """Partition exact UTF-8 bytes into contiguous, non-overlapping spans."""
    chunks: list[dict[str, object]] = []
    start = 0
    while start < len(content):
        candidate = min(start + config.target_chunk_bytes, len(content))
        end = candidate
        if end < len(content):
            # Move left to a UTF-8 leading-byte boundary. The start is always a
            # verified boundary from the preceding iteration.
            while end > start and content[end] & 0b1100_0000 == 0b1000_0000:
                end -= 1
        if end <= start:
            _fail("chunk_size_cannot_fit_codepoint")
        try:
            content[start:end].decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            _fail("invalid_utf8_boundary")
        chunks.append({
            "start_offset": start,
            "end_offset": end,
            "content_sha256": hashlib.sha256(content[start:end]).hexdigest(),
        })
        if len(chunks) > config.max_chunks:
            _fail("chunk_count_limit_exceeded")
        start = end
    if not chunks:
        _fail("empty_document")
    return chunks


def _source_record_id(policy: dict[str, object], tenant_id: str, repository_id: str) -> str:
    return deterministic_id("src", {
        "schema_version": SCHEMA_VERSION,
        "policy_reference": policy["source_id"],
        "tenant_id": tenant_id,
        "repository_id": repository_id,
    })


def _document_record_id(source_id: str, tenant_id: str, repository_id: str, document_key: str) -> str:
    return deterministic_id("doc", {
        "schema_version": SCHEMA_VERSION,
        "source_id": source_id,
        "tenant_id": tenant_id,
        "repository_id": repository_id,
        "document_key": document_key,
    })


def _version_record_id(document_id: str, digest: str, content_type: str) -> str:
    return deterministic_id("ver", {
        "schema_version": SCHEMA_VERSION,
        "document_id": document_id,
        "content_sha256": digest,
        "content_type": content_type,
    })


def _latest_version_id(versions: list[dict[str, object]]) -> str | None:
    referenced = {version["previous_version_id"] for version in versions
                  if version["previous_version_id"] is not None}
    candidates = [version["version_id"] for version in versions
                  if version["version_id"] not in referenced]
    if len(candidates) > 1:
        _fail("invalid_version_history")
    return candidates[0] if candidates else None


def _strip_document_content(manifest: dict[str, object]) -> dict[str, object]:
    result = deepcopy(manifest)
    for version in result.get("document_versions", []):
        version.pop("synthetic_content", None)
    return result


class KnowledgeIngestionEngine:
    """Deterministic in-memory dry-run engine; no durable content is retained."""

    def __init__(self) -> None:
        self._documents: dict[tuple[str, str, str], dict[str, object]] = {}
        self._sources: dict[tuple[str, str, str], dict[str, object]] = {}
        self._source_uris: dict[tuple[str, str, str], str] = {}
        self._source_documents: dict[tuple[str, str, str], tuple[str, str, str]] = {}

    @classmethod
    def from_manifest(cls, manifest: object) -> "KnowledgeIngestionEngine":
        """Restore explicitly supplied metadata history after KI-1 validation."""
        if type(manifest) is not dict:
            _fail("invalid_history_manifest")
        try:
            validation = validate_manifest(manifest)
        except ManifestValidationError as error:
            _fail(error.code)
        metadata = _strip_document_content(manifest)
        try:
            validate_manifest(metadata)
        except ManifestValidationError as error:
            _fail(error.code)
        policies = metadata["policies"]
        sources = metadata["sources"]
        versions = metadata["document_versions"]
        if len(policies) != 1 or len(sources) != 1 or not versions:
            _fail("unsupported_history_shape")
        policy = policies[0]
        source = sources[0]
        if policy.get("source_type") != "synthetic_fixture" or source.get("source_status") != "ACTIVE":
            _fail("history_source_not_active")
        document_key = versions[0]["document_key"]
        document_ids = {version["document_id"] for version in versions}
        if len(document_ids) != 1 or any(version["document_key"] != document_key for version in versions):
            _fail("unsupported_history_shape")
        engine = cls()
        tenant_id = source["tenant_id"]
        repository_id = source["repository_id"]
        source_key = (tenant_id, repository_id, policy["source_id"])
        uri_key = (tenant_id, repository_id, policy["source_uri"])
        document_key_tuple = (tenant_id, repository_id, document_key)
        engine._sources[source_key] = {"policy": deepcopy(policy), "state": "ACTIVE",
                                       "source_record": deepcopy(source)}
        engine._source_uris[uri_key] = policy["source_id"]
        engine._source_documents[source_key] = document_key_tuple
        engine._documents[document_key_tuple] = {
            "source_key": source_key,
            "source_uri_key": uri_key,
            "document_key": document_key,
            "manifest": metadata,
            "state": "ACTIVE",
            "validation": validation,
        }
        return engine

    def ingest_document(
        self,
        source_policy: object,
        document_bytes: object,
        source_version: object,
        document_key: object,
        tenant_id: object,
        repository_id: object,
        content_type: object,
        created_at: object,
        chunking: ChunkingConfig | None = None,
    ) -> IngestionResult:
        config = chunking if chunking is not None else ChunkingConfig()
        (
            policy, content, source_version, document_key,
            tenant_id, repository_id, content_type, parsed_time,
        ) = _validate_request_fields(
            source_policy, document_bytes, source_version, document_key, tenant_id,
            repository_id, content_type, created_at, config,
        )
        digest = hashlib.sha256(content).hexdigest()
        source_key = (tenant_id, repository_id, policy["source_id"])
        uri_key = (tenant_id, repository_id, policy["source_uri"])
        document_scope = (tenant_id, repository_id, document_key)
        source_state = self._sources.get(source_key)
        existing = self._documents.get(document_scope)
        registered_source = self._source_uris.get(uri_key)
        registered_document = self._source_documents.get(source_key)

        if existing is not None and existing["state"] == "DELETED":
            _fail("document_deleted")
        if registered_document is not None and registered_document != document_scope:
            _fail("source_document_conflict")
        if existing is None and len(self._documents) >= MAX_ENGINE_DOCUMENTS:
            _fail("engine_document_limit_exceeded")
        if source_state is not None and source_state["state"] == "REVOKED":
            _fail("source_revoked")
        if source_state is not None and source_state["state"] == "DELETED":
            _fail("source_deleted")
        if registered_source is not None and registered_source != policy["source_id"]:
            _fail("source_identity_conflict")
        if existing is not None and existing["state"] != "ACTIVE":
            _fail("source_revoked")
        if existing is not None and existing["source_key"] != source_key:
            _fail("document_identity_conflict")
        if source_state is not None and _canonical_json(source_state["policy"]) != _canonical_json(policy):
            _fail("source_policy_conflict")
        if existing is not None:
            manifest = deepcopy(existing["manifest"])
        else:
            if policy["content_sha256"] != digest:
                _fail("policy_content_hash_mismatch")
            manifest = {
                "schema_version": SCHEMA_VERSION,
                "manifest_mode": "SYNTHETIC_OFFLINE",
                "policies": [deepcopy(policy)],
                "sources": [{
                    "schema_version": SCHEMA_VERSION,
                    "source_id": _source_record_id(policy, tenant_id, repository_id),
                    "source_type": "synthetic_fixture",
                    "tenant_id": tenant_id,
                    "repository_id": repository_id,
                    "policy_reference": policy["source_id"],
                    "provenance": deepcopy(policy["provenance"]),
                    "source_status": "ACTIVE",
                }],
                "document_versions": [],
                "chunks": [],
            }

        source_id = manifest["sources"][0]["source_id"]
        document_id = _document_record_id(source_id, tenant_id, repository_id, document_key)
        existing_versions = manifest["document_versions"]
        if existing_versions and any(version["document_id"] != document_id
                                     or version["document_key"] != document_key
                                     for version in existing_versions):
            _fail("document_identity_conflict")
        version_id = _version_record_id(document_id, digest, content_type)
        duplicate = next((version for version in existing_versions
                          if version["version_id"] == version_id), None)
        if duplicate is not None:
            validation = validate_manifest(manifest)
            report = self._report("DUPLICATE", source_version, digest, validation, config)
            return IngestionResult(manifest=manifest, report=report)
        if len(existing_versions) >= KI1_MAX_VERSIONS:
            _fail("version_count_limit_exceeded")
        if existing_versions:
            previous_id = _latest_version_id(existing_versions)
            prior = next((version for version in existing_versions
                          if version["version_id"] == previous_id), None)
            if prior is None or _timestamp(prior["created_at"]) >= parsed_time:
                _fail("invalid_version_order")
        else:
            previous_id = None
        new_chunks = _chunk_document(content, config)
        if len(manifest["chunks"]) + len(new_chunks) > KI1_MAX_CHUNKS:
            _fail("manifest_chunk_limit_exceeded")
        if len(new_chunks) > config.max_chunks:
            _fail("chunk_count_limit_exceeded")
        version = {
            "document_id": document_id,
            "source_id": source_id,
            "version_id": version_id,
            "document_key": document_key,
            "content_sha256": digest,
            "content_type": content_type,
            "byte_size": len(content),
            "created_at": created_at,
            "previous_version_id": previous_id,
            "synthetic_content": content.decode("utf-8", errors="strict"),
        }
        # All emitted chunks belong to this new version; this explicit index
        # is stable and begins at zero for every document revision.
        for index, chunk in enumerate(new_chunks):
            chunk_id = deterministic_id("chunk", {
                "schema_version": SCHEMA_VERSION,
                "version_id": version_id,
                "chunk_index": index,
                "start_offset": chunk["start_offset"],
                "end_offset": chunk["end_offset"],
                "offset_unit": "UTF8_BYTE",
                "content_sha256": chunk["content_sha256"],
            })
            manifest["chunks"].append({
                "chunk_id": chunk_id,
                "document_id": document_id,
                "version_id": version_id,
                "chunk_index": index,
                "content_sha256": chunk["content_sha256"],
                "start_offset": chunk["start_offset"],
                "end_offset": chunk["end_offset"],
                "offset_unit": "UTF8_BYTE",
                "tenant_id": tenant_id,
                "repository_id": repository_id,
            })
        manifest["document_versions"].append(version)
        manifest_bytes = canonical_manifest_bytes(manifest)
        if len(manifest_bytes) > KI1_MAX_MANIFEST_BYTES:
            _fail("manifest_too_large")
        try:
            validate_manifest(manifest)
            metadata_manifest = _strip_document_content(manifest)
            metadata_validation = validate_manifest(metadata_manifest)
        except ManifestValidationError as error:
            _fail(error.code)

        operation = "CREATED" if existing is None else "VERSION_ADDED"
        report = self._report(operation, source_version, digest, metadata_validation, config)
        document_record = {
            "source_key": source_key,
            "source_uri_key": uri_key,
            "document_key": document_key,
            "manifest": metadata_manifest,
            "state": "ACTIVE",
            "validation": metadata_validation,
        }
        if existing is None:
            self._sources[source_key] = {"policy": deepcopy(policy), "state": "ACTIVE",
                                         "source_record": deepcopy(metadata_manifest["sources"][0])}
            self._source_uris[uri_key] = policy["source_id"]
            self._source_documents[source_key] = document_scope
        self._documents[document_scope] = document_record
        return IngestionResult(manifest=metadata_manifest, report=report)

    @staticmethod
    def _report(
        operation: str,
        source_version: str,
        digest: str,
        validation: dict[str, object],
        chunking: ChunkingConfig,
    ) -> dict[str, object]:
        validation_summary = deepcopy(validation)
        if validation_summary.get("content_integrity") == "UNVERIFIED_NO_CONTENT_BYTES":
            # KI-1's v1 assurance label is broader than a metadata-only result.
            # Keep its explicit integrity value and narrow the surfaced label.
            validation_summary["assurance"] = "STRUCTURE_ONLY"
        return {
            "schema_version": SCHEMA_VERSION,
            "decision": "PASS",
            "operation": operation,
            "dry_run": True,
            "persistence": "NONE",
            "document_content_persisted": False,
            "lifecycle_assurance": "IN_MEMORY_ONLY",
            "authorization_assurance": "STRUCTURE_ONLY",
            "source_version": source_version,
            "input_content_sha256": digest,
            "input_content_verification": "VERIFIED_IN_MEMORY",
            "manifest_validation": validation_summary,
            "chunking": {
                "target_chunk_bytes": chunking.target_chunk_bytes,
                "overlap_bytes": chunking.overlap_bytes,
                "offset_unit": "UTF8_BYTE",
            },
        }

    def get_manifest(
        self, tenant_id: str, repository_id: str, document_key: str,
    ) -> dict[str, object] | None:
        record = self._documents.get((tenant_id, repository_id, document_key))
        if record is None or record["state"] != "ACTIVE":
            return None
        source_state = self._sources.get(record["source_key"])
        if source_state is None or source_state["state"] != "ACTIVE":
            return None
        return deepcopy(record["manifest"])

    def delete_document(self, tenant_id: str, repository_id: str, document_key: str) -> None:
        record = self._documents.get((tenant_id, repository_id, document_key))
        if record is None:
            _fail("document_not_found")
        if record["state"] != "ACTIVE":
            _fail("invalid_lifecycle_transition")
        source = self._sources.get(record["source_key"])
        if source is None or source["state"] != "ACTIVE":
            _fail("invalid_lifecycle_transition")
        record["state"] = "DELETED"
        source["state"] = "DELETED"

    def revoke_source(self, tenant_id: str, repository_id: str, policy_source_id: str) -> None:
        source_key = (tenant_id, repository_id, policy_source_id)
        source = self._sources.get(source_key)
        if source is None:
            _fail("source_not_found")
        if source["state"] != "ACTIVE":
            _fail("invalid_lifecycle_transition")
        source["state"] = "REVOKED"
        for record in self._documents.values():
            if record["source_key"] == source_key:
                record["state"] = "REVOKED"


def _request_object(value: object) -> dict[str, object]:
    if type(value) is not dict or set(value) != REQUEST_FIELDS:
        _fail("invalid_request_fields")
    if type(value["schema_version"]) is not int or value["schema_version"] != SCHEMA_VERSION:
        _fail("unsupported_request_schema")
    chunking = value["chunking"]
    if type(chunking) is not dict or set(chunking) != CHUNKING_FIELDS:
        _fail("invalid_chunk_config")
    return value


def _read_regular_file(path: Path, limit: int) -> bytes:
    try:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            _fail("input_not_regular_file")
        if info.st_size > limit:
            _fail("input_too_large")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                _fail("input_not_regular_file")
            data = stream.read(limit + 1)
    except IngestionError:
        raise
    except OSError:
        _fail("input_unreadable")
    if len(data) > limit:
        _fail("input_too_large")
    return data


def _cli_ingest(args: argparse.Namespace) -> int:
    request_value = _parse_json(_read_regular_file(args.request, MAX_REQUEST_BYTES), MAX_REQUEST_BYTES)
    request = _request_object(request_value)
    content = _read_regular_file(args.document, MAX_DOCUMENT_BYTES)
    if args.history is None:
        engine = KnowledgeIngestionEngine()
    else:
        history_value = _parse_json(_read_regular_file(args.history, KI1_MAX_MANIFEST_BYTES),
                                    KI1_MAX_MANIFEST_BYTES)
        engine = KnowledgeIngestionEngine.from_manifest(history_value)
    result = engine.ingest_document(
        source_policy=request["source_policy"],
        document_bytes=content,
        source_version=request["source_version"],
        document_key=request["document_key"],
        tenant_id=request["tenant_id"],
        repository_id=request["repository_id"],
        content_type=request["content_type"],
        created_at=request["created_at"],
        chunking=ChunkingConfig(**request["chunking"]),
    )
    print(canonical_result_bytes(result).decode("utf-8"))
    return 0


def _synthetic_benchmark_policy(content: bytes, size: int) -> dict[str, object]:
    source_id = f"synthetic-benchmark-{size}"
    return {
        "schema_version": 1,
        "source_id": source_id,
        "source_type": "synthetic_fixture",
        "source_version": "benchmark-policy-v1",
        "source_uri": f"fixture://{source_id}",
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "tenant_id": "synthetic-benchmark-tenant",
        "repository_id": "synthetic-benchmark-org/synthetic-benchmark-repo",
        "owner_id": "synthetic-benchmark-owner",
        "classification": "INTERNAL",
        "license_status": "NOT_APPLICABLE",
        "ingestion_authorized": True,
        "retention_policy": {"mode": "EPHEMERAL_TEST", "max_age_seconds": 3600},
        "deletion_policy": "DELETE_ON_COMPLETION",
        "provenance": {
            "recorded_at": "2026-11-27T00:00:00Z",
            "recorded_by": "synthetic-benchmark-runner",
            "approval_reference": "synthetic-benchmark-only",
        },
        "approval_status": "APPROVED",
    }


def run_benchmark(
    sizes: tuple[int, ...] | list[int] = DEFAULT_BENCHMARK_SIZES,
    repetitions: int = 5,
) -> dict[str, object]:
    """Measure only full-pipeline sizes accepted by KI-1; report larger sizes blocked."""
    if type(repetitions) is not int or not 1 <= repetitions <= MAX_BENCHMARK_REPETITIONS:
        _fail("invalid_benchmark_repetitions")
    if (type(sizes) not in (tuple, list) or not sizes
            or len(sizes) > MAX_BENCHMARK_SIZES or len(set(sizes)) != len(sizes)):
        _fail("invalid_benchmark_sizes")
    if any(type(size) is not int or not 1 <= size <= MAX_BENCHMARK_BYTES for size in sizes):
        _fail("invalid_benchmark_sizes")
    measurements: list[dict[str, object]] = []
    for size in sizes:
        if size > MAX_DOCUMENT_BYTES:
            measurements.append({
                "document_bytes": size,
                "status": "BLOCKED_BY_KI1_CONTENT_LIMIT",
                "limit_bytes": MAX_DOCUMENT_BYTES,
            })
            continue
        content = b"K" * size
        policy = _synthetic_benchmark_policy(content, size)
        request_args = {
            "source_policy": policy,
            "document_bytes": content,
            "source_version": policy["source_version"],
            "document_key": f"benchmark-document-{size}",
            "tenant_id": policy["tenant_id"],
            "repository_id": policy["repository_id"],
            "content_type": "text/plain; charset=utf-8",
            "created_at": "2026-11-27T00:00:00Z",
            "chunking": ChunkingConfig(),
        }
        processing_samples: list[float] = []
        validation_samples: list[float] = []
        peak_allocations: list[int] = []
        last_result: IngestionResult | None = None
        for _ in range(repetitions):
            engine = KnowledgeIngestionEngine()
            tracemalloc.start()
            started = time.perf_counter()
            result = engine.ingest_document(**request_args)
            if not isinstance(result, IngestionResult):
                _fail("benchmark_measurement_missing")
            processing_samples.append(time.perf_counter() - started)
            _current, peak = tracemalloc.get_traced_memory()
            peak_allocations.append(peak)
            tracemalloc.stop()
            started = time.perf_counter()
            validate_manifest(result.manifest)
            validation_samples.append(time.perf_counter() - started)
            last_result = result
        if last_result is None:
            _fail("benchmark_measurement_missing")
        measurements.append({
            "document_bytes": size,
            "status": "MEASURED",
            "sample_count": repetitions,
            "chunk_count": len(last_result.manifest["chunks"]),
            "processing_seconds_median": statistics.median(processing_samples),
            "processing_seconds_mean": statistics.fmean(processing_samples),
            "manifest_validation_seconds_median": statistics.median(validation_samples),
            "peak_python_allocation_bytes": max(peak_allocations),
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "measurement_mode": "SYNTHETIC_LOCAL_DRY_RUN",
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "architecture": platform.machine(),
        "document_limit_bytes": MAX_DOCUMENT_BYTES,
        "measurements": measurements,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    ingest_parser = commands.add_parser("ingest", help="validate one explicit synthetic document")
    ingest_parser.add_argument("--request", required=True, type=Path)
    ingest_parser.add_argument("--document", required=True, type=Path)
    ingest_parser.add_argument("--history", type=Path,
                               help="optional explicit metadata-only KI-1 history manifest")
    benchmark_parser = commands.add_parser("benchmark", help="measure bounded synthetic ingestion")
    benchmark_parser.add_argument("--repetitions", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "ingest":
            return _cli_ingest(args)
        if args.command == "benchmark":
            print(_canonical_json(run_benchmark(repetitions=args.repetitions)).decode("utf-8"))
            return 0
        _fail("unsupported_command")
    except IngestionError as error:
        print(_canonical_json({
            "schema_version": SCHEMA_VERSION,
            "decision": "FAIL",
            "errors": [error.code],
        }).decode("utf-8"))
        return 1
    except PolicyValidationError:
        print(_canonical_json({
            "schema_version": SCHEMA_VERSION,
            "decision": "FAIL",
            "errors": ["source_policy_invalid"],
        }).decode("utf-8"))
        return 1
    except ManifestValidationError as error:
        print(_canonical_json({
            "schema_version": SCHEMA_VERSION,
            "decision": "FAIL",
            "errors": [error.code],
        }).decode("utf-8"))
        return 1


if __name__ == "__main__":
    sys.exit(main())

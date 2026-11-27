#!/usr/bin/env python3
"""Deterministic, local-only BM25 retrieval over validated KI-2 records.

This module is a synthetic-data research baseline, not an authorization service
or runtime API. Search normalization is transient and never changes source
bytes, hashes, or KI-1 UTF-8 byte offsets.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import math
import re
import unicodedata
from typing import Mapping, Sequence

try:
    from scripts.check_knowledge_source_manifest import (
        MAX_CHUNKS,
        MAX_CONTENT_BYTES,
        ManifestValidationError,
        validate_manifest,
    )
    from scripts.check_knowledge_source_policy import PolicyValidationError, validate_policy
    from scripts.knowledge_ingestion import IngestionError, KnowledgeIngestionEngine
except ModuleNotFoundError:  # Direct `python3 scripts/knowledge_retrieval.py` invocation.
    from check_knowledge_source_manifest import (
        MAX_CHUNKS,
        MAX_CONTENT_BYTES,
        ManifestValidationError,
        validate_manifest,
    )
    from check_knowledge_source_policy import PolicyValidationError, validate_policy
    from knowledge_ingestion import IngestionError, KnowledgeIngestionEngine

DEFAULT_K1 = 1.2
DEFAULT_B = 0.75
DEFAULT_TOP_K = 5
MAX_TOP_K = 20
MAX_QUERY_BYTES = 4096
MAX_CORPUS_RECORDS = 100
MAX_CORPUS_CHUNKS = MAX_CHUNKS
_TENANT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_REPOSITORY_RE = re.compile(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}\Z")
_RECORD_FIELDS = frozenset({"policy", "manifest", "content_by_version", "lifecycle_state"})
_RESULT_FIELDS = frozenset({
    "rank", "lexical_score", "source_id", "document_id", "version_id", "chunk_id",
    "content_sha256", "start_offset", "end_offset", "offset_unit", "provenance_reference",
})
_LIFECYCLE_STATES = frozenset({"ACTIVE", "REVOKED", "DELETED"})


class RetrievalError(ValueError):
    """Fixed validation code; never includes caller-supplied source content."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _fail(code: str) -> None:
    raise RetrievalError(code)


def tokenize(text: str) -> list[str]:
    """NFKC/casefold search tokens; retain Unicode letters, marks and numbers.

    This is deliberately lexical: it does not stem, lemmatize, strip Arabic
    diacritics, or rewrite source bytes.
    """
    if type(text) is not str:
        _fail("invalid_text")
    normalized = unicodedata.normalize("NFKC", text).casefold()
    tokens: list[str] = []
    current: list[str] = []
    for character in normalized:
        category = unicodedata.category(character)
        if category[0] in {"L", "M", "N"}:
            current.append(character)
        elif current:
            tokens.append("".join(current))
            current.clear()
    if current:
        tokens.append("".join(current))
    return tokens


@dataclass(frozen=True)
class _Chunk:
    chunk_id: str
    source_id: str
    document_id: str
    document_key: str
    version_id: str
    content_sha256: str
    start_offset: int
    end_offset: int
    offset_unit: str
    provenance_reference: str
    terms: tuple[str, ...]
    term_frequency: Mapping[str, int]
    tenant_id: str
    repository_id: str


def _scope_from_record(record: object) -> tuple[dict[str, object], dict[str, object], str, str]:
    if type(record) is not dict or set(record) != _RECORD_FIELDS:
        _fail("invalid_record_fields")
    policy = record.get("policy")
    manifest = record.get("manifest")
    if type(policy) is not dict or type(manifest) is not dict:
        _fail("missing_policy_or_manifest")
    sources = manifest.get("sources")
    if type(sources) is not list or len(sources) != 1 or type(sources[0]) is not dict:
        _fail("invalid_source_scope")
    tenant_policy, repo_policy = policy.get("tenant_id"), policy.get("repository_id")
    tenant_source, repo_source = sources[0].get("tenant_id"), sources[0].get("repository_id")
    if (type(tenant_policy) is not str or _TENANT_RE.fullmatch(tenant_policy) is None
            or type(tenant_source) is not str or _TENANT_RE.fullmatch(tenant_source) is None
            or type(repo_policy) is not str or _REPOSITORY_RE.fullmatch(repo_policy) is None
            or type(repo_source) is not str or _REPOSITORY_RE.fullmatch(repo_source) is None):
        _fail("missing_or_invalid_scope")
    if (tenant_policy, repo_policy) != (tenant_source, repo_source):
        _fail("scope_conflict")
    return policy, manifest, tenant_policy, repo_policy


def _validate_record(record: object) -> tuple[list[_Chunk], str, str, str]:
    policy, manifest, tenant_id, repository_id = _scope_from_record(record)
    if policy.get("source_type") != "synthetic_fixture":
        _fail("non_synthetic_source_not_supported")
    try:
        validate_manifest(manifest)
    except ManifestValidationError:
        _fail("manifest_or_lifecycle_invalid")

    content_by_version = record.get("content_by_version")
    if type(content_by_version) is not dict:
        _fail("content_bytes_required")
    versions = manifest.get("document_versions")
    if type(versions) is not list or not versions or len(versions) > 500:
        _fail("invalid_document_versions")
    version_ids = {item.get("version_id") for item in versions if type(item) is dict}
    if len(version_ids) != len(versions) or set(content_by_version) != version_ids:
        _fail("content_version_references_mismatch")

    full_manifest = {
        key: value.copy() if type(value) is dict else list(value) if type(value) is list else value
        for key, value in manifest.items()
    }
    full_versions = []
    decoded_by_version: dict[str, bytes] = {}
    for version in full_manifest.get("document_versions", []):
        if type(version) is not dict or type(version.get("version_id")) is not str:
            _fail("invalid_document_version")
        version_id = version["version_id"]
        raw = content_by_version[version_id]
        if type(raw) is not bytes or not raw or len(raw) > MAX_CONTENT_BYTES:
            _fail("invalid_content_bytes")
        try:
            decoded = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            _fail("invalid_utf8_content")
        copied_version = version.copy()
        copied_version["synthetic_content"] = decoded
        full_versions.append(copied_version)
        decoded_by_version[version_id] = raw
    full_manifest["document_versions"] = full_versions

    try:
        validation = validate_manifest(full_manifest)
        # KI-2 owns the in-memory lifecycle behavior and revalidates its
        # content-free manifest through KI-1 before it can be queried.
        lifecycle = KnowledgeIngestionEngine.from_manifest(manifest)
    except (ManifestValidationError, IngestionError):
        _fail("manifest_or_lifecycle_invalid")
    if validation.get("decision") != "PASS":
        _fail("manifest_validation_failed")

    policy_records = manifest.get("policies")
    source_records = manifest.get("sources")
    if (type(policy_records) is not list or len(policy_records) != 1
            or policy_records[0] != policy or type(source_records) is not list
            or source_records[0].get("policy_reference") != policy.get("source_id")):
        _fail("policy_reference_mismatch")
    source = source_records[0]
    state = record.get("lifecycle_state")
    if type(state) is not str or state not in _LIFECYCLE_STATES:
        _fail("lifecycle_state_invalid")
    document_keys = {version.get("document_key") for version in versions}
    if len(document_keys) != 1:
        _fail("unsupported_document_history")
    document_key = next(iter(document_keys))
    try:
        if state == "REVOKED":
            lifecycle.revoke_source(tenant_id, repository_id, policy["source_id"])
        elif state == "DELETED":
            lifecycle.delete_document(tenant_id, repository_id, document_key)
        active_manifest = lifecycle.get_manifest(tenant_id, repository_id, document_key)
    except IngestionError:
        _fail("lifecycle_transition_invalid")
    if active_manifest is None:
        return [], tenant_id, repository_id, document_key

    # The KI-1 version chain is validated above. Index only its single current
    # leaf, preventing stale versions from competing with current evidence.
    previous_ids = {version.get("previous_version_id") for version in versions
                    if version.get("previous_version_id") is not None}
    latest = [version for version in versions if version.get("version_id") not in previous_ids]
    if len(latest) != 1:
        _fail("invalid_latest_version")
    current = latest[0]
    raw = decoded_by_version[current["version_id"]]
    source_provenance = source.get("provenance")
    if type(source_provenance) is not dict:
        _fail("provenance_missing")
    provenance_reference = source_provenance.get("approval_reference")
    if type(provenance_reference) is not str or not provenance_reference:
        _fail("provenance_missing")
    chunks = manifest.get("chunks")
    if type(chunks) is not list or len(chunks) > MAX_CHUNKS:
        _fail("invalid_chunks")
    selected: list[_Chunk] = []
    for chunk in chunks:
        if chunk.get("version_id") != current["version_id"]:
            continue
        start, end = chunk.get("start_offset"), chunk.get("end_offset")
        if (chunk.get("document_id") != current.get("document_id")
                or chunk.get("tenant_id") != tenant_id
                or chunk.get("repository_id") != repository_id
                or chunk.get("offset_unit") != "UTF8_BYTE"
                or type(start) is not int or type(end) is not int
                or not 0 <= start < end <= len(raw)):
            _fail("chunk_scope_or_boundary_invalid")
        chunk_bytes = raw[start:end]
        if hashlib.sha256(chunk_bytes).hexdigest() != chunk.get("content_sha256"):
            _fail("chunk_integrity_invalid")
        try:
            text = chunk_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            _fail("chunk_utf8_boundary_invalid")
        terms = tokenize(text)
        selected.append(_Chunk(
            chunk_id=chunk["chunk_id"],
            source_id=current["source_id"],
            document_id=current["document_id"],
            document_key=document_key,
            version_id=current["version_id"],
            content_sha256=chunk["content_sha256"],
            start_offset=start,
            end_offset=end,
            offset_unit="UTF8_BYTE",
            provenance_reference=provenance_reference,
            terms=tuple(terms),
            term_frequency=Counter(terms),
            tenant_id=tenant_id,
            repository_id=repository_id,
        ))
    if not selected:
        _fail("current_version_has_no_chunks")
    return selected, tenant_id, repository_id, document_key


class LexicalIndex:
    """Immutable in-memory BM25 index for one declared tenant/repository scope."""

    def __init__(
        self,
        chunks: Sequence[_Chunk],
        *,
        tenant_id: str,
        repository_id: str,
        k1: float,
        b: float,
        top_k: int,
        excluded_scope_count: int = 0,
    ) -> None:
        self._chunks = tuple(sorted(chunks, key=lambda item: item.chunk_id))
        self.tenant_id = tenant_id
        self.repository_id = repository_id
        self.k1 = float(k1)
        self.b = float(b)
        self.top_k = top_k
        self._document_frequency: Counter[str] = Counter()
        postings: dict[str, list[_Chunk]] = {}
        for chunk in self._chunks:
            for term in set(chunk.terms):
                self._document_frequency[term] += 1
                postings.setdefault(term, []).append(chunk)
        self._inverted_index = {
            term: tuple(sorted(term_chunks, key=lambda item: item.chunk_id))
            for term, term_chunks in postings.items()
        }
        self._average_document_length = (
            sum(len(chunk.terms) for chunk in self._chunks) / len(self._chunks)
            if self._chunks else 0.0
        )
        self._chunks_by_id = {chunk.chunk_id: chunk for chunk in self._chunks}
        self._excluded_scope_count = excluded_scope_count

    @property
    def statistics(self) -> dict[str, int | float]:
        """Safe index counts; out-of-scope records are deliberately omitted."""
        return {
            "document_count": len(self._chunks),
            "vocabulary_size": len(self._document_frequency),
            "average_document_length": self._average_document_length,
            "chunk_count": len(self._chunks),
        }

    def _score(self, query: str | Sequence[str], chunk: _Chunk) -> float:
        query_terms = tokenize(query) if isinstance(query, str) else list(query)
        total = 0.0
        count = len(self._chunks)
        for term in query_terms:
            tf = chunk.term_frequency.get(term, 0)
            if tf == 0:
                continue
            df = self._document_frequency.get(term, 0)
            inverse_document_frequency = math.log(1.0 + (count - df + 0.5) / (df + 0.5))
            average = self._average_document_length
            length_norm = 1.0 if average == 0 else 1.0 - self.b + self.b * len(chunk.terms) / average
            total += inverse_document_frequency * (tf * (self.k1 + 1.0)) / (tf + self.k1 * length_norm)
        if not math.isfinite(total) or total < 0:
            _fail("score_invalid")
        return total

    def search(self, query: str, top_k: int | None = None) -> list[dict[str, object]]:
        if type(query) is not str:
            _fail("invalid_query")
        try:
            query_size = len(query.encode("utf-8", errors="strict"))
        except UnicodeError:
            _fail("invalid_query_encoding")
        if query_size > MAX_QUERY_BYTES:
            _fail("query_too_large")
        query_terms = tokenize(query)
        if not query_terms:
            _fail("empty_query")
        limit = self.top_k if top_k is None else top_k
        if type(limit) is not int or not 1 <= limit <= MAX_TOP_K:
            _fail("invalid_top_k")
        candidate_ids: set[str] = set()
        for term in set(query_terms):
            candidate_ids.update(
                chunk.chunk_id for chunk in self._inverted_index.get(term, ())
            )
        candidates = (self._chunks_by_id[chunk_id] for chunk_id in sorted(candidate_ids))
        ranked = [
            (score, chunk)
            for chunk in candidates
            if (score := self._score(query_terms, chunk)) > 0.0
        ]
        ranked.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return [
            {
                "rank": rank,
                "lexical_score": score,
                "source_id": chunk.source_id,
                "document_id": chunk.document_id,
                "version_id": chunk.version_id,
                "chunk_id": chunk.chunk_id,
                "content_sha256": chunk.content_sha256,
                "start_offset": chunk.start_offset,
                "end_offset": chunk.end_offset,
                "offset_unit": chunk.offset_unit,
                "provenance_reference": chunk.provenance_reference,
            }
            for rank, (score, chunk) in enumerate(ranked[:limit], start=1)
        ]

    def validates_citation(self, result: object) -> bool:
        if (type(result) is not dict or set(result) != _RESULT_FIELDS
                or type(result.get("rank")) is not int or result["rank"] < 1
                or type(result.get("lexical_score")) not in {int, float}
                or type(result.get("lexical_score")) is bool
                or not math.isfinite(float(result["lexical_score"]))
                or result["lexical_score"] < 0
                or type(result.get("chunk_id")) is not str):
            return False
        chunk = self._chunks_by_id.get(result["chunk_id"])
        if chunk is None:
            return False
        expected = {
            "source_id": chunk.source_id,
            "document_id": chunk.document_id,
            "version_id": chunk.version_id,
            "chunk_id": chunk.chunk_id,
            "content_sha256": chunk.content_sha256,
            "start_offset": chunk.start_offset,
            "end_offset": chunk.end_offset,
            "offset_unit": "UTF8_BYTE",
            "provenance_reference": chunk.provenance_reference,
        }
        return all(result.get(key) == value for key, value in expected.items())

    def validates_scope(self, result: object) -> bool:
        return self.validates_citation(result)


def build_index(
    records: Sequence[object],
    *,
    tenant_id: str,
    repository_id: str,
    k1: float = DEFAULT_K1,
    b: float = DEFAULT_B,
    top_k: int = DEFAULT_TOP_K,
) -> LexicalIndex:
    """Validate, scope-filter, and index explicit synthetic KI-2 records.

    The requested scope is a caller declaration only; it does not authenticate
    a caller or establish runtime tenant isolation.
    """
    if type(tenant_id) is not str or _TENANT_RE.fullmatch(tenant_id) is None:
        _fail("invalid_tenant_scope")
    if type(repository_id) is not str or _REPOSITORY_RE.fullmatch(repository_id) is None:
        _fail("invalid_repository_scope")
    if (type(k1) not in {int, float} or type(k1) is bool or not math.isfinite(float(k1))
            or float(k1) <= 0):
        _fail("invalid_bm25_k1")
    if (type(b) not in {int, float} or type(b) is bool or not math.isfinite(float(b))
            or not 0.0 <= float(b) <= 1.0):
        _fail("invalid_bm25_b")
    if type(top_k) is not int or not 1 <= top_k <= MAX_TOP_K:
        _fail("invalid_top_k")
    if not isinstance(records, (list, tuple)) or len(records) > MAX_CORPUS_RECORDS:
        _fail("corpus_record_limit_exceeded")

    included: list[_Chunk] = []
    seen_sources: set[tuple[str, str, str]] = set()
    seen_documents: set[tuple[str, str, str]] = set()
    seen_versions: set[str] = set()
    seen_chunks: set[str] = set()
    for record in records:
        policy, _manifest, declared_tenant, declared_repository = _scope_from_record(record)
        try:
            validate_policy(policy)
        except PolicyValidationError:
            _fail("source_policy_invalid")
        if policy.get("source_type") != "synthetic_fixture":
            _fail("non_synthetic_source_not_supported")
        lifecycle_state = record.get("lifecycle_state")
        if type(lifecycle_state) is not str or lifecycle_state not in _LIFECYCLE_STATES:
            _fail("lifecycle_state_invalid")
        if (declared_tenant, declared_repository) != (tenant_id, repository_id):
            continue
        chunks, checked_tenant, checked_repository, document_key = _validate_record(record)
        if not chunks:  # Explicit KI-2 revoke/delete states are ineligible.
            continue
        source_id = policy.get("source_id")
        source_key = (checked_tenant, checked_repository, source_id)
        doc_key = (checked_tenant, checked_repository, document_key)
        version_ids = {chunk.version_id for chunk in chunks}
        chunk_ids = {chunk.chunk_id for chunk in chunks}
        if (source_key in seen_sources or doc_key in seen_documents
                or seen_versions.intersection(version_ids) or seen_chunks.intersection(chunk_ids)):
            _fail("duplicate_corpus_identifier")
        seen_sources.add(source_key)
        seen_documents.add(doc_key)
        seen_versions.update(version_ids)
        seen_chunks.update(chunk_ids)
        if len(included) + len(chunks) > MAX_CORPUS_CHUNKS:
            _fail("corpus_chunk_limit_exceeded")
        included.extend(chunks)
    return LexicalIndex(
        included,
        tenant_id=tenant_id,
        repository_id=repository_id,
        k1=float(k1),
        b=float(b),
        top_k=top_k,
    )

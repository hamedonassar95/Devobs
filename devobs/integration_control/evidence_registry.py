"""Evidence registry with traceability and contradiction detection."""

from __future__ import annotations

from .models import EvidenceRecord, Finding, MAX_FINDINGS
from .validation import redact


def build_registry(normalized: dict, findings: list[Finding]) -> list[dict]:
    records: list[EvidenceRecord] = []
    repo = normalized.get("repository") or ""
    head_sha = normalized.get("head_sha")
    for idx, raw in enumerate(normalized.get("evidence", [])):
        if not isinstance(raw, dict):
            findings.append(Finding("MALFORMED_EVIDENCE_RECORD", "error", "evidence", f"evidence[{idx}] must be object"))
            continue
        source = str(raw.get("source", "")).strip()
        kind = str(raw.get("kind", "")).strip()
        ref = str(raw.get("ref", "")).strip()
        sha = raw.get("sha")
        ts = raw.get("timestamp")
        if not source or not kind or not ref:
            findings.append(Finding("UNVERIFIABLE_EVIDENCE", "error", "evidence", f"evidence[{idx}] missing source/kind/ref"))
            continue
        if sha is not None and (not isinstance(sha, str) or len(sha) != 40):
            findings.append(Finding("UNVERIFIABLE_EVIDENCE", "error", "evidence", f"evidence[{idx}] has invalid sha"))
            continue
        sha_norm = sha.lower() if isinstance(sha, str) else None
        rec = EvidenceRecord(source=source, kind=kind, ref=ref, sha=sha_norm, timestamp=str(ts) if ts else None, data=redact(raw.get("data", {})) if isinstance(raw.get("data", {}), dict) else {})
        records.append(rec)

    # deterministic built-ins
    records.append(EvidenceRecord("input", "repository", repo or "unknown", head_sha, normalized.get("timestamps", {}).get("evidence_collected_at")))
    if head_sha:
        records.append(EvidenceRecord("input", "head_sha", head_sha, head_sha))

    # duplicate/contradiction checks
    seen: dict[tuple[str, str, str, str], EvidenceRecord] = {}
    by_key: dict[tuple[str, str, str], set[str]] = {}
    for rec in records:
        ident = rec.identity()
        if ident in seen:
            findings.append(Finding("DUPLICATE_EVIDENCE", "error", "evidence", f"Duplicate evidence record: {rec.kind}:{rec.ref}", {"source": rec.source, "sha": rec.sha}))
        else:
            seen[ident] = rec
        by_key.setdefault((rec.source, rec.kind, rec.ref), set()).add(rec.sha or "")
    for (source, kind, ref), shas in by_key.items():
        shas.discard("")
        if len(shas) > 1:
            findings.append(Finding("CONTRADICTORY_EVIDENCE", "error", "evidence", f"Contradictory evidence SHAs for {kind}:{ref}", {"source": source, "shas": sorted(shas)}))

    # bound findings
    del findings[MAX_FINDINGS:]
    return [r.as_dict() for r in sorted(seen.values(), key=lambda r: (r.kind, r.source, r.ref, r.sha or ""))]

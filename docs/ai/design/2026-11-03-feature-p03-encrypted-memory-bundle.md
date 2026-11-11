---
phase: design
title: Tenant-scoped encrypted incident-memory bundle
description: Protect a bounded offline memory export with authenticated encryption and explicit expiry
---

# Design

## Wire contract

The v1 envelope contains only schema version, algorithm identifier, canonical
creation/expiry times, a 32-byte random salt, and ciphertext. Scope is omitted
from public metadata. The caller supplies the exact tenant/project and a
32-byte key on both operations.

HKDF-SHA256 derives an archive-specific AES-256 key using a domain-separated
info string. AES-GCM uses a fixed nonce under that derived key; the random
256-bit salt gives each archive a separate derived key. The tenant, project,
schema, algorithm, salt, and canonical times are authenticated as associated
data. The encrypted plaintext is the existing canonical `IncidentMemory`
bundle, capped at 2 MiB.

## Fail-closed rules

- Reject mixed-tenant/project memory before encryption.
- Reject wrong key/scope, changed salt/ciphertext/metadata, malformed encoding,
  duplicate JSON keys, unsupported versions and invalid record bundles.
- Reject expired or future archives; maximum accepted retention is one year.
- Return records only; the bundle format does not serialize curator approvals.

## Trust and lifecycle limits

The symmetric key holder can create valid ciphertext, so the envelope does not
authenticate an exporter or confer curator approval. The API never generates,
stores or transmits the key. Expiry prevents later decryption through this API
but does not erase a file or enforce a retention policy. Actual key custody,
durable storage, deletion/export workflows and production isolation remain
separate T25 work. Tests use synthetic records and test keys only.

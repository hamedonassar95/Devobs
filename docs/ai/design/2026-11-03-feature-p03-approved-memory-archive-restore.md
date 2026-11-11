---
phase: design
title: Restore approved memory from an encrypted archive
description: Re-apply signed approval only after exact archive and record-set verification
---

# Design

The encrypted memory archive intentionally contains incident records but no
curator-approval provenance. Plain decryption therefore remains unapproved.
Callers that separately hold the original signed approval envelopes may opt in
to `decrypt_approved_incident_memory_bundle`.

The helper decrypts for the exact caller-supplied tenant/project, verifies every
approval against the caller's trusted public-key map and current time, and
compares the entire canonical approved-record bundle with the decrypted archive.
It then claims the approval IDs through the existing `IncidentMemoryApprovalRegistry`.
No ID is consumed for an invalid or mismatched batch. A replay or full registry
fails closed.

Approval envelopes contain the incident records and are sensitive. The helper
does not store or transport them; callers must protect them and pass them
directly. The replay registry remains process-local, keys remain caller-owned,
and this is not a durable storage, retention, deletion, or production-isolation
solution.

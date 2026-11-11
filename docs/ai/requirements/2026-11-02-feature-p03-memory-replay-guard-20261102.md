---
phase: requirements
title: Process-local incident-memory approval replay guard
description: Require a shared bounded consumer for signed incident-memory approvals
---

# Requirements

## Problem

The signed approval verifier rejects duplicate IDs in one imported batch, but is stateless across separate imports. A still-valid signed envelope can therefore be loaded repeatedly within one running process.

## Goals

- Require an explicit, shared process-local registry when importing approved incident memory.
- Accept a valid approval ID at most once per registry instance, including concurrent imports.
- Validate a complete batch before consuming any IDs; reject replay and capacity exhaustion closed.
- Keep the change offline, metadata-only, bounded, and independent of a database or cloud service.

## Non-goals

- Persistence across process restarts or coordination across worker processes.
- Authenticated curator enrollment, production incident ingestion, encryption, retention policy, or an AI-9 evaluation.
- Changing approval signatures, approval expiry, finding authorization, or action state.

## User story

As a caller loading signed incident metadata, I want to reuse one approval registry for the lifetime of the process so a signed approval cannot be applied twice inside that process.

## Acceptance criteria

1. Signed import requires a real registry instance; absent or invalid registry input fails closed.
2. Reusing an approval ID through the same registry fails with a stable `ContextError`.
3. Invalid batches and capacity failures consume no IDs; a later valid import remains possible.
4. Concurrent attempts using the same approval yield exactly one successful import.
5. Registry memory has a hard upper bound and does not evict consumed IDs.
6. Documentation states that restart and multi-process replay remain unsupported.

## Constraints and assumptions

- Use the existing Ed25519 verifier, canonical approval digest, and exact tenant/project/curator trust scope.
- The caller retains one registry object and passes it to each import in that process. Constructing a fresh registry per request defeats replay tracking.
- The registry is transient local memory, not protected durable state. This assumption is deliberately named and must not be described as production-grade one-time consumption.
- No external incident data, network call, secret, migration, deployment, or paid service is involved.

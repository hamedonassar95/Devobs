---
phase: requirements
title: Category-bound incident-memory runbooks
description: Reject incident memory runbook IDs that do not match the supported category catalog
---

# Requirements

## Problem

`IncidentRecord` currently checks that a runbook ID matches the general `RB-...` shape, while the deterministic adviser has a fixed runbook for each supported category. A signed and otherwise valid incident record can therefore carry a syntactically valid but unsupported or category-mismatched runbook ID. `correlate(...)` can return that ID as a recommendation. Curator approval authenticates the exact payload against a trusted key; it does not establish that the runbook ID is supported for the record's category.

## Goals

- Accept only the existing deterministic runbook ID for each supported incident category.
- Use one authoritative category-to-runbook catalog for the adviser and incident-memory validation.
- Reject unsupported or mismatched IDs at both in-process record construction and serialized record import, including signed imports.
- Preserve the current runbook IDs and successful output for valid records.
- Keep the behavior offline, bounded, deterministic, and advisory-only.

## Non-goals

- Adding runbooks, changing the category set, or making the catalog dynamically configurable.
- Executing a runbook, changing human-approval state, or granting the model/tool authority.
- Importing live incidents or changing data retention, persistence, hosting, model use, or readiness gates.

## User story

As an operator reviewing a locally generated incident finding, I want memory-derived runbook IDs to be known and valid for the finding category so an approved memory record cannot inject an unrelated or unsupported runbook reference.

## Acceptance criteria

1. Each supported category has exactly one current runbook ID, matching the existing deterministic adviser output.
2. A mismatched category/runbook pair and an unknown runbook ID fail closed when constructing an `IncidentRecord`.
3. Serialized record parsing rejects the same invalid pairs even if the record digest is recomputed; a correctly signed envelope with such a record is also rejected.
4. The deterministic adviser and memory validation read from the same catalog; no duplicated category-to-ID mapping remains.
5. Existing valid memory, signed provenance, correlation, and adviser results remain unchanged.
6. Offline tests cover supported pairs, mismatches, unknown IDs, and a re-signed malformed envelope. No live data, network service, model API, or cloud resource is used by the feature tests.

## Constraints and assumptions

- **Assumption:** the existing `_RUNBOOKS` mapping in `scripts/devobs_intelligence/adviser.py` is the authoritative source for the three supported category/ID pairs: `ci_failure`/`RB-CI-01`, `high_error_rate`/`RB-SLO-01`, and `capacity_pressure`/`RB-CAP-01`.
- Existing syntactic validation remains useful for stable error handling but must not replace catalog membership and category matching.
- Invalid memory must be rejected before it can contribute to a finding; valid behavior and public record shapes do not change.

## Alternatives considered

- Keep syntax-only validation: smallest change, but permits a signed record to recommend an unsupported or wrong-category ID.
- Duplicate an allowlist in `incident_memory.py`: blocks bad IDs but creates two sources that can drift from the adviser.
- Share the existing catalog across validation and advice: chosen because it prevents drift while preserving current outputs.

## Open questions

None for this offline change. New runbooks or categories require a separate catalog update and matching tests.

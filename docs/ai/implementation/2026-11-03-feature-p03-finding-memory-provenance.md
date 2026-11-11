---
phase: implementation
title: Require paired runbook and memory provenance fields
description: Fail closed on internally inconsistent finding records
---

# Implementation

`IncidentFinding.from_record` now rejects findings where `memory_provenance` is
present without `runbook_ids`, or `runbook_ids` are present without
`memory_provenance`. The check runs after the existing schema and digest
validation. No wire fields or schema version changed.

---
phase: design
title: Keep finding memory provenance paired with runbooks
description: Reject serialized findings with incomplete incident-memory attribution
---

# Design

Correlation derives runbook identifiers only from incident-memory records that
passed its retrieval checks. A serialized finding must therefore carry both
the selected runbooks and their memory-provenance entries, or neither. Accepting
only one side creates an ambiguous audit record: a runbook without attribution
or an approval trail that did not contribute to the finding.

The finding digest is unkeyed and only detects accidental changes. This
consistency check does not independently verify the original curator signature;
that still requires the signed approval envelope and trusted key.

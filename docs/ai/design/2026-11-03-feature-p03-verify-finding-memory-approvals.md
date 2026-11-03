---
phase: design
title: Re-verify signed incident-memory approvals in findings
description: Bind a serialized correlation result to its original curator approvals
---

# Design

The finding digest is unkeyed and cannot prove curator approval. When a finding
contains incident-memory provenance, verification must receive the original
signed approval envelopes and a separate trusted memory public-key map.

The verifier checks that the complete approval set matches the finding's
tenant/project, evidence and record digests, source SHA, recorded time, approver,
approval digest and runbook set. It rejects missing, extra, invalid, expired,
or cross-scope approvals. The verifier also requires a caller-supplied memory
age bound and rejects signed records whose recorded time is in the future or
outside that bound. Findings without memory provenance require no approval
envelopes or memory age bound.

The existing signed-topology validator composes both checks when memory is
present. The caller still owns topology and memory trust roots and must provide
the original approval envelopes and age bound; no keys or envelopes are stored
here.

---
phase: design
title: Abstain from incident memory on legacy topology inputs
description: Prevent unprovenanced memory from influencing topology correlations
---

# Design

`ServiceTopology` has tenant/project and edges, but no source revision or capture
time. Correlation can still rank its separately validated telemetry and compute
declared impact paths. It must not add incident-memory runbooks from that graph,
because it cannot establish when or against which source the memory was
recorded.

Memory remains eligible when correlation receives a source-bound
`ServiceTopologySnapshot`, the caller supplies a bounded maximum age, and the
memory row has an active verified approval. This is an abstention rule for one
input path, not a topology-authentication or production-readiness claim.

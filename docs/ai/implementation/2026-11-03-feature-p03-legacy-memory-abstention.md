---
phase: implementation
title: Require source-bound topology before using incident memory
description: Keep legacy graph correlation advisory while omitting unverified runbooks
---

# Implementation

Updated `correlate` so a legacy `ServiceTopology` still produces telemetry
ranking and impact paths but contributes no incident-memory records. The
existing snapshot path still requires an explicit memory-age policy and active
verified approval. The API does not change and no live source, external service,
or customer data was introduced.

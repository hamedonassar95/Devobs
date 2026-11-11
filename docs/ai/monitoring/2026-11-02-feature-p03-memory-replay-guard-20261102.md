---
phase: monitoring
title: Approval replay guard monitoring boundary
description: Local error outcomes only; no telemetry or service is activated
---

# Monitoring

The local contract returns stable errors for replay and full capacity. This change adds no metrics, logs, network export, or service monitoring. Callers must avoid logging signed envelopes, key material, or incident content.

No operational alert, runtime handshake, production replay metric, or service-level objective is established by offline tests. A future persistent implementation needs explicit capacity, retention, reset, alert, and recovery policies before adoption.

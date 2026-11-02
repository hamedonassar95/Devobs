---
phase: monitoring
title: Monitoring scope for category-bound runbook catalog
description: Record observability applicability for this offline validation change
---

# Monitoring and observability

This feature does not add a running process, endpoint, background job, or external integration, so it introduces no service metrics, dashboards, alerts, or on-call procedure.

The behavior is verified by deterministic unit tests: supported category/runbook pairs pass, while mismatched or unsupported pairs fail closed at record creation and import. The normal CI suite remains the operational signal for regressions. Validation errors continue to use the existing stable error contracts and do not log record contents or signer material.

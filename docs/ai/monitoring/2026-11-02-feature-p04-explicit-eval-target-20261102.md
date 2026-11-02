---
phase: monitoring
title: Monitoring scope for optional evaluation target
description: Record observability applicability for an offline scorecard correction
---

# Monitoring

No runtime service or new metric is introduced. The regression is covered by deterministic unit tests and repository CI. Consumers should treat a null target decision as “no target comparison requested,” not as a pass or failure.

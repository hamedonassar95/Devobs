---
phase: deployment
title: Approval replay guard deployment boundary
description: No deployment or runtime activation in this offline change
---

# Deployment

This change adds only a local Python API contract and tests. It does not deploy a service or alter runtime configuration. A caller adopting the API must create one registry for its process lifetime and pass the same instance to each signed-memory import.

This registry is not durable, encrypted, cross-process, or restart-safe. Do not use it as the production replay boundary; a separate protected persistent-consumption design and owner approval are required first. Rollback is a normal reviewed source revert; no data cleanup is required.

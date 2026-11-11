---
phase: monitoring
title: P01 AC02 JWK operation monitoring
description: Observability applicability for local verifier configuration checks
---

# Monitoring

This change adds no telemetry or runtime behavior for valid requests. Invalid key configuration continues to return the fixed `invalid_auth_config` error; callers must not log the raw JWKS. Existing test and CI results are the relevant evidence for this local change.

No new dashboard, alert, external log sink, or live monitoring target is introduced. Live provider/JWKS monitoring remains outside this code-only change.

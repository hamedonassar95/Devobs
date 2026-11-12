---
phase: monitoring
title: Monitoring & Observability
description: Avoid logging mail content and tokens
---

# Monitoring

No telemetry, persistent logs, analytics or scheduled checks. UI status is fixed; recipient, message, token and provider body are never logged. On uncertain delivery, inspect Gmail Sent before reload; revoke Google access if the device is untrusted.

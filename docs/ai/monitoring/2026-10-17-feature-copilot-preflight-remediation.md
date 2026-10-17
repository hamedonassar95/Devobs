---
phase: monitoring
title: Copilot preflight remediation
description: Monitor the manual credential preflight without making model calls
---

# Monitoring

The evidence source is the **AI Provider Preflight** Actions run and its job summary. A missing or malformed secret must leave the `copilot` job failed and show setup guidance without exposing the value. A prefix-accepted result is only a format check; it does not verify `Copilot Requests: Read`, quota, or model access.

No new scheduled runs or alerts are added. The owner should rerun the manual preflight after updating the Actions secret. Only after it passes should an authorized, quota-aware controlled incident evaluation be considered.

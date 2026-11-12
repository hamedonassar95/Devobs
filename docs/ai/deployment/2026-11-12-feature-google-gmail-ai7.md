---
phase: deployment
title: Deployment Strategy
description: Keep Gmail summaries opt-in and local
---

# Deployment

No hosted service is added; the dashboard stays on loopback and outside Pages. Gmail is disabled unless the operator passes `--google-gmail-client-id <public-client-id>` after configuring Gmail API and the local OAuth origin. Never put a client secret in the browser or repo.

Disable by restarting without the flag and revoking any Google grant. Main CI Pages publication does not deploy this dashboard or enable Gmail.

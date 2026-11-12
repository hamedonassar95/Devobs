---
phase: requirements
title: Requirements & Problem Understanding
description: One user-approved AI-7 aggregate email via Gmail
---

# Requirements

The source repo reads and sends Gmail; AI-7 needs only a reviewed summary sent to one chosen address.

Goal: fixed aggregate counts, visible preview, explicit confirmation, and just-in-time `gmail.send` consent.
Out of scope: inbox reads, attachments, arbitrary composition, multiple recipients, scheduling, customer logs, and hosted email.
Acceptance: reject malformed addresses/header injection; send one aggregate-only message; never read Gmail; allow one attempt per page; tests pass.
Constraint/open item: local loopback, public OAuth client ID, no stored token. Live use needs owner-configured Google OAuth.

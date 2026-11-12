---
phase: design
title: System Design & Architecture
description: Local send-only Gmail delivery of an allowlisted summary
---

# Design

```mermaid
flowchart LR
  User -->|confirm| Dashboard[Loopback AI-7]
  Dashboard -->|gmail.send token| GIS[Google Identity Services]
  Dashboard -->|one MIME POST| Gmail[Gmail send API]
  Dashboard -->|read config| LocalAPI[Loopback API]
```

The module validates one address and builds fixed aggregate content. Loopback returns only a public client ID; the browser requests a token after confirmation and calls Gmail directly. No read scope, token storage, logging, retry or background send; an uncertain result blocks more sends in-page.

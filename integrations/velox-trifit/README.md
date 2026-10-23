# Velox TriFit — isolated integration

Status: documentation-only scaffold; no deployment, credentials, uploads or paid generation.

## Purpose

Prepare a separate, reviewable integration for Velox DressMe. Do not connect this module to the Devobs website, CI deploy jobs, or production automation.

## Upstream reference

https://github.com/Velox-XR/trifit-partner-api-example

Read upstream `docs/GETTING_STARTED.md`, `WALKTHROUGH.md`, SDK source/types and license before copying code. Confirm supported commands from the checked-out version.

## Safe local workflow

1. Clone the upstream example to a separate local workspace.
2. Run its documented offline mock success and failure tests (`node demo.mjs` and `node demo.mjs --failure` from its root).
3. Do not supply real credentials or submit a paid generation.
4. Record verified test results and only then propose an implementation PR.

## Partner integration requirements (future, not implemented)

- Obtain environment-specific partner configuration from Velox; never use checked-in demo keys.
- Store partner credentials server-side only; verify `/me` identity and environment before use.
- Derive opaque shopper identity from a verified server session.
- Reserve and persist image asset IDs; upload personal and product images separately using only returned signed-upload headers.
- Persist an idempotency UUID and exact input asset IDs before submitting a DressMe job; persist job receipt and poll status.
- Never automatically retry uncertain submissions or expose private result URLs in logs.

## Non-goals and boundaries

- No changes to `main`, GitHub Pages, workflows or secrets.
- No automatic deployment, production API traffic, or generation.
- No claims that a preview or mock is a live service.

## Verification

- Branch-only scaffold created; offline mock has **not** been executed in this repository.
- Next step: inspect the upstream example and add isolated mock tests with explicit failure cases.

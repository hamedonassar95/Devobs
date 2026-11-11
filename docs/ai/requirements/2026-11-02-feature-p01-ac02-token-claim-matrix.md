---
phase: requirements
title: P01 AC02 JWK operation constraints
description: Reject configured public signing keys that advertise operations outside verification
---

# P01 AC02 JWK operation constraints

## Problem

`AccessTokenVerifier` checked RSA type, algorithm, signature use, key ID, modulus and exponent, but ignored a JWK `key_ops` member. A key marked for encryption or signing could therefore be accepted by a verifier-only configuration.

## Goals and acceptance criteria

- If `key_ops` is present, accept exactly the JSON array `["verify"]`.
- Reject malformed, empty, duplicate, or non-verification operation lists with the existing fixed `invalid_auth_config` error.
- Continue accepting otherwise-valid keys when `key_ops` is absent.
- Prove both cases with generated local RSA keys; no network or provider access.

## Non-goals and constraints

- No remote JWKS discovery/fetch, live issuer validation, rotation, staging, or deployment changes.
- No readiness disposition changes. This local control is not live identity-provider evidence.
- Use the existing Python test suite and locked dependencies; no paid service.

## Open items

Independent review and any live OIDC acceptance remain separate work. RFC 7517 §4.3 defines `key_ops`; the API's narrower policy is limited to verification.

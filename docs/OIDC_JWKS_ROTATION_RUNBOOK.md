# DevObs trusted OIDC JWKS rotation — review-only staging primitive

**Current state:** implemented local **validation and atomic key-set replacement** in
`scripts/devobs_intelligence/oidc_rotation.py`; this is **NOT** a live key
refresh service, a network fetcher, or a production identity provider.

## Trust and safety contract

1. DevObs pins the exact HTTPS issuer, intended API audience, and OAuth client.
2. An authorized deployment operator must authenticate the metadata/JWKS source
   independently. Do not copy JWKS from a token header (`jku`, `jwk`) or
   from an agent response, issue comment, log, user input or arbitrary URL.
3. Trusted JWKS may contain a bounded set of RSA/RS256 **public** keys, with
   unique `kid` identifiers. The API checks signature, token type `at+jwt`,
   issuer, audience, client ID, expiry, subject and `devobs.read` scope.
4. Use `RotatingOIDCVerifier.install_operator_verified(..., revision=N)`
   only from an authorized *internal* operator-controlled mechanism. A revision
   must strictly increase; bad configurations preserve the prior verifier.
5. A provider can publish both old and new public keys during a handover; once
   an old key is omitted from a newer verified snapshot, signatures made with
   the old key are rejected for subsequent requests in this process.
6. Each Gunicorn worker owns its own process-local verifier. **No coordinated
   cross-worker update, freshness TTL, distributed revision source or provider
   revocation mechanism exists yet.** Service restart with newly authenticated
   secret values is still the operational option. Do not enable automatic
   provider fetching or expose a public rotation endpoint without design review.
7. Protect the key-set delivery channel, check signed access-token claims and
   audit operator approval separately. A public JWKS is not a secret, but its
   *authenticity* is a security requirement. Do not store signing private keys.

## Reproducible review

```bash
python3 -m unittest discover -s tests -p 'test_intelligence_oidc_rotation.py' -v
python3 -m unittest discover -s tests -p 'test_intelligence_staging_app.py' -v
python3 -m unittest discover -s tests -v
```

Tests use synthetic RSA key pairs generated locally; they never contact an
identity provider. Passing these tests is NOT evidence of real-world rotation,
provider availability, token revocation or correct account provisioning.

## Go/no-go for hosted Staging

- [ ] Dedicated DevObs issuer and resource-server client authorized.
- [ ] Independently authenticated HTTPS metadata and JWKS from that issuer.
- [ ] Distributed rollout/restart process tested for two overlapping public
  keys and all Gunicorn workers.
- [ ] Provider revocation and key compromise response tested; max-age/freshness
  and fallback behavior agreed and documented.
- [ ] Observed negative test: revoked/superseded `kid`, forged issuer,
  wrong audience, wrong client, wrong scope, expired token, unavailable issuer.
- [ ] Source credentials and controls separated from Phone Repair Assistant.

## Official references

- OpenID Connect Core §10.1.1 (signing key rotation):
  https://openid.net/specs/openid-connect-core-1_0.html#RotateSigKeys
- OAuth 2.0 Security BCP, RFC 9700:
  https://www.rfc-editor.org/rfc/rfc9700.html
- Render secret/environment management:
  https://render.com/docs/configure-environment-variables

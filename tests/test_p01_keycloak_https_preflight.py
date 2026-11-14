"""Offline contract tests for the HTTPS-only Keycloak preflight.

These tests use synthetic public JWKS and injected response documents. They do
not create certificates, private keys, tokens, OAuth clients, or Docker services
and are not evidence of a real TLS handshake.
"""
from __future__ import annotations

import base64
import contextlib
import io
import socket
import ssl
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import p01_keycloak_https_preflight as preflight


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _public_jwks() -> dict[str, object]:
    # A deterministic 2048-bit odd RSA modulus and public exponent. No private
    # signing material is generated or included in this fixture.
    modulus = (1 << 2047) + 1
    raw_modulus = modulus.to_bytes(256, "big")
    return {
        "keys": [{
            "kty": "RSA",
            "kid": "fixture-key-1",
            "use": "sig",
            "alg": "RS256",
            "n": _b64url(raw_modulus),
            "e": _b64url((65537).to_bytes(3, "big")),
        }]
    }


def _discovery(**updates) -> dict[str, object]:
    document: dict[str, object] = {
        "issuer": preflight.ISSUER,
        "jwks_uri": preflight.JWKS_URI,
    }
    document.update(updates)
    return document


class _Response:
    def __init__(self, status=200, headers=None, body=b"{}"):
        self.status = status
        self._headers = headers or [("Content-Type", "application/json")]
        self._body = body
        self.read_called = False

    def getheaders(self):
        return list(self._headers)

    def getheader(self, name, default=None):
        for header, value in self._headers:
            if header.lower() == name.lower():
                return value
        return default

    def read(self, size=-1):
        self.read_called = True
        return self._body[:size]


class KeycloakHTTPSPreflightTests(unittest.TestCase):
    def context(self):
        return SimpleNamespace(verify_mode=ssl.CERT_REQUIRED, check_hostname=True)

    def run_with_documents(self, discovery=None, jwks=None):
        documents = {
            preflight.DISCOVERY_PATH: _discovery() if discovery is None else discovery,
            preflight.JWKS_PATH: _public_jwks() if jwks is None else jwks,
        }
        requested: list[tuple[str, int]] = []

        def fetch_json(path, limit):
            requested.append((path, limit))
            return documents[path]

        result = preflight.run_preflight(
            "public-ca.pem", fetch_json=fetch_json,
            context_factory=lambda _path: self.context())
        return result, requested

    def assert_preflight_error(self, category, discovery=None, jwks=None):
        documents = {
            preflight.DISCOVERY_PATH: _discovery() if discovery is None else discovery,
            preflight.JWKS_PATH: _public_jwks() if jwks is None else jwks,
        }
        requested = []

        def fetch_json(path, limit):
            requested.append(path)
            return documents[path]

        with self.assertRaises(preflight.PreflightError) as raised:
            preflight.run_preflight(
                "public-ca.pem", fetch_json=fetch_json,
                context_factory=lambda _path: self.context())
        self.assertEqual(raised.exception.category, category)
        return requested

    def test_valid_discovery_and_jwks_report_https_only_preflight(self):
        result, requested = self.run_with_documents()
        self.assertEqual(result["result"], "LOCAL_HTTPS_OIDC_PREFLIGHT_PASS")
        self.assertEqual(result["certificate_verification"], "PASS")
        self.assertEqual(result["public_rs256_signing_keys"], 1)
        self.assertEqual(result["signed_token_acceptance"], "NOT_TESTED")
        self.assertEqual(result["readiness_claim"], "NOT_ESTABLISHED")
        self.assertEqual(requested, [
            (preflight.DISCOVERY_PATH, preflight.DISCOVERY_LIMIT),
            (preflight.JWKS_PATH, preflight.JWKS_LIMIT),
        ])

    def test_issuer_mismatch_fails_before_jwks_request(self):
        requested = self.assert_preflight_error(
            "issuer_mismatch", discovery=_discovery(issuer="https://other.test/realm"))
        self.assertEqual(requested, [preflight.DISCOVERY_PATH])

    def test_non_local_or_wrong_jwks_uri_fails_before_fetch(self):
        for uri in (
            "http://localhost:8443" + preflight.JWKS_PATH,
            "https://127.0.0.1:8443" + preflight.JWKS_PATH,
            "https://attacker.test:8443" + preflight.JWKS_PATH,
            "https://localhost:9443" + preflight.JWKS_PATH,
            preflight.JWKS_URI + "?redirect=https://attacker.test",
            preflight.JWKS_URI + "#fragment",
        ):
            with self.subTest(uri=uri):
                requested = self.assert_preflight_error(
                    "jwks_uri_mismatch", discovery=_discovery(jwks_uri=uri))
                self.assertEqual(requested, [preflight.DISCOVERY_PATH])

    def test_missing_malformed_or_empty_jwks_fails_closed(self):
        for jwks, category in (
            ({}, "invalid_jwks_document"),
            ({"keys": []}, "no_compatible_public_signing_key"),
            ({"keys": [{"kty": "RSA", "kid": "x", "alg": "RS256", "use": "sig"}]},
             "incompatible_public_jwks"),
        ):
            with self.subTest(jwks=jwks):
                self.assert_preflight_error(category, jwks=jwks)

    def test_private_jwk_fields_are_rejected(self):
        jwks = _public_jwks()
        jwks["keys"][0]["d"] = "never-accept-private-material"
        self.assert_preflight_error("incompatible_public_jwks", jwks=jwks)

    def test_wrong_alg_duplicate_kid_and_too_many_keys_are_rejected(self):
        wrong_alg = _public_jwks()
        wrong_alg["keys"][0]["alg"] = "RS384"
        self.assert_preflight_error("incompatible_public_jwks", jwks=wrong_alg)

        duplicate = _public_jwks()
        duplicate["keys"].append(dict(duplicate["keys"][0]))
        self.assert_preflight_error("incompatible_public_jwks", jwks=duplicate)

        too_many = _public_jwks()
        too_many["keys"] *= preflight.MAX_KEYS + 1
        self.assert_preflight_error("no_compatible_public_signing_key", jwks=too_many)

    def test_tls_context_requires_operator_ca_and_hostname_verification(self):
        fake_context = SimpleNamespace(
            check_hostname=False, verify_mode=ssl.CERT_NONE,
            minimum_version=None, load_verify_locations=mock.Mock())
        with (
            mock.patch.object(Path, "is_file", return_value=True),
            mock.patch.object(preflight.ssl, "SSLContext", return_value=fake_context),
        ):
            context = preflight._build_tls_context("operator-public-ca.pem")
        self.assertIs(context, fake_context)
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2)
        context.load_verify_locations.assert_called_once_with(
            cafile="operator-public-ca.pem")

    def test_missing_ca_blocks_before_any_endpoint_request(self):
        fetch = mock.Mock()
        with self.assertRaises(preflight.PreflightError) as raised:
            preflight.run_preflight("/definitely/not/a/public-ca.pem", fetch_json=fetch)
        self.assertEqual(raised.exception.category, "public_ca_unavailable")
        fetch.assert_not_called()

    def test_context_without_required_tls_verification_fails_closed(self):
        context = SimpleNamespace(verify_mode=ssl.CERT_NONE, check_hostname=False)
        fetch = mock.Mock()
        with self.assertRaises(preflight.PreflightError) as raised:
            preflight.run_preflight("public-ca.pem", fetch_json=fetch,
                                    context_factory=lambda _path: context)
        self.assertEqual(raised.exception.category, "tls_verification_not_enabled")
        fetch.assert_not_called()

    def test_non_loopback_dns_answer_is_rejected(self):
        non_loopback = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP,
                         "", ("192.0.2.10", preflight.PORT))]
        with mock.patch.object(preflight.socket, "getaddrinfo", return_value=non_loopback):
            with self.assertRaises(preflight.PreflightError) as raised:
                preflight._resolve_loopback_addresses()
        self.assertEqual(raised.exception.category, "non_loopback_address_rejected")

    def test_redirect_is_rejected_without_reading_or_following_location(self):
        response = _Response(
            status=302,
            headers=[("Location", "https://attacker.test/token?secret=hidden")],
            body=b"must-not-be-read")
        with self.assertRaises(preflight.PreflightError) as raised:
            preflight._response_body(response, 1024)
        self.assertEqual(raised.exception.category, "redirect_rejected")
        self.assertFalse(response.read_called)

    def test_http_errors_content_types_and_limits_are_rejected(self):
        cases = (
            (_Response(status=401), "endpoint_http_error"),
            (_Response(headers=[("Content-Type", "text/html")]),
             "invalid_response_content_type"),
            (_Response(headers=[("Content-Type", "application/json"),
                                ("Content-Length", str(preflight.DISCOVERY_LIMIT + 1))]),
             "response_body_too_large"),
            (_Response(headers=[("Content-Type", "application/json"),
                                ("Content-Encoding", "gzip")]),
             "unsupported_response_encoding"),
        )
        for response, category in cases:
            with self.subTest(category=category), self.assertRaises(
                    preflight.PreflightError) as raised:
                preflight._response_body(response, preflight.DISCOVERY_LIMIT)
            self.assertEqual(raised.exception.category, category)

    def test_duplicate_json_keys_and_non_object_documents_are_rejected(self):
        for body in (b'{"issuer":"a","issuer":"b"}', b"[]", b"not-json"):
            with self.subTest(body=body), self.assertRaises(
                    preflight.PreflightError) as raised:
                preflight._decode_document(body)
            self.assertEqual(raised.exception.category, "invalid_json_response")

    def test_cli_rejects_extra_arguments_without_echoing_them(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = preflight.main([
                "--ca-cert", "operator-public-ca.pem", "--url",
                "https://untrusted.test/secret-value",
            ])
        self.assertEqual(status, 2)
        self.assertNotIn("untrusted.test", output.getvalue())
        self.assertNotIn("secret-value", output.getvalue())


if __name__ == "__main__":
    unittest.main()

"""Behavioral tests against synthetic, loopback-only OIDC HTTP fixtures."""
from __future__ import annotations

import base64
import contextlib
import io
import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from p01_keycloak_local_preflight import (  # noqa: E402
    DISCOVERY_PATH,
    JWKS_PATH,
    LOCAL_ORIGIN,
    PreflightError,
    main,
    run_preflight,
)


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def public_key(modulus: bytes | None = None) -> dict[str, object]:
    return {
        "kty": "RSA",
        "kid": "local-test-key",
        "alg": "RS256",
        "use": "sig",
        "n": b64url(modulus or (b"\x80" + b"\x01" * 255)),
        "e": b64url(b"\x01\x00\x01"),
    }


class KeycloakLocalPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        fixtures: dict[str, tuple[int, bytes, dict[str, str]]] = {}
        requests: list[str] = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                path = urlsplit(self.path).path
                requests.append(path)
                status, body, headers = fixtures.get(
                    path, (404, b"synthetic fixture missing", {}))
                self.send_response(status)
                self.send_header("Content-Type", headers.get(
                    "Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(body)))
                for name, value in headers.items():
                    if name.lower() != "content-type":
                        self.send_header(name, value)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, _format: str, *_args: object) -> None:
                return

        self.fixtures = fixtures
        self.requests = requests
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.set_documents()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def set_documents(self, *, discovery: object | None = None,
                       jwks: object | None = None) -> None:
        expected_issuer = f"{self.origin}/realms/devobs-local"
        if discovery is None:
            discovery = {
                "issuer": expected_issuer,
                "jwks_uri": expected_issuer + "/protocol/openid-connect/certs",
            }
        if jwks is None:
            jwks = {"keys": [public_key()]}
        self.fixtures[DISCOVERY_PATH] = (
            200, json.dumps(discovery).encode("utf-8"), {})
        self.fixtures[JWKS_PATH] = (
            200, json.dumps(jwks).encode("utf-8"), {})

    def assert_preflight_error(self, code: str) -> None:
        with self.assertRaises(PreflightError) as caught:
            run_preflight(self.origin)
        self.assertEqual(caught.exception.code, code)

    def test_valid_discovery_and_public_rsa_jwks_are_reported_without_readiness(self):
        result = run_preflight(self.origin)
        self.assertEqual(result["result"], "LOCAL_OIDC_PREFLIGHT_PASS")
        self.assertEqual(result["public_rs256_signing_keys"], 1)
        self.assertEqual(result["https_only_issuer_policy"],
                         "NOT_COMPATIBLE_WITH_LOCAL_HTTP")
        self.assertEqual(result["readiness_claim"], "NOT_ESTABLISHED")
        self.assertEqual(self.requests, [DISCOVERY_PATH, JWKS_PATH])

    def test_compose_uses_versioned_immutable_quay_image_and_local_port_only(self):
        compose = (Path(__file__).resolve().parents[1]
                   / "dev/keycloak/compose.local.yaml").read_text(encoding="utf-8")
        self.assertRegex(
            compose,
            r"(?m)^\s+image:\s+quay\.io/keycloak/keycloak:26\.8\.2@sha256:[a-f0-9]{64}$",
        )
        self.assertNotIn(":latest", compose)
        self.assertNotIn("KC_BOOTSTRAP_ADMIN_USERNAME", compose)
        self.assertNotIn("KC_BOOTSTRAP_ADMIN_PASSWORD", compose)
        self.assertIn('"127.0.0.1:8080:8080"', compose)
        self.assertEqual(LOCAL_ORIGIN, "http://127.0.0.1:8080")

    def test_realm_is_minimal_import_json_without_users_or_clients(self):
        realm_path = (Path(__file__).resolve().parents[1]
                      / "dev/keycloak/realm.local.json")
        realm = json.loads(realm_path.read_text(encoding="utf-8"))
        self.assertEqual(realm["realm"], "devobs-local")
        self.assertIs(realm["enabled"], True)
        self.assertEqual(realm["sslRequired"], "external")
        self.assertEqual(realm["users"], [])
        self.assertEqual(realm["clients"], [])

    def test_rejects_non_exact_local_origin_without_request(self):
        for origin in (
            self.origin.replace("127.0.0.1", "localhost"),
            self.origin.replace("http://", "https://"),
            self.origin + "/extra",
            self.origin.replace("127.0.0.1", "127.0.0.2"),
        ):
            with self.subTest(origin_kind=urlsplit(origin).hostname):
                with self.assertRaises(PreflightError) as caught:
                    run_preflight(origin)
                self.assertEqual(caught.exception.code, "invalid_local_origin")
        self.assertEqual(self.requests, [])

    def test_rejects_wrong_issuer_before_fetching_jwks(self):
        self.set_documents(discovery={
            "issuer": "http://127.0.0.1/other-realm",
            "jwks_uri": f"{self.origin}/realms/devobs-local/protocol/openid-connect/certs",
        })
        self.assert_preflight_error("issuer_mismatch")
        self.assertEqual(self.requests, [DISCOVERY_PATH])

    def test_rejects_cross_origin_or_wrong_path_jwks_uri(self):
        expected = f"{self.origin}/realms/devobs-local"
        for uri in (
            "https://example.invalid/keys",
            f"{self.origin}/realms/other/protocol/openid-connect/certs",
        ):
            with self.subTest(uri=urlsplit(uri).hostname):
                self.set_documents(discovery={
                    "issuer": expected, "jwks_uri": uri,
                })
                self.requests.clear()
                self.assert_preflight_error("jwks_uri_mismatch")
                self.assertEqual(self.requests, [DISCOVERY_PATH])

    def test_redirect_is_rejected_without_following_location(self):
        marker = "synthetic-redirect-marker"
        self.fixtures[DISCOVERY_PATH] = (
            302, b"", {"Location": f"https://example.invalid/{marker}"})
        self.assert_preflight_error("redirect_rejected")
        self.assertEqual(self.requests, [DISCOVERY_PATH])
        self.assertNotIn(marker, str(PreflightError("redirect_rejected")))

    def test_discovery_response_size_is_bounded(self):
        self.fixtures[DISCOVERY_PATH] = (200, b" " * (16 * 1024 + 1), {})
        self.assert_preflight_error("response_body_too_large")
        self.assertEqual(self.requests, [DISCOVERY_PATH])

    def test_jwks_response_size_is_bounded(self):
        self.fixtures[JWKS_PATH] = (200, b" " * (64 * 1024 + 1), {})
        self.assert_preflight_error("response_body_too_large")
        self.assertEqual(self.requests, [DISCOVERY_PATH, JWKS_PATH])

    def test_rejects_malformed_json_and_non_json_content_type(self):
        self.fixtures[DISCOVERY_PATH] = (200, b"{bad", {})
        self.assert_preflight_error("invalid_json_response")
        self.fixtures[DISCOVERY_PATH] = (
            200, b"{}", {"Content-Type": "text/plain"})
        self.assert_preflight_error("invalid_response_content_type")

    def test_rejects_duplicate_json_fields(self):
        self.fixtures[DISCOVERY_PATH] = (
            200, b'{"issuer":"one","issuer":"two"}', {})
        self.assert_preflight_error("invalid_json_response")

    def test_rejects_missing_weak_or_duplicate_signing_keys(self):
        for jwks in (
            {"keys": []},
            {"keys": [public_key(b"\x80" + b"\x01" * 127)]},
            {"keys": [public_key(), public_key()]},
        ):
            with self.subTest(key_count=len(jwks["keys"])):
                self.set_documents(jwks=jwks)
                self.assert_preflight_error(
                    "invalid_jwks_document" if not jwks["keys"]
                    else "invalid_public_rsa_key")

    def test_rejects_private_key_material_without_echoing_it(self):
        marker = "synthetic-private-field-marker"
        self.set_documents(jwks={"keys": [dict(public_key(), d=marker)]})
        with self.assertRaises(PreflightError) as caught:
            run_preflight(self.origin)
        self.assertEqual(caught.exception.code, "private_jwk_material_rejected")
        self.assertNotIn(marker, str(caught.exception))

    def test_http_errors_and_redirect_locations_are_sanitized(self):
        marker = "synthetic-sensitive-response-marker"
        self.fixtures[DISCOVERY_PATH] = (500, marker.encode(), {})
        with self.assertRaises(PreflightError) as caught:
            run_preflight(self.origin)
        self.assertEqual(caught.exception.code, "local_endpoint_http_error")
        self.assertNotIn(marker, str(caught.exception))
        output = io.StringIO()
        error = io.StringIO()
        with patch("p01_keycloak_local_preflight.run_preflight",
                   side_effect=PreflightError("local_endpoint_http_error")):
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
                self.assertEqual(main([]), 2)
        self.assertNotIn(marker, output.getvalue() + error.getvalue())
        self.assertIn("local_endpoint_http_error", output.getvalue())

    def test_cli_rejects_arguments_without_echoing_them(self):
        marker = "synthetic-argument-marker"
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            self.assertEqual(main([marker]), 2)
        self.assertNotIn(marker, output.getvalue())


if __name__ == "__main__":
    unittest.main()

"""Offline acceptance contract for the read-only managed-staging smoke verifier.

All HTTP responses and tokens are synthetic. The tests never open a socket.
"""
from __future__ import annotations

import io
import json
import unittest
from dataclasses import replace
from urllib.error import HTTPError
from unittest.mock import patch

from scripts.devobs_intelligence import staging_smoke as smoke


BASE_URL = "https://smoke-fixture.onrender.com"
TENANT_TOKEN = "synthetic-tenant-token-" + "a" * 40 + ".payload.signature"
DENIED_TOKEN = "synthetic-denied-token-" + "b" * 40 + ".payload.signature"
SOURCE_SHA = "a" * 40
OTHER_SHA = "b" * 64


def reply(status: int, value=None, *, cache="no-store", content_type="application/json"):
    if value is None:
        body = b""
    elif isinstance(value, bytes):
        body = value
    else:
        body = json.dumps(value, separators=(",", ":")).encode()
    return status, {"cache-control": cache, "content-type": content_type}, body


def accepted_sequence():
    return [
        reply(204),
        reply(204),
        reply(401, {"error": "invalid_token"}),
        reply(200, {"ci_state": "success", "source_sha": SOURCE_SHA}),
        reply(200, {"ci_state": "failed", "source_sha": OTHER_SHA}),
        reply(403, {"error": "access_denied"}),
    ]


class QueueFetch:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, token):
        self.calls.append((url, token))
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class StagingSmokeAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.settings = smoke.SmokeSettings(
            base_url=BASE_URL,
            expected_host="smoke-fixture.onrender.com",
            tenant="tenant-alpha",
            project="project-visible",
            denied_tenant="tenant-beta",
            bearer_token=TENANT_TOKEN,
            denied_tenant_token=DENIED_TOKEN,
        )

    def assert_safe_failure(self, failure, expected_code):
        self.assertEqual(str(failure), expected_code)
        public_text = str(failure)
        self.assertNotIn(TENANT_TOKEN, public_text)
        self.assertNotIn(DENIED_TOKEN, public_text)
        self.assertNotIn(BASE_URL, public_text)

    def test_complete_six_call_read_only_acceptance_sequence(self):
        fetch = QueueFetch(accepted_sequence())
        self.assertIsNone(smoke.run_smoke(self.settings, fetch=fetch))
        self.assertEqual(fetch.calls, [
            (BASE_URL + "/healthz", None),
            (BASE_URL + "/readyz", None),
            (BASE_URL + "/v1/tenants/tenant-alpha/projects/project-visible/ci", None),
            (BASE_URL + "/v1/tenants/tenant-alpha/projects/project-visible/ci", TENANT_TOKEN),
            (BASE_URL + "/v1/tenants/tenant-beta/projects/project-visible/ci", DENIED_TOKEN),
            (BASE_URL + "/v1/tenants/tenant-beta/projects/project-visible/ci", TENANT_TOKEN),
        ])
        self.assertEqual(fetch.responses, [])

    def test_readiness_unavailable_fails_at_second_call(self):
        responses = accepted_sequence()
        responses[1] = reply(503)
        fetch = QueueFetch(responses)
        with self.assertRaises(smoke.SmokeFailure) as raised:
            smoke.run_smoke(self.settings, fetch=fetch)
        self.assert_safe_failure(raised.exception, "readiness_status")
        self.assertEqual(len(fetch.calls), 2)

    def test_liveness_requires_exact_no_store_directive(self):
        for cache in ("", "private", "no-store-extra", "public, no-cache"):
            with self.subTest(cache=cache):
                responses = accepted_sequence()
                responses[0] = reply(204, cache=cache)
                fetch = QueueFetch(responses)
                with self.assertRaises(smoke.SmokeFailure) as raised:
                    smoke.run_smoke(self.settings, fetch=fetch)
                self.assert_safe_failure(raised.exception, "liveness_cache")
                self.assertEqual(len(fetch.calls), 1)

    def test_unexpected_status_fails_closed(self):
        responses = accepted_sequence()
        responses[0] = reply(200)
        fetch = QueueFetch(responses)
        with self.assertRaises(smoke.SmokeFailure) as raised:
            smoke.run_smoke(self.settings, fetch=fetch)
        self.assert_safe_failure(raised.exception, "liveness_status")

    def test_empty_malformed_non_dict_and_oversized_json_are_rejected(self):
        cases = [
            (b"", "anonymous_format"),
            (b"{not-json", "anonymous_format"),
            (b"[]", "anonymous_format"),
            (b"x" * (smoke._BODY_LIMIT + 1), "anonymous_format"),
        ]
        for body, expected in cases:
            with self.subTest(expected=expected, size=len(body)):
                responses = accepted_sequence()
                responses[2] = reply(401, body)
                fetch = QueueFetch(responses)
                with self.assertRaises(smoke.SmokeFailure) as raised:
                    smoke.run_smoke(self.settings, fetch=fetch)
                self.assert_safe_failure(raised.exception, expected)
                self.assertEqual(len(fetch.calls), 3)

    def test_success_payload_requires_valid_full_sha_and_known_ci_state(self):
        bad_payloads = [
            {"ci_state": "success", "source_sha": "short"},
            {"ci_state": "success", "source_sha": "g" * 40},
            {"ci_state": "unknown", "source_sha": SOURCE_SHA},
            {"ci_state": "success", "source_sha": SOURCE_SHA, "extra": "field"},
        ]
        for value in bad_payloads:
            with self.subTest(value=value):
                responses = accepted_sequence()
                responses[3] = reply(200, value)
                fetch = QueueFetch(responses)
                with self.assertRaises(smoke.SmokeFailure) as raised:
                    smoke.run_smoke(self.settings, fetch=fetch)
                self.assert_safe_failure(raised.exception, "allowed_response")
                self.assertEqual(len(fetch.calls), 4)

    def test_nonexistent_denied_fixture_does_not_count_as_isolation(self):
        responses = accepted_sequence()
        responses[4] = reply(403, {"error": "access_denied"})
        fetch = QueueFetch(responses)
        with self.assertRaises(smoke.SmokeFailure) as raised:
            smoke.run_smoke(self.settings, fetch=fetch)
        self.assert_safe_failure(raised.exception, "denied_fixture_status")
        self.assertEqual(len(fetch.calls), 5)
        self.assertNotEqual(fetch.calls[-1][1], self.settings.bearer_token)

    def test_wrong_origin_hostname_scheme_path_or_credentials_are_rejected(self):
        invalid = [
            replace(self.settings, expected_host="other-fixture.onrender.com"),
            replace(self.settings, base_url="https://example.invalid"),
            replace(self.settings, base_url="http://smoke-fixture.onrender.com"),
            replace(self.settings, base_url=BASE_URL + "/api"),
            replace(self.settings, base_url="https://user:pass@smoke-fixture.onrender.com"),
            replace(self.settings, base_url=BASE_URL + "?token=synthetic"),
        ]
        for settings in invalid:
            with self.subTest(base_url=settings.base_url):
                with self.assertRaises(smoke.SmokeFailure) as raised:
                    settings.validate()
                self.assert_safe_failure(raised.exception, "invalid_staging_target")

    def test_duplicate_tokens_and_same_tenant_scope_are_rejected(self):
        with self.assertRaises(smoke.SmokeFailure) as raised:
            replace(self.settings, denied_tenant_token=TENANT_TOKEN).validate()
        self.assert_safe_failure(raised.exception, "invalid_staging_credentials")
        with self.assertRaises(smoke.SmokeFailure) as raised:
            replace(self.settings, denied_tenant=self.settings.tenant).validate()
        self.assert_safe_failure(raised.exception, "invalid_staging_scope")

    def test_network_exception_is_sanitized_by_real_fetch_adapter(self):
        class BrokenOpener:
            def open(self, request, timeout):
                raise RuntimeError("private-url=" + BASE_URL + " auth=" + TENANT_TOKEN)

        with patch.object(smoke.request, "build_opener", return_value=BrokenOpener()):
            with self.assertRaises(smoke.SmokeFailure) as raised:
                smoke.fetch_https(BASE_URL + "/healthz", TENANT_TOKEN)
        self.assert_safe_failure(raised.exception, "network_failure")

    def test_redirect_is_not_followed_and_becomes_status_failure(self):
        class RedirectRejectingOpener:
            def __init__(self, handlers):
                self.handlers = handlers
                self.followed = False

            def open(self, request, timeout):
                handler = next(h for h in self.handlers
                               if isinstance(h, smoke._RejectRedirects))
                redirected = handler.redirect_request(
                    request, None, 302, "Found", {}, "https://other.invalid/"
                )
                self.followed = redirected is not None
                raise HTTPError(request.full_url, 302, "Found", {}, io.BytesIO(b""))

        opener = RedirectRejectingOpener([smoke._RejectRedirects()])
        with patch.object(smoke.request, "build_opener", return_value=opener):
            fetch = QueueFetch([smoke.fetch_https(BASE_URL + "/healthz", None)])
            # The response captured from the mocked adapter is a rejected redirect.
            self.assertFalse(opener.followed)
            with self.assertRaises(smoke.SmokeFailure) as raised:
                smoke.run_smoke(self.settings, fetch=fetch)
        self.assert_safe_failure(raised.exception, "liveness_status")

    def test_accepted_headers_require_json_for_status_payloads(self):
        responses = accepted_sequence()
        responses[3] = reply(200, {"ci_state": "success", "source_sha": SOURCE_SHA},
                             content_type="text/plain")
        fetch = QueueFetch(responses)
        with self.assertRaises(smoke.SmokeFailure) as raised:
            smoke.run_smoke(self.settings, fetch=fetch)
        self.assert_safe_failure(raised.exception, "allowed_format")


if __name__ == "__main__":
    unittest.main()

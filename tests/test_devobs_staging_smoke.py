"""Offline behavior tests for an operator-only managed staging smoke gate."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib import request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from devobs_intelligence import staging_smoke as mod


class SmokeContractTests(unittest.TestCase):
    def settings(self, **changes):
        kwargs = {
            "base_url": "https://devobs-staging.onrender.com",
            "expected_host": "devobs-staging.onrender.com",
            "tenant": "alpha",
            "project": "shared",
            "denied_tenant": "beta",
            "bearer_token": "ey.ey." + "a" * 55,
        }
        kwargs.update(changes)
        return mod.SmokeSettings(**kwargs)

    def fake_transport(self, origin, bearer):
        suffix = origin.split(".onrender.com", 1)[-1]
        no_cache = {"cache-control": "no-store"}
        js = {"cache-control": "no-store", "content-type": "application/json"}
        if suffix in ("/healthz", "/readyz"):
            return 204, no_cache, b""
        if bearer is None:
            return 401, js, b'{"error":"invalid_token"}'
        if "/tenants/beta/" in suffix:
            return 403, js, b'{"error":"access_denied"}'
        return 200, js, ('{"ci_state":"success","source_sha":"' +
                         "a" * 40 + '"}').encode("ascii")

    def test_full_positive_negative_contract(self):
        paths = []
        def fetch(url, bearer):
            paths.append((url, bearer is not None))
            return self.fake_transport(url, bearer)
        mod.run_smoke(self.settings(), fetch=fetch)
        self.assertEqual([p[1] for p in paths],
                         [False, False, False, True, True])
        self.assertEqual(len(paths), 5)
        self.assertTrue(all("devobs-staging.onrender.com" in u for u, _ in paths))

    def test_rejects_untrusted_hosts_before_any_network_call(self):
        for url, host in [
            ("http://devobs-staging.onrender.com", "devobs-staging.onrender.com"),
            ("https://localhost", "localhost"),
            ("https://127.0.0.1", "127.0.0.1"),
            ("https://attacker.example", "attacker.example"),
            ("https://devobs-staging.onrender.com.attacker.test",
             "devobs-staging.onrender.com.attacker.test"),
            ("https://devobs-staging.onrender.com@attacker.test",
             "devobs-staging.onrender.com"),
            ("https://devobs-staging.onrender.com:8443",
             "devobs-staging.onrender.com"),
            ("https://devobs-staging.onrender.com/external",
             "devobs-staging.onrender.com"),
            ("https://devobs-staging.onrender.com?redirect=true",
             "devobs-staging.onrender.com"),
            ("https://devobs-staging.onrender.com#fragment",
             "devobs-staging.onrender.com"),
            ("https://onrender.com", "onrender.com"),
            ("https://devobs-staging.onrender.com",
             "different.onrender.com"),
        ]:
            with self.subTest(url=url):
                calls=[]
                with self.assertRaisesRegex(
                        mod.SmokeFailure, "invalid_staging_target"):
                    mod.run_smoke(
                        self.settings(base_url=url, expected_host=host),
                        fetch=lambda u,t: calls.append(u))
                self.assertEqual(calls, [])

    def test_scope_and_token_must_be_explicit_and_credible(self):
        for change in [
            {"denied_tenant": "alpha"},
            {"tenant": "alpha/../../etc"},
            {"tenant": ""},
            {"project": "white space"},
            {"denied_tenant": ""},
        ]:
            with self.subTest(change=change), self.assertRaisesRegex(
                    mod.SmokeFailure, "invalid_staging_scope"):
                mod.run_smoke(self.settings(**change),
                              fetch=lambda *x: self.fail("network"))
        for token in ("", "not_a_signed_token", "a.b.c", "a.b." + "x"*9000):
            with self.subTest(token=token), self.assertRaisesRegex(
                    mod.SmokeFailure, "invalid_staging_credentials"):
                mod.run_smoke(self.settings(bearer_token=token),
                              fetch=lambda *x: self.fail("network"))

    def test_denies_silent_unauthorized_tenant_access(self):
        def leak(url, token):
            if "/tenants/beta/" in url:
                return (200, {"content-type":"application/json",
                              "cache-control":"no-store"},
                        b'{"ci_state":"success","source_sha":"' +
                        b"a"*40 + b'"}')
            return self.fake_transport(url, token)
        with self.assertRaisesRegex(
                mod.SmokeFailure, "^tenant_isolation_status$"):
            mod.run_smoke(self.settings(), fetch=leak)

    def test_bad_readiness_and_redirects_fail_closed(self):
        for status in (302, 401, 403, 500, 200):
            with self.subTest(status=status):
                def fetch(url, token):
                    if url.endswith("/readyz"):
                        return status, {"cache-control": "no-store"}, b""
                    return self.fake_transport(url, token)
                with self.assertRaisesRegex(mod.SmokeFailure, "readiness_status"):
                    mod.run_smoke(self.settings(), fetch=fetch)

    def test_response_cache_and_shape_are_required(self):
        def fetch(url, token):
            status, headers, body = self.fake_transport(url, token)
            if "/tenants/alpha/" in url and token:
                return 200, {"content-type": "application/json"}, body
            return status, headers, body
        with self.assertRaisesRegex(mod.SmokeFailure, "allowed_cache"):
            mod.run_smoke(self.settings(), fetch=fetch)
        def oversized(url, token):
            status, headers, body = self.fake_transport(url, token)
            if "/tenants/alpha/" in url and token:
                return 200, headers, b"z" * 3000
            return status, headers, body
        with self.assertRaisesRegex(mod.SmokeFailure, "allowed_format"):
            mod.run_smoke(self.settings(), fetch=oversized)

    def test_no_redirect_is_ever_authorized(self):
        self.assertIsNone(mod._RejectRedirects().redirect_request(
            request.Request("https://devobs-staging.onrender.com/readyz"),
            None, 302, "moved", {}, "https://attacker.example/steal"))

    def test_cli_never_echoes_credentials_even_on_failure(self):
        bad = self.settings(bearer_token="SECRET-test-token")
        with patch.dict(mod.os.environ, {
                "DEVOBS_STAGING_BASE_URL": bad.base_url,
                "DEVOBS_STAGING_EXPECTED_HOST": bad.expected_host,
                "DEVOBS_STAGING_TENANT": bad.tenant,
                "DEVOBS_STAGING_PROJECT": bad.project,
                "DEVOBS_STAGING_DENIED_TENANT": bad.denied_tenant,
                "DEVOBS_STAGING_TOKEN": bad.bearer_token}, clear=True):
            with patch.object(mod.sys, "stderr") as output:
                self.assertEqual(mod.main(), 1)
                txt="".join(str(c) for c in output.write.call_args_list)
                self.assertNotIn(bad.bearer_token,txt)
                self.assertIn("invalid_staging_credentials",txt)


if __name__ == "__main__":
    unittest.main()

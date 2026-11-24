"""Synthetic tests for binding OTLP conversion to the existing tenant gate."""
from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from devobs_intelligence.oidc_tokens import AuthenticatedPrincipal  # noqa: E402
from devobs_intelligence.tenant_scope import Membership, ProjectSnapshot  # noqa: E402
from integrations.otlp_logs_traces_adapter import (  # noqa: E402
    OtlpAdapterError,
    ScopedOtlpConverter,
)

NOW = datetime.now(timezone.utc).replace(microsecond=0)
STAMP = str(int(NOW.timestamp()) * 1_000_000_000)


class SyntheticVerifier:
    """Resolver stub only; cryptographic token checks live in AccessTokenVerifier."""

    def verify(self, value: str) -> AuthenticatedPrincipal:
        principals = {
            "synthetic-reader": AuthenticatedPrincipal(
                "collector-alpha", frozenset({"devobs.read"})
            ),
            "synthetic-no-read": AuthenticatedPrincipal(
                "collector-alpha", frozenset({"profile.read"})
            ),
            "synthetic-other-tenant": AuthenticatedPrincipal(
                "collector-beta", frozenset({"devobs.read"})
            ),
        }
        if value not in principals:
            raise ValueError("synthetic verifier failure detail")
        return principals[value]


def otlp_logs() -> str:
    return json.dumps({
        "resourceLogs": [{
            "resource": {"attributes": [
                {"key": "service.name", "value": {"stringValue": "api"}},
            ]},
            "scopeLogs": [{"scope": {}, "logRecords": [{
                "timeUnixNano": STAMP,
                "attributes": [
                    {"key": "devobs.operation", "value": {"stringValue": "http.request"}},
                    {"key": "devobs.status", "value": {"stringValue": "error"}},
                ],
            }]}],
        }],
    })


class ScopedOtlpConverterTests(unittest.TestCase):
    def setUp(self):
        self.converter = ScopedOtlpConverter(
            SyntheticVerifier(),
            [
                Membership("tenant-alpha", "collector-alpha", "viewer", ("project-a",)),
                Membership("tenant-beta", "collector-beta", "viewer", ("project-a",)),
            ],
            [
                ProjectSnapshot("tenant-alpha", "project-a", "a" * 40, "success"),
                ProjectSnapshot("tenant-beta", "project-a", "b" * 40, "failed"),
            ],
        )

    def test_verified_identity_membership_and_snapshot_set_output_scope(self):
        signals = self.converter.convert(
            otlp_logs(), access_token="synthetic-reader", tenant="tenant-alpha",
            project="project-a", now_utc=NOW,
        )
        signal, = signals
        self.assertEqual(
            (signal.tenant, signal.project, signal.source_sha),
            ("tenant-alpha", "project-a", "a" * 40),
        )

    def test_no_scope_or_wrong_membership_is_denied_without_scope_leakage(self):
        requests = (
            ("synthetic-no-read", "tenant-alpha", "project-a"),
            ("synthetic-reader", "tenant-beta", "project-a"),
            ("synthetic-reader", "tenant-alpha", "unlisted-project"),
            ("unknown-synthetic", "tenant-alpha", "project-a"),
        )
        for token, tenant, project in requests:
            with self.subTest(tenant=tenant, project=project):
                with self.assertRaises(OtlpAdapterError) as caught:
                    self.converter.convert(
                        otlp_logs(), access_token=token, tenant=tenant,
                        project=project, now_utc=NOW,
                    )
                self.assertEqual(str(caught.exception), "scope_denied")

    def test_client_cannot_supply_source_sha_or_change_the_tenant_snapshot(self):
        with self.assertRaises(TypeError):
            self.converter.convert(
                otlp_logs(), access_token="synthetic-reader", tenant="tenant-alpha",
                project="project-a", source_sha="b" * 40, now_utc=NOW,
            )
        tampered = json.loads(otlp_logs()) | {"source_sha": "b" * 40}
        with self.assertRaises(OtlpAdapterError):
            self.converter.convert(
                json.dumps(tampered), access_token="synthetic-reader",
                tenant="tenant-alpha", project="project-a", now_utc=NOW,
            )

    def test_missing_verifier_fails_at_construction(self):
        with self.assertRaisesRegex(ValueError, "^invalid_trust_boundary$"):
            ScopedOtlpConverter(object(), [], [])


if __name__ == "__main__":
    unittest.main()

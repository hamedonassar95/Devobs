"""Synthetic tests for binding OTLP conversion to the existing tenant gate."""
from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from devobs_intelligence.oidc_tokens import AuthenticatedPrincipal  # noqa: E402
from devobs_intelligence.context import ServiceTopologySnapshot  # noqa: E402
from devobs_intelligence.tenant_scope import Membership, ProjectSnapshot  # noqa: E402
from devobs_intelligence.topology_attestation import (  # noqa: E402
    VerifiedTopologyAttestation,
)
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


def otlp_logs(service: str = "api") -> str:
    return json.dumps({
        "resourceLogs": [{
            "resource": {"attributes": [
                {"key": "service.name", "value": {"stringValue": service}},
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


def synthetic_verified_topology(
        services: list[str] | None = None, *, source_sha: str = "a" * 40
        ) -> VerifiedTopologyAttestation:
    """Result stub returned by a mocked verifier; it is not a signed fixture."""
    snapshot = ServiceTopologySnapshot(
        "tenant-alpha", "project-a", services or ["api"], [], source_sha,
        NOW.isoformat(),
    )
    return VerifiedTopologyAttestation(snapshot, "synthetic-topology-key", "c" * 64)


def synthetic_topology_public_keys() -> dict[tuple[str, str, str], bytes]:
    """Public-key-shaped fixture; cryptographic verification is mocked here."""
    return {("tenant-alpha", "project-a", "synthetic-topology-key"): b"x" * 32}


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
            {("tenant-alpha", "project-a"): {"synthetic-envelope": True}},
            synthetic_topology_public_keys(),
        )

    def test_verified_identity_membership_and_snapshot_set_output_scope(self):
        with patch(
            "devobs_intelligence.topology_attestation.verify_topology_attestation",
            return_value=synthetic_verified_topology(),
        ) as verify:
            signals = self.converter.convert(
                otlp_logs(), access_token="synthetic-reader", tenant="tenant-alpha",
                project="project-a", now_utc=NOW,
            )
        verify.assert_called_once_with(
            {"synthetic-envelope": True}, synthetic_topology_public_keys(),
            expected_tenant="tenant-alpha", expected_project="project-a",
            expected_source_sha="a" * 40, now=NOW, max_age_seconds=900,
        )
        signal, = signals
        self.assertEqual(
            (signal.tenant, signal.project, signal.source_sha),
            ("tenant-alpha", "project-a", "a" * 40),
        )
        self.assertEqual(signal.service, "api")

    def test_telemetry_service_must_be_in_the_verified_topology(self):
        with patch(
            "devobs_intelligence.topology_attestation.verify_topology_attestation",
            return_value=synthetic_verified_topology(["api"]),
        ):
            with self.assertRaisesRegex(OtlpAdapterError, "^service_scope_denied$"):
                self.converter.convert(
                    otlp_logs("unlisted-service"), access_token="synthetic-reader",
                    tenant="tenant-alpha", project="project-a", now_utc=NOW,
                )

    def test_topology_verification_is_bound_to_scope_and_source_snapshot(self):
        for bad_topology in (
            synthetic_verified_topology(["api"], source_sha="b" * 40),
            object(),
        ):
            with self.subTest(topology=type(bad_topology).__name__):
                with patch(
                    "devobs_intelligence.topology_attestation.verify_topology_attestation",
                    return_value=bad_topology,
                ):
                    with self.assertRaisesRegex(
                            OtlpAdapterError, "^service_topology_unverified$"):
                        self.converter.convert(
                            otlp_logs(), access_token="synthetic-reader",
                            tenant="tenant-alpha", project="project-a", now_utc=NOW,
                        )

    def test_missing_project_attestation_fails_closed(self):
        converter = ScopedOtlpConverter(
            SyntheticVerifier(),
            [Membership("tenant-alpha", "collector-alpha", "viewer", ("project-a",))],
            [ProjectSnapshot("tenant-alpha", "project-a", "a" * 40, "success")],
            {("tenant-beta", "project-a"): {"synthetic-envelope": True}},
            synthetic_topology_public_keys(),
        )
        with self.assertRaisesRegex(OtlpAdapterError, "^service_topology_unverified$"):
            converter.convert(
                otlp_logs(), access_token="synthetic-reader", tenant="tenant-alpha",
                project="project-a", now_utc=NOW,
            )

    def test_topology_envelope_configuration_is_copied_at_construction(self):
        envelope = {"synthetic-envelope": True}
        converter = ScopedOtlpConverter(
            SyntheticVerifier(),
            [Membership("tenant-alpha", "collector-alpha", "viewer", ("project-a",))],
            [ProjectSnapshot("tenant-alpha", "project-a", "a" * 40, "success")],
            {("tenant-alpha", "project-a"): envelope},
            synthetic_topology_public_keys(),
        )
        envelope["synthetic-envelope"] = False
        with patch(
            "devobs_intelligence.topology_attestation.verify_topology_attestation",
            return_value=synthetic_verified_topology(),
        ) as verify:
            converter.convert(
                otlp_logs(), access_token="synthetic-reader", tenant="tenant-alpha",
                project="project-a", now_utc=NOW,
            )
        self.assertEqual(verify.call_args.args[0], {"synthetic-envelope": True})

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
            ScopedOtlpConverter(object(), [], [], {}, {})

    def test_missing_topology_configuration_fails_at_construction(self):
        with self.assertRaisesRegex(ValueError, "^invalid_trust_boundary$"):
            ScopedOtlpConverter(SyntheticVerifier(), [], [], {}, {})

    def test_missing_topology_trust_keys_fail_at_construction(self):
        with self.assertRaisesRegex(ValueError, "^invalid_trust_boundary$"):
            ScopedOtlpConverter(
                SyntheticVerifier(), [], [],
                {("tenant-alpha", "project-a"): {"synthetic-envelope": True}}, {},
            )


if __name__ == "__main__":
    unittest.main()

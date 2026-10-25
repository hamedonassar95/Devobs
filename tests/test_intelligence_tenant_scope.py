"""Tenant-scoped access tests: no network, no OAuth assertion and no live data."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from devobs_intelligence.tenant_scope import AccessDenied, OfflineTenantGate, Membership, ProjectSnapshot

SHA = "a" * 40
MEMBERSHIPS = [
    Membership("tenant-alpha", "alice", "viewer", ("project-1",)),
    Membership("tenant-alpha", "editor", "operator", ("project-1",)),
    Membership("tenant-beta", "bob", "owner", ("project-1",)),
]
SNAPSHOTS = [
    ProjectSnapshot("tenant-alpha", "project-1", SHA, "success"),
    ProjectSnapshot("tenant-alpha", "private-other", "b" * 40, "failed"),
    ProjectSnapshot("tenant-beta", "project-1", "c" * 40, "failed"),
]


def identity(token):
    return {"valid-alice": "alice", "valid-editor": "editor", "valid-bob": "bob"}.get(token)


class TenantScopeTests(unittest.TestCase):
    def setUp(self):
        self.gate = OfflineTenantGate(identity, MEMBERSHIPS, SNAPSHOTS)

    def test_tenant_scoped_viewer_reads_only_authorized_snapshot(self):
        result = self.gate.read_status("valid-alice", "tenant-alpha", "project-1")
        self.assertEqual(result, {"ci_state": "success", "source_sha": SHA})
        self.assertNotIn("tenant-alpha", str(result))

    def test_cross_tenant_same_project_id_denied(self):
        with self.assertRaisesRegex(AccessDenied, "^access_denied$"):
            self.gate.read_status("valid-alice", "tenant-beta", "project-1")

    def test_same_tenant_ungranted_project_denied(self):
        with self.assertRaisesRegex(AccessDenied, "^access_denied$"):
            self.gate.read_status("valid-alice", "tenant-alpha", "private-other")

    def test_missing_token_denied(self):
        for token in (None, "", "unverified"):
            with self.subTest(token=token), self.assertRaisesRegex(AccessDenied, "^access_denied$"):
                self.gate.read_status(token, "tenant-alpha", "project-1")

    def test_token_verifier_errors_fail_closed_without_leakage(self):
        def broken(_): raise RuntimeError("PRIVATE_BEARER_TOKEN")
        gate = OfflineTenantGate(broken, MEMBERSHIPS, SNAPSHOTS)
        with self.assertRaises(AccessDenied) as caught:
            gate.read_status("some-token", "tenant-alpha", "project-1")
        self.assertEqual(str(caught.exception), "access_denied")

    def test_read_only_role_cannot_propose_write(self):
        with self.assertRaisesRegex(AccessDenied, "^access_denied$"):
            self.gate.propose_change("valid-alice", "tenant-alpha", "project-1")

    def test_operator_can_propose_but_not_execute(self):
        result = self.gate.propose_change("valid-editor", "tenant-alpha", "project-1")
        self.assertEqual(result["decision"], "PROPOSE_ONLY")
        self.assertEqual(result["source_sha"], SHA)
        self.assertNotIn("APPROVED", str(result))
        with self.assertRaises(AccessDenied):
            self.gate.execute("valid-editor", "tenant-alpha", "project-1")

    def test_unknown_resource_and_tenant_have_identical_denial(self):
        outputs = []
        for tenant, project in (("tenant-not-found", "project-1"), ("tenant-alpha", "project-not-found")):
            try:
                self.gate.read_status("valid-alice", tenant, project)
            except AccessDenied as exc:
                outputs.append(str(exc))
        self.assertEqual(outputs, ["access_denied", "access_denied"])

    def test_duplicate_and_bad_record_config_fail_closed(self):
        with self.assertRaises(ValueError):
            OfflineTenantGate(identity, MEMBERSHIPS, SNAPSHOTS + [SNAPSHOTS[0]])
        with self.assertRaises(ValueError):
            OfflineTenantGate(identity, MEMBERSHIPS + [MEMBERSHIPS[0]], SNAPSHOTS)
        with self.assertRaises(ValueError):
            ProjectSnapshot("tenant-alpha", "project-1", "invalid-sha", "success")

    def test_cannot_choose_role_or_actor_from_request(self):
        with self.assertRaisesRegex(AccessDenied, "^access_denied$"):
            self.gate.read_status("valid-alice", "tenant-alpha", "private-other", role="owner", actor="editor")

    def test_different_tenant_owner_does_not_access_first_tenant(self):
        with self.assertRaisesRegex(AccessDenied, "^access_denied$"):
            self.gate.read_status("valid-bob", "tenant-alpha", "project-1")


if __name__ == "__main__":
    unittest.main()

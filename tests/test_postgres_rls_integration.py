"""REAL PostgreSQL RLS integration tests; require ephemeral CI database only.

Never run with a production connection string. Run in a disposable DB with:
PG_TEST_ADMIN_DSN, PG_TEST_READER_DSN.
"""
import json
import os
import sys
import time
import unittest
from unittest.mock import patch
from pathlib import Path
from wsgiref.util import setup_testing_defaults

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
try:
    import psycopg
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    from devobs_intelligence.postgres_store import PostgresTenantStore, StorageUnavailable
    from devobs_intelligence.api_app import make_app
    from devobs_intelligence.oidc_tokens import AccessTokenVerifier
except ImportError:
    psycopg = None

ROOT = Path(__file__).resolve().parents[1]
ADMIN_DSN = os.getenv("PG_TEST_ADMIN_DSN")
READER_DSN = os.getenv("PG_TEST_READER_DSN")


@unittest.skipUnless(ADMIN_DSN and READER_DSN and psycopg, "requires disposable PostgreSQL service")
class PostgresTenantRLSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = psycopg.connect(ADMIN_DSN, autocommit=True)
        cls.admin.execute((ROOT / "deploy/postgres/001_tenant_rls.sql").read_text())
        cls.admin.execute((ROOT / "deploy/postgres/002_service_registry.sql").read_text())
        # This login role is a CI fixture only, with NO credentials or admin rights.
        cls.admin.execute("CREATE ROLE devobs_ci_reader LOGIN INHERIT NOBYPASSRLS")
        cls.admin.execute("GRANT devobs_ai_reader TO devobs_ci_reader")
        cls.admin.execute(
            "INSERT INTO devobs_ai.project_ci VALUES (%s,%s,%s,%s),(%s,%s,%s,%s),(%s,%s,%s,%s)",
            ("alpha","shared","a"*40,"success",
             "beta","shared","b"*40,"failed",
             "alpha","hidden","c"*40,"failed"))
        cls.admin.execute(
            "INSERT INTO devobs_ai.memberships VALUES (%s,%s,%s),(%s,%s,%s)",
            ("alpha","shared","alice","beta","shared","bob"))
        cls.admin.execute(
            "INSERT INTO devobs_ai.service_registry VALUES "
            "(%s,%s,%s),(%s,%s,%s),(%s,%s,%s)",
            ("alpha", "shared", "collector", "beta", "shared", "collector",
             "alpha", "hidden", "private-service"))
        cls.store = PostgresTenantStore(READER_DSN)

    @classmethod
    def tearDownClass(cls):
        cls.admin.close()  # Ephemeral CI service destroys fixture DB.

    def test_database_enables_and_forces_rls(self):
        with self.admin.cursor() as cur:
            cur.execute("""SELECT relname, relrowsecurity, relforcerowsecurity
                           FROM pg_class WHERE oid IN
                            ('devobs_ai.project_ci'::regclass,
                             'devobs_ai.memberships'::regclass,
                             'devobs_ai.service_registry'::regclass)""")
            rows = cur.fetchall()
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(enabled and forced for _,enabled,forced in rows))

    def test_readonly_runtime_role_is_not_owner_or_bypass(self):
        with psycopg.connect(READER_DSN, autocommit=True) as conn:
            flags = conn.execute(
                """SELECT rolsuper, rolbypassrls, pg_has_role(current_user, 'devobs_ai_reader', 'USAGE')
                   FROM pg_roles WHERE rolname=current_user"""
            ).fetchone()
            self.assertEqual(flags, (False,False,True))
            self.assertEqual(conn.execute("SELECT count(*) FROM devobs_ai.project_ci").fetchone(), (0,))
            self.assertEqual(conn.execute("SELECT count(*) FROM devobs_ai.memberships").fetchone(), (0,))
            self.assertEqual(conn.execute("SELECT count(*) FROM devobs_ai.service_registry").fetchone(), (0,))
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                conn.execute("UPDATE devobs_ai.project_ci SET ci_state='success'")
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                conn.execute("UPDATE devobs_ai.service_registry SET service_id='changed'")

    def test_readiness_refuses_extra_write_privileges(self):
        self.assertIs(self.store.probe_readiness(), True)
        # Disposable integration DB only. A leaked write grant must block readiness.
        for table in ("project_ci", "memberships", "service_registry"):
            with self.subTest(table=table):
                self.admin.execute(f"GRANT UPDATE ON devobs_ai.{table} TO devobs_ci_reader")
                try:
                    with self.assertRaisesRegex(StorageUnavailable, "^unsafe_database_schema$"):
                        self.store.probe_readiness()
                finally:
                    self.admin.execute(f"REVOKE UPDATE ON devobs_ai.{table} FROM devobs_ci_reader")
                self.assertIs(self.store.probe_readiness(), True)

    def test_readiness_refuses_disabled_rls_on_each_table(self):
        # CI fixture only. Never change an external/customer database.
        self.assertIs(self.store.probe_readiness(), True)
        for table in ("project_ci", "memberships", "service_registry"):
            with self.subTest(table=table):
                # Table names come from fixed trusted test fixtures, not inputs.
                self.admin.execute(f"ALTER TABLE devobs_ai.{table} DISABLE ROW LEVEL SECURITY")
                try:
                    with self.assertRaisesRegex(StorageUnavailable, "^unsafe_database_schema$"):
                        self.store.probe_readiness()
                finally:
                    self.admin.execute(f"ALTER TABLE devobs_ai.{table} ENABLE ROW LEVEL SECURITY")
                self.assertIs(self.store.probe_readiness(), True)

    def test_readiness_refuses_missing_select_on_each_table(self):
        # Simulates privilege drift using only the disposable PostgreSQL CI DB.
        self.assertIs(self.store.probe_readiness(), True)
        for table in ("project_ci", "memberships", "service_registry"):
            with self.subTest(table=table):
                self.admin.execute(
                    f"REVOKE SELECT ON devobs_ai.{table} FROM devobs_ai_reader")
                try:
                    with self.assertRaisesRegex(StorageUnavailable, "^unsafe_database_schema$"):
                        self.store.probe_readiness()
                finally:
                    self.admin.execute(
                        f"GRANT SELECT ON devobs_ai.{table} TO devobs_ai_reader")
                self.assertIs(self.store.probe_readiness(), True)

    def test_readiness_rejects_unexpected_permissive_rls_policy(self):
        # Database belongs exclusively to disposable GitHub CI.
        # An extra OR-combined RLS policy can widen access without disabling RLS.
        self.assertIs(self.store.probe_readiness(), True)
        self.admin.execute(
            "CREATE POLICY ci_broad_read ON devobs_ai.project_ci "
            "FOR SELECT TO devobs_ai_reader USING (true)")
        try:
            # API denies access even if database policy protection drifts.
            with self.assertRaisesRegex(
                    StorageUnavailable, "^unsafe_database_schema$"):
                self.store.read_status("alice", "beta", "shared")
            with self.assertRaisesRegex(
                    StorageUnavailable, "^unsafe_database_schema$"):
                self.store.probe_readiness()
        finally:
            self.admin.execute("DROP POLICY ci_broad_read ON devobs_ai.project_ci")
        self.assertIs(self.store.probe_readiness(), True)

    def test_readiness_rejects_changed_policy_body(self):
        # Same policy name, roles and kind; only its expression drifts.
        # Run exclusively against the disposable PostgreSQL Actions service.
        self.assertIs(self.store.probe_readiness(), True)
        self.admin.execute(
            "ALTER POLICY devobs_project_member_read ON devobs_ai.project_ci "
            "USING (true)"
        )
        try:
            # API denies access even if database policy protection drifts.
            with self.assertRaisesRegex(
                    StorageUnavailable, "^unsafe_database_schema$"):
                self.store.read_status("alice", "beta", "shared")
            with self.assertRaisesRegex(
                    StorageUnavailable, "^unsafe_database_schema$"):
                self.store.probe_readiness()
        finally:
            self.admin.execute(
                "ALTER POLICY devobs_project_member_read ON devobs_ai.project_ci "
                "USING (tenant_id = NULLIF(current_setting('devobs_ai.tenant_id', true), '') "
                "AND EXISTS (SELECT 1 FROM devobs_ai.memberships AS m "
                "WHERE m.tenant_id = project_ci.tenant_id "
                "AND m.project_id = project_ci.project_id "
                "AND m.subject_id = NULLIF(current_setting('devobs_ai.subject_id', true), '')))"
            )
        self.assertIs(self.store.probe_readiness(), True)

    def test_readiness_rejects_changed_membership_policy_body(self):
        self.assertIs(self.store.probe_readiness(), True)
        self.admin.execute(
            "ALTER POLICY devobs_membership_self ON devobs_ai.memberships "
            "USING (true)"
        )
        try:
            # The reader now sees rows that should be hidden when no scope
            # is set, even though the policy inventory is unchanged.
            with psycopg.connect(READER_DSN, autocommit=True) as conn:
                self.assertGreater(
                    conn.execute("SELECT count(*) FROM devobs_ai.memberships"
                                 ).fetchone()[0], 0
                )
            with self.assertRaisesRegex(
                    StorageUnavailable, "^unsafe_database_schema$"):
                self.store.probe_readiness()
        finally:
            self.admin.execute(
                "ALTER POLICY devobs_membership_self ON devobs_ai.memberships "
                "USING (tenant_id = NULLIF(current_setting('devobs_ai.tenant_id', true), '') "
                "AND subject_id = NULLIF(current_setting('devobs_ai.subject_id', true), ''))"
            )
        self.assertIs(self.store.probe_readiness(), True)

    def test_readiness_rejects_changed_service_policy_body(self):
        self.assertIs(self.store.probe_readiness(), True)
        self.admin.execute(
            "ALTER POLICY devobs_service_member_read ON devobs_ai.service_registry "
            "USING (true)"
        )
        try:
            # Existing rows become visible without a tenant/subject context.
            with psycopg.connect(READER_DSN, autocommit=True) as conn:
                self.assertGreater(
                    conn.execute("SELECT count(*) FROM devobs_ai.service_registry").fetchone()[0], 0
                )
            with self.assertRaisesRegex(StorageUnavailable, "^unsafe_database_schema$"):
                self.store.authorize_service("alice", "alpha", "shared", "collector")
            with self.assertRaisesRegex(StorageUnavailable, "^unsafe_database_schema$"):
                self.store.probe_readiness()
        finally:
            self.admin.execute(
                "ALTER POLICY devobs_service_member_read ON devobs_ai.service_registry "
                "USING (tenant_id = NULLIF(current_setting('devobs_ai.tenant_id', true), '') "
                "AND EXISTS (SELECT 1 FROM devobs_ai.memberships AS m "
                "WHERE m.tenant_id = service_registry.tenant_id "
                "AND m.project_id = service_registry.project_id "
                "AND m.subject_id = NULLIF(current_setting('devobs_ai.subject_id', true), '')))"
            )
        self.assertIs(self.store.probe_readiness(), True)

    def test_runtime_read_denies_original_policy_body_drift(self):
        # Read endpoint must fail closed even between Render readiness probes.
        # Disposable PostgreSQL in CI only; test owns the migration role.
        self.assertIs(self.store.probe_readiness(), True)
        self.admin.execute(
            "ALTER POLICY devobs_project_member_read ON devobs_ai.project_ci "
            "USING (true)"
        )
        try:
            with self.assertRaisesRegex(
                    StorageUnavailable, "^unsafe_database_schema$"):
                self.store.read_status("alice", "beta", "shared")
        finally:
            self.admin.execute(
                "ALTER POLICY devobs_project_member_read ON devobs_ai.project_ci "
                "USING (tenant_id = NULLIF(current_setting('devobs_ai.tenant_id', true), '') "
                "AND EXISTS (SELECT 1 FROM devobs_ai.memberships AS m "
                "WHERE m.tenant_id = project_ci.tenant_id "
                "AND m.project_id = project_ci.project_id "
                "AND m.subject_id = NULLIF(current_setting('devobs_ai.subject_id', true), '')))"
            )
        self.assertIs(self.store.probe_readiness(), True)

    def test_runtime_read_denies_added_broad_policy(self):
        self.admin.execute(
            "CREATE POLICY ci_broad_read ON devobs_ai.project_ci "
            "FOR SELECT TO devobs_ai_reader USING (true)"
        )
        try:
            with self.assertRaisesRegex(
                    StorageUnavailable, "^unsafe_database_schema$"):
                self.store.read_status("alice", "beta", "shared")
        finally:
            self.admin.execute("DROP POLICY ci_broad_read ON devobs_ai.project_ci")

    def test_runtime_holds_access_share_locks_before_policy_check(self):
        # A concurrent migration must not alter the protected tables after
        # the policy check but before the tenant-scoped read. Only CI fixture.
        original = PostgresTenantStore._verify_readonly_contract
        blocked = []

        def check_inside_active_transaction(connection):
            for table in ("memberships", "project_ci", "service_registry"):
                # Identifier is a hardcoded fixture, not user input.
                with psycopg.connect(ADMIN_DSN, autocommit=True) as migrator:
                    try:
                        with migrator.transaction():
                            migrator.execute(
                                f"LOCK TABLE devobs_ai.{table} "
                                "IN ACCESS EXCLUSIVE MODE NOWAIT"
                            )
                    except psycopg.errors.LockNotAvailable:
                        blocked.append(table)
            return original(connection)

        with patch.object(
                PostgresTenantStore, "_verify_readonly_contract",
                staticmethod(check_inside_active_transaction)):
            self.assertEqual(
                self.store.read_status("alice", "alpha", "shared")["source_sha"],
                "a" * 40
            )
        self.assertEqual(blocked, ["memberships", "project_ci", "service_registry"])

    def test_exact_tenant_and_subject_match(self):
        self.assertEqual(self.store.read_status("alice","alpha","shared"),
                         {"ci_state":"success","source_sha":"a"*40})
        self.assertEqual(self.store.read_status("bob","beta","shared"),
                         {"ci_state":"failed","source_sha":"b"*40})

    def test_same_project_id_cross_tenant_and_unknown_denied(self):
        for subject,tenant,project in [
            ("alice","beta","shared"),("bob","alpha","shared"),
            ("alice","alpha","hidden"),("alice","missing","shared"),
            ("alice","alpha","missing"),("unknown","alpha","shared"),
        ]:
            with self.subTest(subject=subject,tenant=tenant,project=project):
                with self.assertRaisesRegex(ValueError,"^access_denied$"):
                    self.store.read_status(subject,tenant,project)

    def test_registered_service_requires_exact_member_tenant_project_and_service(self):
        self.assertIs(self.store.authorize_service("alice", "alpha", "shared", "collector"), True)
        self.assertIs(self.store.authorize_service("bob", "beta", "shared", "collector"), True)
        for subject, tenant, project, service_id in [
            ("alice", "beta", "shared", "collector"),
            ("bob", "alpha", "shared", "collector"),
            ("alice", "alpha", "hidden", "private-service"),
            ("unknown", "alpha", "shared", "collector"),
            ("alice", "alpha", "shared", "missing-service"),
            ("alice", "alpha", "missing", "collector"),
            ("alice", "missing", "shared", "collector"),
        ]:
            with self.subTest(subject=subject, tenant=tenant, project=project, service=service_id):
                self.assertIs(
                    self.store.authorize_service(subject, tenant, project, service_id), False
                )

    def test_invalid_service_scope_is_denied_before_database_connect(self):
        with patch("devobs_intelligence.postgres_store.psycopg.connect") as connect:
            for subject, tenant, project, service_id in [
                ("alice", "alpha' OR true --", "shared", "collector"),
                ("alice", "alpha", "../shared", "collector"),
                ("alice", "alpha", "shared", "collector;DROP TABLE"),
                ("", "alpha", "shared", "collector"),
            ]:
                with self.subTest(subject=subject, tenant=tenant, project=project, service=service_id):
                    with self.assertRaisesRegex(ValueError, "^access_denied$"):
                        self.store.authorize_service(subject, tenant, project, service_id)
        connect.assert_not_called()

    def test_context_does_not_survive_read_transaction(self):
        # Two identities are served by separate short-lived transactions.
        self.assertIs(self.store.authorize_service(
            "alice", "alpha", "shared", "collector"), True)
        self.store.read_status("alice","alpha","shared")
        self.store.read_status("bob","beta","shared")
        with psycopg.connect(READER_DSN, autocommit=True) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM devobs_ai.project_ci").fetchone(), (0,))

    def test_admin_connection_refused_by_read_adapter(self):
        with self.assertRaisesRegex(StorageUnavailable,"^unsafe_database_role$"):
            PostgresTenantStore(ADMIN_DSN).read_status("alice","alpha","shared")
        with self.assertRaisesRegex(StorageUnavailable,"^unsafe_database_role$"):
            PostgresTenantStore(ADMIN_DSN).authorize_service(
                "alice", "alpha", "shared", "collector")

    def test_invalid_scope_rejected_before_database_connect(self):
        for subject,tenant,project in [
            ("alice","alpha' OR true --","shared"),("alice","alpha","../shared"),
            ("alice","", "shared"),("", "alpha", "shared"),
        ]:
            with self.subTest(tenant=tenant):
                with self.assertRaisesRegex(ValueError,"^access_denied$"):
                    self.store.read_status(subject,tenant,project)

    def test_wsgiread_verified_signed_token_to_rls(self):
        private = rsa.generate_private_key(public_exponent=65537,key_size=2048)
        public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
        public.update(kid="rsa-one",alg="RS256",use="sig")
        verifier=AccessTokenVerifier("https://issuer.example.test","devobs-api","devobs-client",{"keys":[public]})
        app=make_app(verifier,self.store)
        def request(tenant,subject):
            now=int(time.time())
            token=jwt.encode({"iss":"https://issuer.example.test","aud":"devobs-api",
                        "sub":subject,"client_id":"devobs-client","iat":now,"exp":now+300,
                        "jti":"test-only","scope":"devobs.read"},
                        private,algorithm="RS256",headers={"typ":"at+jwt","kid":"rsa-one"})
            env={};setup_testing_defaults(env)
            env["REQUEST_METHOD"]="GET"
            env["PATH_INFO"]=f"/v1/tenants/{tenant}/projects/shared/ci"
            env["HTTP_AUTHORIZATION"]="Bearer "+token
            statuses=[]
            response=b"".join(app(env,lambda status,headers:statuses.append(status)))
            return statuses[0],json.loads(response)
        self.assertEqual(request("alpha","alice")[1]["source_sha"],"a"*40)
        self.assertEqual(request("beta","bob")[1]["source_sha"],"b"*40)
        self.assertTrue(request("beta","alice")[0].startswith("403"))
        self.assertTrue(request("alpha","bob")[0].startswith("403"))

    def test_missing_database_not_claimed_as_denial(self):
        # Reject a credentialed runtime pointing to a wrong/inaccessible DB.
        unavailable = PostgresTenantStore(
            "host=127.0.0.1 port=1 dbname=absent connect_timeout=1")
        with self.assertRaises(StorageUnavailable):
            unavailable.read_status("alice", "alpha", "shared")
        with self.assertRaises(StorageUnavailable):
            unavailable.authorize_service("alice", "alpha", "shared", "collector")


if __name__=="__main__": unittest.main()

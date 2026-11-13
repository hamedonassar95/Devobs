"""REAL PostgreSQL RLS integration tests; require ephemeral CI database only.

Never run with a production connection string. Run in a disposable DB with:
PG_TEST_ADMIN_DSN, PG_TEST_READER_DSN.
"""
import json
import importlib
import io
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
    from psycopg.conninfo import make_conninfo
    from devobs_intelligence.postgres_store import PostgresTenantStore, StorageUnavailable
except ImportError:
    psycopg = None

ROOT = Path(__file__).resolve().parents[1]
ADMIN_DSN = os.getenv("PG_TEST_ADMIN_DSN")
READER_DSN = os.getenv("PG_TEST_READER_DSN")
_REAL_PG_CONNECT = psycopg.connect if psycopg else None

# GitHub's dedicated postgres-rls job must not silently skip the suite if its
# disposable service or fixture DSNs are missing. GITHUB_JOB is a documented
# default variable identifying the current job:
# https://docs.github.com/en/actions/reference/workflows-and-actions/variables#default-environment-variables
# Local and other CI jobs may skip without a disposable PostgreSQL service.
if (os.getenv("GITHUB_JOB") == "postgres-rls"
        and not (ADMIN_DSN and READER_DSN and psycopg)):
    raise RuntimeError("disposable_postgres_fixture_required")


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

        # The staging entrypoint validates production's normal TLS contract.
        # Its synthetic DSN is rewritten only at the psycopg boundary below so
        # the test does not claim certificate verification for this CI fixture.
        cls.staging_dsn = make_conninfo(
            READER_DSN,
            password="synthetic-ci-only-password",
            sslmode="verify-full",
            sslrootcert="/tmp/devobs-disposable-ci-ca.pem",
        )
        cls.issuer = "https://issuer.example.test"
        cls.audience = "devobs-api"
        cls.client_id = "devobs-ci-staging"
        cls.private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048)
        public_jwk = json.loads(
            jwt.algorithms.RSAAlgorithm.to_jwk(cls.private_key.public_key()))
        public_jwk.update(kid="ci-rsa-one", alg="RS256", use="sig")
        cls.staging_settings = {
            "DEVOBS_OIDC_ISSUER": cls.issuer,
            "DEVOBS_OIDC_AUDIENCE": cls.audience,
            "DEVOBS_OIDC_CLIENT_ID": cls.client_id,
            "DEVOBS_OIDC_METADATA_JSON": json.dumps({
                "issuer": cls.issuer,
                "jwks_uri": cls.issuer + "/.well-known/jwks.json",
            }),
            "DEVOBS_OIDC_JWKS_JSON": json.dumps({"keys": [public_jwk]}),
            "DEVOBS_PG_DSN": cls.staging_dsn,
            "DEVOBS_AI_DIAGNOSTICS_ENABLED": "false",
            "DEVOBS_OTEL_METRICS_ENABLED": "false",
            "DEVOBS_OTEL_METRICS_LOCAL_ONLY": "false",
        }
        # staging_app intentionally bootstraps from process environment on
        # Gunicorn import. Import here under scoped synthetic settings; tests
        # below call build_app() directly with the same non-production config.
        with patch.dict(os.environ, cls.staging_settings, clear=True):
            cls.staging_module = importlib.import_module(
                "devobs_intelligence.staging_app")

    @classmethod
    def tearDownClass(cls):
        cls.admin.close()  # Ephemeral CI service destroys fixture DB.

    def build_staging_app(self, settings=None):
        return self.staging_module.build_app(
            dict(self.staging_settings if settings is None else settings))

    def issue_token(self, subject="alice", scope="devobs.read"):
        now = int(time.time())
        return jwt.encode(
            {"iss": self.issuer, "aud": self.audience, "sub": subject,
             "client_id": self.client_id, "iat": now, "exp": now + 300,
             "jti": "synthetic-ci-token", "scope": scope},
            self.private_key,
            algorithm="RS256",
            headers={"typ": "at+jwt", "kid": "ci-rsa-one"},
        )

    @staticmethod
    def wsgi_request(app, path, *, token=None, method="GET", body=b""):
        environ = {}
        setup_testing_defaults(environ)
        environ.update({
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "HTTP_AUTHORIZATION": "Bearer " + token if token else "",
            "wsgi.input": io.BytesIO(body),
            "CONTENT_LENGTH": str(len(body)) if body else "",
        })
        if body:
            environ["CONTENT_TYPE"] = "application/json"
        responses = []
        response_body = b"".join(
            app(environ, lambda status, headers: responses.append(
                (status, dict(headers)))))
        return responses[0][0], responses[0][1], response_body

    def staging_reader_transport(self, calls, *, failure_message=None):
        """Map only the synthetic TLS-verified DSN to the disposable CI reader."""
        def connect(dsn, *args, **kwargs):
            if dsn == self.staging_dsn:
                calls.append("staging-reader")
                if failure_message is not None:
                    raise psycopg.OperationalError(failure_message)
                return _REAL_PG_CONNECT(READER_DSN, *args, **kwargs)
            return _REAL_PG_CONNECT(dsn, *args, **kwargs)

        return patch(
            "devobs_intelligence.postgres_store.psycopg.connect", new=connect)

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

    def test_context_does_not_survive_pooled_connection_reuse(self):
        # Simulate two requests borrowing one connection from a pool. The
        # transaction-local GUCs used by PostgresTenantStore must reset before
        # the next borrower can observe rows under a stale tenant context.
        with psycopg.connect(READER_DSN, autocommit=True) as conn:
            with conn.transaction():
                conn.execute("SET TRANSACTION READ ONLY")
                conn.execute(
                    "SELECT set_config('devobs_ai.tenant_id', %s, true), "
                    "set_config('devobs_ai.subject_id', %s, true)",
                    ("alpha", "alice"),
                )
                self.assertEqual(
                    conn.execute("SELECT count(*) FROM devobs_ai.project_ci").fetchone(),
                    (1,),
                )
            with conn.transaction():
                conn.execute("SET TRANSACTION READ ONLY")
                self.assertEqual(
                    conn.execute("SELECT count(*) FROM devobs_ai.project_ci").fetchone(),
                    (0,),
                )

    def test_revoked_membership_denies_reads_and_service_access_immediately(self):
        self.assertIs(self.store.authorize_service(
            "alice", "alpha", "shared", "collector"), True)
        self.assertEqual(
            self.store.read_status("alice", "alpha", "shared")["source_sha"],
            "a" * 40,
        )
        self.admin.execute(
            "DELETE FROM devobs_ai.memberships "
            "WHERE tenant_id=%s AND project_id=%s AND subject_id=%s",
            ("alpha", "shared", "alice"),
        )
        try:
            with self.assertRaisesRegex(ValueError, "^access_denied$"):
                self.store.read_status("alice", "alpha", "shared")
            self.assertIs(
                self.store.authorize_service("alice", "alpha", "shared", "collector"),
                False,
            )
        finally:
            self.admin.execute(
                "INSERT INTO devobs_ai.memberships (tenant_id, project_id, subject_id) "
                "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                ("alpha", "shared", "alice"),
            )
        self.assertIs(self.store.authorize_service(
            "alice", "alpha", "shared", "collector"), True)

    def test_service_registry_migration_rolls_back_partial_ddl(self):
        migration = (ROOT / "deploy/postgres/002_service_registry.sql").read_text()
        self.admin.execute("DROP TABLE devobs_ai.service_registry")
        # Inject a duplicate CREATE after the migration's DDL but before COMMIT.
        # PostgreSQL must roll back the complete transaction on this failure.
        broken_migration = migration.replace(
            "COMMIT;",
            "CREATE TABLE devobs_ai.service_registry (rollback_probe integer);\nCOMMIT;",
        )
        self.assertNotEqual(broken_migration, migration)
        try:
            with self.assertRaises(psycopg.errors.DuplicateTable):
                self.admin.execute(broken_migration)
            self.admin.execute("ROLLBACK")
            self.assertIsNone(
                self.admin.execute(
                    "SELECT to_regclass('devobs_ai.service_registry')"
                ).fetchone()[0]
            )
        finally:
            self.admin.execute("ROLLBACK")
            self.admin.execute(migration)
            self.admin.execute(
                "INSERT INTO devobs_ai.service_registry VALUES "
                "(%s,%s,%s),(%s,%s,%s),(%s,%s,%s)",
                ("alpha", "shared", "collector", "beta", "shared", "collector",
                 "alpha", "hidden", "private-service"),
            )

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
        app = self.build_staging_app()
        calls = []
        with self.staging_reader_transport(calls):
            for tenant, subject, expected_state, expected_sha in (
                ("alpha", "alice", "success", "a" * 40),
                ("beta", "bob", "failed", "b" * 40),
            ):
                status, headers, body = self.wsgi_request(
                    app, f"/v1/tenants/{tenant}/projects/shared/ci",
                    token=self.issue_token(subject))
                self.assertEqual(status, "200 OK")
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.assertEqual(json.loads(body), {
                    "ci_state": expected_state, "source_sha": expected_sha})

            for tenant, subject in (("beta", "alice"), ("alpha", "bob")):
                status, _, body = self.wsgi_request(
                    app, f"/v1/tenants/{tenant}/projects/shared/ci",
                    token=self.issue_token(subject))
                self.assertEqual(status, "403 Forbidden")
                self.assertEqual(body, b'{"error":"access_denied"}')
        self.assertEqual(calls, ["staging-reader"] * 4)

    def test_wsgiread_verified_signed_token_to_service_registry_rls(self):
        app = self.build_staging_app()
        calls = []

        with self.staging_reader_transport(calls):
            for tenant, project, service, subject in (
                ("alpha", "shared", "collector", "alice"),
                ("beta", "shared", "collector", "bob"),
            ):
                path = (f"/v1/tenants/{tenant}/projects/{project}/services/"
                        f"{service}/authorization")
                status, headers, body = self.wsgi_request(
                    app, path, token=self.issue_token(subject))
                self.assertEqual(status, "204 No Content")
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.assertEqual(body, b"")

            for tenant, project, service, subject in (
                ("beta", "shared", "collector", "alice"),
                ("alpha", "shared", "collector", "bob"),
                ("alpha", "hidden", "private-service", "alice"),
                ("alpha", "shared", "missing-service", "alice"),
            ):
                path = (f"/v1/tenants/{tenant}/projects/{project}/services/"
                        f"{service}/authorization")
                status, _, body = self.wsgi_request(
                    app, path, token=self.issue_token(subject))
                self.assertEqual(status, "403 Forbidden")
                self.assertEqual(body, b'{"error":"access_denied"}')
        self.assertEqual(calls, ["staging-reader"] * 6)

    def test_staging_entrypoint_health_and_readiness_use_real_ci_postgres(self):
        app = self.build_staging_app()
        self.assertTrue(callable(app))
        calls = []
        with self.staging_reader_transport(calls):
            health_status, health_headers, health_body = self.wsgi_request(
                app, "/healthz")
            self.assertEqual(health_status, "204 No Content")
            self.assertEqual(health_headers["Cache-Control"], "no-store")
            self.assertEqual(health_body, b"")
            self.assertEqual(calls, [], "healthz must not open a DB connection")

            ready_status, ready_headers, ready_body = self.wsgi_request(
                app, "/readyz")
            self.assertEqual(ready_status, "204 No Content")
            self.assertEqual(ready_headers["Cache-Control"], "no-store")
            self.assertEqual(ready_body, b"")
            self.assertEqual(calls, ["staging-reader"])

    def test_staging_entrypoint_rejects_missing_or_invalid_bootstrap_settings(self):
        missing_database = dict(self.staging_settings)
        missing_database.pop("DEVOBS_PG_DSN")
        invalid_tls_mode = {
            **self.staging_settings,
            "DEVOBS_PG_TLS_MODE": "disable-verification",
        }
        invalid_metadata = {
            **self.staging_settings,
            "DEVOBS_OIDC_METADATA_JSON": '{"issuer":"synthetic-secret-marker"}',
        }
        for settings in (missing_database, invalid_tls_mode, invalid_metadata):
            with self.subTest(settings_invalid=True):
                with self.assertRaises(
                        self.staging_module.StagingConfigurationError) as caught:
                    self.staging_module.build_app(settings)
                self.assertEqual(str(caught.exception), "invalid_staging_config")
                self.assertNotIn("synthetic-secret-marker", str(caught.exception))

    def test_staging_entrypoint_rejects_anonymous_and_invalid_tokens_without_echo(self):
        app = self.build_staging_app()
        calls = []
        invalid_token = "synthetic-invalid-token-marker"
        with self.staging_reader_transport(calls):
            anonymous = self.wsgi_request(
                app, "/v1/tenants/alpha/projects/shared/ci")
            invalid = self.wsgi_request(
                app, "/v1/tenants/alpha/projects/shared/ci",
                token=invalid_token)

        for status, headers, body in (anonymous, invalid):
            self.assertEqual(status, "401 Unauthorized")
            self.assertEqual(json.loads(body), {"error": "invalid_token"})
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertNotIn(invalid_token.encode(), body)
            self.assertNotIn(b"synthetic-ci-only-password", body)
        self.assertEqual(calls, [])

    def test_staging_entrypoint_keeps_ai_diagnostics_disabled(self):
        app = self.build_staging_app()
        request_body = json.dumps({
            "error_log": "Synthetic diagnostic fixture only",
            "data_redacted": True,
        }).encode("utf-8")
        calls = []
        with self.staging_reader_transport(calls):
            status, headers, body = self.wsgi_request(
                app,
                "/v1/tenants/alpha/projects/shared/services/collector/diagnostics",
                token=self.issue_token(scope="devobs.read devobs.ai.diagnose"),
                method="POST",
                body=request_body,
            )
        self.assertEqual(status, "503 Service Unavailable")
        self.assertEqual(json.loads(body), {"error": "ai_not_configured"})
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(calls, ["staging-reader"])

    def test_staging_entrypoint_redacts_postgres_errors_tokens_and_dsn(self):
        app = self.build_staging_app()
        token = self.issue_token()
        database_error = "synthetic-sql-error-marker"
        calls = []
        with self.staging_reader_transport(
                calls, failure_message=database_error):
            ready = self.wsgi_request(app, "/readyz")
            response = self.wsgi_request(
                app, "/v1/tenants/alpha/projects/shared/ci", token=token)

        self.assertEqual(ready[0], "503 Service Unavailable")
        self.assertEqual(ready[2], b"")
        self.assertEqual(response[0], "503 Service Unavailable")
        self.assertEqual(response[2], b'{"error":"backend_unavailable"}')
        public_response = str((ready[1], ready[2], response[1], response[2]))
        for private_value in (
                database_error, token, "synthetic-ci-only-password"):
            self.assertNotIn(private_value, public_response)
        self.assertEqual(calls, ["staging-reader", "staging-reader"])

    def test_staging_entrypoint_fails_closed_on_rls_policy_drift(self):
        self.admin.execute(
            "ALTER POLICY devobs_project_member_read ON devobs_ai.project_ci "
            "USING (true)")
        try:
            app = self.build_staging_app()
            calls = []
            with self.staging_reader_transport(calls):
                ready = self.wsgi_request(app, "/readyz")
                response = self.wsgi_request(
                    app, "/v1/tenants/alpha/projects/shared/ci",
                    token=self.issue_token())
            self.assertEqual(ready[0], "503 Service Unavailable")
            self.assertEqual(ready[2], b"")
            self.assertEqual(response[0], "503 Service Unavailable")
            self.assertEqual(response[2], b'{"error":"backend_unavailable"}')
            self.assertEqual(calls, ["staging-reader", "staging-reader"])
        finally:
            self.admin.execute(
                "ALTER POLICY devobs_project_member_read ON devobs_ai.project_ci "
                "USING (tenant_id = NULLIF(current_setting('devobs_ai.tenant_id', true), '') "
                "AND EXISTS (SELECT 1 FROM devobs_ai.memberships AS m "
                "WHERE m.tenant_id = project_ci.tenant_id "
                "AND m.project_id = project_ci.project_id "
                "AND m.subject_id = NULLIF(current_setting('devobs_ai.subject_id', true), '')))")
        self.assertIs(self.store.probe_readiness(), True)

    def test_staging_entrypoint_fails_closed_on_runtime_role_bypass_drift(self):
        self.admin.execute("ALTER ROLE devobs_ci_reader BYPASSRLS")
        try:
            app = self.build_staging_app()
            calls = []
            with self.staging_reader_transport(calls):
                ready = self.wsgi_request(app, "/readyz")
                response = self.wsgi_request(
                    app, "/v1/tenants/alpha/projects/shared/ci",
                    token=self.issue_token())
            self.assertEqual(ready[0], "503 Service Unavailable")
            self.assertEqual(ready[2], b"")
            self.assertEqual(response[0], "503 Service Unavailable")
            self.assertEqual(response[2], b'{"error":"backend_unavailable"}')
            self.assertEqual(calls, ["staging-reader", "staging-reader"])
        finally:
            self.admin.execute("ALTER ROLE devobs_ci_reader NOBYPASSRLS")
        self.assertIs(self.store.probe_readiness(), True)

    def test_missing_database_not_claimed_as_denial(self):
        # Reject a credentialed runtime pointing to a wrong/inaccessible DB.
        unavailable = PostgresTenantStore(
            "host=127.0.0.1 port=1 dbname=absent connect_timeout=1")
        with self.assertRaises(StorageUnavailable):
            unavailable.read_status("alice", "alpha", "shared")
        with self.assertRaises(StorageUnavailable):
            unavailable.authorize_service("alice", "alpha", "shared", "collector")


if __name__=="__main__": unittest.main()

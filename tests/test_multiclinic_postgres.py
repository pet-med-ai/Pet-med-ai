"""Real PostgreSQL tests. Creates/drops only a new random test database."""

import copy
from datetime import datetime, timezone, timedelta
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.engine import make_url
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from passlib.hash import bcrypt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from multiclinic import api
from multiclinic.gate import scope_gate
from multiclinic.migrate import backfill, revoke_membership

ADMIN = os.getenv("PMAI_TEST_POSTGRES_ADMIN_URL", "")
KEY = "synthetic-multiclinic-tests-only-32-characters"


@unittest.skipUnless(ADMIN, "requires an isolated PostgreSQL test administrator")
class ClinicPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.name = "pmai_scope_test_" + uuid4().hex[:12]
        cls.admin = sa.create_engine(ADMIN, isolation_level="AUTOCOMMIT")
        with cls.admin.connect() as conn:
            conn.exec_driver_sql(f'CREATE DATABASE "{cls.name}"')
        cls.admin_url = (
            make_url(ADMIN).set(database=cls.name).render_as_string(hide_password=False)
        )
        cls.owner = sa.create_engine(cls.admin_url)
        cls.runtime_url = (
            make_url(cls.admin_url)
            .set(username="pmai_scope_runtime")
            .render_as_string(hide_password=False)
        )
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alembic",
                    "-c",
                    "alembic.ini",
                    "upgrade",
                    "mc01_scope_expand",
                ],
                cwd=ROOT / "backend",
                env={**os.environ, "DATABASE_URL": cls.admin_url},
                check=True,
                capture_output=True,
                text=True,
            )
            cls.o1, cls.o2, cls.c1, cls.c2, cls.c3 = [str(uuid4()) for _ in range(5)]
            cls.members = {i: str(uuid4()) for i in range(1, 10)}
            cls.password = "synthetic-only-Password1!"
            digest = bcrypt.hash(cls.password)
            with cls.owner.begin() as conn:
                for i in range(1, 10):
                    conn.execute(
                        sa.text(
                            "INSERT INTO users(id,email,hashed_password,created_at) VALUES (:id,:email,:password,now())"
                        ),
                        {"id": i, "email": f"u{i}@example.invalid", "password": digest},
                    )
                for i, (clinic, owner, visibility) in enumerate(
                    [
                        (cls.c1, 1, "clinic"),
                        (cls.c2, 2, "clinic"),
                        (cls.c3, 7, "clinic"),
                        (cls.c1, 2, "owner_private"),
                    ],
                    1,
                ):
                    conn.execute(
                        sa.text("""INSERT INTO cases(id,owner_id,patient_name,species,chief_complaint,treatment,created_at)
                        VALUES (:id,:owner,:name,'dog','clinical secret','café 🐾\n{{literal}}',now())"""),
                        {"id": i, "owner": owner, "name": f"synthetic-{i}"},
                    )
            cls.manifest = {
                "migration_key": "initial",
                "operator_user_id": 9,
                "reason": "synthetic test setup",
                "organizations": [
                    {"id": cls.o1, "name": "Org A"},
                    {"id": cls.o2, "name": "Org B"},
                ],
                "clinics": [
                    {"id": c, "org_id": o, "code": str(i), "name": f"Clinic {i}"}
                    for i, (o, c) in enumerate(
                        [(cls.o1, cls.c1), (cls.o1, cls.c2), (cls.o2, cls.c3)]
                    )
                ],
                "memberships": [
                    {
                        "id": cls.members[i],
                        "org_id": cls.o2 if i == 7 else cls.o1,
                        "user_id": i,
                    }
                    for i in range(1, 10)
                ],
                "role_bindings": [],
                "cases": [
                    {
                        "case_id": i,
                        "expected_owner_id": owner,
                        "org_id": org,
                        "clinic_id": clinic,
                    }
                    for i, owner, org, clinic in [
                        (1, 1, cls.o1, cls.c1),
                        (2, 2, cls.o1, cls.c2),
                        (3, 7, cls.o2, cls.c3),
                        (4, 2, cls.o1, cls.c1),
                    ]
                ],
            }
            roles = {
                1: "veterinarian",
                2: "veterinarian",
                3: "frontdesk",
                4: "org_admin",
                5: "cashier",
                6: "pharmacist",
                7: "veterinarian",
                8: "clinical_assistant",
                9: "org_admin",
            }
            for i, role in roles.items():
                cls.manifest["role_bindings"].append(
                    {
                        "id": str(uuid4()),
                        "org_id": cls.o2 if i == 7 else cls.o1,
                        "membership_id": cls.members[i],
                        "scope_kind": "org" if role == "org_admin" else "clinic",
                        "clinic_id": None
                        if role == "org_admin"
                        else cls.c3
                        if i == 7
                        else cls.c2
                        if i == 2
                        else cls.c1,
                        "role_code": role,
                        "granted_by": 9,
                    }
                )
            backfill(cls.owner, cls.manifest, apply=True, batch_size=2)
            with cls.owner.begin() as conn:
                conn.exec_driver_sql(
                    "UPDATE cases SET visibility='clinic' WHERE id IN (1,2,3)"
                )
                conn.exec_driver_sql(
                    (ROOT / "backend/multiclinic/read_policy.sql").read_text()
                )
                # CI database passwords are synthetic; use the supplied test-service password.
                password = make_url(ADMIN).password
                if password:
                    conn.execute(
                        sa.text("ALTER ROLE pmai_scope_runtime PASSWORD :password"),
                        {"password": password},
                    )
            cls.runtime = sa.create_engine(cls.runtime_url, pool_size=1, max_overflow=0)
            cls.env = patch.dict(
                os.environ,
                PMAI_MULTICLINIC_MODE="read_pilot",
                MULTICLINIC_DATABASE_URL=cls.runtime_url,
                MULTICLINIC_TOKEN_SECRET=KEY,
            )
            cls.env.start()
            cls.app = FastAPI()
            cls.app.middleware("http")(scope_gate)
            cls.app.include_router(api.router)

            @cls.app.get("/api/cases/{case_id}")
            def unported(case_id: int):
                return {"must_not_run": True}

            cls.client = TestClient(cls.app)
        except Exception:
            cls.owner.dispose()
            with cls.admin.connect() as conn:
                conn.exec_driver_sql(f'DROP DATABASE "{cls.name}" WITH (FORCE)')
            raise

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.env.stop()
        cls.runtime.dispose()
        api.engine_for(cls.runtime_url).dispose()
        api.engine_for.cache_clear()
        cls.owner.dispose()
        with cls.admin.connect() as conn:
            conn.exec_driver_sql(f'DROP DATABASE "{cls.name}" WITH (FORCE)')
        cls.admin.dispose()

    def setUp(self):
        with self.owner.begin() as conn:
            conn.exec_driver_sql("UPDATE org_memberships SET status='active'")
            conn.exec_driver_sql(
                "UPDATE users SET status='active',principal_kind='human',token_version=1"
            )
            conn.exec_driver_sql(
                "UPDATE organizations SET status='active',policy_version=1"
            )
            conn.exec_driver_sql(
                "UPDATE role_bindings SET revoked_at=NULL,valid_until=NULL"
            )
            conn.exec_driver_sql("DELETE FROM case_access_grants")

    def auth(self, user=1):
        response = self.client.post(
            "/api/v2/auth/login",
            json={"email": f"u{user}@example.invalid", "password": self.password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def url(self, case=None, clinic=None, org=None):
        return (
            f"/api/v2/organizations/{org or self.o1}/clinics/{clinic or self.c1}/cases"
            + ("" if case is None else f"/{case}")
        )

    def test_01_private_history_and_scope_boundary(self):
        auth = self.auth()
        self.assertEqual(
            [
                r["id"]
                for r in self.client.get(self.url(), headers=auth).json()["items"]
            ],
            [1],
        )
        for url in [
            self.url(2),
            self.url(2, clinic=self.c2),
            self.url(3, clinic=self.c3, org=self.o2),
            self.url(4),
        ]:
            self.assertEqual(self.client.get(url, headers=auth).status_code, 404, url)
        self.assertEqual(
            self.client.get(self.url(1), headers=auth).json()["treatment"],
            "café 🐾\n{{literal}}",
        )

    def test_02_demographic_projection_and_admin_separation(self):
        front = self.auth(3)
        response = self.client.get(
            self.url(1) + "?projection=demographics", headers=front
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("treatment", response.json())
        self.assertNotIn("chief_complaint", response.json())
        self.assertEqual(self.client.get(self.url(1), headers=front).status_code, 404)
        for user in (4, 5, 6):
            auth = self.auth(user)
            self.assertEqual(
                self.client.get("/api/v2/scopes", headers=auth).json()["items"], []
            )
            self.assertEqual(
                self.client.get(self.url(1), headers=auth).status_code, 404
            )

    def test_03_direct_sql_views_enforce_projection_and_unset_context(self):
        token = self.auth(3)["Authorization"].split()[1]
        claims = jwt.decode(token, KEY, algorithms=["HS256"], audience=api.AUDIENCE)
        with self.runtime.begin() as conn:
            self.assertEqual(
                conn.exec_driver_sql("SELECT * FROM pmai_scope.clinical_cases").all(),
                [],
            )
            conn.execute(
                sa.text(
                    "SELECT set_config('pmai.actor_id','3',true),set_config('pmai.session_id',:sid,true),set_config('pmai.org_id',:org,true),set_config('pmai.clinic_id',:clinic,true)"
                ),
                {"sid": claims["sid"], "org": self.o1, "clinic": self.c1},
            )
            self.assertEqual(
                conn.exec_driver_sql("SELECT * FROM pmai_scope.clinical_cases").all(),
                [],
            )
            self.assertEqual(
                len(
                    conn.exec_driver_sql(
                        "SELECT * FROM pmai_scope.demographic_cases"
                    ).all()
                ),
                1,
            )
        # Reuse the very same pool connection: transaction-local identity is gone.
        with self.runtime.connect() as conn:
            self.assertEqual(
                conn.exec_driver_sql(
                    "SELECT * FROM pmai_scope.demographic_cases"
                ).all(),
                [],
            )
        for sql in [
            "SELECT * FROM cases",
            "SELECT * FROM followups",
            "UPDATE cases SET treatment='forbidden'",
            "TRUNCATE cases",
            "ALTER TABLE cases DISABLE ROW LEVEL SECURITY",
        ]:
            with self.assertRaises(sa.exc.DBAPIError), self.runtime.begin() as conn:
                conn.exec_driver_sql(sql)

    def test_04_explicit_grant_expiry_and_no_cross_org_foreign_keys(self):
        auth = self.auth(1)
        with self.owner.begin() as conn:
            conn.execute(
                sa.text("""INSERT INTO case_access_grants(id,org_id,clinic_id,case_id,grantee_membership_id,reason,expires_at,granted_by)
              VALUES (:id,:org,:clinic,2,:member,'synthetic consultation',now()+interval '1 hour',9)"""),
                {
                    "id": str(uuid4()),
                    "org": self.o1,
                    "clinic": self.c2,
                    "member": self.members[1],
                },
            )
        self.assertEqual(
            self.client.get(self.url(2, clinic=self.c2), headers=auth).status_code, 200
        )
        with self.owner.begin() as conn:
            conn.exec_driver_sql(
                "UPDATE case_access_grants SET expires_at=now()-interval '1 second'"
            )
        self.assertEqual(
            self.client.get(self.url(2, clinic=self.c2), headers=auth).status_code, 404
        )
        with self.assertRaises(sa.exc.IntegrityError), self.owner.begin() as conn:
            conn.execute(
                sa.text("UPDATE cases SET clinic_id=:clinic WHERE id=1"),
                {"clinic": self.c3},
            )
        with self.assertRaises(sa.exc.IntegrityError), self.owner.begin() as conn:
            conn.execute(
                sa.text(
                    "UPDATE role_bindings SET membership_id=:member WHERE role_code='frontdesk'"
                ),
                {"member": self.members[7]},
            )

    def test_05_revoke_is_audited_idempotent_and_effective_on_existing_token(self):
        auth = self.auth(1)
        key = uuid4().hex + uuid4().hex
        kwargs = dict(
            org_id=self.o1,
            membership_id=self.members[1],
            actor_id=9,
            reason="synthetic departure",
            request_key=key,
        )
        self.assertFalse(revoke_membership(self.owner, **kwargs)["replayed"])
        self.assertTrue(revoke_membership(self.owner, **kwargs)["replayed"])
        self.assertEqual(self.client.get(self.url(1), headers=auth).status_code, 404)
        with self.assertRaises(ValueError):
            revoke_membership(self.owner, **{**kwargs, "reason": "different command"})
        with self.assertRaises(sa.exc.DBAPIError), self.owner.begin() as conn:
            conn.exec_driver_sql("DELETE FROM access_audit_events")
        with self.assertRaises(ValueError):
            revoke_membership(
                self.owner,
                **{**kwargs, "actor_id": 3, "request_key": uuid4().hex + uuid4().hex},
            )

    def test_06_token_version_logout_and_old_token_rejected(self):
        auth = self.auth()
        self.assertEqual(
            self.client.post("/api/v2/auth/logout", headers=auth).status_code, 204
        )
        self.assertEqual(self.client.get(self.url(1), headers=auth).status_code, 401)
        auth = self.auth()
        with self.owner.begin() as conn:
            conn.exec_driver_sql("UPDATE users SET token_version=2 WHERE id=1")
        self.assertEqual(self.client.get(self.url(1), headers=auth).status_code, 401)
        old = jwt.encode(
            {
                "sub": "u1@example.invalid",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            KEY,
            algorithm="HS256",
        )
        self.assertEqual(
            self.client.get(
                self.url(1), headers={"Authorization": "Bearer " + old}
            ).status_code,
            401,
        )

    def test_07_legacy_routes_disabled_even_for_owner(self):
        auth = self.auth()
        for path in [
            "/api/cases/1",
            "/auth/signup",
            "/auth/login",
            "/api/clinical-docs/render",
            "/api/cases/1/followup-contacts/confirm",
            "/docs",
            "/openapi.json",
        ]:
            for method in ["get", "post"]:
                response = getattr(self.client, method)(path, headers=auth)
                self.assertEqual(
                    response.status_code, 409, (path, method, response.text)
                )
        self.assertEqual(self.client.post(self.url(1), headers=auth).status_code, 405)

    def test_08_refuses_privileged_runtime_and_unknown_mode(self):
        with patch.dict(os.environ, MULTICLINIC_DATABASE_URL=self.admin_url):
            self.assertEqual(self.client.get("/api/v2/scopes").status_code, 503)
        api.engine_for(self.admin_url).dispose()
        with patch.dict(os.environ, PMAI_MULTICLINIC_MODE="formal"):
            self.assertEqual(self.client.get(self.url(1)).status_code, 409)

    def test_09_unknown_policy_and_service_principal_fail_closed(self):
        auth = self.auth()
        with self.owner.begin() as conn:
            conn.exec_driver_sql("UPDATE organizations SET policy_version=99")
        self.assertEqual(self.client.get(self.url(1), headers=auth).status_code, 404)
        with self.owner.begin() as conn:
            conn.exec_driver_sql("UPDATE users SET principal_kind='service' WHERE id=1")
        self.assertEqual(
            self.client.get("/api/v2/scopes", headers=auth).status_code, 401
        )
        self.assertEqual(
            self.client.post(
                "/api/v2/auth/login",
                json={"email": "u1@example.invalid", "password": self.password},
            ).status_code,
            401,
        )

    def test_10_backfill_dry_run_resume_hash_and_rollback(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["migration_key"] = "resume_test"
        manifest["organizations"] = []
        manifest["clinics"] = []
        manifest["memberships"] = []
        manifest["role_bindings"] = []
        manifest["cases"] = [
            dict(case_id=i, expected_owner_id=1, org_id=self.o1, clinic_id=self.c1)
            for i in (100, 101)
        ]
        with self.owner.begin() as conn:
            for i in (100, 101):
                conn.execute(
                    sa.text(
                        "INSERT INTO cases(id,owner_id,patient_name,species,chief_complaint,treatment,created_at) VALUES (:id,1,'same animal name','dog','preserve','raw\\n{{literal}}',now())"
                    ),
                    {"id": i},
                )
        self.assertFalse(backfill(self.owner, manifest, batch_size=1)["applied"])
        with self.owner.connect() as conn:
            self.assertIsNone(
                conn.exec_driver_sql("SELECT org_id FROM cases WHERE id=100").scalar()
            )

        def fail_second(conn, cursor, statement, parameters, context, many):
            if (
                statement.startswith("INSERT INTO migration_batches")
                and parameters.get("batch_no") == 2
            ):
                raise RuntimeError("simulated interruption")

        sa.event.listen(self.owner, "before_cursor_execute", fail_second)
        try:
            with self.assertRaisesRegex(RuntimeError, "interruption"):
                backfill(self.owner, manifest, apply=True, batch_size=1)
        finally:
            sa.event.remove(self.owner, "before_cursor_execute", fail_second)
        with self.owner.connect() as conn:
            self.assertIsNotNone(
                conn.exec_driver_sql("SELECT org_id FROM cases WHERE id=100").scalar()
            )
            self.assertIsNone(
                conn.exec_driver_sql("SELECT org_id FROM cases WHERE id=101").scalar()
            )
        backfill(self.owner, manifest, apply=True, batch_size=1)
        backfill(self.owner, manifest, apply=True, batch_size=1)
        with self.owner.connect() as conn:
            self.assertEqual(
                conn.exec_driver_sql(
                    "SELECT count(DISTINCT patient_id) FROM cases WHERE id IN (100,101)"
                ).scalar(),
                2,
            )
            self.assertEqual(
                conn.exec_driver_sql(
                    "SELECT DISTINCT visibility FROM cases WHERE id IN (100,101)"
                ).scalar(),
                "owner_private",
            )
        changed = copy.deepcopy(manifest)
        changed["cases"][0]["expected_owner_id"] = 2
        with self.assertRaisesRegex(ValueError, "Mapping changed"):
            backfill(self.owner, changed, apply=True, batch_size=1)
        with self.assertRaises(ValueError):
            backfill(self.owner, manifest, apply=True, batch_size=2)

    def test_11_expired_role_and_user_deactivation_apply_without_relogin(self):
        auth = self.auth(8)
        self.assertEqual(self.client.get(self.url(1), headers=auth).status_code, 200)
        with self.owner.begin() as conn:
            conn.execute(
                sa.text(
                    "UPDATE role_bindings SET valid_from=now()-interval '2 hour',valid_until=now()-interval '1 hour' WHERE membership_id=:id"
                ),
                {"id": self.members[8]},
            )
        self.assertEqual(self.client.get(self.url(1), headers=auth).status_code, 404)
        with self.owner.begin() as conn:
            conn.exec_driver_sql("UPDATE users SET status='suspended' WHERE id=8")
        self.assertEqual(
            self.client.get("/api/v2/scopes", headers=auth).status_code, 401
        )

    def test_12_user_deletion_cannot_delete_unmapped_case(self):
        with self.owner.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO users(id,email,hashed_password,created_at) VALUES (100,'history@example.invalid','unused',now())"
                )
            )
            conn.execute(
                sa.text(
                    "INSERT INTO cases(id,owner_id,patient_name,species,chief_complaint,created_at) VALUES (200,100,'historical','dog','original',now())"
                )
            )
        with self.assertRaises(sa.exc.IntegrityError), self.owner.begin() as conn:
            conn.exec_driver_sql("DELETE FROM users WHERE id=100")
        # Loaded ORM relationships must not delete the children before the FK can protect them.
        from sqlalchemy.orm import Session
        from models import User

        with Session(self.owner) as db:
            user = db.get(User, 100)
            self.assertEqual([case.id for case in user.cases], [200])
            db.delete(user)
            with self.assertRaises(sa.exc.IntegrityError):
                db.commit()
            db.rollback()
        with self.owner.connect() as conn:
            self.assertEqual(
                conn.exec_driver_sql(
                    "SELECT chief_complaint FROM cases WHERE id=200"
                ).scalar(),
                "original",
            )

    def test_13_disabled_mode_and_missing_auth_never_serve_clinic_data(self):
        self.assertEqual(self.client.get(self.url(1)).status_code, 401)
        with patch.dict(os.environ, PMAI_MULTICLINIC_MODE="off"):
            self.assertEqual(self.client.get("/api/v2/scopes").status_code, 503)
            self.assertEqual(
                self.client.get("/api/cases/1").json(), {"must_not_run": True}
            )

    def test_14_policy_reinstallation_is_idempotent(self):
        with self.owner.begin() as conn:
            conn.exec_driver_sql(
                (ROOT / "backend/multiclinic/read_policy.sql").read_text()
            )
        self.assertEqual(
            self.client.get(self.url(1), headers=self.auth()).status_code, 200
        )

    def test_15_actual_application_routes_are_guarded(self):
        self.assert_actual_application_auth_contract()

    def assert_actual_application_auth_contract(self):
        # Match deployment's backend-only import path in a fresh process; legacy
        # modules support both package and flat imports, which must not be mixed.
        code = """
import os
from uuid import UUID
from jose import jwt
from fastapi.testclient import TestClient
from main import app
from multiclinic.api import AUDIENCE
with TestClient(app) as client:
    assert client.get('/healthz').status_code == 200
    assert client.get('/api/cases/1').status_code == 409
    assert client.post('/auth/signup',json={}).status_code == 409
    login={'email':'u1@example.invalid','password':os.environ['PMAI_TEST_PASSWORD']}
    form={'username':login['email'],'password':login['password']}
    for body in ({'data':form}, {'files':{k:(None,v) for k,v in form.items()}},
                 {'json':login}):
        response=client.post('/auth/login',**body)
        assert response.status_code == 409, response.text
        assert response.json()['code'] == 'CLINIC_WORKFLOW_NOT_PORTED'
    response=client.post('/api/v2/auth/login',json=login)
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['pragma'] == 'no-cache'
    token=response.json()
    assert set(token) == {'access_token','token_type','expires_in'}
    assert token['token_type'] == 'bearer' and token['expires_in'] == 900
    claims=jwt.decode(token['access_token'],os.environ['MULTICLINIC_TOKEN_SECRET'],
                      algorithms=['HS256'],audience=AUDIENCE,issuer=AUDIENCE)
    assert claims['sub'] == '1' and claims['ver'] == 2 and claims['tv'] == 1
    assert str(UUID(claims['sid'])) == claims['sid']
    assert claims['exp']-claims['iat'] == 900
    auth={'Authorization':'Bearer '+token['access_token']}
    assert client.get('/api/cases/1',headers=auth).status_code == 409
    response=client.get(os.environ['PMAI_TEST_PATH'],headers=auth)
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'no-store'
    assert client.get(os.environ['PMAI_TEST_PATH']).status_code == 401
    bad=client.post('/api/v2/auth/login',json={**login,'password':'incorrect'})
    assert bad.status_code == 401, bad.text
    assert bad.headers['cache-control'] == 'no-store'
    assert client.post('/api/v2/auth/login',json={'email':login['email']}).status_code == 422
    assert client.post('/api/v2/auth/login',data=form).status_code == 422
    old=jwt.encode({'sub':login['email'],'exp':claims['exp']},
                   os.environ['MULTICLINIC_TOKEN_SECRET'],algorithm='HS256')
    assert client.get(os.environ['PMAI_TEST_PATH'],headers={'Authorization':'Bearer '+old}).status_code == 401
    assert client.post('/api/v2/auth/logout',headers=auth).status_code == 204
    assert client.get(os.environ['PMAI_TEST_PATH'],headers=auth).status_code == 401
"""
        with tempfile.TemporaryDirectory() as cwd:
            # Only this fixture's fresh database and generated session settings
            # enter the real application; inherited connection settings do not.
            keep = ("PATH", "HOME", "LANG", "LC_ALL", "LD_LIBRARY_PATH", "SSL_CERT_FILE", "SSL_CERT_DIR")
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=cwd,
                env={
                    **{k: os.environ[k] for k in keep if k in os.environ},
                    "PYTHONPATH": str(ROOT / "backend"),
                    "DATABASE_URL": self.runtime_url,
                    "MULTICLINIC_DATABASE_URL": self.runtime_url,
                    "MULTICLINIC_TOKEN_SECRET": KEY,
                    "PMAI_MULTICLINIC_MODE": os.environ["PMAI_MULTICLINIC_MODE"],
                    "PMAI_TEST_PASSWORD": self.password,
                    "PMAI_TEST_PATH": self.url(1),
                },
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_16_autogenerate_does_not_drop_sql_managed_permissions(self):
        from alembic.migration import MigrationContext
        from alembic.autogenerate import compare_metadata
        from db import Base
        from multiclinic.migration_ownership import include_object, TABLES, COLUMNS

        with self.owner.connect() as conn:
            context = MigrationContext.configure(
                conn, opts={"include_object": include_object}
            )
            diffs = compare_metadata(context, Base.metadata)
        for item in diffs:
            if isinstance(item, tuple) and item[0] == "remove_table":
                self.assertNotIn(item[1].name, TABLES)
            if isinstance(item, tuple) and item[0] == "remove_column":
                self.assertNotIn(item[3].name, COLUMNS.get(item[2], set()))


if __name__ == "__main__":
    unittest.main(verbosity=2)

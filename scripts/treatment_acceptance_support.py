"""Fresh local PostgreSQL only. Shared by the acceptance host and restore drill."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
BASELINE = "8d70d10f3c76d1b9df04214accb17894ec3c2394"
DBNAME = "pmai_acceptance"
TEXT = "合成验收 café 🐾\n原文 {{literal}}; literal \\n remains"
CONTENT = {
    "schema": "treatment-content-v1",
    "diagnoses": [{"label": "合成诊断（仅软件验收）", "code_system": None, "code": None}],
    "assessment": TEXT,
    "treatment": {"goals": ["软件验收"], "management_text": TEXT, "monitoring_text": "", "followup_text": ""},
    "linked_orders": [],
    "provenance": {"ai_generation_ids": [], "voice_transcript_revision_ids": []},
}


def check(value, message):
    if not value:
        raise RuntimeError(message)


def clean_env(**extra):
    # No inherited database URL, PG service, token, cloud or application settings.
    keep = ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "LD_LIBRARY_PATH", "SYSTEMROOT", "SSL_CERT_FILE", "SSL_CERT_DIR")
    return {**{k: os.environ[k] for k in keep if k in os.environ}, **extra}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temp = path.with_name(path.name + ".tmp-" + secrets.token_hex(4))
    with temp.open("x", encoding="utf-8") as f:
        os.chmod(temp, 0o600)
        json.dump(value, f, ensure_ascii=False, indent=2, default=str)
        f.write("\n")
    temp.replace(path)


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def identity():
    manifest = ROOT / "acceptance-manifest.json"
    if manifest.exists():
        info = json.loads(manifest.read_text())
        for name, expected in info["files"].items():
            path = (ROOT / name).resolve()
            check(path.is_relative_to(ROOT), "Unsafe manifest path")
            check(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == expected, f"Candidate file changed: {name}")
        return {"commit": info["commit"], "tree": info["tree"], "baseline": BASELINE, "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(), "packaged_files_verified": len(info["files"]), "dirty": False}
    def git(*args):
        return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()
    return {"commit": git("rev-parse", "HEAD"), "tree": git("rev-parse", "HEAD^{tree}"), "baseline": BASELINE, "dirty": bool(git("status", "--porcelain")), "diff_sha256": hashlib.sha256(git("diff", "HEAD").encode()).hexdigest()}


class Cluster:
    """Cannot connect to an existing server: always initdb into a new directory."""
    def __init__(self, path, pg_bin, admin="pmai_acceptance_admin"):
        self.path, self.bin = Path(path).resolve(), Path(pg_bin).resolve()
        self.admin, self.password = admin, secrets.token_urlsafe(32)
        self.runtime_password = secrets.token_urlsafe(32)
        self.port, self.process, self.log = free_port(), None, None
        self.engines = []

    def run(self, tool, *args, database="postgres", **kwargs):
        env = clean_env(PGHOST="127.0.0.1", PGPORT=str(self.port), PGUSER=self.admin, PGPASSWORD=self.password, PGDATABASE=database, PGCONNECT_TIMEOUT="5")
        return subprocess.run([str(self.bin / tool), *map(str, args)], env=env, check=True, **kwargs)

    def url(self, database=DBNAME, user=None, password=None):
        selected_password = password if password is not None else self.runtime_password if user == "pmai_treatment_runtime" else self.password
        return URL.create("postgresql+psycopg2", username=user or self.admin, password=selected_password, host="127.0.0.1", port=self.port, database=database).render_as_string(hide_password=False)

    def engine(self, database=DBNAME, user=None, password=None):
        engine = sa.create_engine(self.url(database, user, password))
        self.engines.append(engine)
        return engine

    def __enter__(self):
        self.path.mkdir(mode=0o700, parents=False, exist_ok=False)
        (self.path / "owned-by-acceptance").write_text("fresh local synthetic cluster\n")
        pw = self.path / "init-password"
        pw.write_text(self.password)
        pw.chmod(0o600)
        self.log = (self.path.parent / (self.path.name + ".log")).open("w+")
        try:
            subprocess.run([str(self.bin / "initdb"), "-D", str(self.path / "data"), "-U", self.admin, "--pwfile", str(pw), "--auth-host=scram-sha-256", "--auth-local=scram-sha-256", "--no-locale", "-E", "UTF8"], env=clean_env(), check=True, stdout=self.log, stderr=self.log)
            pw.unlink()
            self.process = subprocess.Popen([str(self.bin / "postgres"), "-D", str(self.path / "data"), "-h", "127.0.0.1", "-p", str(self.port), "-c", "unix_socket_directories=", "-c", "password_encryption=scram-sha-256"], env=clean_env(), stdout=self.log, stderr=self.log)
            for _ in range(100):
                check(self.process.poll() is None, "Fresh PostgreSQL exited; see local log")
                result = subprocess.run([str(self.bin / "pg_isready"), "-h", "127.0.0.1", "-p", str(self.port)], env=clean_env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if result.returncode == 0:
                    return self
                time.sleep(0.1)
            raise RuntimeError("Fresh PostgreSQL startup timed out")
        except BaseException:
            self.__exit__(*sys.exc_info())
            raise

    def __exit__(self, *_):
        for engine in self.engines:
            engine.dispose()
        if self.process and self.process.poll() is None:
            import signal
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
        if self.log:
            self.log.close()
        if (self.path / "owned-by-acceptance").is_file():
            shutil.rmtree(self.path)


def migrate(cluster, head):
    with (cluster.path.parent / "migrations.log").open("a") as log:
        subprocess.run([sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", head], cwd=ROOT / "backend", env=clean_env(DATABASE_URL=cluster.url()), check=True, stdout=log, stderr=log)


def seed_legacy(cluster):
    from passlib.hash import bcrypt
    cluster.run("createdb", DBNAME)
    migrate(cluster, "0009_diag_data")
    password = "Synthetic-" + secrets.token_urlsafe(12)
    fixture = {"password": password, "org": str(uuid4()), "other_org": str(uuid4()), "clinic": str(uuid4()), "remote_clinic": str(uuid4()), "other_clinic": str(uuid4()), "members": {str(i): str(uuid4()) for i in range(1, 8)}, "other_admin": str(uuid4())}
    names = {1: "doctor-a", 2: "doctor-b", 3: "assistant", 4: "frontdesk", 5: "admin", 6: "remote", 7: "other"}
    fixture["accounts"] = [{"id": i, "email": name + "@example.invalid"} for i, name in names.items()]
    hashed = bcrypt.hash(password)
    case_names = {101: "合成犬-基础签署", 102: "合成猫-跨院只读", 103: "合成犬-医生B私有", 104: "合成猫-旧文本未签署", 105: "合成犬-第二院区", 106: "合成猫-另一机构", 107: "合成犬-双医生", 108: "合成猫-资料变化", 109: "合成犬-丢响应恢复", 110: "合成猫-修订作废"}
    fixture["case_names"] = case_names
    owner = cluster.engine()
    with owner.begin() as conn:
        for account in fixture["accounts"]:
            conn.execute(sa.text("INSERT INTO users(id,email,hashed_password,created_at) VALUES (:id,:email,:password,now())"), {**account, "password": hashed})
        for i, name in case_names.items():
            conn.execute(sa.text("INSERT INTO cases(id,owner_id,patient_name,species,chief_complaint,analysis,treatment,created_at) VALUES (:id,:owner,:name,'synthetic','仅软件验收',:text,:text,now())"), {"id": i, "owner": 2 if i == 103 else 6 if i == 105 else 7 if i == 106 else 1, "name": name, "text": TEXT})
    return fixture


def expand_and_seed(cluster, f):
    from multiclinic.migrate import backfill
    from treatment_store.admin import configure, import_legacy, install_policy
    owner = cluster.engine()
    migrate(cluster, "mc01_scope_expand")
    org, clinic, members = f["org"], f["clinic"], f["members"]
    manifest = {"migration_key": "synthetic-acceptance-v1", "operator_user_id": 5, "reason": "全新一次性数据库合成映射", "organizations": [{"id": org, "name": "合成机构A"}, {"id": f["other_org"], "name": "合成机构B"}], "clinics": [{"id": c, "org_id": o, "code": str(n), "name": name} for n, (o, c, name) in enumerate([(org, clinic, "一院"), (org, f["remote_clinic"], "二院"), (f["other_org"], f["other_clinic"], "隔离院区")])], "memberships": [{"id": members[str(i)], "org_id": f["other_org"] if i == 7 else org, "user_id": i} for i in range(1, 8)] + [{"id": f["other_admin"], "org_id": f["other_org"], "user_id": 5}], "role_bindings": [], "cases": []}
    for i, role in {1: "veterinarian", 2: "veterinarian", 3: "clinical_assistant", 4: "frontdesk", 5: "org_admin", 6: "veterinarian", 7: "veterinarian"}.items():
        manifest["role_bindings"].append({"id": str(uuid4()), "org_id": f["other_org"] if i == 7 else org, "membership_id": members[str(i)], "scope_kind": "org" if i == 5 else "clinic", "clinic_id": None if i == 5 else f["remote_clinic"] if i == 6 else f["other_clinic"] if i == 7 else clinic, "role_code": role, "granted_by": 5})
    manifest["role_bindings"].append({"id": str(uuid4()), "org_id": f["other_org"], "membership_id": f["other_admin"], "scope_kind": "org", "clinic_id": None, "role_code": "org_admin", "granted_by": 5})
    for case in f["case_names"]:
        i = int(case)
        manifest["cases"].append({"case_id": i, "expected_owner_id": 2 if i == 103 else 6 if i == 105 else 7 if i == 106 else 1, "org_id": f["other_org"] if i == 106 else org, "clinic_id": f["remote_clinic"] if i == 105 else f["other_clinic"] if i == 106 else clinic})
    dry = backfill(owner, manifest, batch_size=2)
    with owner.connect() as conn:
        check(conn.exec_driver_sql("SELECT count(*) FROM cases WHERE org_id IS NOT NULL").scalar() == 0, "Dry run changed scope")
    applied = backfill(owner, manifest, apply=True, batch_size=2)
    replay = backfill(owner, manifest, apply=True, batch_size=2)
    with owner.begin() as conn:
        check(conn.exec_driver_sql("SELECT bool_and(visibility='owner_private') FROM cases").scalar(), "Backfill shared private history")
        check(conn.execute(sa.text("SELECT bool_and(treatment=:t AND analysis=:t) FROM cases"), {"t": TEXT}).scalar(), "Backfill changed source text")
        # Explicitly change ONLY newly generated fixtures to clinic-shared samples.
        conn.exec_driver_sql("UPDATE cases SET visibility='clinic' WHERE id<>103")
        conn.exec_driver_sql((ROOT / "backend/multiclinic/read_policy.sql").read_text())
        conn.execute(sa.text("INSERT INTO case_access_grants(id,org_id,clinic_id,case_id,grantee_membership_id,reason,expires_at,granted_by) VALUES (:id,:o,:c,102,:m,'合成只读授权',now()+interval '7 days',5)"), {"id": str(uuid4()), "o": org, "c": clinic, "m": members["6"]})
    migrate(cluster, "mc02_treatment_store")
    install_policy(owner)
    for i in (1, 2, 6, 7):
        args = dict(org=f["other_org"] if i == 7 else org, actor=5, membership=members[str(i)], name=f"合成医生 {i}", credential="SYNTHETIC-NOT-A-LICENSE", key="synthetic-profile-" + str(i), reason="仅合成档案")
        configure(owner, **args)
        configure(owner, **args, apply=True)
    args = dict(org=org, clinic=clinic, case_id=104, actor=5, key="synthetic-legacy", reason="旧文本显式导入演练")
    preview = import_legacy(owner, **args)
    with owner.connect() as conn:
        check(conn.exec_driver_sql("SELECT count(*) FROM treatment_plans").scalar() == 0, "Import dry run wrote plan")
    imported = import_legacy(owner, **args, apply=True, expected_sha256=preview["source_sha256"])
    repeated = import_legacy(owner, **args, apply=True, expected_sha256=preview["source_sha256"])
    with owner.begin() as conn:
        check(conn.exec_driver_sql("SELECT count(*) FROM treatment_signatures").scalar() == 0, "Import manufactured signature")
        conn.execute(sa.text("ALTER ROLE pmai_treatment_runtime PASSWORD :p"), {"p": cluster.runtime_password})
    return {"backfill_dry_run": dry, "backfill_apply": applied, "backfill_replay": replay, "private_history_preserved": True, "source_text_preserved": True, "unsigned_import": imported, "unsigned_import_replay": repeated, "migration_chain": ["0009_diag_data", "mc01_scope_expand", "mc02_treatment_store"]}


def set_policy(owner, fixture, policy):
    from treatment_store.admin import configure
    return configure(owner, org=fixture["org"], actor=5, review_policy=policy, assurance="account_attestation", key=uuid4().hex, reason="合成验收切换签署规则", apply=True)


def source_change(owner, case):
    check(case in (108, 101), "Only the synthetic source-change cases are supported")
    with owner.begin() as conn:
        conn.execute(sa.text("INSERT INTO diagnostic_reports(case_id,report_type,source_type,status,title,report_text,ai_summary_status,created_at) VALUES (:id,'synthetic','manual','draft','合成新增资料','用于验证旧冻结版本失效','not_generated',now())"), {"id": case})


def make_api(runtime_url, token_secret):
    from fastapi import FastAPI
    from multiclinic import api
    from multiclinic.gate import scope_gate
    from treatment_store import api as treatment_api
    # These values are generated by this process, never taken from shell settings.
    os.environ.update(PMAI_MULTICLINIC_MODE="treatment_pilot", MULTICLINIC_DATABASE_URL=runtime_url, MULTICLINIC_TOKEN_SECRET=token_secret)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.middleware("http")(scope_gate)
    app.include_router(api.router)
    app.include_router(treatment_api.router)
    return app


def fingerprint(owner):
    result = {"tables": {}, "sequences": {}, "catalog": {}}
    with owner.connect() as conn:
        for schema, table in conn.exec_driver_sql("SELECT schemaname,tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1,2"):
            rows = conn.exec_driver_sql(f'SELECT row_to_json(t)::text FROM "{schema}"."{table}" t').scalars().all()
            result["tables"][table] = {"rows": len(rows), "sha256": digest(sorted(canonical(json.loads(r)) for r in rows))}
        for schema, name in conn.exec_driver_sql("SELECT schemaname,sequencename FROM pg_sequences WHERE schemaname='public' ORDER BY 1,2"):
            result["sequences"][name] = list(conn.exec_driver_sql(f'SELECT last_value,is_called FROM "{schema}"."{name}"').one())
        queries = {
            "relations": "SELECT n.nspname,c.relname,c.relkind,c.relrowsecurity,c.relforcerowsecurity,pg_get_userbyid(c.relowner),COALESCE(c.relacl::text,'') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('public','pmai_scope','pmai_treatment') ORDER BY 1,2",
            "policies": "SELECT schemaname,tablename,policyname,permissive,roles::text,cmd,qual,with_check FROM pg_policies ORDER BY 1,2,3",
            "constraints": "SELECT n.nspname,c.relname,x.conname,pg_get_constraintdef(x.oid) FROM pg_constraint x JOIN pg_class c ON c.oid=x.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY 1,2,3",
            "functions": "SELECT n.nspname,p.proname,pg_get_function_identity_arguments(p.oid),pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner),COALESCE(p.proacl::text,'') FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname IN ('public','pmai_scope','pmai_treatment') AND p.prokind='f' ORDER BY 1,2,3",
            "triggers": "SELECT n.nspname,c.relname,t.tgname,t.tgenabled,pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY 1,2,3",
            "roles": "SELECT rolname,rolsuper,rolinherit,rolcreaterole,rolcreatedb,rolcanlogin,rolreplication,rolbypassrls FROM pg_roles WHERE rolname LIKE 'pmai_scope_%' OR rolname='pmai_treatment_runtime' ORDER BY 1",
            "schemas": "SELECT nspname,pg_get_userbyid(nspowner),COALESCE(nspacl::text,'') FROM pg_namespace WHERE nspname IN ('public','pmai_scope','pmai_treatment') ORDER BY 1",
            "database": "SELECT pg_get_userbyid(datdba),COALESCE(datacl::text,'') FROM pg_database WHERE datname=current_database()",
        }
        for name, sql in queries.items():
            values = [list(row) for row in conn.exec_driver_sql(sql.replace("%", "%%"))]
            if name == "constraints":
                values = [[*row[:-1], normalize_constraint(row[-1])] for row in values]
            result["catalog"][name] = {"sha256": digest(values), "definitions": values} if name == "constraints" else digest(values)
    return result


def normalize_constraint(value):
    # pg_dump/restore can distribute varchar[] -> text[] casts into each literal.
    # Normalize ONLY this exact constant-array equivalence. No general SQL rewriting.
    literal = r"'(?:''|[^'])*'::character varying"
    array = r"\(ARRAY\[((?:" + literal + r")(?:, " + literal + r")*)\]\)::text\[\]"
    value = re.sub(array, lambda m: "ARRAY[" + m[1].replace("::character varying", "::text") + "]", value)
    return re.sub(r"\(('(?:''|[^'])*')::character varying\)::text", r"\1::text", value)


def backup(cluster, output):
    output = Path(output)
    cluster.run("pg_dump", "--format=custom", "--create", "--file", output, database=DBNAME)
    roles = output.with_suffix(".roles.sql")
    cluster.run("pg_dumpall", "--roles-only", "--no-role-passwords", "--file", roles)
    output.chmod(0o600)
    roles.chmod(0o600)
    return {"archive": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "roles_sha256": hashlib.sha256(roles.read_bytes()).hexdigest(), "bytes": output.stat().st_size}


def restore(cluster, archive):
    archive = Path(archive)
    cluster.run("psql", "-X", "--set", "ON_ERROR_STOP=1", "--file", archive.with_suffix(".roles.sql"), stdout=subprocess.DEVNULL)
    cluster.run("pg_restore", "--exit-on-error", "--create", "--dbname", "postgres", archive)
    with cluster.engine().begin() as conn:
        conn.execute(sa.text("ALTER ROLE pmai_treatment_runtime PASSWORD :p"), {"p": cluster.runtime_password}) if conn.exec_driver_sql("SELECT EXISTS(SELECT FROM pg_roles WHERE rolname='pmai_treatment_runtime')").scalar() else None

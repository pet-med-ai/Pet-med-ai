"""New disposable SQLite only; imported business application remains unmodified."""
import argparse
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "clinical-doctor-trial-cw-b26-v1"
FLAGS = ("CASE_ATTACHMENTS", "MANUAL_LAB_RESULTS", "MANUAL_LAB_DOCUMENTS", "MANUAL_IMAGING",
         "VISIT_OVERVIEW", "LAB_RANGE_REVIEW", "LAB_COMPARISON", "LAB_COMPARISON_DOCUMENTS",
         "FOLLOWUP_PLANS", "FOLLOWUP_PLAN_DOCUMENTS", "FOLLOWUP_PLAN_OWNER_DOCUMENTS",
         "FOLLOWUP_PLAN_OVERVIEW", "FOLLOWUP_PLAN_QUEUE", "FOLLOWUP_CONTACTS",
         "FOLLOWUP_CONTACT_OVERVIEW", "FOLLOWUP_CONTACT_DOCUMENTS",
         "FOLLOWUP_CONTACT_OWNER_DOCUMENTS", "FOLLOWUP_CONTACT_QUEUE")


def validate_config(path):
    path = Path(path).absolute()
    directory = path.parent
    if (path.name != "environment.json" or path.is_symlink() or directory.is_symlink()
            or directory.parent != Path(tempfile.gettempdir()).resolve()
            or not directory.name.startswith("pmai-cwb26-") or path.resolve() != path):
        raise ValueError("unrecognized temporary config")
    marker, private, database = directory / "synthetic-only", directory / "private", directory / "synthetic.sqlite"
    if marker.is_symlink() or marker.read_text() != "CW-B26" or private.is_symlink() or not private.is_dir():
        raise ValueError("invalid synthetic marker/private directory")
    config = json.loads(path.read_text())
    if config.get("schema") != SCHEMA:
        raise ValueError("invalid trial schema")
    if database.exists() or database.is_symlink():
        raise ValueError("existing database refused")
    if config.get("database_url") != "sqlite:///" + str(database) or config.get("private_dir") != str(private):
        raise ValueError("database or private path mismatch")
    for key, size in (("session", 64), ("head", 40), ("source_sha256", 64), ("secret", 96)):
        if not re.fullmatch("[0-9a-f]{" + str(size) + "}", config.get(key, "")):
            raise ValueError("invalid runtime identity")
    for key in ("api", "ui"):
        port = config.get(key + "_port")
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError("invalid port")
        if config.get(key + "_origin") != "http://127.0.0.1:" + str(port):
            raise ValueError("non-loopback origin")
    if config["api_port"] == config["ui_port"]:
        raise ValueError("duplicate ports")
    if not re.fullmatch(r"practice-[0-9a-f]{12}@example\.com", config.get("email", "")):
        raise ValueError("invalid synthetic account")
    if not re.fullmatch(r"[A-Za-z0-9_-]{32}", config.get("password", "")):
        raise ValueError("invalid ephemeral password")
    return config, database


def network_guard(database, api_port):
    def guard(event, args):
        if event in {"socket.connect", "socket.connect_ex"}:
            raise RuntimeError("Doctor trial prohibits outbound connections")
        if event == "socket.bind":
            address = args[1]
            if not isinstance(address, tuple) or address[:2] != ("127.0.0.1", api_port):
                raise RuntimeError("Doctor trial bind refused")
        if event == "socket.getaddrinfo" and args[0] not in {"127.0.0.1", "::1", "localhost", None}:
            raise RuntimeError("Doctor trial external DNS refused")
        if event == "sqlite3.connect":
            if str(args[0]) != str(database) or database.is_symlink():
                raise RuntimeError("Doctor trial database refused")
    return guard


def load_fixture():
    manifest = json.loads((ROOT / "tests/fixtures/clinical_doctor_trial_cw_b26_cases.json").read_text())
    if manifest["source_fixture"] != "tests/fixtures/clinical_visit_journey_cw_b24_cases.json":
        raise ValueError("unrecognized synthetic fixture")
    fixture = json.loads((ROOT / manifest["source_fixture"]).read_text())
    for row, name in zip(fixture["cases"], manifest["patient_names"], strict=True):
        row["patient_name"] = name
    return manifest, fixture


def prepare_app(config_path):
    config, database = validate_config(config_path)
    os.environ.clear()
    os.environ.update(DATABASE_URL=config["database_url"], SECRET_KEY=config["secret"],
                      ENVIRONMENT="test", RENDER="false", PYTHONDONTWRITEBYTECODE="1",
                      CORS_ORIGINS=config["ui_origin"], CASE_ATTACHMENTS_DIR=config["private_dir"])
    for prefix in FLAGS:
        os.environ[prefix + "_ENABLED"] = "1"
        os.environ[prefix + "_SYNTHETIC_ONLY"] = "1"
    sys.dont_write_bytecode = True
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    if head != config["head"]:
        raise ValueError("candidate head changed")
    sys.addaudithook(network_guard(database, config["api_port"]))
    sys.path[:] = [str(ROOT / "backend")] + [p for p in sys.path if Path(p or ".").resolve() != ROOT]
    import main
    import db
    import models
    import feature_flags
    from passlib.hash import bcrypt
    from sqlalchemy import inspect
    from starlette.responses import JSONResponse
    if feature_flags.dangerous_enabled_flags() or main.app.dependency_overrides:
        raise ValueError("unsafe application configuration")
    if db.engine.url.get_backend_name() != "sqlite" or inspect(db.engine).get_table_names():
        raise ValueError("not an empty disposable database")
    db.Base.metadata.create_all(db.engine)  # New temporary schema only; never Alembic/migration.
    manifest, fixture = load_fixture()
    with db.SessionLocal() as session:
        owner = models.User(email=config["email"], hashed_password=bcrypt.hash(config["password"]),
                            full_name="CW-B26 合成练习账号")
        session.add(owner)
        session.flush()
        cases = [models.Case(owner_id=owner.id, **row) for row in fixture["cases"]]
        session.add_all(cases)
        session.commit()
        public_cases = [{"id": row.id, "name": row.patient_name, "species": row.species} for row in cases]
    public = {key: config[key] for key in ("schema", "session", "head", "source_sha256")}
    public.update(synthetic_only=True, cases=public_cases, steps=manifest["steps"],
                  sample_files=manifest["sample_files"])
    headers = {"X-PMAI-Trial-Session": config["session"],
               "X-PMAI-Trial-Head": config["head"], "X-PMAI-Trial-Source": config["source_sha256"]}
    error_headers = {**headers, "Access-Control-Allow-Origin": config["ui_origin"],
                     "Access-Control-Expose-Headers": ", ".join(headers), "Vary": "Origin"}

    @main.app.middleware("http")
    async def trial_boundary(request, call_next):
        if request.headers.get("host") != urlsplit(config["api_origin"]).netloc:
            return JSONResponse({"detail": "Trial host mismatch"}, status_code=403)
        origin = request.headers.get("origin")
        if origin and origin != config["ui_origin"]:
            return JSONResponse({"detail": "Trial origin mismatch"}, status_code=403)
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        if path not in {"/", "/healthz", "/__doctor_trial"}:
            if any(request.headers.get(key) != value for key, value in headers.items()):
                return JSONResponse({"detail": "Trial identity mismatch"}, status_code=409, headers=error_headers)
            allowed = (path in {"/auth/login", "/auth/me"}
                       or path == "/api/cases" or path.startswith("/api/cases/")
                       or path.startswith("/api/clinical-docs/")
                       or path == "/api/followup-plan-queue"
                       or request.method == "GET" and (
                           path.startswith("/kb/") or path.startswith("/api/diagnostic-data/")
                           or path == "/api/ai/consult/sessions" or path.startswith("/api/ai/consult/session/")))
            if path.endswith("/analyze"):
                allowed = False
            if not allowed:
                return JSONResponse({"detail": "本机合成练习未启用此接口"}, status_code=403, headers=error_headers)
        response = await call_next(request)
        for key, value in headers.items():
            response.headers[key] = value
        # DOCX downloads verify X-PMAI-Content-Snapshot. Preserve existing exposure.
        exposed = [name.strip() for name in response.headers.get("Access-Control-Expose-Headers", "").split(",") if name.strip()]
        response.headers["Access-Control-Expose-Headers"] = ", ".join(dict.fromkeys(exposed + list(headers)))
        response.headers["Cache-Control"] = "no-store"
        return response

    @main.app.get("/__doctor_trial", include_in_schema=False)
    def identity():
        return public

    return main.app, config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("--fd", type=int, required=True)
    args = parser.parse_args()
    app, config = prepare_app(args.config)
    listener = socket.socket(fileno=args.fd)
    if listener.getsockname() != ("127.0.0.1", config["api_port"]):
        raise ValueError("listener identity mismatch")
    import uvicorn
    uvicorn.Server(uvicorn.Config(app, loop="asyncio", access_log=False)).run(sockets=[listener])


if __name__ == "__main__":
    main()

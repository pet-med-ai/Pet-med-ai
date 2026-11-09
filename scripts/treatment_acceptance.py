#!/usr/bin/env python3
"""Synthetic acceptance host. No existing database URL or production target input."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import subprocess
import sys
import time

from treatment_acceptance_support import (
    ROOT, Cluster, check, clean_env, expand_and_seed, free_port, identity,
    make_api, seed_legacy, set_policy, source_change, write_json,
)

CHECKS = ("roles", "sign-readback", "utf8", "stale-draft", "stale-source", "expired-copy", "lost-response", "two-person", "amend-revoke-resign", "late-200", "late-401")
ACTIONS = ("expire", "source-change", "policy-two", "policy-self", "lose-sign-response", "late-200", "late-401", "release", "stop")


def session_path(arg=None):
    path = Path(arg).expanduser().resolve() if arg else Path(json.loads((ROOT / ".acceptance/latest.json").read_text())["session"]).resolve()
    marker = json.loads((path / "session.json").read_text())
    check(marker["session"] == str(path) and marker["format"] == "pmai-treatment-acceptance-v1", "Unrecognized session directory")
    return path


def new_session(arg, candidate):
    parent = ROOT / ".acceptance"
    parent.mkdir(exist_ok=True, mode=0o700)
    state = Path(arg).expanduser().resolve() if arg else parent / (time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(4))
    state.mkdir(mode=0o700, parents=False, exist_ok=False)
    write_json(state / "session.json", {"format": "pmai-treatment-acceptance-v1", "session": str(state), "candidate": candidate})
    write_json(parent / "latest.json", {"session": str(state)})
    return state


def postgres_bin(given):
    candidates = [Path(given)] if given else [Path("/opt/homebrew/opt/postgresql@17/bin"), Path("/usr/local/opt/postgresql@17/bin")]
    found = shutil.which("initdb")
    if not given and found:
        candidates.append(Path(found).parent)
    for path in candidates:
        if all((path / n).is_file() for n in ("initdb", "postgres", "pg_isready", "pg_dump", "pg_dumpall", "pg_restore", "psql", "createdb")):
            version = subprocess.check_output([str(path / "postgres"), "--version"], text=True, env=clean_env()).strip()
            check(re.search(r"\b17\.", version), "This kit was verified with PostgreSQL 17; select that toolchain")
            return path.resolve()
    raise RuntimeError("PostgreSQL 17 tools not found. On Mac: brew install postgresql@17 (do not start brew services)")


def build_ui(state):
    output = state / "ui"
    with (state / "build.log").open("w") as log:
        subprocess.run(["npm", "run", "build", "--", "--outDir", str(output)], cwd=ROOT / "frontend", env=clean_env(VITE_MULTICLINIC_READ_PILOT="1", VITE_TREATMENT_PILOT="1", VITE_API_BASE=""), check=True, stdout=log, stderr=log)
    check((output / "index.html").is_file(), "Frontend build missing")
    return output


class Controls:
    def __init__(self, state, owner, fixture, receipt):
        self.state, self.owner, self.fixture, self.receipt = state, owner, fixture, receipt
        self.fault = None
        self.held = []
        self.events = []
        (state / "requests").mkdir(mode=0o700)
        (state / "responses").mkdir(mode=0o700)

    def event(self, event_type, **fields):
        self.events.append({"time": time.time(), "event": event_type, **fields})
        write_json(self.state / "events.json", self.events)

    def apply(self, action, user=1):
        import sqlalchemy as sa
        check(action in ACTIONS and user in range(1, 8), "Unsupported synthetic action")
        if action == "expire":
            with self.owner.begin() as conn:
                conn.execute(sa.text("UPDATE auth_sessions SET revoked_at=now() WHERE user_id=:u AND revoked_at IS NULL"), {"u": user})
        elif action == "source-change":
            source_change(self.owner, 108)
        elif action in ("policy-two", "policy-self"):
            set_policy(self.owner, self.fixture, "two_person" if action == "policy-two" else "self_allowed")
        elif action == "release" or action == "stop":
            for gate in self.held:
                gate.set()
            self.fault = None
        else:
            check(self.fault is None, "A one-shot fault is already armed; release it first")
            self.fault = action
        self.event("control", action=action, user=user)
        return {"action": action, "applied": True, "manual_safari_result": self.receipt["manual_safari_result"]}

    async def pump(self, server):
        while not server.should_exit:
            for request in sorted((self.state / "requests").glob("*.json")):
                try:
                    body = json.loads(request.read_text())
                    result = self.apply(body["action"], body.get("user", 1))
                    if body["action"] == "stop":
                        server.should_exit = True
                except Exception as exc:
                    result = {"applied": False, "error": str(exc)}
                write_json(self.state / "responses" / request.name, result)
                request.unlink()
            await asyncio.sleep(0.1)

    async def intercept(self, request, call_next):
        from starlette.responses import JSONResponse, Response
        kind = self.fault
        path = request.url.path
        matches = (kind == "lose-sign-response" and request.method == "POST" and path.endswith("/signatures")) or (kind in ("late-200", "late-401") and request.method == "GET" and bool(re.search(r"/cases/\d+(?:/treatment)?$", path)))
        if not matches:
            return await call_next(request)
        self.fault = None
        # The original API executes exactly once; never replay a write.
        response = await call_next(request)
        data = b"".join([chunk async for chunk in response.body_iterator])
        gate = asyncio.Event()
        self.held.append(gate)
        self.event("response_prepared", kind=kind, path=path, status=response.status_code, idempotency_key=request.headers.get("Idempotency-Key"), browser_receipt=False)
        try:
            await asyncio.wait_for(gate.wait(), timeout=180)
        except asyncio.TimeoutError:
            pass
        finally:
            self.held.remove(gate)
        self.event("response_released", kind=kind, path=path, browser_receipt=False)
        if kind == "lose-sign-response":
            return JSONResponse({"code": "SYNTHETIC_RESPONSE_LOST"}, status_code=504, headers={"Cache-Control": "no-store"})
        if kind == "late-401":
            return JSONResponse({"detail": "Synthetic delayed 401"}, status_code=401, headers={"Cache-Control": "no-store"})
        return Response(data, status_code=response.status_code, headers=dict(response.headers), media_type=response.media_type)


def hosted_app(api, ui, controls, port, receipt):
    from fastapi import FastAPI
    from starlette.responses import JSONResponse
    from starlette.staticfiles import StaticFiles
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def boundary(request, call_next):
        if request.headers.get("host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
            return JSONResponse({"error": "local host required"}, status_code=403)
        origin = request.headers.get("origin")
        if origin and origin not in (f"http://127.0.0.1:{port}", f"http://localhost:{port}"):
            return JSONResponse({"error": "same origin required"}, status_code=403)
        return await controls.intercept(request, call_next)

    @app.get("/__acceptance__/health")
    def health():
        return {"session": receipt["session"], "candidate": receipt["candidate"], "synthetic_only": True, "manual_safari_result": "PENDING", "acceptance": "NOT_CLOSED"}

    # Preserve production router paths and gate. Static content has its own host.
    app.mount("/api", PrefixAPI(api, "/api"))
    app.mount("/", StaticFiles(directory=str(ui), html=True))
    return app


class PrefixAPI:
    def __init__(self, app, prefix):
        self.app, self.prefix = app, prefix

    async def __call__(self, scope, receive, send):
        # Mounted ASGI routers see root_path; the real API is rooted at /api/v2.
        scope = {**scope, "root_path": ""}
        if not scope["path"].startswith(self.prefix + "/"):
            scope["path"] = self.prefix + scope["path"]
        await self.app(scope, receive, send)


def serve(state, pg_bin, candidate, open_safari=False):
    import uvicorn
    receipt = {"session": str(state), "candidate": candidate, "synthetic_only": True, "host_platform": platform.platform(), "status": "PREPARING", "manual_safari_result": "PENDING", "acceptance": "NOT_CLOSED", "cleanup": False}
    write_json(state / "receipt.json", receipt)
    try:
        ui = build_ui(state)
        with Cluster(state / "postgres", pg_bin) as cluster:
            fixture = seed_legacy(cluster)
            receipt["migration"] = expand_and_seed(cluster, fixture)
            # Account secrets are local, random and never placed in public artifacts.
            write_json(state / "accounts.json", {"password": fixture["password"], "accounts": fixture["accounts"], "org": fixture["org"], "clinic": fixture["clinic"], "remote_clinic": fixture["remote_clinic"], "case_names": fixture["case_names"]})
            port = free_port()
            receipt.update(status="RUNNING", url=f"http://127.0.0.1:{port}", pid=os.getpid())
            write_json(state / "receipt.json", receipt)
            controls = Controls(state, cluster.engine(), fixture, receipt)
            api = make_api(cluster.url(user="pmai_treatment_runtime"), secrets.token_urlsafe(48))
            app = hosted_app(api, ui, controls, port, receipt)
            server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False, timeout_graceful_shutdown=3))

            async def host():
                pump = asyncio.create_task(controls.pump(server))
                try:
                    await server.serve()
                finally:
                    pump.cancel()
                    for gate in controls.held:
                        gate.set()

            print(f"仅合成病例；候选 {candidate['commit']}\nSafari 地址：{receipt['url']}\n合成密码：{fixture['password']}\n账号：doctor-a@example.invalid\n会话：{state}\n保持此终端打开；Ctrl+C 或另一个终端运行 control stop。", flush=True)
            if open_safari:
                check(platform.system() == "Darwin", "Native Safari launch requires macOS")
                # Safari can briefly show connection refused before the server is ready.
                # An async readiness task opens it only once TCP is accepting.
                async def host_and_open():
                    async def open_when_ready():
                        while not server.started and not server.should_exit:
                            await asyncio.sleep(.1)
                        if server.started:
                            subprocess.run(["open", "-a", "Safari", receipt["url"]], check=True)
                    opener = asyncio.create_task(open_when_ready())
                    try:
                        await host()
                    finally:
                        opener.cancel()
                asyncio.run(host_and_open())
            else:
                asyncio.run(host())
            receipt["status"] = "STOPPED"
    except BaseException as exc:
        receipt["status"] = "STOPPED" if isinstance(exc, KeyboardInterrupt) else "FAILED"
        if not isinstance(exc, KeyboardInterrupt):
            receipt["error"] = f"{type(exc).__name__}: {exc}"
            raise
    finally:
        receipt["cleanup"] = not (state / "postgres").exists()
        write_json(state / "receipt.json", receipt)
    return receipt


def control(state, action, user=1):
    receipt = json.loads((state / "receipt.json").read_text())
    check(receipt["status"] == "RUNNING", "Session is not running")
    request_id = secrets.token_hex(16)
    write_json(state / "requests" / (request_id + ".json"), {"action": action, "user": user})
    response = state / "responses" / (request_id + ".json")
    for _ in range(100):
        if response.exists():
            result = json.loads(response.read_text())
            check(result.get("applied"), result.get("error", "Control failed"))
            if action == "stop":
                for _ in range(200):
                    end = json.loads((state / "receipt.json").read_text())
                    if end["status"] != "RUNNING":
                        check(end["status"] == "STOPPED" and end["cleanup"], "Stop cleanup was not confirmed")
                        return end
                    time.sleep(.1)
                raise RuntimeError("Stop requested, but shutdown/cleanup not confirmed")
            return result
        time.sleep(.1)
    raise RuntimeError("No control acknowledgment; do not assume it executed")


def record_observation(state, args):
    check(platform.system() == "Darwin", "Native Safari observations must be entered on macOS")
    check(args.note.strip(), "A concrete operator observation is required")
    path = state / "manual-observations.json"
    records = json.loads(path.read_text()) if path.exists() else []
    records.append({"check": args.check, "result": args.result, "observation": args.note, "browser": args.browser, "time": time.time(), "platform": platform.platform(), "candidate": json.loads((state / "session.json").read_text())["candidate"], "reported_by_operator": True})
    write_json(path, records)
    # Recording individual observations does not close acceptance automatically.
    return {"recorded": args.check, "manual_safari_result": "PENDING_REVIEW", "acceptance": "NOT_CLOSED"}


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state", help="New or existing local acceptance directory; never a database target")
    sub = p.add_subparsers(dest="command", required=True)
    for cmd in ("serve", "drill"):
        c = sub.add_parser(cmd)
        c.add_argument("--postgres-bin")
        c.add_argument("--allow-dirty", action="store_true", help="Development only; receipt records dirty candidate")
        if cmd == "serve":
            c.add_argument("--open-safari", action="store_true")
    sub.add_parser("status")
    sub.add_parser("accounts")
    sub.add_parser("cleanup")
    c = sub.add_parser("control")
    c.add_argument("action", choices=ACTIONS)
    c.add_argument("--user", type=int, choices=range(1, 8), default=1)
    c = sub.add_parser("observe")
    c.add_argument("check", choices=CHECKS)
    c.add_argument("result", choices=("PASS", "FAIL", "BLOCKED"))
    c.add_argument("--note", required=True)
    c.add_argument("--browser", required=True, help="Observed native Safari version")
    args = p.parse_args()
    if args.command in ("serve", "drill"):
        candidate = identity()
        check(not candidate["dirty"] or args.allow_dirty, "Uncommitted candidate; use a pinned clean package")
        pg_bin = postgres_bin(args.postgres_bin)
        state = new_session(args.state, candidate)
        if args.command == "drill":
            from treatment_acceptance_drill import run_drill
            result = run_drill(state, pg_bin, candidate)
        else:
            result = serve(state, pg_bin, candidate, args.open_safari)
    else:
        state = session_path(args.state)
        if args.command == "control":
            result = control(state, args.action, args.user)
        elif args.command == "observe":
            result = record_observation(state, args)
        elif args.command == "cleanup":
            receipt_file = state / "receipt.json"
            receipt = json.loads((receipt_file if receipt_file.exists() else state / "drill-receipt.json").read_text())
            check(receipt["status"] in ("STOPPED", "PASS", "FAILED") and receipt["cleanup"], "Stop and confirm database cleanup first")
            # Only this kit's known generated items; evidence remains in place.
            if (state / "ui").is_dir():
                shutil.rmtree(state / "ui")
            (state / "accounts.json").unlink(missing_ok=True)
            result = {"cleanup": True, "receipt_retained": True, "manual_safari_result": receipt["manual_safari_result"], "acceptance": "NOT_CLOSED"}
            write_json(state / "cleanup-receipt.json", result)
        elif args.command == "accounts":
            result = json.loads((state / "accounts.json").read_text())
        else:
            path = state / "receipt.json"
            result = json.loads((path if path.exists() else state / "drill-receipt.json").read_text())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

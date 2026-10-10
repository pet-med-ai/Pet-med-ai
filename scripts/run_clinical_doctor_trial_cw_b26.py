"""A local, disposable doctor's practice session. No installs, existing DBs or deploys."""
from __future__ import annotations

import argparse
import functools
import hashlib
import http.server
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "clinical-doctor-trial-cw-b26-v1"


class TrialError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def clean_environment():
    """Do not inherit DATABASE_URL, credentials, proxies, feature flags or dotenv."""
    return {"PATH": os.environ.get("PATH", os.defpath), "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            # macOS commonly selects /var/folders/.../T, not /tmp. Both processes
            # must validate the same temporary root without inheriting other env.
            "TMPDIR": tempfile.gettempdir()}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, env=clean_environment())


def source_identity():
    head = git("rev-parse", "HEAD").decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise TrialError("candidate", "无法核对当前候选提交。")
    names = set(git("ls-files", "-z").split(b"\0"))
    # CI evidence is generated output, not application source; it changes during checks.
    untracked = {name for name in git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
                 if name and not name.startswith(b"acceptance-results/")}
    names.update(untracked)
    digest = hashlib.sha256()
    for raw in sorted(names - {b""}):
        path = ROOT / os.fsdecode(raw)
        if path.is_symlink() or not path.is_file():
            raise TrialError("source_path", "候选源文件缺失或为符号链接。")
        digest.update(raw + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return {"head": head, "source_sha256": digest.hexdigest(),
            "clean": not bool(git("diff", "--name-only", "HEAD").strip() or untracked)}


def preflight(expected_head=None):
    if sys.version_info < (3, 11):
        raise TrialError("python", "需要 Python 3.11 或更高版本。")
    required = ("fastapi", "uvicorn", "sqlalchemy", "jose", "passlib", "multipart",
                "pydantic", "yaml", "jsonschema", "httpx", "email_validator")
    missing = [name for name in required if importlib.util.find_spec(name) is None]
    if missing:
        raise TrialError("dependencies", "缺少 Python 依赖，请按说明准备环境：" + ", ".join(missing))
    node = shutil.which("node")
    if not node:
        raise TrialError("node", "未找到 Node，请先准备项目依赖。")
    version = subprocess.check_output([node, "--version"], env=clean_environment(), text=True)
    if int(version.lstrip("v").split(".")[0]) < 20:
        raise TrialError("node", "需要 Node 20 或更高版本。")
    for name in ("vite", "@vitejs/plugin-react", "react", "react-dom", "axios", "react-router-dom"):
        if not (ROOT / "frontend/node_modules" / name / "package.json").is_file():
            raise TrialError("dependencies", "前端依赖未准备好，请按说明运行 npm ci。")
    identity = source_identity()
    if expected_head and identity["head"] != expected_head:
        raise TrialError("candidate", "当前提交与指定候选不一致，未启动。")
    return node, identity


def reserve_port(port):
    if not 1024 <= port <= 65535:
        raise TrialError("port", "端口必须在 1024 到 65535 之间。")
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listener.bind(("127.0.0.1", port))
    except OSError as error:
        listener.close()
        raise TrialError("port_busy", "本机端口被占用；未结束其他程序。") from error
    return listener


def write_private(path, value):
    with path.open("x", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        json.dump(value, stream, ensure_ascii=False, indent=2)


def make_session(identity, ui_port, api_port):
    directory = Path(tempfile.mkdtemp(prefix="pmai-cwb26-")).resolve()
    (directory / "synthetic-only").write_text("CW-B26", encoding="utf-8")
    (directory / "private").mkdir(mode=0o700)
    config = {**identity, "schema": SCHEMA, "session": secrets.token_hex(32),
              "database_url": "sqlite:///" + str(directory / "synthetic.sqlite"),
              "private_dir": str(directory / "private"),
              "ui_origin": "http://127.0.0.1:" + str(ui_port),
              "api_origin": "http://127.0.0.1:" + str(api_port),
              "api_port": api_port, "ui_port": ui_port,
              "email": "practice-" + secrets.token_hex(6) + "@example.com",
              "password": secrets.token_urlsafe(24), "secret": secrets.token_hex(48)}
    write_private(directory / "environment.json", config)
    return directory, config


def remove_session(directory, session):
    """Delete only the exact marked session this invocation created."""
    if directory.is_symlink() or directory.parent != Path(tempfile.gettempdir()).resolve():
        raise TrialError("cleanup", "临时目录身份不符，未执行清理。")
    if not directory.name.startswith("pmai-cwb26-"):
        raise TrialError("cleanup", "临时目录名称不符，未执行清理。")
    marker = directory / "synthetic-only"
    config = directory / "environment.json"
    if marker.is_symlink() or config.is_symlink() or marker.read_text() != "CW-B26":
        raise TrialError("cleanup", "临时目录标记不符，未执行清理。")
    if json.loads(config.read_text())["session"] != session:
        raise TrialError("cleanup", "临时会话不符，未执行清理。")
    shutil.rmtree(directory)


def stop_process(process):
    """Signal only a child/process group created by this launcher."""
    if process is None or process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def build_frontend(node, directory, config):
    # configFile:false and a new envDir prevent loading project .env files/plugins.
    code = """
      import {build} from 'vite';
      import react from '@vitejs/plugin-react';
      const c=JSON.parse(process.argv[1]);
      await build({configFile:false,root:process.cwd(),envDir:c.envDir,
        plugins:[react()],define:c.define,
        build:{outDir:c.outDir,emptyOutDir:true,manifest:true}});
    """
    build = {"envDir": str(directory), "outDir": str(directory / "web"),
             "define": {("import.meta.env." + key): json.dumps(value) for key, value in {
                 "VITE_API_BASE": config["api_origin"], "VITE_DOCTOR_TRIAL": "1",
                 "VITE_DOCTOR_TRIAL_SESSION": config["session"],
                 "VITE_DOCTOR_TRIAL_HEAD": config["head"],
                 "VITE_DOCTOR_TRIAL_SOURCE": config["source_sha256"]}.items()}}
    with (directory / "build.log").open("w") as log:
        process = subprocess.Popen([node, "--input-type=module", "-e", code, json.dumps(build)],
                                   cwd=ROOT / "frontend", env=clean_environment(),
                                   stdout=log, stderr=log, start_new_session=True)
        try:
            if process.wait(timeout=90):
                raise TrialError("build", "前端构建失败，请核对依赖和候选版本。")
        finally:
            stop_process(process)
    if source_identity() != {k: config[k] for k in ("head", "source_sha256", "clean")}:
        raise TrialError("source_changed", "构建期间源文件变化，已停止。")
    spec = importlib.util.spec_from_file_location("trial_samples", ROOT / "tests/fixtures/build_attachment_cw_b6_fixtures.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    samples = directory / "web/trial-samples"
    samples.mkdir()
    for name, _, data in module.samples():
        (samples / name).write_bytes(data)
    fixture = json.loads((ROOT / "tests/fixtures/clinical_visit_journey_cw_b24_cases.json").read_text())
    (samples / "practice.json").write_text(json.dumps(fixture, ensure_ascii=False, indent=2))


class TrialHTTPServer(http.server.ThreadingHTTPServer):
    daemon_threads = True


class TrialHandler(http.server.SimpleHTTPRequestHandler):
    api_origin = ""
    ui_origin = ""

    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; connect-src 'self' " + self.api_origin +
                         "; img-src 'self' data:; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
        super().end_headers()

    def do_GET(self):
        if self.headers.get("Host") != urlsplit(self.ui_origin).netloc:
            self.send_error(403)
            return
        path = Path(self.translate_path(self.path))
        if not path.is_file() and "." not in urlsplit(self.path).path.rsplit("/", 1)[-1]:
            self.path = "/index.html"
        super().do_GET()

    do_HEAD = http.server.SimpleHTTPRequestHandler.do_HEAD


def identity_matches(actual, config):
    return (actual.get("schema") == SCHEMA and actual.get("synthetic_only") is True
            and all(actual.get(key) == config[key] for key in ("session", "head", "source_sha256")))


def run(args):
    receipt = {"schema": SCHEMA, "status": "STARTING", "external_business_calls": 0,
               "platform": sys.platform, "temporary_data_removed": False, "children_stopped": False}
    directory = config = backend = web = thread = api_socket = ui_socket = None
    previous_signals = {}

    def interrupted(signum, frame):
        raise KeyboardInterrupt

    try:
        if args.receipt and (args.receipt.exists() or not args.receipt.parent.is_dir()):
            raise TrialError("receipt_path", "回执路径已存在或父目录不存在，未覆盖文件。")
        node, identity = preflight(args.expect_head)
        receipt.update(identity)
        if args.ui_port == args.api_port:
            raise TrialError("port", "前后端端口不能相同。")
        ui_socket = reserve_port(args.ui_port)
        api_socket = reserve_port(args.api_port)
        directory, config = make_session(identity, args.ui_port, args.api_port)
        receipt.update(session=config["session"], ui_origin=config["ui_origin"], api_origin=config["api_origin"])
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_signals[signum] = signal.signal(signum, interrupted)
        print("正在构建本机合成病例练习入口……", flush=True)
        build_frontend(node, directory, config)
        api_socket.listen(128)
        with (directory / "backend.log").open("w") as log:
            backend = subprocess.Popen([sys.executable, "-B", str(ROOT / "tests/acceptance/clinical_doctor_trial_runtime.py"),
                                        str(directory / "environment.json"), "--fd", str(api_socket.fileno())],
                                       cwd=directory, env=clean_environment(), stdout=log, stderr=log,
                                       pass_fds=(api_socket.fileno(),), start_new_session=True)
        api_socket.close()
        api_socket = None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(120):
            if backend.poll() is not None:
                raise TrialError("backend", "合成后端启动失败；未接入其他数据库。")
            try:
                with opener.open(config["api_origin"] + "/__doctor_trial", timeout=0.5) as response:
                    actual = json.load(response)
                if not identity_matches(actual, config):
                    raise TrialError("identity", "后端版本或会话不符。")
                break
            except (OSError, ValueError):
                time.sleep(0.1)
        else:
            raise TrialError("backend_timeout", "合成后端启动超时。")
        handler = type("BoundTrialHandler", (TrialHandler,), {
            "api_origin": config["api_origin"], "ui_origin": config["ui_origin"]})
        web = TrialHTTPServer(("127.0.0.1", args.ui_port),
                              functools.partial(handler, directory=str(directory / "web")), bind_and_activate=False)
        web.socket.close()
        web.socket, ui_socket = ui_socket, None
        web.server_address = web.socket.getsockname()
        web.server_activate()
        thread = threading.Thread(target=web.serve_forever, daemon=True)
        thread.start()
        receipt["status"] = "READY"
        print("合成病例练习，不录入真实资料。按 Ctrl+C 结束；本轮临时记录将清理。", flush=True)
        # Only the interactive terminal/control pipe receives ephemeral credentials.
        # Browser acceptance captures this line in memory, never in artifacts.
        print("PMAI_TRIAL_READY " + json.dumps({
            "url": config["ui_origin"], "api": config["api_origin"], "email": config["email"],
            "password": config["password"], "head": config["head"], "source_sha256": config["source_sha256"],
            "session": config["session"], "samples_dir": str(directory / "web/trial-samples"),
            "temporary_dir": str(directory)}, ensure_ascii=False), flush=True)
        while True:
            time.sleep(0.2)
            if backend.poll() is not None or not thread.is_alive():
                raise TrialError("child_exit", "本次服务已停止，请核对保存结果后重新启动。")
    except KeyboardInterrupt:
        receipt["status"] = "STOPPED" if receipt["status"] == "READY" else "INTERRUPTED"
    except Exception as error:
        receipt["status"] = "FAILED"
        receipt["error_code"] = getattr(error, "code", type(error).__name__)
        print(str(error) if isinstance(error, TrialError) else "试用启动失败：" + type(error).__name__, file=sys.stderr)
    finally:
        for signum, previous in previous_signals.items():
            signal.signal(signum, previous)
        if web:
            if thread:
                web.shutdown()
                thread.join(timeout=5)
            web.server_close()
        stop_process(backend)
        receipt["children_stopped"] = backend is None or backend.poll() is not None
        for listener in (api_socket, ui_socket):
            if listener:
                listener.close()
        if directory:
            try:
                remove_session(directory, config["session"])
                receipt["temporary_data_removed"] = True
            except Exception:
                receipt.update(status="FAILED", error_code="cleanup")
        if args.receipt and not args.receipt.exists() and args.receipt.parent.is_dir():
            write_private(args.receipt, receipt)
        print("PMAI_TRIAL_STOPPED " + json.dumps(receipt, ensure_ascii=False), flush=True)
    return 0 if receipt["status"] == "STOPPED" else 1


def main():
    parser = argparse.ArgumentParser(description="仅本机、仅新建临时数据的合成病例练习。依赖须预先准备。")
    parser.add_argument("--ui-port", type=int, default=5174)
    parser.add_argument("--api-port", type=int, default=18027)
    parser.add_argument("--expect-head", help="必须与指定 Git 提交一致，否则拒绝启动")
    parser.add_argument("--receipt", type=Path, help="可选脱敏回执路径；不覆盖已有文件")
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())

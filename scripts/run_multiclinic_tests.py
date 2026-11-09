#!/usr/bin/env python3
"""Run isolated PostgreSQL tests; optionally start a local unprivileged temporary cluster."""

import argparse
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time


def run(env):
    if not env.get("PMAI_TEST_POSTGRES_ADMIN_URL"):
        raise SystemExit(
            "Set PMAI_TEST_POSTGRES_ADMIN_URL to a disposable PostgreSQL administrator URL, or pass --postgres-bin"
        )
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            env.get("PMAI_POSTGRES_TEST_PATTERN", "test_multiclinic_postgres.py"),
            "-v",
        ],
        env=env,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-bin", type=Path)
    args = parser.parse_args()
    os.chdir(Path(__file__).resolve().parents[1])
    if not args.postgres_bin:
        return run(os.environ.copy())
    with tempfile.TemporaryDirectory(prefix="pmai-pg-") as tmp:
        data = Path(tmp) / "data"
        subprocess.run(
            [
                str(args.postgres_bin / "initdb"),
                "-D",
                str(data),
                "--auth-local=trust",
                "--auth-host=trust",
                "--no-locale",
                "-E",
                "UTF8",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        with (Path(tmp) / "postgres.log").open("w+") as log:
            server = subprocess.Popen(
                [
                    str(args.postgres_bin / "postgres"),
                    "-D",
                    str(data),
                    "-h",
                    "127.0.0.1",
                    "-p",
                    str(port),
                    "-c",
                    "unix_socket_directories=",
                ],
                stdout=log,
                stderr=log,
            )
            try:
                import getpass

                url = f"postgresql+psycopg2://{getpass.getuser()}@127.0.0.1:{port}/postgres"
                for _ in range(100):
                    probe = subprocess.run(
                        [
                            str(args.postgres_bin / "pg_isready"),
                            "-h",
                            "127.0.0.1",
                            "-p",
                            str(port),
                        ],
                        stdout=subprocess.DEVNULL,
                    )
                    if probe.returncode == 0:
                        break
                    if server.poll() is not None:
                        log.seek(0)
                        raise RuntimeError(
                            "Temporary PostgreSQL failed to start: " + log.read()
                        )
                    time.sleep(0.1)
                else:
                    raise RuntimeError("Temporary PostgreSQL startup timed out")
                return run({**os.environ, "PMAI_TEST_POSTGRES_ADMIN_URL": url})
            finally:
                server.send_signal(signal.SIGINT)
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Start, test and stop a disposable host in one process/network execution unit."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

from treatment_acceptance_support import ROOT, check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--postgres-bin", required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    state = args.state.resolve()
    command = [sys.executable, str(ROOT / "scripts/treatment_acceptance.py"), "--state", str(state)]
    log_path = state.parent / (state.name + "-host.log")
    with log_path.open("w") as log:
        process = subprocess.Popen(command + ["serve", "--postgres-bin", args.postgres_bin] + (["--allow-dirty"] if args.allow_dirty else []), stdout=log, stderr=log)
        try:
            for _ in range(600):
                check(process.poll() is None, "Acceptance host exited; inspect host log")
                if (state / "receipt.json").exists():
                    receipt = json.loads((state / "receipt.json").read_text())
                    if receipt["status"] == "RUNNING":
                        try:
                            with urllib.request.urlopen(receipt["url"] + "/__acceptance__/health", timeout=1) as r:
                                check(json.load(r)["candidate"] == receipt["candidate"], "Host candidate mismatch")
                            break
                        except OSError:
                            pass
                time.sleep(.1)
            else:
                raise RuntimeError("Acceptance host startup timed out")
            subprocess.run(["node", "frontend/tests/treatment-acceptance-browser.mjs"], cwd=ROOT, env={**os.environ, "PMAI_ACCEPTANCE_STATE": str(state), "PMAI_ACCEPTANCE_PYTHON": sys.executable}, check=True)
        finally:
            if process.poll() is None:
                subprocess.run(command + ["control", "stop"], stdout=subprocess.DEVNULL, check=True)
            process.wait(timeout=20)
            if (state / "receipt.json").exists():
                receipt = json.loads((state / "receipt.json").read_text())
                check(receipt["status"] == "STOPPED" and receipt["cleanup"], "Host shutdown or cleanup not verified")
                subprocess.run(command + ["cleanup"], stdout=subprocess.DEVNULL, check=True)


if __name__ == "__main__":
    main()

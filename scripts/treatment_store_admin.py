#!/usr/bin/env python3
"""Offline treatment pilot administration. Configure/import defaults to dry run."""
import argparse
import json
import os
from pathlib import Path
import sys
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from sqlalchemy import create_engine
from treatment_store.admin import configure, import_legacy, install_policy


def uuid(value):
    return str(UUID(value))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("install-policy")
    for name in ("clinician", "policy", "import-legacy"):
        c = sub.add_parser(name)
        c.add_argument("--org", type=uuid, required=True)
        c.add_argument("--actor", type=int, required=True)
        c.add_argument("--key", required=True)
        c.add_argument("--reason", required=True)
        c.add_argument("--apply", action="store_true")
        if name == "clinician":
            c.add_argument("--membership", type=uuid, required=True)
            c.add_argument("--name", required=True)
            c.add_argument("--credential", required=True)
            c.add_argument("--status", choices=["active", "revoked"], default="active")
        elif name == "policy":
            c.add_argument(
                "--review-policy", choices=["self_allowed", "two_person"], required=True
            )
            c.add_argument(
                "--assurance",
                choices=["account_attestation", "certificate_signature"],
                required=True,
            )
        else:
            c.add_argument("--clinic", type=uuid, required=True)
            c.add_argument("--case-id", type=int, required=True)
            c.add_argument("--expected-sha256")
    args = vars(p.parse_args())
    command = args.pop("command")
    url = os.getenv("MULTICLINIC_ADMIN_DATABASE_URL")
    if not url:
        p.error(
            "Set an explicit MULTICLINIC_ADMIN_DATABASE_URL; the application default is never used"
        )
    engine = create_engine(url)
    try:
        result = (
            install_policy(engine)
            if command == "install-policy"
            else (
                import_legacy(engine, **args)
                if command == "import-legacy"
                else configure(engine, **args)
            )
        )
        print(json.dumps(result, ensure_ascii=False))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

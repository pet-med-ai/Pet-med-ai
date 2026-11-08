#!/usr/bin/env python3
"""Administrator-only offline commands; defaults to backfill validation, never deployment."""

import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from sqlalchemy import create_engine
from multiclinic.migrate import backfill, revoke_membership


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    mapping = commands.add_parser("backfill")
    mapping.add_argument("manifest", type=Path)
    mapping.add_argument("--apply", action="store_true")
    mapping.add_argument("--batch-size", type=int, default=200)
    commands.add_parser("install-read-policy")
    revoke = commands.add_parser("revoke-membership")
    for name in ("org-id", "membership-id", "reason", "request-key"):
        revoke.add_argument("--" + name, required=True)
    revoke.add_argument("--actor-id", type=int, required=True)
    args = parser.parse_args()
    url = os.environ.get("MULTICLINIC_ADMIN_DATABASE_URL")
    if not url:
        parser.error(
            "MULTICLINIC_ADMIN_DATABASE_URL is required; the default app database is never used"
        )
    engine = create_engine(url)
    try:
        if args.command == "backfill":
            result = backfill(
                engine,
                json.loads(args.manifest.read_text()),
                apply=args.apply,
                batch_size=args.batch_size,
            )
        elif args.command == "install-read-policy":
            if engine.dialect.name != "postgresql":
                parser.error("Read policy requires PostgreSQL")
            with engine.begin() as conn:
                head = (
                    conn.exec_driver_sql("SELECT version_num FROM alembic_version")
                    .scalars()
                    .all()
                )
                if head != ["mc01_scope_expand"]:
                    raise ValueError("Unexpected schema head; do not stamp")
                conn.exec_driver_sql(
                    (
                        Path(__file__).resolve().parents[1]
                        / "backend/multiclinic/read_policy.sql"
                    ).read_text()
                )
            result = {"read_policy_installed": True, "web_service_enabled": False}
        else:
            result = revoke_membership(
                engine,
                org_id=args.org_id,
                membership_id=args.membership_id,
                actor_id=args.actor_id,
                reason=args.reason,
                request_key=args.request_key,
            )
        print(json.dumps(result, ensure_ascii=False))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

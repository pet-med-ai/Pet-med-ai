#!/usr/bin/env python3
"""Check a selected pilot's backend configuration without connecting to PostgreSQL."""

import os
import sys

ROLES = {
    "read_pilot": "pmai_scope_runtime",
    "treatment_pilot": "pmai_treatment_runtime",
}
USAGE = "Usage: python scripts/check_pilot_config.py {read_pilot|treatment_pilot}"


def database_status(expected_role, env):
    try:
        from psycopg2 import Error as PsycopgError
        from psycopg2.extensions import make_dsn, parse_dsn
        from sqlalchemy.dialects.postgresql.psycopg2 import dialect
        from sqlalchemy.engine import make_url
        from sqlalchemy.exc import ArgumentError
    except ImportError:
        return 2, "SETUP: use a backend Python environment with backend/requirements.txt installed."

    value = env.get("MULTICLINIC_DATABASE_URL")
    if not value:
        return 1, "INVALID: MULTICLINIC_DATABASE_URL is missing."
    try:
        url = make_url(value)
        if url.get_backend_name() != "postgresql":
            return 1, "INVALID: MULTICLINIC_DATABASE_URL must select PostgreSQL."
        # The pilot selects psycopg2 regardless of the URL's driver suffix.
        # Its dialect applies query-string overrides to authority components.
        if url.query.get("plugin"):
            return 3, "INDETERMINATE: an engine plugin may change connection settings."
        url = url.difference_update_query(["plugin", "plugins"])
        _, params = dialect().create_connect_args(url.set(drivername="postgresql+psycopg2"))
        if params.keys() & {"connection_factory", "cursor_factory", "async", "async_"}:
            return 3, "INDETERMINATE: nonstandard driver settings need separate verification."
        # Both libpq helpers parse strings only. No connection or service lookup.
        params = parse_dsn(make_dsn(**params))
    except (ArgumentError, PsycopgError, ValueError, TypeError):
        return 1, "INVALID: the PostgreSQL URL could not be parsed."
    dbname = params.get("dbname") or env.get("PGDATABASE", "")
    if (
        params.get("service") or env.get("PGSERVICE")
        or params.get("options") or env.get("PGOPTIONS")
        or dbname.startswith(("postgresql://", "postgres://")) or "=" in dbname
    ):
        return 3, "INDETERMINATE: indirect connection settings prevent an offline role check."
    user = params.get("user")
    if not user:
        return 3, "INDETERMINATE: the URL leaves the database user to connection defaults."
    if user != expected_role:
        return 1, "INVALID: the URL's selected user does not match the selected pilot role."
    return 0, "OK: the PostgreSQL URL selects the expected pilot user."


def main(argv, env):
    if argv in (["--help"], ["-h"]):
        print(USAGE)
        return 0
    if len(argv) != 1 or argv[0] not in ROLES:
        # Do not repeat invalid arguments, which may contain credentials.
        print(USAGE, file=sys.stderr)
        return 2
    selected = argv[0]
    result, message = database_status(ROLES[selected], env)
    print(message)
    if result == 2:
        return result
    if env.get("PMAI_MULTICLINIC_MODE") != selected:
        print("INVALID: PMAI_MULTICLINIC_MODE does not match the selected pilot.")
        result = 1
    if len(env.get("MULTICLINIC_TOKEN_SECRET", "")) < 32:
        print("INVALID: MULTICLINIC_TOKEN_SECRET needs at least 32 characters.")
        result = 1
    if result == 0:
        print("OK: mode, configured database user and token secret length match the selected pilot.")
    return result


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.environ))

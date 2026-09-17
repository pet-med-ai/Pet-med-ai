"""Test-only bootstrap. Refuses remote/existing databases; never runs migrations."""
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get('PMAI_ACCEPTANCE_OUT', ROOT / 'acceptance-results')).resolve()
URL = os.environ.get('DATABASE_URL', '')
u = urlparse(URL)
assert u.scheme == 'postgresql' and u.hostname == '127.0.0.1' and u.port == 55432
assert u.username == 'pmai_acceptance' and u.path == '/pmai_acceptance' and not u.query
assert os.environ.get('PMAI_SYNTHETIC_ACCEPTANCE') == 'PR26', 'Explicit synthetic test mode required'
OUT.mkdir(parents=True, exist_ok=True)
os.environ.clear()
os.environ.update(DATABASE_URL=URL, SECRET_KEY='synthetic-pr26-acceptance-only',
                  ENVIRONMENT='test', RENDER='false', PYTHONDONTWRITEBYTECODE='1')
sys.dont_write_bytecode = True
sys.path[:] = [str(ROOT / 'backend')] + [p for p in sys.path if Path(p or '.').resolve() != ROOT]


def network_guard(event, args):
    if event in {'socket.connect', 'socket.connect_ex', 'socket.bind'}:
        address = args[1]
        if isinstance(address, tuple):
            assert address[0] in {'127.0.0.1', '::1'} and address[1] in {55432, 18026}, address
    if event == 'socket.getaddrinfo':
        assert args[0] in {'localhost', '127.0.0.1', '::1', None}, args[0]
    if event == 'sqlite3.connect':
        raise RuntimeError('SQLite cannot substitute for PostgreSQL acceptance')


sys.addaudithook(network_guard)
import main
import db
import models
import feature_flags
from sqlalchemy import inspect, text

assert db.engine.url.get_backend_name() == 'postgresql'
assert not main.app.dependency_overrides
assert not feature_flags.dangerous_enabled_flags()


def prepare_empty_database():
    assert inspect(db.engine).get_table_names() == [], 'Refusing an existing schema'
    # Disposable schema from exact candidate ORM; this is not migration acceptance.
    db.Base.metadata.create_all(db.engine)
    with db.engine.connect() as c:
        details = dict(c.execute(text("SELECT version() AS version, current_database() AS database, current_user AS username, current_setting('transaction_isolation') AS isolation")).mappings().one())
    assert details['database'] == 'pmai_acceptance' and details['username'] == 'pmai_acceptance'
    (OUT / 'postgres-environment.json').write_text(json.dumps(details, indent=2))


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(main.app, host='127.0.0.1', port=18026, loop='asyncio')

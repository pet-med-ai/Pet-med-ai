"""Test-only bootstrap. Refuses remote/existing databases; never runs migrations."""
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get('PMAI_ACCEPTANCE_OUT', ROOT / 'acceptance-results')).resolve()
# CW-B24 alone may use its newly created, marked temporary SQLite directory.
CWB24 = '--visit-journey' in sys.argv
CWB24_CONFIG = None
if CWB24:
    config_path = Path(sys.argv[sys.argv.index('--visit-journey') + 1]).resolve()
    assert config_path.parent.name.startswith('pmai-cwb24-')
    assert config_path.name == 'environment.json' and (config_path.parent / 'synthetic-only').read_text() == 'CW-B24'
    CWB24_CONFIG = json.loads(config_path.read_text())
URL = CWB24_CONFIG['database_url'] if CWB24 else os.environ.get('DATABASE_URL', '')
CWB24_SQLITE = CWB24 and URL.startswith('sqlite:///')
u = urlparse(URL)
if CWB24_SQLITE:
    CWB24_DATABASE = (config_path.parent / 'synthetic.sqlite').resolve()
    assert URL == 'sqlite:///' + str(CWB24_DATABASE) and not CWB24_DATABASE.exists()
else:
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
        if not CWB24_SQLITE: raise RuntimeError('SQLite cannot substitute for PostgreSQL acceptance')
        assert Path(args[0]).resolve() == CWB24_DATABASE


sys.addaudithook(network_guard)
import main
import db
import models
import feature_flags
from sqlalchemy import inspect, text

assert db.engine.url.get_backend_name() == ('sqlite' if CWB24_SQLITE else 'postgresql')
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


def enable_manual_lab_documents():
    assert os.environ.get('ENVIRONMENT') == 'test' and os.environ.get('RENDER') == 'false'
    os.environ.update(MANUAL_LAB_DOCUMENTS_ENABLED='1', MANUAL_LAB_DOCUMENTS_SYNTHETIC_ONLY='1')


def enable_manual_imaging():
    assert os.environ.get('ENVIRONMENT') == 'test' and os.environ.get('RENDER') == 'false'
    os.environ.update(MANUAL_IMAGING_ENABLED='1', MANUAL_IMAGING_SYNTHETIC_ONLY='1')
    enable_manual_lab_documents()


def enable_visit_overview():
    assert os.environ.get('ENVIRONMENT') == 'test' and os.environ.get('RENDER') == 'false'
    os.environ.update(VISIT_OVERVIEW_ENABLED='1', VISIT_OVERVIEW_SYNTHETIC_ONLY='1')
    enable_manual_imaging()


def enable_lab_range_review():
    assert os.environ.get('ENVIRONMENT') == 'test' and os.environ.get('RENDER') == 'false'
    os.environ.update(LAB_RANGE_REVIEW_ENABLED='1', LAB_RANGE_REVIEW_SYNTHETIC_ONLY='1')


def enable_lab_comparison():
    assert os.environ.get('ENVIRONMENT') == 'test' and os.environ.get('RENDER') == 'false'
    os.environ.update(LAB_COMPARISON_ENABLED='1', LAB_COMPARISON_SYNTHETIC_ONLY='1')


def enable_lab_comparison_documents():
    enable_lab_comparison()
    enable_manual_lab_documents()
    os.environ.update(LAB_COMPARISON_DOCUMENTS_ENABLED='1', LAB_COMPARISON_DOCUMENTS_SYNTHETIC_ONLY='1')


def enable_followup_plans():
    assert os.environ.get('ENVIRONMENT') == 'test' and os.environ.get('RENDER') == 'false'
    os.environ.update(FOLLOWUP_PLANS_ENABLED='1', FOLLOWUP_PLANS_SYNTHETIC_ONLY='1')


def enable_followup_plan_documents():
    enable_followup_plans()
    os.environ.update(FOLLOWUP_PLAN_DOCUMENTS_ENABLED='1', FOLLOWUP_PLAN_DOCUMENTS_SYNTHETIC_ONLY='1')


def enable_followup_plan_owner_documents():
    enable_followup_plan_documents()
    os.environ.update(FOLLOWUP_PLAN_OWNER_DOCUMENTS_ENABLED='1', FOLLOWUP_PLAN_OWNER_DOCUMENTS_SYNTHETIC_ONLY='1')


def enable_followup_plan_overview():
    enable_visit_overview()
    enable_followup_plans()
    os.environ.update(FOLLOWUP_PLAN_OVERVIEW_ENABLED='1', FOLLOWUP_PLAN_OVERVIEW_SYNTHETIC_ONLY='1')


def enable_followup_plan_queue():
    enable_followup_plans()
    os.environ.update(FOLLOWUP_PLAN_QUEUE_ENABLED='1', FOLLOWUP_PLAN_QUEUE_SYNTHETIC_ONLY='1')


def enable_followup_contacts():
    enable_followup_plans()
    os.environ.update(FOLLOWUP_CONTACTS_ENABLED='1', FOLLOWUP_CONTACTS_SYNTHETIC_ONLY='1')


def enable_followup_contact_overview():
    enable_followup_plan_overview()
    enable_followup_contacts()
    os.environ.update(FOLLOWUP_CONTACT_OVERVIEW_ENABLED='1', FOLLOWUP_CONTACT_OVERVIEW_SYNTHETIC_ONLY='1')


def enable_followup_contact_documents():
    enable_followup_contacts()
    enable_followup_plan_documents()
    os.environ.update(FOLLOWUP_CONTACT_DOCUMENTS_ENABLED='1', FOLLOWUP_CONTACT_DOCUMENTS_SYNTHETIC_ONLY='1')


def enable_followup_contact_owner_documents():
    enable_followup_contact_documents()
    enable_followup_plan_owner_documents()
    os.environ.update(FOLLOWUP_CONTACT_OWNER_DOCUMENTS_ENABLED='1', FOLLOWUP_CONTACT_OWNER_DOCUMENTS_SYNTHETIC_ONLY='1')


def enable_followup_contact_queue():
    enable_followup_plan_queue()
    enable_followup_contacts()
    os.environ.update(FOLLOWUP_CONTACT_QUEUE_ENABLED='1', FOLLOWUP_CONTACT_QUEUE_SYNTHETIC_ONLY='1')


def enable_visit_journey():
    """Explicit test-only union of existing flags; no production activation."""
    assert CWB24 and os.environ['ENVIRONMENT'] == 'test' and os.environ['RENDER'] == 'false'
    private = (config_path.parent / 'private').resolve()
    assert CWB24_CONFIG['private_dir'] == str(private) and private.is_dir()
    os.environ.update(CASE_ATTACHMENTS_ENABLED='1', CASE_ATTACHMENTS_SYNTHETIC_ONLY='1',
                      CASE_ATTACHMENTS_DIR=str(private), MANUAL_LAB_RESULTS_ENABLED='1',
                      MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1')
    enable_followup_contact_queue()
    enable_followup_contact_overview()
    enable_followup_contact_owner_documents()
    enable_lab_comparison_documents()
    enable_lab_range_review()
    if CWB24_SQLITE:
        assert inspect(db.engine).get_table_names() == []
        db.Base.metadata.create_all(db.engine)  # New disposable schema, never a migration.


if __name__ == '__main__':
    if CWB24: enable_visit_journey()
    import uvicorn
    uvicorn.run(main.app, host='127.0.0.1', port=18026, loop='asyncio')

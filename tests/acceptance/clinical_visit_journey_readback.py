"""CW-B24 independent read-only database, DOCX and evidence verification."""
import argparse
from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse
import zipfile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / 'tests/fixtures/clinical_visit_journey_cw_b24_cases.json'
SCHEMA = 'clinical-visit-journey-cw-b24-v1'
TABLES = ('cases', 'diagnostic_reports', 'observations', 'imaging_studies',
          'followups', 'audit_log', 'consult_sessions')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str)


def environment(config):
    config = Path(config).resolve()
    require(os.environ.get('PMAI_SYNTHETIC_ACCEPTANCE') == 'PR26', 'Explicit synthetic test mode required')
    require(config.name == 'environment.json' and config.parent.name.startswith('pmai-cwb24-'), 'Unmarked environment')
    require((config.parent / 'synthetic-only').read_text() == 'CW-B24', 'Missing temporary marker')
    values = json.loads(config.read_text())
    url = values['database_url']
    if url.startswith('sqlite:///'):
        dbfile = (config.parent / 'synthetic.sqlite').resolve()
        require(url == 'sqlite:///' + str(dbfile) and dbfile.is_file(), 'Invalid disposable SQLite')
    else:
        u = urlparse(url)
        require(u.scheme == 'postgresql' and u.hostname == '127.0.0.1' and u.port == 55432
                and u.username == 'pmai_acceptance' and not u.password and u.path == '/pmai_acceptance'
                and not u.query and not u.fragment, 'Only the native synthetic PostgreSQL target is allowed')
    return values


def database_rows(config, case_id):
    from sqlalchemy import create_engine, event, text
    require(type(case_id) is int and case_id > 0, 'Invalid case ID')
    values = environment(config)
    url = values['database_url']
    if url.startswith('sqlite:///'):
        # SQLite's URI mode and query_only both refuse writes, including accidental ORM activity.
        url = 'sqlite:///file:' + url[len('sqlite:///'):] + '?mode=ro&uri=true'
    engine = create_engine(url)
    statements = []

    @event.listens_for(engine, 'before_cursor_execute')
    def guard(conn, cursor, statement, parameters, context, many):
        require(statement.lstrip().upper().startswith(('SELECT ', 'SET TRANSACTION READ ONLY', 'PRAGMA QUERY_ONLY=ON')),
                'Readback attempted a non-read statement')
        statements.append(statement.split()[0].upper())

    try:
        with engine.connect() as conn:
            conn.execute(text('PRAGMA query_only=ON' if engine.dialect.name == 'sqlite' else 'SET TRANSACTION READ ONLY'))
            rows = {}
            for table in TABLES:
                key = 'id' if table == 'cases' else 'case_id'
                rows[table] = sorted([dict(row) for row in conn.execute(
                    text(f'SELECT * FROM {table} WHERE {key} = :cid'), {'cid': case_id}).mappings()], key=canonical)
            conn.rollback()
        require(len(rows['cases']) == 1 and rows['cases'][0]['deleted_at'] is None, 'Missing/deleted synthetic case')
        require(rows['cases'][0]['patient_name'].startswith('CW24 合成'), 'Not a CW-B24 synthetic case')
        return rows, {'backend': engine.dialect.name, 'case_id': case_id, 'sha256': sha(canonical(rows).encode()),
                      'counts': {key: len(value) for key, value in rows.items()}, 'select_count': statements.count('SELECT'),
                      'read_only': True}
    finally:
        engine.dispose()


def json_value(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def metadata(row):
    for value in row.values():
        value = json_value(value)
        if isinstance(value, dict) and {'root_id', 'version', 'data'} <= set(value):
            return value
    raise ValueError('Missing version metadata')


def document_text(file):
    w = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    with zipfile.ZipFile(file) as archive:
        root = ET.fromstring(archive.read('word/document.xml'))
    return '\n'.join(''.join((node.text or '') if node.tag == w+'t' else '\n' if node.tag == w+'br'
                            else '\t' if node.tag == w+'tab' else '' for node in p.iter()) for p in root.iter(w+'p'))


def validate_evidence(report, directory, head, fixture=None):
    fixture = fixture or json.loads(FIXTURE.read_text())
    require(report['schema'] == SCHEMA and report['head'] == head, 'Evidence HEAD/schema mismatch')
    require(report['fixture_sha256'] == sha(FIXTURE.read_bytes()), 'Fixture binding mismatch')
    require(report['status'] == 'PASS' and report['errors'] == [] and report['external'] == [], 'Incomplete/failed browser evidence')
    require(report['doctor_acceptance'] == 'pending' and report['merged'] is False and report['deployed'] is False,
            'Automatic evidence cannot sign off, merge or deploy')
    require(report['passed'] == fixture['scenarios'], 'Missing/duplicate scenario')
    require(report['backend'] in {'sqlite', 'postgresql'}, 'Unknown database')
    require(len(report['cases']) == 2 and [row['species'] for row in report['cases']] == ['dog', 'cat'], 'Missing dog/cat journey')
    require(len({row['case_id'] for row in report['cases']}) == 2, 'Duplicate case')
    files = []
    for row, expected in zip(report['cases'], fixture['cases']):
        require(row['steps'] == fixture['steps'], 'Missing/out-of-order clinical step')
        require(row['case_id'] == row['saved_case']['id'], 'Wrong case binding')
        for key, value in expected.items():
            require(row['saved_case'][key] == value, 'Wrong saved case field: '+key)
        require(row['requests']['create'] == 1 and row['requests']['attachments'] == 2 and row['requests']['lab'] == 2
                and row['requests']['imaging'] == 1 and row['requests']['plan'] == 1 and row['requests']['contact'] == 1,
                'Missing or repeated UI save')
        require(row['readonly_before'] == row['readonly_after'], 'Read-only journey changed the database')
        require(row['readonly_before']['case_id'] == row['case_id'], 'Wrong read-only snapshot')
        require(row['lab']['reports'][0]['state'] == 'superseded' and row['lab']['reports'][1]['version'] == 2,
                'Missing lab correction history')
        require(row['lab']['reports'][0]['data']['items'][0]['value'] == fixture['lab']['items'][0]['value']
                and row['lab']['reports'][1]['data']['items'][0]['value'] == fixture['corrected_lab_value'], 'Wrong lab literals')
        require(row['plans']['plans'][0]['data'] == fixture['plan'], 'Wrong saved plan')
        require(row['contacts']['records'][0]['data'] == fixture['contact'], 'Wrong saved contact')
        require(row['contacts']['records'][0]['source']['id'] == row['plans']['plans'][0]['id'], 'Wrong contact source')
        require({doc['template'] for doc in row['documents']} == {'outpatient_record_zh', 'owner_visit_summary_zh'}
                and len(row['documents']) == 2, 'Missing/duplicate document')
        require(len(row['originals']) == 2 and len({x['attachment_id'] for x in row['originals']}) == 2, 'Missing/duplicate original download')
        require(len(row['screenshots']) == 2, 'Missing wide/narrow screenshot')
        require({item['viewport'] for item in row['screenshots']} == {'wide', 'narrow'}, 'Wrong screenshot viewports')
        for item in row['documents'] + row['screenshots'] + row['originals']:
            file = (Path(directory) / item['file']).resolve()
            require(file.parent == Path(directory).resolve(), 'Evidence path escape')
            require(file.is_file() and file.stat().st_size == item['bytes'] and sha(file.read_bytes()) == item['sha256'],
                    'Missing/changed evidence file: '+item['file'])
            require(item['file'] not in files, 'Duplicate evidence file')
            files.append(item['file'])
        for doc in row['documents']:
            require(doc['case_id'] == row['case_id'] and doc['plan_id'] == row['plans']['plans'][0]['id']
                    and doc['contact_id'] == row['contacts']['records'][0]['id'], 'Wrong document selection')
            text = document_text(Path(directory) / doc['file'])
            literals = [expected['patient_name'], expected['history'], expected['treatment'], fixture['lab']['report']['title'],
                        fixture['corrected_lab_value'], fixture['imaging']['findings'], fixture['plan']['purpose'],
                        *fixture['plan']['items'], fixture['plan']['note'], fixture['contact']['note'], fixture['contact']['next_action']]
            for value in literals + ['尚未签署', '待医生核对']:
                require(value in text, 'DOCX missing selected literal: '+repr(value))
            require(row['contacts']['records'][0]['token'] in text, 'DOCX wrong contact version')
    require(report['faults']['lost_write_response']['confirm_posts'] == 1, 'Lost response caused duplicate save')
    require(report['faults']['stale_document_source']['rejected_status'] == 409, 'Stale document was not refused')
    require(report['faults']['late_case_account_response']['modes'] == ['case', 'account'], 'Missing stale response isolation')
    require(report['faults']['failed_cancelled_download']['downloads'] == 0, 'Failed/cancelled export downloaded a file')
    for value in report['faults'].values():
        require(value['status'] == 'PASS', 'Failed fault scenario')
    return files


def verify_database(report, config):
    receipts = []
    for case in report['cases']:
        rows, receipt = database_rows(config, case['case_id'])
        actual = rows['cases'][0]
        require(actual['owner_id'] == report['owner_id'], 'Database ownership mismatch')
        for key in json.loads(FIXTURE.read_text())['cases'][0]:
            require(actual[key] == case['saved_case'][key], 'Database field mismatch: '+key)
        require(not rows['consult_sessions'], 'Manual journey unexpectedly created AI consultation')
        for key, table in [('lab', 'diagnostic_reports'), ('imaging', 'imaging_studies')]:
            for expected in case[key]['reports']:
                row = next((r for r in rows[table] if r['id'] == expected['id']), None)
                require(row is not None, 'Missing independently read report')
                meta = metadata(row)
                for field in ('root_id', 'version', 'data'):
                    require(meta[field] == expected[field], 'Independent report mismatch: '+field)
        for expected in case['plans']['plans'] + case['final_contacts']['records']:
            row = next((r for r in rows['followups'] if r['id'] == expected['id']), None)
            require(row is not None and row['done_at'] is None, 'Missing follow-up or unexpected completion')
            meta = metadata(row)
            for field in ('root_id', 'version', 'data'):
                require(meta[field] == expected[field], 'Independent follow-up mismatch: '+field)
            if 'source' in expected:
                require(meta['source'] == expected['source'], 'Frozen contact source mismatch')
        attachments = json_value(actual['attachments'])
        require(len(attachments) == 2, 'Wrong attachment count')
        for original in case['originals']:
            row = next((r for r in attachments if r['id'] == original['attachment_id']), None)
            require(row is not None and row['sha256'] == original['sha256'] and row['state'] == 'active', 'Original source mismatch')
        audit_requests = {r['request_id'] for r in rows['audit_log']}
        require(set(case['confirm_request_ids']) <= audit_requests, 'Missing actual save audit receipt')
        require(all(r['clinician_id'] == str(report['owner_id']) for r in rows['audit_log']), 'Audit owner mismatch')
        receipts.append(receipt)
    return receipts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--environment', required=True)
    parser.add_argument('--snapshot', type=int)
    parser.add_argument('--input')
    parser.add_argument('--output')
    args = parser.parse_args()
    if args.snapshot:
        print(canonical(database_rows(args.environment, args.snapshot)[1]))
        return
    report = json.loads(Path(args.input).read_text())
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    files = validate_evidence(report, Path(args.input).parent, head)
    receipts = verify_database(report, args.environment)
    result = {'schema': SCHEMA, 'head': head, 'status': 'PASS', 'fresh_process': True,
              'backend': report['backend'], 'files_verified': files, 'database': receipts,
              'doctor_acceptance': 'pending', 'merged': False, 'deployed': False, 'external_business_calls': 0}
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(canonical(result))


if __name__ == '__main__':
    main()

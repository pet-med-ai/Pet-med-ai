"""Real JWT, routes, SQL transactions and independent connections on PostgreSQL."""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4
import fixture as f
from fastapi.testclient import TestClient
from sqlalchemy import text

checks = []
client = TestClient(f.main.app)
PASSWORD = 'Synthetic-PR26-only-20260916'


def call(method, path, headers=None, expected=200, **kw):
    r = client.request(method, path, headers=headers, **kw)
    assert r.status_code == expected, (path, r.status_code, r.text)
    return r.json()


def login(name):
    return {'Authorization': 'Bearer ' + call('POST', '/auth/login', data={'username': name+'@example.com', 'password': PASSWORD})['access_token']}


def record(name):
    checks.append(name)
    print('PASS:', name, flush=True)
    filename = 'postgres-restart.json' if '--readback' in sys.argv else 'postgres-checks.json'
    (f.OUT / filename).write_text(json.dumps({'passed': checks}, ensure_ascii=False, indent=2))


def count():
    with f.db.engine.connect() as c:
        return c.execute(text('SELECT count(*) FROM cases')).scalar_one()


def read(cid, auth):
    f.db.engine.dispose()
    return call('GET', f'/api/cases/{cid}', auth)


# CW-B6 reuses the real Case/AuditLog schema and actual routes on native PostgreSQL.
# No SQLite test fixture is imported here; fixture.py rejects SQLite and egress.
import hashlib
import os
import tempfile
from pathlib import Path
from urllib.parse import quote
sys.path.insert(0, str(f.ROOT / 'tests' / 'fixtures'))
from build_attachment_cw_b6_fixtures import samples as attachment_samples
import case_attachment_store as attachment_store
import case_attachment_service as attachment_service
attachment_directory = Path(tempfile.gettempdir()) / ('pmai-cwb6-pg-' + hashlib.sha256(str(f.OUT).encode()).hexdigest()[:20])
os.environ.update(CASE_ATTACHMENTS_ENABLED='1', CASE_ATTACHMENTS_SYNTHETIC_ONLY='1', CASE_ATTACHMENTS_DIR=str(attachment_directory))

def attachment_readback():
    saved = json.loads((f.OUT / 'cwb6-restart-expected.json').read_text())
    auth = login('pg-owner')
    root = f'/api/cases/{saved["case_id"]}/attachments'
    listing = call('GET', root, auth)
    assert listing == saved['listing']
    for item in listing['items']:
        r = client.get(root + '/' + item['id'] + '/content', headers=auth, params={'request_id': uuid4().hex})
        if item['state'] == 'withdrawn':
            assert r.status_code == 404
        else:
            assert r.status_code == 200 and hashlib.sha256(r.content).hexdigest() == item['sha256']
    with f.db.SessionLocal() as db:
        assert db.query(f.models.AuditLog).filter_by(case_id=saved['case_id'], event_type='attachment_confirm').count() == 2
    record('cwb6_fresh_process_exact_refs_raw_sha256_and_withdrawn_access')


if '--readback' in sys.argv:
    expected = json.loads((f.OUT / 'restart-expected.json').read_text())
    auth = login('pg-owner')
    assert read(expected['case_id'], auth) == expected['record']
    assert call('GET', expected['session_url'], auth)['case_id'] == expected['case_id']
    record('fresh_process_relogin_and_readback')
    for item in json.loads((f.OUT / 'm7-restart-expected.json').read_text()):
        assert read(item['case_id'], auth) == item['record']
        assert call('GET', item['session_url'], auth)['case_id'] == item['case_id']
    record('m7_dog_cat_fresh_process_relogin_and_exact_readback')
    for item in json.loads((f.OUT / 'b1-restart-expected.json').read_text()):
        assert read(item['case_id'], auth) == item['record']
        assert call('GET', item['session_url'], auth)['case_id'] == item['case_id']
    record('b1_all_enabled_dog_cat_fresh_process_exact_readback')
    for item in json.loads((f.OUT / 'b4-restart-expected.json').read_text()):
        assert read(item['case_id'], auth) == item['record']
        reopened = call('GET', item['session_url'], auth)
        assert reopened['result']['input_evidence'] == item['evidence']
        assert reopened['case_id'] == item['case_id']
    record('b4_dog_cat_fresh_process_exact_evidence_and_case_readback')
    import speech_budget as speech_budget
    from sqlalchemy.orm import sessionmaker
    speech_factory = sessionmaker(bind=f.db.engine.execution_options(schema_translate_map={None: 'cwb5_budget_test'}))
    assert speech_budget.budget_status(speech_factory)['attempts'] == 100
    saved_voice = json.loads((f.OUT / 'cwb5-restart-expected.json').read_text())
    assert read(saved_voice['case_id'], auth) == saved_voice['record']
    with f.db.SessionLocal() as session:
        rows = session.query(f.models.AuditLog).filter_by(case_id=saved_voice['case_id'], event_type='speech_confirm').order_by(f.models.AuditLog.created_at, f.models.AuditLog.log_id).all()
        assert len(rows) == 2 and [row.extra_data for row in rows] == saved_voice['audits']
    record('cwb5_fresh_process_exact_history_audit_and_spent_budget')
    attachment_readback()
    client.close(); f.db.engine.dispose()
    sys.exit(0)

f.prepare_empty_database()
for name in ['pg-owner', 'pg-other', 'browser-owner']:
    call('POST', '/auth/signup', json={'email': name+'@example.com', 'password': PASSWORD})
owner, other = login('pg-owner'), login('pg-other')
with f.db.SessionLocal() as s:
    owner_id = s.query(f.models.User).filter_by(email='pg-owner@example.com').one().id
record('native_postgresql_real_auth_no_overrides')

# Manual creation uses the real authenticated legacy endpoint; all fifteen
# reviewed fields must persist without creating a consultation.
manual = {'patient_name': '手工新建合成犬🐾', 'species': 'dog', 'sex': 'M', 'age_info': '2y',
          'breed': '合成品种', 'weight': '5.2kg', 'coat_color': None, 'owner_name': '合成主人',
          'owner_phone': None, 'chief_complaint': '  手工主诉\r\n ',
          'history': '  原始手工病史🐾\r\n尾部空格。  \n\t', 'exam_findings': '合成体检',
          'analysis': '  手工分析\r\n ', 'treatment': '手工处理 <script>literal</script>',
          'prognosis': '  手工随访\n '}
before_manual = count()
with f.db.engine.connect() as connection:
    sessions_before_manual = connection.execute(text('SELECT count(*) FROM consult_sessions')).scalar_one()
manual_id = call('POST', '/api/cases', owner, expected=201, json=manual)['id']
manual_readback = read(manual_id, owner)
assert all(manual_readback[key] == value for key, value in manual.items())
assert count() == before_manual + 1
call('GET', f'/api/cases/{manual_id}', other, expected=404)
with f.db.engine.connect() as connection:
    assert connection.execute(text('SELECT count(*) FROM consult_sessions')).scalar_one() == sessions_before_manual
record('manual_create_fifteen_fields_exact_independent_postgresql_readback')

sid = call('POST', '/api/ai/consult/session', owner, json={'text': '合成犬，呕吐两次，精神正常', 'species': 'dog'})['session_id']
url = '/api/ai/consult/session/' + sid
call('POST', url+'/answer', owner, json={'question': '合成补问', 'answer': '持续两天，合成数据'})
body = {'patient_name': 'PG合成犬🐾', 'species': 'dog', 'sex': 'M', 'age_info': '4岁', 'breed': '合成品种',
        'weight': '5kg', 'coat_color': '白', 'owner_name': '合成主人', 'owner_phone': 'synthetic-only',
        'chief_complaint': '医生核对主诉', 'history': '  原始病史🐾\r\n必须保留尾部空格。  \n\t',
        'exam_findings': '合成体检', 'structured_intake_answers': {'sections': [{'title': '病史', 'answers': [{'label': '用药', 'answer': '合成补充病史'}]}]}}
before = count()
p = call('POST', url+'/preview-case', owner, json=body)
assert count() == before and call('GET', url, owner)['case_id'] is None
assert p['history'].startswith(body['history']) and '合成补充病史' in p['history']
record('preview_no_case_write_unicode_and_structured_history')
for key in body:
    changed = {**body, key: {} if key == 'structured_intake_answers' else 'changed', 'expected_preview_token': p['preview_token']}
    call('POST', url+'/save-case', owner, expected=409, json=changed)
assert count() == before
record('all_input_changes_reject_stale_confirmation_without_write')
for suffix in ['/preview-case', '/save-case']:
    call('POST', url+suffix, expected=401, json=body)
    call('POST', url+suffix, other, expected=404, json=body)
assert count() == before
record('authentication_and_foreign_owner_rejected')
saved = call('POST', url+'/save-case', owner, json={**body, 'expected_preview_token': p['preview_token']})
cid = saved['case_id']; current = read(cid, owner)
assert all(current[k] == p[k] for k in f.main.CONSULT_SAVE_FIELDS)
assert count() == before+1
record('fifteen_fields_match_independent_postgresql_readback')
again = call('POST', url+'/save-case', owner, json={**body, 'history': 'do not overwrite'})
assert again['case_id'] == cid and again['message'] == 'already_saved'
assert read(cid, owner) == current and count() == before+1
record('duplicate_save_same_case_no_overwrite')
call('POST', url+'/answer', owner, json={'question': '后续补问', 'answer': '后续合成内容'})
assert read(cid, owner) == current
up = call('POST', url+'/preview-update-case', owner)
assert up['proposed']['history'].startswith(current['history'])
call('POST', url+'/answer', owner, json={'question': '再次补问', 'answer': '使预览失效'})
call('POST', url+'/update-case', owner, expected=409, json={'expected_preview_token': up['preview_token']})
assert read(cid, owner) == current
record('followup_and_stale_update_do_not_write_case')
up = call('POST', url+'/preview-update-case', owner)
call('POST', url+'/update-case', owner, json={'expected_preview_token': up['preview_token']})
current = read(cid, owner)
assert all(current[k] == up['proposed'][k] for k in f.main.CONSULT_UPDATE_FIELDS)
assert current['history'].startswith(p['history'])
record('six_update_fields_match_history_original_retained')
up = call('POST', url+'/preview-update-case', owner)
call('POST', url+'/update-case', owner, json={'expected_preview_token': up['preview_token']})
assert read(cid, owner)['history'] == current['history']
record('identical_update_does_not_duplicate_history')
(f.OUT / 'restart-expected.json').write_text(json.dumps({'case_id': cid, 'record': read(cid, owner), 'session_url': url}, ensure_ascii=False))


def race(unowned):
    session_id = uuid4().hex
    with f.db.SessionLocal() as s:
        s.add(f.models.ConsultSession(session_uid=session_id, owner_id=None if unowned else owner_id,
              text='合成并发保存', answers=[], result={'risk_level': 'low'})); s.commit()
    baseline = count()
    preview = call('POST', f'/api/ai/consult/session/{session_id}/preview-case', owner, json=body)
    request = {**body, 'expected_preview_token': preview['preview_token']}
    barrier = Barrier(2, timeout=15)
    original = f.main._consult_save_snapshot
    def snapshot(*args):
        result = original(*args); barrier.wait(); return result
    def worker(auth):
        with TestClient(f.main.app) as c:
            return c.post(f'/api/ai/consult/session/{session_id}/save-case', headers=auth, json=request)
    # Only a scheduling barrier is inserted; auth, routes and SQL are unchanged.
    with patch.object(f.main, '_consult_save_snapshot', side_effect=snapshot):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker, h) for h in [owner, other if unowned else owner]]
            responses = [x.result(timeout=25) for x in futures]
    assert sorted(r.status_code for r in responses) == ([200,404] if unowned else [200,200]), [(r.status_code,r.text) for r in responses]
    assert count() == baseline+1, 'Losing transaction left an orphan case'
    success = [r.json() for r in responses if r.status_code == 200]
    assert len({r['case_id'] for r in success}) == 1
    with f.db.SessionLocal() as s:
        row = s.query(f.models.ConsultSession).filter_by(session_uid=session_id).one()
        case = s.get(f.models.Case, row.case_id)
        assert case.owner_id == row.owner_id and case.id == success[0]['case_id']
        if not unowned: assert case.owner_id == owner_id
    if unowned:
        loser = owner if responses[0].status_code == 404 else other
        call('GET', f"/api/cases/{success[0]['case_id']}", loser, expected=404)


race(False); record('same_owner_simultaneous_save_one_case_no_orphan')
race(True); record('two_owner_unowned_race_single_owner_loser_cannot_read')

# Clinician addenda use the same real preview/update routes and native row locks.
note = "  PostgreSQL复诊补记🐾\r\n保留末尾空格。  \n"
prior = read(cid, owner)
np = call('POST', url+'/preview-update-case', owner, json={'history_addendum': note})
assert read(cid, owner) == prior and np['history_addendum'] == note
assert np['proposed']['history'].startswith(prior['history'])
call('POST', url+'/update-case', owner, expected=409, json={'history_addendum': note+'changed', 'expected_preview_token': np['preview_token']})
assert read(cid, owner) == prior
record('changed_addendum_rejects_stale_confirmation_without_write')
call('POST', url+'/update-case', owner, json={'history_addendum': note, 'expected_preview_token': np['preview_token']})
assert read(cid, owner)['history'] == np['proposed']['history']
assert read(cid, owner)['history'].endswith('【医生病史补记】\n'+note)
record('addendum_exact_old_and_new_text_independent_postgres_readback')
once = read(cid, owner)['history']
for same in [note, ' \n\t']:
    np = call('POST', url+'/preview-update-case', owner, json={'history_addendum': same})
    call('POST', url+'/update-case', owner, json={'history_addendum': same, 'expected_preview_token': np['preview_token']})
    assert read(cid, owner)['history'] == once
record('identical_or_blank_addendum_does_not_append_again')

# Hold the real session row so BOTH actual HTTP requests demonstrably wait on
# PostgreSQL locks. No snapshot, route, result, auth or SQL implementation mock.
notes = ['并发医生甲补记', '并发医生乙补记']
previews = [call('POST', url+'/preview-update-case', owner, json={'history_addendum': n, 'update_mode': 'history_only'}) for n in notes]
barrier = Barrier(2, timeout=10)
def note_worker(index):
    with TestClient(f.main.app) as c:
        barrier.wait()
        return c.post(url+'/update-case', headers=owner, json={'history_addendum': notes[index], 'update_mode': 'history_only', 'expected_preview_token': previews[index]['preview_token']})
with f.db.engine.connect() as lock:
    transaction = lock.begin()
    lock.execute(text('SELECT id FROM consult_sessions WHERE session_uid=:sid FOR UPDATE'), {'sid': sid})
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(note_worker, n) for n in range(2)]
        try:
            waiting = 0
            for attempt in range(100):
                with f.db.engine.connect() as monitor:
                    waiting = monitor.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname='pmai_acceptance' AND wait_event_type='Lock' AND query LIKE '%consult_sessions%' AND query LIKE '%FOR UPDATE%'")).scalar_one()
                if waiting >= 2: break
                time.sleep(0.05)
            assert waiting >= 2, 'Both real writers must reach the PostgreSQL lock'
        finally:
            transaction.rollback()  # release fixture lock without writing data
        results = [future.result(timeout=20) for future in futures]
assert sorted(r.status_code for r in results) == [200, 409], [(r.status_code,r.text) for r in results]
winner = next(n for n,r in enumerate(results) if r.status_code == 200)
loser = 1-winner
written = read(cid, owner)['history']
assert written.startswith(once) and notes[winner] in written and notes[loser] not in written
np = call('POST', url+'/preview-update-case', owner, json={'history_addendum': notes[loser], 'update_mode': 'history_only'})
call('POST', url+'/update-case', owner, json={'history_addendum': notes[loser], 'update_mode': 'history_only', 'expected_preview_token': np['preview_token']})
final = read(cid, owner)['history']
assert final.startswith(written) and all(final.count(n) == 1 for n in notes)
record('two_blocked_addendum_writers_conflict_then_repreview_preserves_both')
(f.OUT / 'restart-expected.json').write_text(json.dumps({'case_id': cid, 'record': read(cid, owner), 'session_url': url}, ensure_ascii=False))

# Preserve unrelated clinician fields while adding notes, with real routes.
protected = {'chief_complaint': '  PG医生确认主诉🐾\r\n ', 'exam_findings': '  PG体检原文\r\n ',
             'analysis': 'PG医生分析', 'treatment': 'PG医生治疗', 'prognosis': 'PG医生风险'}
call('PUT', '/api/cases/'+str(cid), owner, json=protected)
prior = read(cid, owner); note = 'PG仅补记模式新增记录'
np = call('POST', url+'/preview-update-case', owner, json={'history_addendum': note, 'update_mode':'history_only'})
assert np['update_mode'] == 'history_only' and all(np['proposed'][k] == prior[k] for k in protected)
assert read(cid, owner) == prior
for invalid in [{'history_addendum':note, 'update_mode':'consult_sync'}, {'history_addendum':note}]:
    call('POST', url+'/update-case', owner, expected=409, json={**invalid,'expected_preview_token':np['preview_token']})
assert read(cid, owner) == prior
record('update_scope_changed_or_omitted_rejects_without_writing')
call('POST', url+'/update-case', owner, json={'history_addendum':note,'update_mode':'history_only','expected_preview_token':np['preview_token']})
current = read(cid, owner)
assert current['history'] == np['proposed']['history']
assert {k:v for k,v in current.items() if k!='history'} == {k:v for k,v in prior.items() if k!='history'}
record('history_only_preserves_every_other_case_field_exactly')
np = call('POST', url+'/preview-update-case', owner, json={'history_addendum':'后续补记','update_mode':'history_only'})
call('PUT','/api/cases/'+str(cid),owner,json={'treatment':'另一医生修改后的治疗'})
changed = read(cid,owner)
call('POST',url+'/update-case',owner,expected=409,json={'history_addendum':'后续补记','update_mode':'history_only','expected_preview_token':np['preview_token']})
assert read(cid,owner) == changed
np = call('POST',url+'/preview-update-case',owner,json={'history_addendum':'后续补记','update_mode':'history_only'})
call('POST',url+'/update-case',owner,json={'history_addendum':'后续补记','update_mode':'history_only','expected_preview_token':np['preview_token']})
assert read(cid,owner)['treatment'] == changed['treatment']
record('history_only_repreview_preserves_intervening_doctor_treatment')
np = call('POST',url+'/preview-update-case',owner,json={'history_addendum':'','update_mode':'consult_sync'})
assert all(np['proposed'][k] == protected[k] for k in ['chief_complaint','exam_findings'])
assert np['proposed']['analysis'] != protected['analysis']
call('POST',url+'/update-case',owner,json={'history_addendum':'','update_mode':'consult_sync','expected_preview_token':np['preview_token']})
current = read(cid,owner)
assert all(current[k] == np['proposed'][k] for k in f.main.CONSULT_UPDATE_FIELDS)
record('explicit_consult_sync_preserves_doctor_chief_and_exam_bytes')
# Existing-case editing uses the same disposable database and real routes.
edit_url = '/api/cases/'+str(cid)
def edit_preview(changes):
    state = call('GET', edit_url+'/edit-state', owner)
    request = {'changes':changes,'expected_case_token':state['case_token']}
    return request,call('POST',edit_url+'/preview-edit',owner,json=request)

def edit_confirm(request,preview,expected=200):
    return call('POST',edit_url+'/confirm-edit',owner,expected=expected,json={**request,'expected_preview_token':preview['preview_token']})

prior=read(cid,owner)
request,ep=edit_preview({'treatment':'  PG编辑医生治疗🐾\r\n '})
assert read(cid,owner)==prior and list(ep['changes'])==['treatment']
record('editor_preview_only_changed_fields_no_database_write')
edit_confirm(request,ep)
current=read(cid,owner)
assert current['treatment']==request['changes']['treatment']
assert {k:v for k,v in current.items() if k!='treatment'}=={k:v for k,v in prior.items() if k!='treatment'}
edit_confirm(request,ep,expected=409)
assert read(cid,owner)==current
record('editor_exact_patch_preserves_all_other_fields_and_rejects_replay')
for headers,code in [(None,401),(other,404)]:
    call('GET',edit_url+'/edit-state',headers,expected=code)
    call('POST',edit_url+'/preview-edit',headers,expected=code,json=request)
    call('POST',edit_url+'/confirm-edit',headers,expected=code,json={**request,'expected_preview_token':ep['preview_token']})
assert read(cid,owner)==current
record('editor_real_auth_foreign_owner_rejected')
request,ep=edit_preview({'treatment':'冲突后重新核对治疗'})
call('PUT',edit_url,owner,json={'history':current['history']+'\n另一医生新补记'})
changed=read(cid,owner)
call('POST',edit_url+'/preview-edit',owner,expected=409,json=request)
edit_confirm(request,ep,expected=409)
assert read(cid,owner)==changed
request,ep=edit_preview(request['changes']);edit_confirm(request,ep)
assert read(cid,owner)['history']==changed['history']
record('editor_stale_open_or_preview_rejects_then_repreview_retains_new_history')

# Force the editor and consultation writer to wait on the same real case row.
request,ep=edit_preview({'treatment':'并发编辑器治疗'})
np=call('POST',url+'/preview-update-case',owner,json={'history_addendum':'并发问诊补记','update_mode':'history_only'})
barrier=Barrier(2,timeout=10)
def mixed_writer(index):
    with TestClient(f.main.app) as c:
        barrier.wait()
        if index==0:
            return c.post(edit_url+'/confirm-edit',headers=owner,json={**request,'expected_preview_token':ep['preview_token']})
        return c.post(url+'/update-case',headers=owner,json={'history_addendum':'并发问诊补记','update_mode':'history_only','expected_preview_token':np['preview_token']})
with f.db.engine.connect() as lock:
    transaction=lock.begin()
    lock.execute(text('SELECT id FROM cases WHERE id=:cid FOR UPDATE'),{'cid':cid})
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(mixed_writer,index) for index in range(2)]
        try:
            waiting=0
            for attempt in range(100):
                with f.db.engine.connect() as monitor:
                    waiting=monitor.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname='pmai_acceptance' AND wait_event_type='Lock' AND query LIKE '%FROM cases%' AND query LIKE '%FOR UPDATE%'")).scalar_one()
                if waiting>=2:break
                time.sleep(0.05)
            assert waiting>=2,'Editor and consult writer must both reach the case lock'
        finally:transaction.rollback()
        responses=[future.result(timeout=20) for future in futures]
assert sorted(r.status_code for r in responses)==[200,409],[(r.status_code,r.text) for r in responses]
if responses[0].status_code==409:
    request,ep=edit_preview(request['changes']);edit_confirm(request,ep)
else:
    np=call('POST',url+'/preview-update-case',owner,json={'history_addendum':'并发问诊补记','update_mode':'history_only'})
    call('POST',url+'/update-case',owner,json={'history_addendum':'并发问诊补记','update_mode':'history_only','expected_preview_token':np['preview_token']})
current=read(cid,owner)
assert current['treatment']=='并发编辑器治疗' and current['history'].count('并发问诊补记')==1
assert current['history'].startswith(changed['history'])
record('editor_and_consult_writers_block_conflict_then_preserve_both_changes')
(f.OUT / 'restart-expected.json').write_text(json.dumps({'case_id':cid,'record':current,'session_url':url},ensure_ascii=False))

# Dedicated synthetic rows: never delete the case used for restart readback.
def deletion_fixture():
    uid = uuid4().hex
    with f.db.SessionLocal() as s:
        obj = f.models.Case(owner_id=owner_id, patient_name='PG删除边界合成犬', species='dog',
                            chief_complaint='合成主诉', history='  不得改写的病史🐾\r\n ',
                            analysis='原分析', treatment='原治疗', prognosis='原风险')
        s.add(obj); s.flush(); case_id = obj.id
        s.add(f.models.ConsultSession(owner_id=owner_id, case_id=case_id, session_uid=uid,
                                      text='合成问诊', answers=[], result={'risk_level':'low'}))
        s.commit()
    return case_id, '/api/ai/consult/session/'+uid


def hidden_rows(case_id):
    # Independent SQL connection checks all columns, including deletion/version.
    with f.db.engine.connect() as connection:
        return tuple(dict(connection.execute(text(sql), {'cid':case_id}).mappings().one())
                     for sql in ('SELECT * FROM cases WHERE id=:cid',
                                 'SELECT * FROM consult_sessions WHERE case_id=:cid'))


def delete_synthetic_case(case_id):
    response = client.delete('/api/cases/'+str(case_id), headers=owner)
    assert response.status_code == 204, response.text
    call('GET', '/api/cases/'+str(case_id), owner, expected=404)
    snapshot = hidden_rows(case_id)
    assert snapshot[0]['deleted_at'] is not None
    return snapshot


deleted_id, deleted_url = deletion_fixture()
deleted_snapshot = delete_synthetic_case(deleted_id)
for body in (None, {'update_mode':'consult_sync','history_addendum':'合成同步补记'},
             {'update_mode':'history_only','history_addendum':'合成病史补记'}):
    assert call('POST', deleted_url+'/preview-update-case', owner, expected=404,
                **({'json':body} if body is not None else {})) == {'detail':'Case not found'}
    assert hidden_rows(deleted_id) == deleted_snapshot
call('POST', deleted_url+'/update-case', owner, expected=404)
assert hidden_rows(deleted_id) == deleted_snapshot
record('deleted_case_preview_and_legacy_update_reject_without_any_row_change')

deleted_id, deleted_url = deletion_fixture()
confirmations = []
for mode in ('consult_sync','history_only'):
    body = {'update_mode':mode,'history_addendum':'不得写入已删除病例的补记'}
    preview = call('POST', deleted_url+'/preview-update-case', owner, json=body)
    confirmations.append({**body,'expected_preview_token':preview['preview_token']})
deleted_snapshot = delete_synthetic_case(deleted_id)
for body in confirmations:
    assert call('POST', deleted_url+'/update-case', owner, expected=404, json=body) == {'detail':'Case not found'}
    assert hidden_rows(deleted_id) == deleted_snapshot
record('delete_after_preview_rejects_both_modes_without_any_row_change')
# M7: canonical states survive the same real first-save/row-lock transaction.
from diarrhea_intake import get_template, build_snapshot
m7_expected = []
for animal in ('dog', 'cat'):
    template = get_template(animal)
    raw = '  M7医生未见黑便🐾\r\n<5 & >2 {{literal}}\t尾部  \n'
    snapshot = build_snapshot({'version': template['version'], 'fingerprint': template['fingerprint'], 'species': animal,
        'answers': {'notes': {'state': 'observed', 'text': raw}, 'blood': {'state': 'uncertain', 'text': '不确定'},
                    'vomiting': {'state': 'absent', 'text': '未见呕吐'}, 'vomiting_detail': {'state': 'observed', 'text': '原分支只读保留'}}})
    created = call('POST', '/api/ai/consult/session', owner, json={'text': 'M7隔离合成腹泻', 'species': animal, 'structured_intake_answers': snapshot})
    m7_url = '/api/ai/consult/session/' + created['session_id']
    m7_body = {'patient_name': 'M7-PG-'+animal, 'species': animal, 'chief_complaint': '合成腹泻原主诉',
               'history': '  M7原医生病史🐾\r\n保留末尾  \n', 'structured_intake_answers': snapshot}
    preview = call('POST', m7_url+'/preview-case', owner, json=m7_body)
    assert preview['history'].count(raw) == 1 and preview['history'].startswith(m7_body['history'])
    assert '当前不适用' in preview['history'] and '状态：不确定' in preview['history']
    call('POST', m7_url+'/preview-case', other, expected=404, json=m7_body)
    call('POST', m7_url+'/save-case', owner, expected=409, json={**m7_body, 'history': 'stale', 'expected_preview_token': preview['preview_token']})
    before_m7 = count()
    request = {**m7_body, 'expected_preview_token': preview['preview_token']}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: call('POST', m7_url+'/save-case', owner, json=request), range(2)))
    assert len({r['case_id'] for r in results}) == 1 and count() == before_m7+1
    m7_id = results[0]['case_id']; saved = read(m7_id, owner)
    assert saved['history'] == preview['history']
    assert f.main._stored_structured_snapshot(call('GET', m7_url, owner)['answers'][0]) == snapshot
    m7_expected.append({'case_id': m7_id, 'record': saved, 'session_url': m7_url})
    record('m7_'+animal+'_canonical_states_originals_concurrent_save_one_case')
(f.OUT / 'm7-restart-expected.json').write_text(json.dumps(m7_expected, ensure_ascii=False))

# B1 uses the same row lock and first-save token as M7, with a distinct template family.
import chief_complaint_intake as b1
b1_expected = []
for key in b1.TEMPLATES:
    for animal in ('dog', 'cat'):
        template = b1.get_template(key, animal)
        raw = '  B1 ' + key + ' 医生原文🐾\r\n<5 & {{literal}}\t末尾  \n'
        snapshot = b1.build_snapshot(key, {'version':template['version'], 'fingerprint':template['fingerprint'], 'species':animal,
            'answers':{'notes':{'state':'observed','text':raw}}})
        created = call('POST', '/api/ai/consult/session', owner, json={'text':'隔离合成问诊','species':animal,'structured_intake_answers':snapshot})
        route = '/api/ai/consult/session/' + created['session_id']
        body = {'patient_name':'B1-PG-'+key+'-'+animal,'species':animal,'chief_complaint':'医生核对主诉',
                'history':'  原病史\n','structured_intake_answers':snapshot}
        preview = call('POST', route+'/preview-case', owner, json=body)
        assert preview['history'].count(raw)==1
        call('POST', route+'/preview-case', other, expected=404, json=body)
        call('POST', route+'/save-case', owner, expected=409, json={**body,'species':'cat' if animal=='dog' else 'dog','expected_preview_token':preview['preview_token']})
        before = count()
        request = {**body,'expected_preview_token':preview['preview_token']}
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _:call('POST',route+'/save-case',owner,json=request),range(2)))
        assert len({x['case_id'] for x in results})==1 and count()==before+1
        saved = read(results[0]['case_id'],owner)
        assert saved['history'].count(raw)==1 and saved['history'].startswith(body['history'])
        assert f.main._stored_structured_snapshot(call('GET',route,owner)['answers'][0])==snapshot
        b1_expected.append({'case_id':results[0]['case_id'],'record':saved,'session_url':route})
        record('b1_'+key+'_'+animal+'_concurrent_save_one_case_exact_original')
(f.OUT / 'b1-restart-expected.json').write_text(json.dumps(b1_expected,ensure_ascii=False))

b4_expected = []
for animal in ['dog', 'cat']:
    created = call('POST', '/api/ai/consult/session', owner, json={'text':'常规体检；未见黑便','species':animal})
    route = '/api/ai/consult/session/' + created['session_id']
    raw = '  不清楚🐾\n保留尾部  '
    updated = call('POST', route+'/answer', owner, json={'question':'是否有黑便、干呕或腹胀？','answer':raw,'expected_answers_token':created['answers_token']})
    assert updated['result']['risk_level'] == '待核对'
    assert updated['result']['diseases']['diseases'] == []
    assert updated['answers'][-1]['answer'] == raw
    body = {'patient_name':'B4-PG-'+animal,'species':animal,'chief_complaint':'常规体检','history':'B4原记录'}
    preview = call('POST', route+'/preview-case', owner, json=body)
    request = {**body,'expected_preview_token':preview['preview_token']}
    before = count()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _:call('POST',route+'/save-case',owner,json=request),range(2)))
    assert len({x['case_id'] for x in results}) == 1 and count() == before + 1
    saved = read(results[0]['case_id'],owner)
    assert raw in saved['history'] and '待核对' in saved['treatment']
    assert '扭转' not in saved['analysis']
    b4_expected.append({'case_id':results[0]['case_id'],'record':saved,'session_url':route,'evidence':updated['result']['input_evidence']})
    record('b4_'+animal+'_assertions_concurrent_save_one_case_evidence_preserved')
(f.OUT / 'b4-restart-expected.json').write_text(json.dumps(b4_expected,ensure_ascii=False))

# CW-B5: isolate the budget stress ledger in a second synthetic schema so it
# cannot reset/reuse the application ledger subsequently used by browser checks.
import speech_budget as speech_budget
import speech_transcription as speech_provider
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock
import base64, io, wave
with f.db.engine.begin() as connection:
    connection.execute(text('CREATE SCHEMA cwb5_budget_test'))
speech_engine = f.db.engine.execution_options(schema_translate_map={None: 'cwb5_budget_test'})
f.db.Base.metadata.create_all(speech_engine)
speech_factory = sessionmaker(bind=speech_engine)
speech_budget.initialize_ledger(speech_factory)
def spend(_):
    try:
        return speech_budget.reserve(uuid4().hex, owner_id, {'session_id': 'synthetic-budget'}, 'f'*64, 1, speech_factory)
    except speech_provider.SpeechError as error:
        assert error.code == 'batch_budget_exhausted'; return None
with ThreadPoolExecutor(max_workers=12) as pool:
    results = list(pool.map(spend, range(112)))
assert sorted(x for x in results if x) == list(range(1,101))
assert speech_budget.budget_status(speech_factory)['reserved_fen'] == 100
record('cwb5_native_postgresql_concurrent_100_attempt_1yuan_cap')
speech_budget.initialize_ledger()
voice_session = call('POST', '/api/ai/consult/session', owner, json={'text':'CW-B5合成语音验收','species':'dog'})['session_id']
voice_route = '/api/ai/consult/session/' + voice_session
buf = io.BytesIO()
with wave.open(buf, 'wb') as writer:
    writer.setnchannels(1); writer.setsampwidth(2); writer.setframerate(16000); writer.writeframes(b'\x00\x00'*16000)
def transcript():
    binding = call('GET', '/api/speech/context/' + voice_session, owner)
    binding.update(patient_name='CW-B5合成犬', species='dog', draft_version='b'*64)
    req = {'request_id':uuid4().hex,'binding':binding,'synthetic_only':True,'audio_base64':base64.b64encode(buf.getvalue()).decode()}
    with patch.object(speech_provider, 'ensure_enabled'), patch.object(speech_provider, 'recognize', AsyncMock(return_value={'text':'未见呕吐，零点五毫升','provider_request_id':'synthetic-only'})):
        r = call('POST','/api/speech/transcribe',owner,json=req)
        call('POST','/api/speech/transcribe',owner,expected=409,json=req)
    return {'receipt':r['receipt'],'original_text':r['text'],'edited_text':'未见呕吐，0.5 毫升。','reviewed':True}
entry = transcript()
body = {'patient_name':'CW-B5合成犬','species':'dog','history':'原始病史\n'+entry['edited_text'],'voice_confirmations':[entry]}
preview = call('POST',voice_route+'/preview-case',owner,json=body)
request = {**body,'expected_preview_token':preview['preview_token']}
with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(lambda _: call('POST',voice_route+'/save-case',owner,json=request),range(2)))
assert len({x['case_id'] for x in results}) == 1
voice_id = results[0]['case_id']; before_voice = read(voice_id,owner)
record('cwb5_concurrent_first_save_one_case_one_voice_audit')
entry = transcript(); entry['edited_text']='补记：核对毫升单位。'
body = {'history_addendum':entry['edited_text'],'update_mode':'history_only','voice_confirmations':[entry]}
preview = call('POST',voice_route+'/preview-update-case',owner,json=body)
request = {**body,'expected_preview_token':preview['preview_token']}
call('POST',voice_route+'/update-case',owner,json=request)
call('POST',voice_route+'/update-case',owner,expected=409,json=request)
saved = read(voice_id,owner); assert saved['history'].startswith(before_voice['history'])
with f.db.SessionLocal() as session:
    audits=[row.extra_data for row in session.query(f.models.AuditLog).filter_by(case_id=voice_id,event_type='speech_confirm').order_by(f.models.AuditLog.created_at, f.models.AuditLog.log_id).all()]
assert len(audits)==2 and audits[1]['edited_text']==entry['edited_text']
(f.OUT / 'cwb5-restart-expected.json').write_text(json.dumps({'case_id':voice_id,'record':saved,'audits':audits},ensure_ascii=False))
record('cwb5_addendum_consumed_once_and_atomic_provenance')

# Isolated private directory must not contain files from another candidate.
assert not attachment_directory.exists(), 'Refusing a pre-existing attachment test store'
a_case = call('POST', '/api/cases', owner, expected=201, json={**manual, 'patient_name':'CW-B6 PG合成犬'})
aid_case = a_case['id']; attachment_root = f'/api/cases/{aid_case}/attachments'
before_attachment = read(aid_case, owner)
meta = {'title':'合成检验报告','kind':'lab','taken_at':'','reported_at':'','source':'','note':''}
def attachment_body(item, operation='confirm', metadata=None, reason=''):
    return {'request_id':uuid4().hex, 'attachment_id':item['id'], 'operation':operation,
            'expected_case_token':call('GET',attachment_root,owner)['case_token'], 'metadata':metadata or meta, 'reason':reason}
def attachment_review(body):
    preview = call('POST', attachment_root+'/preview', owner, json=body)
    return {**body, 'preview_token':preview['preview_token'], 'reviewed':True}
originals = attachment_samples()
# Same idempotency key on independent real route transactions yields one upload/audit.
name, mime, data = originals[0]
version = call('GET',attachment_root,owner)['case_token']; upload_id=uuid4().hex
headers={**owner,'Content-Type':mime,'X-Attachment-Filename':quote(name),'X-Case-Token':version}
with ThreadPoolExecutor(max_workers=2) as pool:
    uploaded=list(pool.map(lambda _:call('POST',attachment_root+'/uploads/'+upload_id,headers,content=data),range(2)))
assert uploaded[0]['attachment']['id']==uploaded[1]['attachment']['id']
item=uploaded[0]['attachment']; request=attachment_review(attachment_body(item))
with ThreadPoolExecutor(max_workers=2) as pool:
    confirmed=list(pool.map(lambda _:call('POST',attachment_root+'/confirm',owner,json=request),range(2)))
assert len(call('GET',attachment_root,owner)['items'])==1
call('POST',attachment_root+'/confirm',owner,expected=409,json={**request,'reason':'mutated'})
with f.db.SessionLocal() as db:
    assert db.query(f.models.AuditLog).filter_by(case_id=aid_case,event_type='attachment_upload').count()==1
    assert db.query(f.models.AuditLog).filter_by(case_id=aid_case,event_type='attachment_confirm').count()==1
record('cwb6_postgresql_concurrent_upload_confirm_one_reference_and_audit')
# Rival metadata corrections invalidate the other preview rather than last-write-wins.
requests=[attachment_review(attachment_body(item,'update',{**meta,'title':'合成更正'+str(i)})) for i in range(2)]
with ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(lambda req:client.post(attachment_root+'/confirm',headers=owner,json=req),requests))
assert sorted(r.status_code for r in results)==[200,409]
record('cwb6_postgresql_concurrent_metadata_revision_rejects_stale_review')
# Fresh connection reads original bytes; foreign and deleted cases never obtain them.
path=attachment_root+'/'+item['id']+'/content'
r=client.get(path,headers=owner,params={'request_id':uuid4().hex}); assert r.content==data
assert client.get(path,headers=other,params={'request_id':uuid4().hex}).status_code==404
f.db.engine.dispose(); assert call('GET',attachment_root,owner)['items'][0]['sha256']==hashlib.sha256(data).hexdigest()
withdraw=attachment_review(attachment_body(item,'withdraw',reason='合成误关联'))
call('POST',attachment_root+'/confirm',owner,json=withdraw)
assert client.get(path,headers=owner,params={'request_id':uuid4().hex}).status_code==404
assert call('GET',attachment_root+'/requests/'+request['request_id'],owner)['attachment']['state']=='withdrawn'
assert attachment_store.Store().path(item['id'],'.blob').read_bytes()==data
# A second format remains active, providing byte-exact independent-process readback.
name,mime,data=originals[1]; upload_id=uuid4().hex
headers={**owner,'Content-Type':mime,'X-Attachment-Filename':quote(name),'X-Case-Token':call('GET',attachment_root,owner)['case_token']}
item2=call('POST',attachment_root+'/uploads/'+upload_id,headers,content=data)['attachment']
req=attachment_review(attachment_body(item2)); call('POST',attachment_root+'/confirm',owner,json=req)
assert read(aid_case,owner)['history']==before_attachment['history']
record('cwb6_postgresql_authorized_bytes_withdrawal_history_unchanged')
# Simulated database commit failure must leave no partial association or audit.
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
change=attachment_review(attachment_body(item2,'update',{**meta,'title':'故障后更正'}))
with patch.object(Session,'commit',side_effect=OperationalError('synthetic',{},Exception('injected'))):
    call('POST',attachment_root+'/confirm',owner,expected=503,json=change)
assert call('GET',attachment_root+'/requests/'+change['request_id'],owner)['state']=='not_committed'
call('POST',attachment_root+'/confirm',owner,json=change)
sys.path.insert(0,str(f.ROOT/'scripts'))
from verify_case_attachment_storage import backup_readback
with tempfile.TemporaryDirectory(prefix='cwb6-pg-backup-') as backup:
    with f.db.SessionLocal() as db:
        case=db.get(f.models.Case,aid_case)
        report=backup_readback(attachment_store.Store(),[{'case_id':case.id,'owner_id':case.owner_id,'attachments':case.attachments}],Path(backup)/'restored')
assert report['verified'] and report['files']==2 and report['database_restored'] is False
(f.OUT/'cwb6-backup-readback.json').write_text(json.dumps(report,indent=2))
(f.OUT/'cwb6-restart-expected.json').write_text(json.dumps({'case_id':aid_case,'listing':call('GET',attachment_root,owner)},ensure_ascii=False,indent=2))
record('cwb6_postgresql_atomic_rollback_retry_private_backup_readback')


client.close(); f.db.engine.dispose()

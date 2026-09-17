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


if '--readback' in sys.argv:
    expected = json.loads((f.OUT / 'restart-expected.json').read_text())
    auth = login('pg-owner')
    assert read(expected['case_id'], auth) == expected['record']
    assert call('GET', expected['session_url'], auth)['case_id'] == expected['case_id']
    record('fresh_process_relogin_and_readback')
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
client.close(); f.db.engine.dispose()

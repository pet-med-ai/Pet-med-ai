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
os.environ.update(CASE_ATTACHMENTS_ENABLED='1', CASE_ATTACHMENTS_SYNTHETIC_ONLY='1', CASE_ATTACHMENTS_DIR=str(attachment_directory), MANUAL_LAB_RESULTS_ENABLED='1', MANUAL_LAB_RESULTS_SYNTHETIC_ONLY='1')

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


def manual_lab_readback():
    saved = json.loads((f.OUT / 'cwb7-restart-expected.json').read_text())
    auth = login('pg-owner')
    assert call('GET',f'/api/cases/{saved["case_id"]}/manual-lab',auth) == saved['listing']
    assert read(saved['case_id'],auth) == saved['case']
    with f.db.SessionLocal() as db:
        rows=db.query(f.models.AuditLog).filter_by(case_id=saved['case_id'],source='manual-lab-cw-b7').order_by(f.models.AuditLog.log_id).all()
        assert [{'id':r.log_id,'event':r.event_type,'data':r.extra_data} for r in rows] == saved['audits']
    for extra in json.loads((f.OUT / 'cwb7-extra-restart.json').read_text()):
        assert call('GET',f'/api/cases/{extra["case_id"]}/manual-lab',auth)==extra['listing']
    record('cwb7_fresh_process_exact_versions_sources_decimal_and_audit')


def manual_lab_document_readback():
    saved=json.loads((f.OUT/'cwb8-restart-expected.json').read_text())
    auth=login('pg-owner');f.enable_manual_lab_documents()
    p=call('POST','/api/clinical-docs/render-preview',auth,json=saved['body'])
    assert p['content_snapshot']==saved['snapshot'] and p['manual_lab_reports']==saved['reports']
    r=client.post('/api/clinical-docs/render',headers=auth,json={**saved['body'],'expected_content_snapshot':saved['snapshot']})
    assert r.status_code==200 and r.headers['x-pmai-content-snapshot']==saved['snapshot']
    (f.OUT/'cwb8-restarted.docx').write_bytes(r.content)
    record('cwb8_fresh_process_exact_reports_source_hashes_and_document_snapshot')


def manual_imaging_readback():
    f.enable_manual_imaging();auth=login('pg-owner')
    saved=json.loads((f.OUT/'cwb9-restart-expected.json').read_text())
    for item in saved:
        cid=item['case_id']
        assert call('GET',f'/api/cases/{cid}/manual-imaging',auth)==item['listing']
        with f.db.SessionLocal() as db:
            audits=[{'id':r.log_id,'event':r.event_type,'data':r.extra_data} for r in db.query(f.models.AuditLog).filter_by(case_id=cid,source='manual-imaging-cw-b9').order_by(f.models.AuditLog.log_id)]
        assert audits==item['audits']
        if 'body' in item:
            p=call('POST','/api/clinical-docs/render-preview',auth,json=item['body'])
            assert p['content_snapshot']==item['snapshot']
            assert p['manual_imaging_reports']==item['images'] and p['manual_lab_reports']==item['labs']
            r=client.post('/api/clinical-docs/render',headers=auth,json={**item['body'],'expected_content_snapshot':item['snapshot']})
            assert r.status_code==200 and r.headers['x-pmai-content-snapshot']==item['snapshot']
            (f.OUT/'cwb9-restarted.docx').write_bytes(r.content)
    record('cwb9_fresh_process_relogin_exact_versions_audits_mixed_snapshot_and_docx')


def overview_readback():
    f.enable_visit_overview(); auth = login('pg-owner')
    saved = json.loads((f.OUT / 'cwb10-restart-expected.json').read_text())
    for item in saved:
        response = call('GET', f'/api/cases/{item["case_id"]}/visit-overview', auth)
        response.pop('read_at')
        assert response == item['overview']
    record('cwb10_fresh_process_relogin_exact_saved_inventory_and_snapshot')


def range_readback():
    f.enable_lab_range_review(); auth = login('pg-owner')
    for item in json.loads((f.OUT / 'cwb11-restart-expected.json').read_text()):
        result = call('GET', f'/api/cases/{item["case_id"]}/lab-range-review', auth)
        result.pop('read_at')
        assert result == item['review']
    record('cwb11_fresh_process_relogin_exact_values_versions_sources_and_snapshot')


def comparison_readback():
    f.enable_lab_comparison(); auth = login('pg-owner')
    for item in json.loads((f.OUT / 'cwb12-restart-expected.json').read_text()):
        url = f'/api/cases/{item["case_id"]}/lab-comparison'
        result = call('GET', url, auth); result.pop('read_at')
        assert result == item['review']
        if item.get('preview'):
            result = call('POST', url + '/preview', auth, json=item['choice']); result.pop('read_at')
            assert result == item['preview']
        else: call('POST', url + '/preview', auth, json=item['choice'], expected=409)
    record('cwb12_fresh_process_relogin_exact_raw_versions_sources_snapshot_and_difference')


def comparison_document_readback():
    f.enable_lab_comparison_documents(); auth=login('pg-owner')
    for item in json.loads((f.OUT/'cwb13-restart-expected.json').read_text()):
        preview=call('POST','/api/clinical-docs/render-preview',auth,json=item['body'])
        assert preview['content_snapshot']==item['snapshot']
        assert preview['manual_lab_comparison']==item['comparison']
        assert preview.get('manual_lab_reports',[])==item['labs']
        assert preview.get('manual_imaging_reports',[])==item['images']
        response=client.post('/api/clinical-docs/render',headers=auth,json={**item['body'],'expected_content_snapshot':item['snapshot']})
        assert response.status_code==200 and response.headers['x-pmai-content-snapshot']==item['snapshot']
        (f.OUT/'cwb13-restarted.docx').write_bytes(response.content)
    record('cwb13_fresh_process_relogin_exact_pair_provenance_mixed_sections_and_content_snapshot')


def followup_plan_readback():
    f.enable_followup_plans()
    auth=login('pg-owner')
    for saved in json.loads((f.OUT/'cwb14-restart-expected.json').read_text()):
        root=f"/api/cases/{saved['case_id']}/followup-plan"
        assert call('GET',root,auth)==saved['listing']
        assert read(saved['case_id'],auth)==saved['case']
        with f.db.SessionLocal() as db:
            rows=db.query(f.models.AuditLog).filter_by(case_id=saved['case_id'],source='clinical-followup-plans-cw-b14').order_by(f.models.AuditLog.log_id).all()
            assert [r.extra_data for r in rows]==saved['audits']
        for request_id in saved['requests']:
            result=call('GET',root+'/requests/'+request_id,auth)
            assert result['state']=='committed' and result['writes_database'] is False
    record('cwb14_fresh_process_relogin_exact_literals_dates_version_history_and_audit_counts')


def followup_document_readback():
    f.enable_followup_plan_documents(); f.enable_lab_comparison_documents(); auth=login('pg-owner')
    for item in json.loads((f.OUT/'cwb15-restart-expected.json').read_text()):
        p=call('POST','/api/clinical-docs/render-preview',auth,json=item['body'])
        assert p['content_snapshot']==item['snapshot'] and p['manual_followup_plan']==item['plan']
        for key in ('manual_lab_reports','manual_imaging_reports','manual_lab_comparison'):
            assert p.get(key)==item.get(key)
        r=client.post('/api/clinical-docs/render',headers=auth,json={**item['body'],'expected_content_snapshot':p['content_snapshot']})
        assert r.status_code==200 and r.headers['cache-control']=='private, no-store'
        assert r.headers['x-pmai-content-snapshot']==item['snapshot']
        (f.OUT/f"cwb15-restarted-{item['body']['case_id']}.docx").write_bytes(r.content)
    record('cwb15_fresh_process_relogin_reselect_full_preview_exact_plan_and_mixed_sections')


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
    manual_lab_readback()
    manual_lab_document_readback()
    manual_imaging_readback()
    overview_readback()
    range_readback()
    comparison_readback()
    comparison_document_readback()
    followup_plan_readback()
    followup_document_readback()
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


# CW-B7: exact authenticated routes, independent transactions, no mock provider.
import manual_lab_results as manual_lab
lab_case=call('POST','/api/cases',owner,expected=201,json={**manual,'patient_name':'CW-B7 PG合成犬'})['id']
lab_root=f'/api/cases/{lab_case}/manual-lab'; lab_files=f'/api/cases/{lab_case}/attachments'
source_request=uuid4().hex
name,mime,raw=attachment_samples()[0]
source=call('POST',lab_files+'/uploads/'+source_request,{**owner,'Content-Type':mime,'X-Attachment-Filename':quote(name),'X-Case-Token':call('GET',lab_files,owner)['case_token']},content=raw)['attachment']
b={'request_id':uuid4().hex,'attachment_id':source['id'],'operation':'confirm','expected_case_token':call('GET',lab_files,owner)['case_token'],'metadata':meta,'reason':''}
p=call('POST',lab_files+'/preview',owner,json=b)
call('POST',lab_files+'/confirm',owner,json={**b,'preview_token':p['preview_token'],'reviewed':True})
lab_data=json.loads((f.ROOT/'tests/fixtures/manual_lab_cw_b7_cases.json').read_text())
def lab_body(old=None,op='create'):
    return {'request_id':uuid4().hex,'attachment_id':source['id'],'operation':op,'expected_case_token':call('GET',lab_root,owner)['case_token'],
            'report_id':old['id'] if old else None,'expected_report_token':old['token'] if old else '',
            'data':None if op=='withdraw' else lab_data,'reason':'合成更正或撤销' if old else ''}
def lab_review(body):
    p=call('POST',lab_root+'/preview',owner,json=body)
    return {**body,'preview_token':p['preview_token'],'reviewed':True}
req=lab_review(lab_body())
with ThreadPoolExecutor(max_workers=2) as pool:
    rows=list(pool.map(lambda _:call('POST',lab_root+'/confirm',owner,json=req)['report'],range(2)))
assert rows[0]['id']==rows[1]['id']
assert manual_lab.input_data(rows[0]['data'])==lab_data
assert rows[0]['data']['items'][0]['decimal']=='0.0100'
call('GET',lab_root,other,expected=404)
call('POST',lab_root+'/confirm',owner,expected=409,json={**req,'reason':'changed'})
assert call('GET',lab_root+'/requests/'+req['request_id'],owner)['state']=='committed'
with f.db.SessionLocal() as db:
    assert db.query(f.models.DiagnosticReport).filter_by(case_id=lab_case).count()==1
    assert db.query(f.models.Observation).filter_by(case_id=lab_case).count()==len(lab_data['items'])
    assert db.query(f.models.AuditLog).filter_by(case_id=lab_case,event_type='manual_lab_create').count()==1
record('cwb7_postgresql_duplicate_confirmation_one_report_observations_audit_exact_originals')
requests=[lab_review(lab_body(rows[0],'correct')) for _ in range(2)]
with ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(lambda r:client.post(lab_root+'/confirm',headers=owner,json=r),requests))
assert sorted(r.status_code for r in results)==[200,409]
row=call('GET',lab_root,owner)['reports'][-1]
req=lab_review(lab_body(row,'correct'))
with patch.object(Session,'commit',side_effect=OperationalError('synthetic',{},Exception('fail'))):
    call('POST',lab_root+'/confirm',owner,expected=503,json=req)
assert call('GET',lab_root+'/requests/'+req['request_id'],owner)['state']=='not_committed'
assert len(call('GET',lab_root,owner)['reports'])==2
record('cwb7_postgresql_competing_versions_and_commit_failure_atomic_rollback')
# Case row lock serializes a concurrent identity change with lab correction.
with ThreadPoolExecutor(max_workers=2) as pool:
    change=pool.submit(client.put,f'/api/cases/{lab_case}',headers=owner,json={'owner_name':'并发更正合成宠主'})
    confirm=pool.submit(client.post,lab_root+'/confirm',headers=owner,json=req)
    assert change.result().status_code==200
    assert confirm.result().status_code in (200,409)
rows=call('GET',lab_root,owner)['reports'];assert rows[-1]['state']=='needs_review'
assert all(r['state']!='confirmed' for r in rows)
row=call('POST',lab_root+'/confirm',owner,json=lab_review(lab_body(rows[-1],'correct')))['report']
assert row['state']=='confirmed'
# Updating the attached report atomically invalidates the latest lab version.
b={'request_id':uuid4().hex,'attachment_id':source['id'],'operation':'update','expected_case_token':call('GET',lab_files,owner)['case_token'],'metadata':{**meta,'title':'PG更正原报告'},'reason':''}
p=call('POST',lab_files+'/preview',owner,json=b)
call('POST',lab_files+'/confirm',owner,json={**b,'preview_token':p['preview_token'],'reviewed':True})
row=call('GET',lab_root,owner)['reports'][-1];assert row['state']=='needs_review'
call('POST',lab_root+'/confirm',owner,json=lab_review(lab_body(row,'withdraw')))
assert call('GET',lab_root,owner)['reports'][-1]['state']=='withdrawn'
with f.db.SessionLocal() as db:
    audits=[{'id':r.log_id,'event':r.event_type,'data':r.extra_data} for r in db.query(f.models.AuditLog).filter_by(case_id=lab_case,source=manual_lab.SOURCE).order_by(f.models.AuditLog.log_id)]
(f.OUT/'cwb7-restart-expected.json').write_text(json.dumps({'case_id':lab_case,'listing':call('GET',lab_root,owner),'case':read(lab_case,owner),'audits':audits},ensure_ascii=False,indent=2))
record('cwb7_postgresql_identity_race_source_revision_withdrawal_and_audit')


# Separate synthetic cases exercise first-create and correct/withdraw races, plus
# original withdrawal versus first confirmation using the same store/case order.
import copy
lab_extra=[]
for scenario,panel in [('first_competition','cbc'),('correct_withdraw','chemistry'),('source_withdraw','urine')]:
    ecid=call('POST','/api/cases',owner,expected=201,json={**manual,'patient_name':'CW-B7 '+scenario})['id']
    eroot=f'/api/cases/{ecid}/manual-lab';efiles=f'/api/cases/{ecid}/attachments'
    name,mime,raw=attachment_samples()[0]
    eitem=call('POST',efiles+'/uploads/'+uuid4().hex,{**owner,'Content-Type':mime,'X-Attachment-Filename':quote(name),'X-Case-Token':call('GET',efiles,owner)['case_token']},content=raw)['attachment']
    ab={'request_id':uuid4().hex,'attachment_id':eitem['id'],'operation':'confirm','expected_case_token':call('GET',efiles,owner)['case_token'],'metadata':meta,'reason':''}
    ap=call('POST',efiles+'/preview',owner,json=ab)
    call('POST',efiles+'/confirm',owner,json={**ab,'preview_token':ap['preview_token'],'reviewed':True})
    edata=copy.deepcopy(lab_data);edata['report']['panel']=panel
    eb={'request_id':uuid4().hex,'attachment_id':eitem['id'],'operation':'create','expected_case_token':call('GET',eroot,owner)['case_token'],'report_id':None,'expected_report_token':'','data':edata,'reason':''}
    def er(body):
        preview=call('POST',eroot+'/preview',owner,json=body)
        return {**body,'preview_token':preview['preview_token'],'reviewed':True}
    first=er(eb)
    if scenario=='first_competition':
        # A failure in the audit append rolls back report and all observations.
        with patch.object(manual_lab,'append_audit',side_effect=OperationalError('synthetic',{},Exception('audit unavailable'))):
            call('POST',eroot+'/confirm',owner,expected=503,json=first)
        assert call('GET',eroot,owner)['reports']==[]
        requests=[first,er({**eb,'request_id':uuid4().hex})]
        with ThreadPoolExecutor(max_workers=2) as pool:
            result=list(pool.map(lambda req:client.post(eroot+'/confirm',headers=owner,json=req),requests))
        assert sorted(r.status_code for r in result)==[200,409]
    elif scenario=='correct_withdraw':
        old=call('POST',eroot+'/confirm',owner,json=first)['report']
        base={**eb,'report_id':old['id'],'expected_report_token':old['token'],'reason':'并发合成更正或撤销'}
        requests=[er({**base,'request_id':uuid4().hex,'operation':op,'data':None if op=='withdraw' else edata}) for op in ('correct','withdraw')]
        with ThreadPoolExecutor(max_workers=2) as pool:
            result=list(pool.map(lambda req:client.post(eroot+'/confirm',headers=owner,json=req),requests))
        assert sorted(r.status_code for r in result)==[200,409]
    else:
        ab={**ab,'request_id':uuid4().hex,'operation':'withdraw','expected_case_token':call('GET',efiles,owner)['case_token'],'reason':'并发合成撤销来源'}
        ap=call('POST',efiles+'/preview',owner,json=ab)
        with ThreadPoolExecutor(max_workers=2) as pool:
            save=pool.submit(client.post,eroot+'/confirm',headers=owner,json=first)
            withdrawal=pool.submit(client.post,efiles+'/confirm',headers=owner,json={**ab,'preview_token':ap['preview_token'],'reviewed':True})
            assert save.result().status_code in (200,409);assert withdrawal.result().status_code==200
        assert all(r['state']!='confirmed' for r in call('GET',eroot,owner)['reports'])
    listing=call('GET',eroot,owner)
    assert sum(r['state']=='confirmed' for r in listing['reports'])<=1
    lab_extra.append({'case_id':ecid,'listing':listing})
    record('cwb7_postgresql_'+scenario+'_one_current_version')
(f.OUT/'cwb7-extra-restart.json').write_text(json.dumps(lab_extra,ensure_ascii=False,indent=2))


# CW-B8 uses real report/source routes and holds the case snapshot until bytes exist.
f.enable_manual_lab_documents()
import io,zipfile
from xml.etree import ElementTree as ET
from threading import Event
import clinical_docs_api as document_api

def document_text(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        return ''.join(ET.fromstring(z.read('word/document.xml')).itertext())

for scenario in ('control','correct','withdraw','source','identity','history'):
    cid=call('POST','/api/cases',owner,expected=201,json={**manual,'patient_name':'CW-B8 '+scenario})['id']
    files=f'/api/cases/{cid}/attachments';root=f'/api/cases/{cid}/manual-lab'
    name,mime,raw=attachment_samples()[0]
    item=call('POST',files+'/uploads/'+uuid4().hex,{**owner,'Content-Type':mime,'X-Attachment-Filename':quote(name),'X-Case-Token':call('GET',files,owner)['case_token']},content=raw)['attachment']
    ab={'request_id':uuid4().hex,'attachment_id':item['id'],'operation':'confirm','expected_case_token':call('GET',files,owner)['case_token'],'metadata':meta,'reason':''}
    ap=call('POST',files+'/preview',owner,json=ab);call('POST',files+'/confirm',owner,json={**ab,'preview_token':ap['preview_token'],'reviewed':True})
    b={'request_id':uuid4().hex,'attachment_id':item['id'],'operation':'create','expected_case_token':call('GET',root,owner)['case_token'],'report_id':None,'expected_report_token':'','data':lab_data,'reason':''}
    p=call('POST',root+'/preview',owner,json=b);row=call('POST',root+'/confirm',owner,json={**b,'preview_token':p['preview_token'],'reviewed':True})['report']
    body={'case_id':cid,'template_id':'outpatient_record_zh','manual_lab_report_ids':[row['id']]}
    p=call('POST','/api/clinical-docs/render-preview',owner,json=body);request={**body,'expected_content_snapshot':p['content_snapshot']}
    call('POST','/api/clinical-docs/render-preview',other,expected=404,json=body)
    if scenario=='control':
        from sqlalchemy import event
        statements=[]
        def writes(_conn,_cursor,statement,*_):
            if statement.lstrip().split(' ',1)[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'}:statements.append(statement)
        event.listen(f.db.engine,'before_cursor_execute',writes)
        try:
            for template in ('outpatient_record_zh','owner_visit_summary_zh'):
                q={**body,'template_id':template};pr=call('POST','/api/clinical-docs/render-preview',owner,json=q)
                r=client.post('/api/clinical-docs/render',headers=owner,json={**q,'expected_content_snapshot':pr['content_snapshot']});assert r.status_code==200
                content=document_text(r.content)
                for exact in ('0.0100','<0.0010','未测','未提供',item['sha256']):assert exact in content
                assert r.headers['x-pmai-writes-database']=='false'
                (f.OUT/('cwb8-pg-'+template+'.docx')).write_bytes(r.content)
        finally:event.remove(f.db.engine,'before_cursor_execute',writes)
        assert statements==[]
        (f.OUT/'cwb8-restart-expected.json').write_text(json.dumps({'body':body,'snapshot':p['content_snapshot'],'reports':p['manual_lab_reports']},ensure_ascii=False,indent=2))
        record('cwb8_postgresql_two_templates_literal_values_no_database_writes')
        continue
    if scenario in ('correct','withdraw'):
        update={**b,'request_id':uuid4().hex,'operation':scenario,'report_id':row['id'],'expected_report_token':row['token'],'reason':'合成并发文书验证','data':None if scenario=='withdraw' else copy.deepcopy(lab_data)}
        if scenario=='correct':update['data']['items'][0]['value']='0.0990'
        review=call('POST',root+'/preview',owner,json=update)
        mutation=lambda:client.post(root+'/confirm',headers=owner,json={**update,'preview_token':review['preview_token'],'reviewed':True})
    elif scenario=='source':
        update={**ab,'request_id':uuid4().hex,'operation':'withdraw','reason':'合成原件撤销','expected_case_token':call('GET',files,owner)['case_token']};review=call('POST',files+'/preview',owner,json=update)
        mutation=lambda:client.post(files+'/confirm',headers=owner,json={**update,'preview_token':review['preview_token'],'reviewed':True})
    else:mutation=lambda:client.put(f'/api/cases/{cid}',headers=owner,json={('owner_name' if scenario=='identity' else 'history'):'并发更正合成字段'})
    entered,release,attempted=Event(),Event(),Event();normal=document_api._render_docx
    def held(*args,**kwargs):
        entered.set();assert release.wait(10);return normal(*args,**kwargs)
    def change():attempted.set();return mutation()
    with ThreadPoolExecutor(max_workers=2) as pool,patch.object(document_api,'_render_docx',side_effect=held):
        export=pool.submit(client.post,'/api/clinical-docs/render',headers=owner,json=request)
        assert entered.wait(10);rival=pool.submit(change);assert attempted.wait(10);assert not rival.done();release.set()
        r=export.result(15);assert r.status_code==200 and '0.0100' in document_text(r.content) and '0.0990' not in document_text(r.content)
        assert rival.result(15).status_code==200
    call('POST','/api/clinical-docs/render',owner,expected=409,json=request)
    record('cwb8_postgresql_export_serializes_'+scenario+'_then_rejects_old_snapshot')


# CW-B9 real PostgreSQL transactions and independently logged-in restart readback.
f.enable_manual_imaging()
import manual_imaging_records as imaging
image_data=json.loads((f.ROOT/'tests/fixtures/manual_imaging_cw_b9_cases.json').read_text())
image_expected=[]
for scenario in ('control','duplicate','first_competition','corrections','correct_withdraw','source_race','identity_race','mixed_export'):
    cid=call('POST','/api/cases',owner,expected=201,json={**manual,'patient_name':'CW-B9 '+scenario})['id']
    files=f'/api/cases/{cid}/attachments';root=f'/api/cases/{cid}/manual-imaging'
    def make_source(index,kind):
        name,mime,raw=attachment_samples()[index]
        item=call('POST',files+'/uploads/'+uuid4().hex,{**owner,'Content-Type':mime,'X-Attachment-Filename':quote(name),'X-Case-Token':call('GET',files,owner)['case_token']},content=raw)['attachment']
        b={'request_id':uuid4().hex,'attachment_id':item['id'],'operation':'confirm','expected_case_token':call('GET',files,owner)['case_token'],'metadata':{**meta,'kind':kind},'reason':''}
        p=call('POST',files+'/preview',owner,json=b)
        return call('POST',files+'/confirm',owner,json={**b,'preview_token':p['preview_token'],'reviewed':True})['attachment']
    source=make_source(0,'dr')
    def ib(old=None,op='create'):
        return {'request_id':uuid4().hex,'attachment_id':source['id'],'operation':op,'expected_case_token':call('GET',root,owner)['case_token'],
                'report_id':old['id'] if old else None,'expected_report_token':old['token'] if old else '',
                'data':None if op=='withdraw' else copy.deepcopy(image_data),'reason':'合成影像更正/撤销' if old else ''}
    def ir(b):
        p=call('POST',root+'/preview',owner,json=b);return {**b,'preview_token':p['preview_token'],'reviewed':True}
    first=ir(ib())
    call('GET',root,other,expected=404)
    if scenario=='source_race':
        b={'request_id':uuid4().hex,'attachment_id':source['id'],'operation':'withdraw','expected_case_token':call('GET',files,owner)['case_token'],'metadata':{**meta,'kind':'dr'},'reason':'合成原件撤销'}
        p=call('POST',files+'/preview',owner,json=b)
        with ThreadPoolExecutor(max_workers=2) as pool:
            save=pool.submit(client.post,root+'/confirm',headers=owner,json=first)
            removal=pool.submit(client.post,files+'/confirm',headers=owner,json={**b,'preview_token':p['preview_token'],'reviewed':True})
            assert save.result().status_code in (200,409);assert removal.result().status_code==200
        assert all(r['state']!='confirmed' for r in call('GET',root,owner)['reports'])
    elif scenario in ('first_competition','duplicate'):
        # Both audit and database failures leave no report or ledger entry.
        for target,attribute in [(imaging,'append_audit'),(Session,'commit')]:
            with patch.object(target,attribute,side_effect=OperationalError('synthetic',{},Exception('injected'))):
                call('POST',root+'/confirm',owner,expected=503,json=first)
            assert call('GET',root,owner)['reports']==[]
            assert call('GET',root+'/requests/'+first['request_id'],owner)['state']=='not_committed'
        requests=[first,first if scenario=='duplicate' else ir(ib())]
        with ThreadPoolExecutor(max_workers=2) as pool:
            result=list(pool.map(lambda req:client.post(root+'/confirm',headers=owner,json=req),requests))
        assert sorted(r.status_code for r in result)==([200,200] if scenario=='duplicate' else [200,409])
        assert len(call('GET',root,owner)['reports'])==1
        with f.db.SessionLocal() as db:assert db.query(f.models.AuditLog).filter_by(case_id=cid,event_type='manual_imaging_create').count()==1
    else:
        row=call('POST',root+'/confirm',owner,json=first)['report'];assert row['data']==image_data
        with f.db.SessionLocal() as db:assert db.get(f.models.ImagingStudy,row['id']).taken_at.isoformat()=='2026-10-07T01:30:00'
        if scenario in ('corrections','correct_withdraw'):
            reqs=[ir(ib(row,op)) for op in ('correct','correct' if scenario=='corrections' else 'withdraw')]
            with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(lambda req:client.post(root+'/confirm',headers=owner,json=req),reqs))
            assert sorted(r.status_code for r in result)==[200,409]
        elif scenario=='identity_race':
            req=ir(ib(row,'correct'))
            with ThreadPoolExecutor(max_workers=2) as pool:
                change=pool.submit(client.put,f'/api/cases/{cid}',headers=owner,json={'owner_name':'并发影像宠主更正'})
                save=pool.submit(client.post,root+'/confirm',headers=owner,json=req)
                assert change.result().status_code==200;assert save.result().status_code in (200,409)
            assert all(r['state']!='confirmed' for r in call('GET',root,owner)['reports'])
        else:
            source_lab=make_source(1,'lab');lab_root=f'/api/cases/{cid}/manual-lab'
            b={'request_id':uuid4().hex,'attachment_id':source_lab['id'],'operation':'create','expected_case_token':call('GET',lab_root,owner)['case_token'],'report_id':None,'expected_report_token':'','data':lab_data,'reason':''}
            p=call('POST',lab_root+'/preview',owner,json=b)
            labrow=call('POST',lab_root+'/confirm',owner,json={**b,'preview_token':p['preview_token'],'reviewed':True})['report']
            body={'case_id':cid,'template_id':'outpatient_record_zh','manual_imaging_report_ids':[row['id']],'manual_lab_report_ids':[labrow['id']]}
            preview=call('POST','/api/clinical-docs/render-preview',owner,json=body)
            req={**body,'expected_content_snapshot':preview['content_snapshot']}
            if scenario=='control':
                for template in ('outpatient_record_zh','owner_visit_summary_zh'):
                    q={**body,'template_id':template};p=call('POST','/api/clinical-docs/render-preview',owner,json=q)
                    r=client.post('/api/clinical-docs/render',headers=owner,json={**q,'expected_content_snapshot':p['content_snapshot']})
                    assert r.status_code==200
                    for value in [image_data['taken_at'],source['sha256'],image_data['impression'],'0.0100']:assert value in document_text(r.content)
                    (f.OUT/('cwb9-pg-'+template+'.docx')).write_bytes(r.content)
                retained={'body':body,'snapshot':preview['content_snapshot'],'images':preview['manual_imaging_reports'],'labs':preview['manual_lab_reports']}
            else:
                image_update=ir(ib(row,'withdraw'))
                lb={**b,'request_id':uuid4().hex,'operation':'withdraw','report_id':labrow['id'],'expected_report_token':labrow['token'],'data':None,'reason':'并发混合附节验证'}
                lp=call('POST',lab_root+'/preview',owner,json=lb)
                entered,release=Event(),Event();normal=document_api._render_docx
                def held(*a,**k):entered.set();assert release.wait(10);return normal(*a,**k)
                with ThreadPoolExecutor(max_workers=3) as pool,patch.object(document_api,'_render_docx',side_effect=held):
                    export=pool.submit(client.post,'/api/clinical-docs/render',headers=owner,json=req);assert entered.wait(10)
                    a=pool.submit(client.post,root+'/confirm',headers=owner,json=image_update)
                    b=pool.submit(client.post,lab_root+'/confirm',headers=owner,json={**lb,'preview_token':lp['preview_token'],'reviewed':True})
                    assert not a.done() and not b.done();release.set()
                    r=export.result(15);assert r.status_code==200
                    assert image_data['impression'] in document_text(r.content) and '0.0100' in document_text(r.content)
                    assert a.result(15).status_code==200 and b.result(15).status_code==200
                call('POST','/api/clinical-docs/render',owner,expected=409,json=req)
    listing=call('GET',root,owner)
    assert sum(r['state']=='confirmed' for r in listing['reports'])<=1
    with f.db.SessionLocal() as db:
        audits=[{'id':r.log_id,'event':r.event_type,'data':r.extra_data} for r in db.query(f.models.AuditLog).filter_by(case_id=cid,source=imaging.SOURCE).order_by(f.models.AuditLog.log_id)]
    image_expected.append({'case_id':cid,'listing':listing,'audits':audits,**(retained if scenario=='control' else {})})
    record('cwb9_postgresql_'+scenario+'_exact_atomic_imaging')
(f.OUT/'cwb9-restart-expected.json').write_text(json.dumps(image_expected,ensure_ascii=False,indent=2))


# CW-B10 reads all saved material in one Store/case transaction, never listing cleanup.
f.enable_visit_overview()
import clinical_case_overview as visit_overview
overview_expected = []
overview_case = json.loads((f.ROOT / 'tests/fixtures/clinical_case_overview_cw_b10_cases.json').read_text())['case']
overview_image = json.loads((f.ROOT / 'tests/fixtures/manual_imaging_cw_b9_cases.json').read_text())
for scenario in ('control', 'imaging', 'lab', 'withdraw', 'source', 'identity', 'history'):
    cid = call('POST', '/api/cases', owner, expected=201, json={**overview_case, 'patient_name': 'CW-B10 ' + scenario})['id']
    files = f'/api/cases/{cid}/attachments'
    records, source_records = {}, {}
    for kind, sample in [('imaging', attachment_samples()[0]), ('lab', attachment_samples()[1])]:
        name, mime, raw = sample
        item = call('POST', files + '/uploads/' + uuid4().hex,
                    {**owner, 'Content-Type': mime, 'X-Attachment-Filename': quote(name), 'X-Case-Token': call('GET', files, owner)['case_token']}, content=raw)['attachment']
        body = {'request_id': uuid4().hex, 'attachment_id': item['id'], 'operation': 'confirm',
                'expected_case_token': call('GET', files, owner)['case_token'],
                'metadata': {'title': '合成' + kind, 'kind': 'dr' if kind == 'imaging' else 'lab', 'taken_at': '', 'reported_at': '', 'source': '', 'note': ''}, 'reason': ''}
        preview = call('POST', files + '/preview', owner, json=body)
        source_records[kind] = call('POST', files + '/confirm', owner, json={**body, 'preview_token': preview['preview_token'], 'reviewed': True})['attachment']
        root = f'/api/cases/{cid}/manual-' + kind
        body = {'request_id': uuid4().hex, 'attachment_id': item['id'], 'operation': 'create',
                'expected_case_token': call('GET', root, owner)['case_token'], 'report_id': None, 'expected_report_token': '',
                'data': overview_image if kind == 'imaging' else lab_data, 'reason': ''}
        preview = call('POST', root + '/preview', owner, json=body)
        records[kind] = call('POST', root + '/confirm', owner, json={**body, 'preview_token': preview['preview_token'], 'reviewed': True})['report']
    url = f'/api/cases/{cid}/visit-overview'
    before = call('GET', url, owner)
    assert before['groups']['lab']['counts']['confirmed'] == before['groups']['imaging']['counts']['confirmed'] == 1
    assert next(row['value'] for row in before['fields'] if row['key'] == 'history') == overview_case['history']
    if scenario == 'control':
        call('GET', url, other, expected=404)
        call('GET', url, expected=401)
        statements = []
        from sqlalchemy import event
        def capture_writes(_conn, _cursor, statement, *_):
            if statement.lstrip().split()[0].upper() in {'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER'}: statements.append(statement)
        def business_digest():
            with f.db.engine.connect() as connection:
                rows = {table.name: [list(map(str, row)) for row in connection.execute(table.select().order_by(*table.primary_key.columns))]
                        for table in [f.models.Case.__table__, f.models.DiagnosticReport.__table__, f.models.Observation.__table__, f.models.ImagingStudy.__table__, f.models.AuditLog.__table__]}
            files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in attachment_directory.iterdir() if p.is_file() and p.name != '.cw-b6.lock'}
            return rows, files
        previous = business_digest()
        event.listen(f.db.engine, 'before_cursor_execute', capture_writes)
        try:
            with patch.object(attachment_store.Store, 'cleanup', side_effect=AssertionError('Overview cannot clean originals or temporary files')):
                assert call('GET', url, owner)['snapshot'] == before['snapshot']
        finally: event.remove(f.db.engine, 'before_cursor_execute', capture_writes)
        assert statements == [] and previous == business_digest()
    else:
        if scenario in {'imaging', 'lab', 'withdraw'}:
            kind = 'lab' if scenario == 'lab' else 'imaging'; row = records[kind]
            root = f'/api/cases/{cid}/manual-' + kind
            body = {'request_id': uuid4().hex, 'attachment_id': row['attachment_id'], 'operation': 'withdraw' if scenario == 'withdraw' else 'correct',
                    'expected_case_token': call('GET', root, owner)['case_token'], 'report_id': row['id'], 'expected_report_token': row['token'],
                    'data': None if scenario == 'withdraw' else (overview_image if kind == 'imaging' else lab_data), 'reason': '合成总览并发验证'}
            preview = call('POST', root + '/preview', owner, json=body)
            request = {**body, 'preview_token': preview['preview_token'], 'reviewed': True}
            mutation = lambda: client.post(root + '/confirm', headers=owner, json=request)
        elif scenario == 'source':
            source = source_records['imaging']
            body = {'request_id': uuid4().hex, 'attachment_id': source['id'], 'operation': 'withdraw',
                    'expected_case_token': call('GET', files, owner)['case_token'], 'metadata': source['metadata'], 'reason': '合成来源撤销'}
            preview = call('POST', files + '/preview', owner, json=body)
            mutation = lambda: client.post(files + '/confirm', headers=owner, json={**body, 'preview_token': preview['preview_token'], 'reviewed': True})
        else:
            mutation = lambda: client.put(f'/api/cases/{cid}', headers=owner, json={('owner_name' if scenario == 'identity' else 'history'): '合成并发修改'})
        entered, release, attempted = Event(), Event(), Event(); normal = visit_overview.assemble
        def held(*args): entered.set(); assert release.wait(10); return normal(*args)
        def mutate(): attempted.set(); return mutation()
        with ThreadPoolExecutor(max_workers=2) as pool, patch.object(visit_overview, 'assemble', side_effect=held):
            reading = pool.submit(call, 'GET', url, owner)
            try:
                assert entered.wait(10)
                changing = pool.submit(mutate); assert attempted.wait(10); assert not changing.done()
            finally: release.set()
            assert reading.result(10)['snapshot'] == before['snapshot']
            assert changing.result(10).status_code == 200
        assert call('GET', url, owner)['snapshot'] != before['snapshot']
    saved = call('GET', url, owner); saved.pop('read_at')
    overview_expected.append({'case_id': cid, 'overview': saved})
    record('cwb10_postgresql_' + scenario + '_consistent_readonly_inventory')
(f.OUT / 'cwb10-restart-expected.json').write_text(json.dumps(overview_expected, ensure_ascii=False, indent=2))

# CW-B11 exact decimal comparison on native PostgreSQL with saved-source and row locks.
f.enable_lab_range_review()
import clinical_lab_range_review as range_review
from copy import deepcopy
range_fixture = json.loads((f.ROOT / 'tests/fixtures/clinical_lab_range_review_cw_b11_cases.json').read_text())
range_expected = []
for scenario in ('control', 'correct', 'withdraw', 'source', 'source_metadata', 'identity'):
    cid = call('POST', '/api/cases', owner, expected=201, json={**range_fixture['case'], 'patient_name': 'CW-B11 ' + scenario})['id']
    files = f'/api/cases/{cid}/attachments'; root = f'/api/cases/{cid}/manual-lab'; url = f'/api/cases/{cid}/lab-range-review'
    name, mime, raw = attachment_samples()[0]
    item = call('POST', files + '/uploads/' + uuid4().hex,
                {**owner, 'Content-Type': mime, 'X-Attachment-Filename': quote(name), 'X-Case-Token': call('GET', files, owner)['case_token']}, content=raw)['attachment']
    metadata = {'title': '合成区间原件', 'kind': 'lab', 'taken_at': '', 'reported_at': '', 'source': '', 'note': ''}
    body = {'request_id': uuid4().hex, 'attachment_id': item['id'], 'operation': 'confirm', 'expected_case_token': call('GET', files, owner)['case_token'], 'metadata': metadata, 'reason': ''}
    preview = call('POST', files + '/preview', owner, json=body)
    source = call('POST', files + '/confirm', owner, json={**body, 'preview_token': preview['preview_token'], 'reviewed': True})['attachment']
    body = {'request_id': uuid4().hex, 'attachment_id': item['id'], 'operation': 'create', 'expected_case_token': call('GET', root, owner)['case_token'], 'report_id': None, 'expected_report_token': '', 'data': range_fixture['data'], 'reason': ''}
    preview = call('POST', root + '/preview', owner, json=body)
    row = call('POST', root + '/confirm', owner, json={**body, 'preview_token': preview['preview_token'], 'reviewed': True})['report']
    before = call('GET', url, owner)
    assert before['counts'] == range_fixture['review']['counts']
    assert [i['comparison'] for i in before['reports'][0]['items']] == range_fixture['expected']
    assert before['reports'][0]['token'] == row['token'] and before['reports'][0]['source']['sha256'] == hashlib.sha256(raw).hexdigest()
    if scenario == 'control':
        call('GET', url, other, expected=404); call('GET', url, expected=401)
        previous = business_digest(); statements = []
        event.listen(f.db.engine, 'before_cursor_execute', capture_writes)
        try:
            with patch.object(attachment_store.Store, 'cleanup', side_effect=AssertionError('No read cleanup')):
                assert call('GET', url, owner)['snapshot'] == before['snapshot']
        finally: event.remove(f.db.engine, 'before_cursor_execute', capture_writes)
        assert statements == [] and business_digest() == previous
    else:
        if scenario in {'correct', 'withdraw'}:
            data = deepcopy(range_fixture['data']); data['items'][0]['value'] = '1.500'
            body = {'request_id': uuid4().hex, 'attachment_id': row['attachment_id'], 'operation': scenario, 'expected_case_token': call('GET', root, owner)['case_token'], 'report_id': row['id'], 'expected_report_token': row['token'], 'data': data if scenario == 'correct' else None, 'reason': '合成区间并发核对'}
            preview = call('POST', root + '/preview', owner, json=body)
            mutation = lambda: client.post(root + '/confirm', headers=owner, json={**body, 'preview_token': preview['preview_token'], 'reviewed': True})
        elif scenario in {'source', 'source_metadata'}:
            body = {'request_id': uuid4().hex, 'attachment_id': source['id'], 'operation': 'withdraw' if scenario == 'source' else 'update', 'expected_case_token': call('GET', files, owner)['case_token'], 'metadata': {**metadata, 'title': '合成来源更正'}, 'reason': '合成来源核对'}
            preview = call('POST', files + '/preview', owner, json=body)
            mutation = lambda: client.post(files + '/confirm', headers=owner, json={**body, 'preview_token': preview['preview_token'], 'reviewed': True})
        else:
            mutation = lambda: client.put(f'/api/cases/{cid}', headers=owner, json={'owner_name': '合成身份更正'})
        entered, release, attempted = Event(), Event(), Event(); normal = range_review.assemble
        def held(*args): entered.set(); assert release.wait(10); return normal(*args)
        def mutate(): attempted.set(); return mutation()
        with ThreadPoolExecutor(max_workers=2) as pool, patch.object(range_review, 'assemble', side_effect=held):
            reading = pool.submit(call, 'GET', url, owner)
            try:
                assert entered.wait(10); changing = pool.submit(mutate)
                assert attempted.wait(10); assert not changing.done()
            finally: release.set()
            assert reading.result(10)['snapshot'] == before['snapshot']; assert changing.result(10).status_code == 200
        after = call('GET', url, owner); assert after['snapshot'] != before['snapshot']
        if scenario == 'correct':
            assert after['reports'][0]['version'] == 2 and after['reports'][0]['items'][0]['value'] == '1.500'
            assert after['reports'][0]['items'][0]['comparison']['state'] == 'between'
        else: assert after['reports'] == []
    saved = call('GET', url, owner); saved.pop('read_at')
    range_expected.append({'case_id': cid, 'review': saved})
    record('cwb11_postgresql_' + scenario + '_exact_readonly_snapshot')
(f.OUT / 'cwb11-restart-expected.json').write_text(json.dumps(range_expected, ensure_ascii=False, indent=2))

# CW-B12: independent sources and explicit selection; native PostgreSQL only.
f.enable_lab_comparison()
import clinical_lab_comparison as lab_comparison
from build_attachment_cw_b6_fixtures import pdf as comparison_pdf
comparison_fixture = json.loads((f.ROOT / 'tests/fixtures/clinical_lab_comparison_cw_b12_cases.json').read_text())
comparison_expected = []


def comparison_pg(scenario, previewing):
    global statements
    cid = call('POST', '/api/cases', owner, expected=201, json={**comparison_fixture['case'], 'patient_name': 'CW-B12 ' + scenario + str(previewing)})['id']
    files, root, url = (f'/api/cases/{cid}/' + suffix for suffix in ('attachments', 'manual-lab', 'lab-comparison'))
    sources, rows = [], []
    metadata = {'title': '合成对照原件', 'kind': 'lab', 'taken_at': '', 'reported_at': '', 'source': '', 'note': ''}
    for index, data in enumerate(comparison_fixture['reports']):
        raw = comparison_pdf().replace(b'CW-B6', f'CW-B{index}'.encode())
        item = call('POST', files + '/uploads/' + uuid4().hex,
                    {**owner, 'Content-Type': 'application/pdf', 'X-Attachment-Filename': f'comparison-{index}.pdf', 'X-Case-Token': call('GET', files, owner)['case_token']}, content=raw)['attachment']
        body = {'request_id': uuid4().hex, 'attachment_id': item['id'], 'operation': 'confirm', 'expected_case_token': call('GET', files, owner)['case_token'], 'metadata': metadata, 'reason': ''}
        p = call('POST', files + '/preview', owner, json=body)
        sources.append(call('POST', files + '/confirm', owner, json={**body, 'preview_token': p['preview_token'], 'reviewed': True})['attachment'])
        body = {'request_id': uuid4().hex, 'attachment_id': item['id'], 'operation': 'create', 'expected_case_token': call('GET', root, owner)['case_token'], 'report_id': None, 'expected_report_token': '', 'data': data, 'reason': ''}
        p = call('POST', root + '/preview', owner, json=body)
        rows.append(call('POST', root + '/confirm', owner, json={**body, 'preview_token': p['preview_token'], 'reviewed': True})['report'])
    before = call('GET', url, owner)
    def choice(index):
        return {'snapshot': before['snapshot'], 'a': lab_comparison.selection(before['reports'][0], before['reports'][0]['items'][index]),
                'b': lab_comparison.selection(before['reports'][1], before['reports'][1]['items'][index]), 'doctor_confirmed': True}
    request = choice(3)
    expected_delta = comparison_fixture['expected_deltas'][3]
    assert call('POST', url + '/preview', owner, json=request)['delta']['value'] == expected_delta
    if scenario == 'control':
        call('GET', url, other, expected=404); call('GET', url, expected=401)
        call('POST', url + '/preview', other, json=request, expected=404)
        previous = business_digest(); statements = []
        event.listen(f.db.engine, 'before_cursor_execute', capture_writes)
        try:
            with patch.object(attachment_store.Store, 'cleanup', side_effect=AssertionError('No comparison cleanup')):
                assert call('GET', url, owner)['snapshot'] == before['snapshot']
                for index, delta in enumerate(comparison_fixture['expected_deltas']):
                    assert call('POST', url + '/preview', owner, json=choice(index))['delta']['value'] == delta
        finally: event.remove(f.db.engine, 'before_cursor_execute', capture_writes)
        assert statements == [] and business_digest() == previous
    else:
        row, source = rows[0], sources[0]
        if scenario in {'correct', 'withdraw'}:
            data = deepcopy(comparison_fixture['reports'][0]); data['items'][0]['value'] = '1.500'
            body = {'request_id': uuid4().hex, 'attachment_id': row['attachment_id'], 'operation': scenario, 'expected_case_token': call('GET', root, owner)['case_token'], 'report_id': row['id'], 'expected_report_token': row['token'], 'data': data if scenario == 'correct' else None, 'reason': '合成前后对照并发核对'}
            p = call('POST', root + '/preview', owner, json=body)
            mutation = lambda: client.post(root + '/confirm', headers=owner, json={**body, 'preview_token': p['preview_token'], 'reviewed': True})
        elif scenario in {'source', 'source_metadata'}:
            body = {'request_id': uuid4().hex, 'attachment_id': source['id'], 'operation': 'withdraw' if scenario == 'source' else 'update', 'expected_case_token': call('GET', files, owner)['case_token'], 'metadata': {**metadata, 'title': '合成对照来源更正'}, 'reason': '合成来源核对'}
            p = call('POST', files + '/preview', owner, json=body)
            mutation = lambda: client.post(files + '/confirm', headers=owner, json={**body, 'preview_token': p['preview_token'], 'reviewed': True})
        else: mutation = lambda: client.put(f'/api/cases/{cid}', headers=owner, json={'owner_name': '对照并发身份更正'})
        entered, release, attempted = Event(), Event(), Event(); normal = lab_comparison.assemble
        def held(*args): entered.set(); assert release.wait(10); return normal(*args)
        def mutate(): attempted.set(); return mutation()
        with ThreadPoolExecutor(max_workers=2) as pool, patch.object(lab_comparison, 'assemble', side_effect=held):
            reading = pool.submit(call, 'POST', url + '/preview', owner, json=request) if previewing else pool.submit(call, 'GET', url, owner)
            try:
                assert entered.wait(10); changing = pool.submit(mutate)
                assert attempted.wait(10); assert not changing.done()
            finally: release.set()
            result = reading.result(10); assert result['snapshot'] == before['snapshot']
            if previewing: assert result['delta']['value'] == expected_delta
            assert changing.result(10).status_code == 200
        after = call('GET', url, owner); assert after['snapshot'] != before['snapshot']
        call('POST', url + '/preview', owner, json=request, expected=409)
        if scenario == 'correct':
            current = next(r for r in after['reports'] if r['root_id'] == row['root_id'])
            assert current['version'] == 2 and current['items'][0]['value'] == '1.500'
        else: assert len(after['reports']) == (0 if scenario == 'identity' else 1)
    saved = call('GET', url, owner); saved.pop('read_at')
    preview_saved = call('POST', url + '/preview', owner, json=request) if scenario == 'control' else None
    if preview_saved: preview_saved.pop('read_at')
    comparison_expected.append({'case_id': cid, 'review': saved, 'choice': request, 'preview': preview_saved})
    record('cwb12_postgresql_' + scenario + ('_preview' if previewing else '_get') + '_consistent_readonly_snapshot')


comparison_pg('control', True)
for comparison_scenario in ('correct', 'withdraw', 'source', 'source_metadata', 'identity'):
    for comparison_preview in (False, True): comparison_pg(comparison_scenario, comparison_preview)
(f.OUT / 'cwb12-restart-expected.json').write_text(json.dumps(comparison_expected, ensure_ascii=False, indent=2))

# CW-B13: native PostgreSQL lock spans selected raw pair, mixed sections and bytes.
f.enable_lab_comparison_documents()
import clinical_lab_comparison_documents as comparison_documents
comparison_document_expected=[]


def comparison_document_pg(scenario, rendering):
    cid = call('POST', '/api/cases', owner, expected=201, json={**comparison_fixture['case'], 'patient_name': 'CW-B13 ' + scenario + str(rendering)})['id']
    files, root, url = (f'/api/cases/{cid}/' + suffix for suffix in ('attachments', 'manual-lab', 'lab-comparison'))
    sources, rows = [], []
    metadata = {'title': '合成对照原件', 'kind': 'lab', 'taken_at': '', 'reported_at': '', 'source': '', 'note': ''}
    for index, data in enumerate(comparison_fixture['reports']):
        raw = comparison_pdf().replace(b'CW-B6', f'CW-B{index}'.encode())
        item = call('POST', files + '/uploads/' + uuid4().hex,
                    {**owner, 'Content-Type': 'application/pdf', 'X-Attachment-Filename': f'comparison-{index}.pdf', 'X-Case-Token': call('GET', files, owner)['case_token']}, content=raw)['attachment']
        body = {'request_id': uuid4().hex, 'attachment_id': item['id'], 'operation': 'confirm', 'expected_case_token': call('GET', files, owner)['case_token'], 'metadata': metadata, 'reason': ''}
        p = call('POST', files + '/preview', owner, json=body)
        sources.append(call('POST', files + '/confirm', owner, json={**body, 'preview_token': p['preview_token'], 'reviewed': True})['attachment'])
        body = {'request_id': uuid4().hex, 'attachment_id': item['id'], 'operation': 'create', 'expected_case_token': call('GET', root, owner)['case_token'], 'report_id': None, 'expected_report_token': '', 'data': data, 'reason': ''}
        p = call('POST', root + '/preview', owner, json=body)
        rows.append(call('POST', root + '/confirm', owner, json={**body, 'preview_token': p['preview_token'], 'reviewed': True})['report'])
    extras={}
    if scenario in {'mixed','control'}:
        name,mime,raw=attachment_samples()[0]
        image_source=call('POST',files+'/uploads/'+uuid4().hex,{**owner,'Content-Type':mime,'X-Attachment-Filename':quote(name),'X-Case-Token':call('GET',files,owner)['case_token']},content=raw)['attachment']
        b={'request_id':uuid4().hex,'attachment_id':image_source['id'],'operation':'confirm','expected_case_token':call('GET',files,owner)['case_token'],'metadata':{**metadata,'kind':'dr'},'reason':''}
        p=call('POST',files+'/preview',owner,json=b);call('POST',files+'/confirm',owner,json={**b,'preview_token':p['preview_token'],'reviewed':True})
        image_root=f'/api/cases/{cid}/manual-imaging'
        b={'request_id':uuid4().hex,'attachment_id':image_source['id'],'operation':'create','expected_case_token':call('GET',image_root,owner)['case_token'],'report_id':None,'expected_report_token':'','data':image_data,'reason':''}
        p=call('POST',image_root+'/preview',owner,json=b);image_row=call('POST',image_root+'/confirm',owner,json={**b,'preview_token':p['preview_token'],'reviewed':True})['report']
        extras={'manual_lab_report_ids':[rows[0]['id']],'manual_imaging_report_ids':[image_row['id']]}
    saved=call('GET',url,owner)
    choice={'snapshot':saved['snapshot'],'a':lab_comparison.selection(saved['reports'][0],saved['reports'][0]['items'][3]),'b':lab_comparison.selection(saved['reports'][1],saved['reports'][1]['items'][3]),'doctor_confirmed':True}
    body={'case_id':cid,'template_id':'outpatient_record_zh','manual_lab_comparison':choice,**extras}
    preview=call('POST','/api/clinical-docs/render-preview',owner,json=body)
    request={**body,'expected_content_snapshot':preview['content_snapshot']}
    if scenario=='control':
        call('POST','/api/clinical-docs/render-preview',other,json=body,expected=404)
        call('POST','/api/clinical-docs/render-preview',json=body,expected=401)
        previous=business_digest();writes=[]
        def capture(_c,_cur,sql,*_):
            if sql.lstrip().split()[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','DROP','ALTER'}:writes.append(sql)
        event.listen(f.db.engine,'before_cursor_execute',capture)
        try:
            p=call('POST','/api/clinical-docs/render-preview',owner,json=body)
            r=client.post('/api/clinical-docs/render',headers=owner,json=request)
            assert r.status_code==200 and r.headers['cache-control']=='private, no-store'
            assert p['content_snapshot']==preview['content_snapshot']
            assert comparison_fixture['expected_deltas'][3] in document_text(r.content)
            (f.OUT/'cwb13-pg-mixed.docx').write_bytes(r.content)
        finally:event.remove(f.db.engine,'before_cursor_execute',capture)
        assert writes==[] and business_digest()==previous
        comparison_document_expected.append({'body':body,'snapshot':p['content_snapshot'],'comparison':p['manual_lab_comparison'],'labs':p.get('manual_lab_reports',[]),'images':p.get('manual_imaging_reports',[])})
    else:
        row,source=rows[0],sources[0]
        if scenario in {'correct','withdraw','mixed'}:
            target=image_root if scenario=='mixed' else root
            selected=image_row if scenario=='mixed' else row
            data=deepcopy(comparison_fixture['reports'][0]);data['items'][0]['value']='1.500'
            b={'request_id':uuid4().hex,'attachment_id':selected['attachment_id'],'operation':'correct' if scenario=='correct' else 'withdraw','expected_case_token':call('GET',target,owner)['case_token'],'report_id':selected['id'],'expected_report_token':selected['token'],'data':data if scenario=='correct' else None,'reason':'合成文书并发核对'}
            p=call('POST',target+'/preview',owner,json=b)
            mutation=lambda:client.post(target+'/confirm',headers=owner,json={**b,'preview_token':p['preview_token'],'reviewed':True})
        elif scenario in {'source','source_metadata'}:
            b={'request_id':uuid4().hex,'attachment_id':source['id'],'operation':'withdraw' if scenario=='source' else 'update','expected_case_token':call('GET',files,owner)['case_token'],'metadata':{**metadata,'title':'合成文书来源更正'},'reason':'合成来源核对'}
            p=call('POST',files+'/preview',owner,json=b)
            mutation=lambda:client.post(files+'/confirm',headers=owner,json={**b,'preview_token':p['preview_token'],'reviewed':True})
        else:mutation=lambda:client.put(f'/api/cases/{cid}',headers=owner,json={('owner_name' if scenario=='identity' else 'history'):'文书并发正文或身份更正'})
        entered,release,attempted=Event(),Event(),Event()
        module,method=(document_api,'_render_docx') if rendering else (comparison_documents,'read_selected')
        normal=getattr(module,method)
        def held(*args,**kwargs):entered.set();assert release.wait(10);return normal(*args,**kwargs)
        def mutate():attempted.set();return mutation()
        with ThreadPoolExecutor(max_workers=2) as pool,patch.object(module,method,side_effect=held):
            reading=pool.submit(client.post,'/api/clinical-docs/'+('render' if rendering else 'render-preview'),headers=owner,json=request if rendering else body)
            try:
                assert entered.wait(10);changing=pool.submit(mutate);assert attempted.wait(10);assert not changing.done()
            finally:release.set()
            r=reading.result(15);assert r.status_code==200
            if rendering:assert comparison_fixture['expected_deltas'][3] in document_text(r.content) and '文书并发正文或身份更正' not in document_text(r.content)
            else:assert r.json()['content_snapshot']==preview['content_snapshot']
            assert changing.result(15).status_code==200
        call('POST','/api/clinical-docs/render',owner,json=request,expected=409)
    record('cwb13_postgresql_'+scenario+('_render' if rendering else '_preview')+'_full_snapshot_consistency')
    return body


comparison_document_pg('control',True)
for document_scenario in ('correct','withdraw','source','source_metadata','identity','body','mixed'):
    for rendering in (False,True):comparison_document_pg(document_scenario,rendering)
(f.OUT/'cwb13-restart-expected.json').write_text(json.dumps(comparison_document_expected,ensure_ascii=False,indent=2))

# CW-B14 native PostgreSQL: separate sessions, Case row locks, no SQLite imports.
f.enable_followup_plans()
import clinical_followup_plans as followup
from threading import Event
from sqlalchemy.exc import OperationalError
followup_fixture=json.loads((f.ROOT/'tests/fixtures/clinical_followup_plans_cw_b14_cases.json').read_text())
followup_expected=[]


def followup_pg(scenario):
    cid=call('POST','/api/cases',owner,expected=201,json={**followup_fixture['case'],'species':'cat' if scenario=='lifecycle' else 'dog'})['id']
    root=f'/api/cases/{cid}/followup-plan'
    original_case=read(cid,owner);request_ids=[]
    def body(operation='create',row=None,data=None):
        l=call('GET',root,owner)
        b={'request_id':uuid4().hex,'operation':operation,'plan_id':row['id'] if row else None,'expected_plan_token':row['token'] if row else '',
           'expected_case_token':l['case_token'],'expected_state_token':l['state_token'],'data':None if operation=='withdraw' else data or followup_fixture['plan'],
           'reason':'' if operation=='create' else followup_fixture['correction_reason']}
        p=call('POST',root+'/preview',owner,json=b)
        return {**b,'preview_token':p['preview_token'],'reviewed':True}
    def save(b,expected=200):
        r=call('POST',root+'/confirm',owner,expected=expected,json=b)
        if expected==200:request_ids.append(b['request_id'])
        return r
    def race(a,b):
        barrier=Barrier(2)
        def send(v):barrier.wait(10);return client.post(root+'/confirm',headers=owner,json=v)
        with ThreadPoolExecutor(2) as pool:
            jobs=[pool.submit(send,v) for v in (a,b)]
            responses=[j.result(20) for j in jobs]
        for b,r in zip((a,b),responses):
            if r.status_code==200:request_ids.append(b['request_id'])
        return responses
    if scenario=='create-race':
        responses=race(body(),body());assert sorted(r.status_code for r in responses)==[200,409]
    elif scenario=='idempotent-race':
        b=body();responses=race(b,b);assert [r.status_code for r in responses]==[200,200]
        assert sorted(r.json()['writes_database'] for r in responses)==[False,True]
    elif scenario=='correct-withdraw':
        row=save(body())['plan'];responses=race(body('correct',row),body('withdraw',row))
        assert sorted(r.status_code for r in responses)==[200,409]
    elif scenario=='case-edit':
        b=body();entered,release=Event(),Event()
        with ThreadPoolExecutor(2) as pool:
            def edit():
                with followup.transaction(owner_id,cid) as (db,case):
                    case.history='并发病例更正';db.flush();entered.set();assert release.wait(10);db.commit()
            writer=pool.submit(edit);assert entered.wait(10)
            future=pool.submit(lambda:client.post(root+'/confirm',headers=owner,json=b));assert not future.done()
            release.set();writer.result(20);assert future.result(20).status_code==409
        original_case=read(cid,owner)
    elif scenario=='rollback':
        for operation in ['create','correct','withdraw']:
            row=save(body())['plan'] if operation=='correct' else (call('GET',root,owner)['plans'][-1] if operation=='withdraw' else None)
            b=body(operation,row);before=call('GET',root,owner);append=followup.append_audit
            def fail(*args):append(*args);args[0].flush();raise OperationalError('synthetic',{},Exception('rollback'))
            with patch.object(followup,'append_audit',side_effect=fail):save(b,503)
            assert call('GET',root,owner)==before
            assert call('GET',root+'/requests/'+b['request_id'],owner)['state']=='not_committed'
    elif scenario=='lost-reply':
        b=body();entered,release=Event(),Event();append=followup.append_audit
        def held(*args):append(*args);args[0].flush();entered.set();assert release.wait(10)
        with patch.object(followup,'append_audit',side_effect=held),ThreadPoolExecutor(2) as pool:
            write=pool.submit(lambda:client.post(root+'/confirm',headers=owner,json=b));assert entered.wait(10)
            result=pool.submit(lambda:client.get(root+'/requests/'+b['request_id'],headers=owner));assert not result.done()
            release.set();assert write.result(20).status_code==200;request_ids.append(b['request_id'])
            receipt=result.result(20);assert receipt.status_code==200 and receipt.json()['state']=='committed'
        assert save(b)['writes_database'] is False
    else:
        row=save(body())['plan'];row=save(body('correct',row,followup_fixture['corrected_plan']))['plan'];save(body('withdraw',row))
        listed=call('GET',root,owner)['plans'];assert [p['data'] for p in listed]==[followup_fixture['plan'],followup_fixture['corrected_plan']]
        assert [p['state'] for p in listed]==['superseded','withdrawn']
        with f.db.SessionLocal() as db:
            rows=db.query(f.models.FollowUp).filter_by(case_id=cid).order_by(f.models.FollowUp.id).all()
            assert [r.due_date.isoformat() for r in rows]==[followup_fixture['expected_due_utc'],followup_fixture['corrected_due_utc']]
    saved=call('GET',root,owner);assert sum(p['stored_state']=='planned' for p in saved['plans'])<=1
    assert read(cid,owner)==original_case
    call('GET',root,other,expected=404)
    with f.db.SessionLocal() as db:
        audits=db.query(f.models.AuditLog).filter_by(case_id=cid,source=followup.SOURCE).order_by(f.models.AuditLog.log_id).all()
        assert len(audits)==len(set(request_ids))
        followup_expected.append({'case_id':cid,'listing':saved,'case':original_case,'audits':[r.extra_data for r in audits],'requests':sorted(set(request_ids))})
    record('cwb14_postgresql_'+scenario)


for scenario in ['create-race','idempotent-race','correct-withdraw','case-edit','rollback','lost-reply','lifecycle']:followup_pg(scenario)
# Independent legacy KPI sample; all CW-B14 source/status records remain excluded.
from datetime import datetime
cid=call('POST','/api/cases',owner,expected=201,json=followup_fixture['case'])['id']
with f.db.SessionLocal() as db:
    for i,done in enumerate([datetime(2024,2,29,12),datetime(2024,3,2),None]):
        db.add(f.models.FollowUp(case_id=cid,due_date=datetime(2024,2,29),done_at=done,status='legacy-'+str(i),channel='phone',note='旧自由文本'))
    db.commit()
kpi_url='/api/kpi/followups?start=2024-02-01&end=2024-03-31'
legacy=call('GET',kpi_url,owner)
for key,value in followup_fixture['legacy_kpi'].items():assert legacy['metrics']['followup_compliance'][key]==value
with f.db.SessionLocal() as db:
    for state,channel in [('cw-b14-broken',''),('corrupt',followup.SOURCE)]:db.add(f.models.FollowUp(case_id=cid,due_date=datetime(2024,2,29),done_at=None,status=state,channel=channel,note='broken'))
    db.commit()
assert call('GET',kpi_url,owner)==legacy
record('cwb14_postgresql_legacy_kpi_unchanged_with_broken_namespace')
(f.OUT/'cwb14-restart-expected.json').write_text(json.dumps(followup_expected,ensure_ascii=False,indent=2))

# CW-B15 native PostgreSQL document locks, complete bytes and fresh-process proof.
f.enable_followup_plan_documents()
import clinical_followup_plan_documents as plan_documents
document_plan_fixture=json.loads((f.ROOT/'tests/fixtures/clinical_followup_plan_documents_cw_b15_cases.json').read_text())
document_plan_expected=[]


def followup_document_pg(scenario, rendering, mixed=False):
    # The earlier CW-B13 control case has real saved lab/image/comparison sections.
    # Reuse only its synthetic immutable records and freshly re-read selectors.
    if mixed:
        baseline=(comparison_document_pg('control',True) if scenario in ('source','source_metadata','lab','imaging') else comparison_document_expected[0]['body'])
        cid=baseline['case_id'];extra={k:v for k,v in baseline.items() if k.startswith('manual_')}
    else:
        cid=call('POST','/api/cases',owner,expected=201,json=document_plan_fixture['case'])['id'];extra={}
    root=f'/api/cases/{cid}/followup-plan'
    def plan_body(operation='create',row=None,data=None):
        listed=call('GET',root,owner)
        b={'request_id':uuid4().hex,'operation':operation,'plan_id':row['id'] if row else None,'expected_plan_token':row['token'] if row else '',
           'expected_case_token':listed['case_token'],'expected_state_token':listed['state_token'],'data':None if operation=='withdraw' else data or document_plan_fixture['plan'],
           'reason':'' if operation=='create' else 'CW-B15 合成并发核对'}
        p=call('POST',root+'/preview',owner,json=b);return {**b,'preview_token':p['preview_token'],'reviewed':True}
    existing=call('GET',root,owner)['plans']
    active=next((p for p in existing if p['stored_state']=='planned'),None)
    row=call('POST',root+'/confirm',owner,json=plan_body('correct' if active else 'create',active))['plan']
    body={'case_id':cid,'template_id':'outpatient_record_zh','manual_followup_plan':{k:row[k] for k in ('id','version','token')},**extra}
    before=call('POST','/api/clinical-docs/render-preview',owner,json=body)
    request={**body,'expected_content_snapshot':before['content_snapshot']}
    if scenario=='control':
        writes=[];original=business_digest()
        with f.db.SessionLocal() as db:plan_before=[(r.id,r.note,r.status,r.updated_at) for r in db.query(f.models.FollowUp).filter_by(case_id=cid).order_by(f.models.FollowUp.id)]
        def capture(_c,_cur,sql,*_):
            if sql.lstrip().split()[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'}:writes.append(sql)
        event.listen(f.db.engine,'before_cursor_execute',capture)
        try:
            p=call('POST','/api/clinical-docs/render-preview',owner,json=body)
            r=client.post('/api/clinical-docs/render',headers=owner,json=request)
            assert r.status_code==200 and r.headers['cache-control']=='private, no-store'
            assert p['manual_followup_plan']['plan']['data']==document_plan_fixture['plan']
            for literal in [row['data']['purpose'],row['data']['planned_date'],row['token'],*row['data']['items']]:assert literal in document_text(r.content)
            (f.OUT/f'cwb15-pg-{cid}.docx').write_bytes(r.content)
        finally:event.remove(f.db.engine,'before_cursor_execute',capture)
        assert writes==[] and business_digest()==original
        with f.db.SessionLocal() as db:assert [(r.id,r.note,r.status,r.updated_at) for r in db.query(f.models.FollowUp).filter_by(case_id=cid).order_by(f.models.FollowUp.id)]==plan_before
        document_plan_expected.append({'body':body,'snapshot':before['content_snapshot'],'plan':before['manual_followup_plan'],
            **{k:before[k] for k in ('manual_lab_reports','manual_imaging_reports','manual_lab_comparison') if k in before}})
    else:
        if scenario in ('correct','withdraw','replace'):
            b=plan_body('correct' if scenario=='correct' else 'withdraw',row,document_plan_fixture['corrected_plan'])
            def mutation():
                r=client.post(root+'/confirm',headers=owner,json=b)
                if scenario=='replace':call('POST',root+'/confirm',owner,json=plan_body(data=document_plan_fixture['short_plan']))
                return r
        elif scenario in ('source','source_metadata','lab','imaging'):
            record_root=f'/api/cases/{cid}/'+('manual-imaging' if scenario=='imaging' else 'manual-lab')
            selected=next(r for r in call('GET',record_root,owner)['reports'] if r['id']==extra['manual_imaging_report_ids' if scenario=='imaging' else 'manual_lab_report_ids'][0])
            if scenario.startswith('source'):
                target=f'/api/cases/{cid}/attachments';state=call('GET',target,owner);source=next(s for s in state['items'] if s['id']==selected['attachment_id'])
                b={'request_id':uuid4().hex,'attachment_id':source['id'],'operation':'withdraw' if scenario=='source' else 'update','expected_case_token':state['case_token'],'metadata':{**source['metadata'],'title':'CW-B15 来源更正'},'reason':'合成来源变更'}
            else:
                target=record_root;b={'request_id':uuid4().hex,'attachment_id':selected['attachment_id'],'operation':'withdraw','expected_case_token':call('GET',target,owner)['case_token'],'report_id':selected['id'],'expected_report_token':selected['token'],'data':None,'reason':'CW-B15 合成撤销'}
            preview=call('POST',target+'/preview',owner,json=b)
            mutation=lambda:client.post(target+'/confirm',headers=owner,json={**b,'preview_token':preview['preview_token'],'reviewed':True})
        elif scenario=='delete':mutation=lambda:client.delete(f'/api/cases/{cid}',headers=owner)
        else:mutation=lambda:client.put(f'/api/cases/{cid}',headers=owner,json={'history':'CW-B15 并发正文更正'})
        entered,release,attempted=Event(),Event(),Event();module,method=(document_api,'_render_docx') if rendering else (plan_documents,'read_selected');normal=getattr(module,method)
        def held(*args,**kwargs):entered.set();assert release.wait(15);return normal(*args,**kwargs)
        def mutate():attempted.set();return mutation()
        with ThreadPoolExecutor(2) as pool,patch.object(module,method,side_effect=held):
            reading=pool.submit(client.post,'/api/clinical-docs/'+('render' if rendering else 'render-preview'),headers=owner,json=request if rendering else body)
            try:
                assert entered.wait(10);changing=pool.submit(mutate);assert attempted.wait(10);assert not changing.done()
            finally:release.set()
            r=reading.result(20);assert r.status_code==200
            if rendering:assert row['data']['purpose'] in document_text(r.content) and 'CW-B15 并发正文更正' not in document_text(r.content)
            else:assert r.json()['content_snapshot']==before['content_snapshot']
            assert changing.result(20).status_code==(204 if scenario=='delete' else 200)
        call('POST','/api/clinical-docs/render',owner,json=request,expected=404 if scenario=='delete' else 409)
    record('cwb15_postgresql_'+scenario+('_mixed' if mixed else '_plan_only')+('_render' if rendering else '_preview'))


for scenario in ('correct','withdraw','replace','body','delete'):
    for rendering in (False,True):followup_document_pg(scenario,rendering)
# Mixed plan races leave the existing comparison sources/case intact for historical readback.
for rendering in (False,True):followup_document_pg('correct',rendering,True)
for scenario in ('source','source_metadata','lab','imaging'):
    for rendering in (False,True):followup_document_pg(scenario,rendering,True)
followup_document_pg('control',True)
followup_document_pg('control',True,True)
(f.OUT/'cwb15-restart-expected.json').write_text(json.dumps(document_plan_expected,ensure_ascii=False,indent=2))

# Close only after every batch has finished using the shared authenticated client.
client.close(); f.db.engine.dispose()

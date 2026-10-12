"""Authenticated synthetic laboratory workflow on disposable SQLite; inherited egress guard."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4
from test_case_attachments import AttachmentFixture, f, storage
import manual_lab_results as lab

DATA = json.loads((Path(__file__).parent / 'fixtures/manual_lab_cw_b7_cases.json').read_text())


class ManualLabFixture(AttachmentFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for model in (f.models.DiagnosticReport, f.models.Observation, f.models.ImagingStudy): model.__table__.create(f.db.engine, checkfirst=True)

    def setUp(self):
        super().setUp()
        self.labenv = patch.dict(os.environ, {'MANUAL_LAB_RESULTS_ENABLED':'1', 'MANUAL_LAB_RESULTS_SYNTHETIC_ONLY':'1'})
        self.labenv.start()
        self.addCleanup(self.labenv.stop)
        self.labroot = f'/api/cases/{self.cid}/manual-lab'

    def lab_state(self):
        r = self.client.get(self.labroot, headers=self.owner_headers)
        self.assertEqual(r.status_code,200,r.text); return r.json()

    def lab_body(self, item=None, old=None, operation='create'):
        return {'request_id':uuid4().hex, 'attachment_id':old['attachment_id'] if old else item['id'],
                'expected_case_token':self.lab_state()['case_token'], 'operation':operation,
                'report_id':old['id'] if old else None, 'expected_report_token':old['token'] if old else '',
                'data':None if operation == 'withdraw' else (lab.input_data(old['data']) if old else copy.deepcopy(DATA)),
                'reason':'合成核对更正/撤销' if old else ''}

    def lab_review(self, body):
        r=self.client.post(self.labroot+'/preview',headers=self.owner_headers,json=body)
        self.assertEqual(r.status_code,200,r.text)
        return {**body,'preview_token':r.json()['preview_token'],'reviewed':True}

    def lab_commit(self, req): return self.client.post(self.labroot+'/confirm',headers=self.owner_headers,json=req)

    def save_lab(self):
        item,_,_=self.attach(); req=self.lab_review(self.lab_body(item)); r=self.lab_commit(req)
        self.assertEqual(r.status_code,200,r.text); return item,req,r.json()['report']


class ManualLabTests(ManualLabFixture):
    def test_exact_original_decimal_comparison_missing_and_relogin(self):
        item,req,row=self.save_lab()
        self.assertEqual(lab.input_data(row['data']),DATA)
        self.assertEqual([r['decimal'] for r in row['data']['items']],['0.0100','0.0010',None,None,None,'0','5.20'])
        self.assertEqual(row['state'],'confirmed'); self.assertEqual(row['reviewed_by'],str(self.owner_id))
        self.assertEqual(row['source']['sha256'],item['sha256'])
        f.db.engine.dispose()
        self.assertEqual(self.lab_state()['reports'],[row])
        with f.db.SessionLocal() as db:
            obs=db.query(f.models.Observation).filter_by(diagnostic_report_id=row['id']).order_by(f.models.Observation.id).all()
            self.assertEqual([o.value_text for o in obs],[r['value'] for r in DATA['items']])
            self.assertTrue(all(o.value_numeric is None and o.abnormal_flag is None for o in obs))

    def test_preview_no_write_checkboxes_and_changed_request(self):
        item,_,_=self.attach(); body=self.lab_body(item); req=self.lab_review(body)
        self.assertEqual(self.lab_state()['reports'],[])
        for change in ({'reviewed':False},{'preview_token':'0'*64},{'reason':'changed'}):
            self.assertIn(self.lab_commit({**req,**change}).status_code,[409,422])
        self.assertEqual(self.lab_state()['reports'],[])
        self.assertEqual(self.lab_commit(req).status_code,200)
        self.assertEqual(self.lab_commit({**req,'reason':'changed'}).status_code,409)

    def test_request_recovery_duplicate_and_later_state(self):
        _,req,row=self.save_lab()
        for _ in range(2): self.assertEqual(self.lab_commit(req).status_code,200)
        self.assertEqual(len(self.lab_state()['reports']),1)
        withdrawal=self.lab_review(self.lab_body(old=row,operation='withdraw'))
        self.assertEqual(self.lab_commit(withdrawal).status_code,200)
        r=self.client.get(self.labroot+'/requests/'+req['request_id'],headers=self.owner_headers)
        self.assertEqual(r.json()['report']['state'],'withdrawn')
        self.assertEqual(self.lab_commit(req).json()['report']['state'],'withdrawn')
        self.assertEqual(self.client.get(self.labroot+'/requests/'+uuid4().hex,headers=self.owner_headers).json()['state'],'not_committed')
        with f.db.SessionLocal() as db:
            self.assertEqual(db.query(f.models.AuditLog).filter_by(case_id=self.cid,event_type='manual_lab_create').count(),1)

    def test_correction_new_version_preserves_original_and_reason(self):
        _,_,old=self.save_lab(); body=self.lab_body(old=old,operation='correct')
        body['data']['items'][0]['value']='0.0200'
        row=self.lab_commit(self.lab_review(body)).json()['report']
        self.assertEqual(row['version'],2); self.assertEqual(row['root_id'],old['id'])
        history=self.lab_state()['reports']; self.assertEqual(history[0]['state'],'superseded')
        self.assertEqual(history[0]['data'],old['data']);self.assertEqual(history[1]['data']['items'][0]['value'],'0.0200')
        self.assertEqual(self.client.post(self.labroot+'/preview',headers=self.owner_headers,json=self.lab_body(old=old,operation='correct')).status_code,409)

    def test_auth_case_deleted_and_production_disabled(self):
        _,req,_=self.save_lab()
        for path in (self.labroot,self.labroot+'/requests/'+req['request_id']):
            self.assertEqual(self.client.get(path).status_code,401)
            self.assertEqual(self.client.get(path,headers=self.other_headers).status_code,404)
        for env in ({'MANUAL_LAB_RESULTS_ENABLED':'0'},{'MANUAL_LAB_RESULTS_SYNTHETIC_ONLY':'0'},{'ENVIRONMENT':'production'},{'RENDER':'true'}):
            with patch.dict(os.environ,env): self.assertEqual(self.client.get(self.labroot,headers=self.owner_headers).status_code,503)
        self.client.delete(f'/api/cases/{self.cid}',headers=self.owner_headers)
        self.assertEqual(self.lab_commit(req).status_code,404)

    def test_validation_no_guessing_no_coercion_or_partial_records(self):
        item,_,_=self.attach(); valid=self.lab_body(item)
        changes=[('value','NaN'),('value','Infinity'),('value','1,234'),('value','1e999'),('value',1.25),('checked',False),('position',''),('reference_low','12'),('reference_unit','mg/dL'),('reference',''),('result_type','not_tested')]
        for key,value in changes:
            body=copy.deepcopy(valid);body['data']['items'][0][key]=value
            r=self.client.post(self.labroot+'/preview',headers=self.owner_headers,json=body)
            self.assertEqual(r.status_code,422,(key,value,r.text))
        for date in ('yesterday','2026-10-06T10:30:00'):
            body=copy.deepcopy(valid);body['data']['report']['collected_at']=date
            self.assertEqual(self.client.post(self.labroot+'/preview',headers=self.owner_headers,json=body).status_code,422)
        self.assertEqual(self.lab_state()['reports'],[])

    def test_row_report_version_limits_allow_withdrawal(self):
        item,_,_=self.attach();body=self.lab_body(item)
        body['data']['items']=[body['data']['items'][0]]*101
        self.assertEqual(self.client.post(self.labroot+'/preview',headers=self.owner_headers,json=body).status_code,422)
        body=self.lab_body(item)
        with patch.object(lab,'MAX_REPORTS',0):
            self.assertEqual(self.client.post(self.labroot+'/preview',headers=self.owner_headers,json=body).status_code,422)
        row=self.lab_commit(self.lab_review(body)).json()['report']
        with patch.object(lab,'MAX_VERSIONS',1),patch.object(lab,'MAX_REPORTS',0):
            self.assertEqual(self.client.post(self.labroot+'/preview',headers=self.owner_headers,json=self.lab_body(old=row,operation='correct')).status_code,422)
            self.assertEqual(self.lab_commit(self.lab_review(self.lab_body(old=row,operation='withdraw'))).status_code,200)

    def test_source_and_identity_changes_invalidate_confirmed_records(self):
        item,_,row=self.save_lab()
        self.meta={**self.meta,'title':'更正原报告描述'}
        self.assertEqual(self.commit(self.reviewed(self.body(item,'update'))).status_code,200)
        self.assertEqual(self.lab_state()['reports'][0]['state'],'needs_review')
        row=self.lab_commit(self.lab_review(self.lab_body(old=self.lab_state()['reports'][0],operation='correct'))).json()['report']
        self.client.put(f'/api/cases/{self.cid}',headers=self.owner_headers,json={'owner_name':'更正合成宠主'})
        self.assertEqual(self.lab_state()['reports'][-1]['state'],'needs_review')
        with f.db.SessionLocal() as db:
            self.assertEqual(db.query(f.models.AuditLog).filter_by(case_id=self.cid,event_type='manual_lab_invalidate').count(),2)
            self.assertTrue(all(o.review_status=='needs_review' for o in db.query(f.models.Observation).filter_by(diagnostic_report_id=row['id'])))

    def test_source_lost_or_corrupted_not_current_and_withdraw_still_works(self):
        item,_,row=self.save_lab();storage.Store().path(item['id'],'.blob').write_bytes(b'corrupt')
        self.assertEqual(self.lab_state()['reports'][0]['state'],'source_unavailable')
        self.assertEqual(self.client.post(self.labroot+'/preview',headers=self.owner_headers,json=self.lab_body(old=row,operation='correct')).status_code,409)
        self.assertEqual(self.lab_commit(self.lab_review(self.lab_body(old=row,operation='withdraw'))).status_code,200)

    def test_source_withdrawal_atomic_and_stale_preview_rejected(self):
        item,_,row=self.save_lab(); req=self.lab_review(self.lab_body(old=row,operation='correct'))
        self.assertEqual(self.commit(self.reviewed(self.body(item,'withdraw'))).status_code,200)
        self.assertEqual(self.lab_state()['reports'][0]['state'],'needs_review')
        self.assertEqual(self.lab_commit(req).status_code,409)

    def test_ordinary_history_change_preserves_exact_data_and_confirmation(self):
        _,_,row=self.save_lab();self.client.put(f'/api/cases/{self.cid}',headers=self.owner_headers,json={'history':'仅更正合成病史'})
        self.assertEqual(self.lab_state()['reports'][0],row)

    def test_legacy_lists_documents_and_mutations_exclude_manual_data(self):
        item,_,_=self.attach();before={}
        routes=[f'/api/diagnostic-data/cases/{self.cid}/'+s for s in ('summary','reports','observations')]
        for route in routes:
            r=self.client.get(route,headers=self.owner_headers);self.assertEqual(r.status_code,200,r.text);before[route]=r.json()
        row=self.lab_commit(self.lab_review(self.lab_body(item))).json()['report']
        for route in routes:self.assertEqual(self.client.get(route,headers=self.owner_headers).json(),before[route])
        self.assertEqual(self.client.get(f'/api/diagnostic-data/reports/{row["id"]}',headers=self.owner_headers).status_code,404)
        with f.db.SessionLocal() as db: oid=db.query(f.models.Observation).filter_by(diagnostic_report_id=row['id']).first().id
        for route in (f'/api/diagnostic-data/diagnostic-reports/{row["id"]}/ai-summary/persistence/apply',f'/api/diagnostic-data/observations/{oid}/abnormal-flag/review/apply'):
            self.assertEqual(self.client.post(route,headers=self.owner_headers,json={}).status_code,409)
            self.assertEqual(self.client.post(route,headers=self.other_headers,json={}).status_code,404)
        self.assertEqual(self.lab_state()['reports'][0],row)


if __name__=='__main__': unittest.main(verbosity=2)

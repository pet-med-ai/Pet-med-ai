"""Authenticated manual imaging, original text and existing-interface isolation."""
import copy
from datetime import datetime
from types import SimpleNamespace
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4
from test_manual_lab_results import ManualLabFixture, f, storage
import manual_imaging_records as imaging

DATA=json.loads((Path(__file__).parent/'fixtures/manual_imaging_cw_b9_cases.json').read_text())


class ImagingFixture(ManualLabFixture):
    def setUp(self):
        super().setUp()
        env=patch.dict(os.environ,{'MANUAL_IMAGING_ENABLED':'1','MANUAL_IMAGING_SYNTHETIC_ONLY':'1'})
        env.start();self.addCleanup(env.stop)
        self.meta={**self.meta,'kind':'dr'}
        self.image_root=f'/api/cases/{self.cid}/manual-imaging'

    def image_state(self):
        r=self.client.get(self.image_root,headers=self.owner_headers)
        self.assertEqual(r.status_code,200,r.text);return r.json()

    def image_body(self,item=None,old=None,operation='create'):
        return {'request_id':uuid4().hex,'attachment_id':old['attachment_id'] if old else item['id'],
                'expected_case_token':self.image_state()['case_token'],'operation':operation,
                'report_id':old['id'] if old else None,'expected_report_token':old['token'] if old else '',
                'data':None if operation=='withdraw' else copy.deepcopy(old['data'] if old else DATA),
                'reason':'合成更正或撤销原因' if old else ''}

    def image_review(self,body):
        r=self.client.post(self.image_root+'/preview',headers=self.owner_headers,json=body)
        self.assertEqual(r.status_code,200,r.text)
        return {**body,'preview_token':r.json()['preview_token'],'reviewed':True}

    def image_commit(self,req):return self.client.post(self.image_root+'/confirm',headers=self.owner_headers,json=req)

    def save_image(self):
        item,_,_=self.attach();req=self.image_review(self.image_body(item));r=self.image_commit(req)
        self.assertEqual(r.status_code,200,r.text);return item,req,r.json()['report']


class ImagingTests(ImagingFixture):
    def test_exact_text_explicit_date_and_restart(self):
        item,req,row=self.save_image()
        self.assertEqual(row['data'],DATA);self.assertEqual(row['state'],'confirmed')
        self.assertEqual(row['source']['sha256'],item['sha256'])
        with f.db.SessionLocal() as db:
            stored=db.get(f.models.ImagingStudy,row['id'])
            self.assertEqual(stored.taken_at.isoformat(),'2026-10-07T01:30:00')
            self.assertEqual(stored.report_text,DATA['findings'])
            self.assertEqual(stored.ai_summary_status,'not_generated')
        f.db.engine.dispose();self.assertEqual(self.image_state()['reports'],[row])

    def test_preview_no_write_and_confirmation_payload_bound(self):
        item,_,_=self.attach();req=self.image_review(self.image_body(item))
        self.assertEqual(self.image_state()['reports'],[])
        for change in ({'reviewed':False},{'preview_token':'0'*64},{'reason':'changed'}):
            self.assertIn(self.image_commit({**req,**change}).status_code,[409,422])
        self.assertEqual(self.image_state()['reports'],[])
        self.assertEqual(self.image_commit(req).status_code,200)
        self.assertEqual(self.image_commit({**req,'reason':'changed'}).status_code,409)

    def test_duplicate_recovery_returns_current_withdrawn_state(self):
        _,req,row=self.save_image()
        for _ in range(2):self.assertEqual(self.image_commit(req).status_code,200)
        self.assertEqual(len(self.image_state()['reports']),1)
        self.image_commit(self.image_review(self.image_body(old=row,operation='withdraw')))
        for r in [self.image_commit(req),self.client.get(self.image_root+'/requests/'+req['request_id'],headers=self.owner_headers)]:
            self.assertEqual(r.json()['report']['state'],'withdrawn')
        self.assertEqual(self.client.get(self.image_root+'/requests/'+uuid4().hex,headers=self.owner_headers).json()['state'],'not_committed')
        with f.db.SessionLocal() as db:self.assertEqual(db.query(f.models.AuditLog).filter_by(case_id=self.cid,event_type='manual_imaging_create').count(),1)

    def test_correction_preserves_original_and_requires_reason(self):
        _,_,old=self.save_image();b=self.image_body(old=old,operation='correct');b['data']['findings']='更正后的原文'
        self.assertEqual(self.client.post(self.image_root+'/preview',headers=self.owner_headers,json={**b,'reason':''}).status_code,422)
        row=self.image_commit(self.image_review(b)).json()['report']
        self.assertEqual(row['version'],2);self.assertEqual(row['root_id'],old['id'])
        self.assertEqual(self.image_state()['reports'][0]['data'],old['data'])
        self.assertEqual(self.image_state()['reports'][0]['state'],'superseded')
        self.assertEqual(self.client.post(self.image_root+'/preview',headers=self.owner_headers,json=self.image_body(old=old,operation='correct')).status_code,409)

    def test_auth_feature_flags_render_and_case_deletion(self):
        _,req,_=self.save_image()
        for path in (self.image_root,self.image_root+'/requests/'+req['request_id']):
            self.assertEqual(self.client.get(path).status_code,401)
            self.assertEqual(self.client.get(path,headers=self.other_headers).status_code,404)
        for env in ({'MANUAL_IMAGING_ENABLED':'0'},{'MANUAL_IMAGING_SYNTHETIC_ONLY':'0'},{'ENVIRONMENT':'production'},{'RENDER':'true'}):
            with patch.dict(os.environ,env):self.assertEqual(self.client.get(self.image_root,headers=self.owner_headers).status_code,503)
        self.client.delete(f'/api/cases/{self.cid}',headers=self.owner_headers)
        self.assertEqual(self.image_commit(req).status_code,404)

    def test_validation_sections_unicode_dates_no_default_or_coercion(self):
        item,_,_=self.attach();valid=self.image_body(item)
        changes=[('taken_at',''),('taken_at','2026-10-07T09:30:00'),('taken_at','yesterday'),('taken_at','0001-01-01T00:00:00+14:00'),
                 ('findings',123),('findings','\x01'),('findings','😀'*5001),('impression','a'*5001),('limitations','a'*1001),
                 ('checked_findings',False),('checked_impression',1),('position',''),('body_part',''),('modality','ct')]
        for key,value in changes:
            b=copy.deepcopy(valid);b['data'][key]=value
            r=self.client.post(self.image_root+'/preview',headers=self.owner_headers,json=b)
            self.assertEqual(r.status_code,422,(key,r.text))
        b=copy.deepcopy(valid);b['data']['findings']=b['data']['impression']=''
        self.assertEqual(self.client.post(self.image_root+'/preview',headers=self.owner_headers,json=b).status_code,422)
        b=copy.deepcopy(valid);b['data']['findings']='😀'*5000;b['data']['impression']=''
        self.image_review(b);self.assertEqual(self.image_state()['reports'],[])

    def test_source_kind_and_report_version_limits(self):
        item,_,_=self.attach();b=self.image_body(item)
        with patch.object(imaging,'MAX_REPORTS',0):self.assertEqual(self.client.post(self.image_root+'/preview',headers=self.owner_headers,json=b).status_code,422)
        b['data']['modality']='ultrasound';self.assertEqual(self.client.post(self.image_root+'/preview',headers=self.owner_headers,json=b).status_code,422)
        b['data']['modality']='dr';row=self.image_commit(self.image_review(b)).json()['report']
        self.assertEqual(self.client.post(self.image_root+'/preview',headers=self.owner_headers,json=self.image_body(item)).status_code,409)
        with patch.object(imaging,'MAX_VERSIONS',1):
            self.assertEqual(self.client.post(self.image_root+'/preview',headers=self.owner_headers,json=self.image_body(old=row,operation='correct')).status_code,422)
            self.assertEqual(self.image_commit(self.image_review(self.image_body(old=row,operation='withdraw'))).status_code,200)

    def test_source_changes_identity_and_feature_off_invalidation(self):
        item,_,row=self.save_image();self.meta={**self.meta,'title':'修订原件标题'}
        with patch.dict(os.environ,{'MANUAL_IMAGING_ENABLED':'0'}):self.assertEqual(self.commit(self.reviewed(self.body(item,'update'))).status_code,200)
        row=self.image_state()['reports'][0];self.assertEqual(row['state'],'needs_review')
        row=self.image_commit(self.image_review(self.image_body(old=row,operation='correct'))).json()['report']
        self.client.put(f'/api/cases/{self.cid}',headers=self.owner_headers,json={'coat_color':'合成棕色'})
        self.assertEqual(self.image_state()['reports'][-1]['state'],'needs_review')
        with f.db.SessionLocal() as db:self.assertEqual(db.query(f.models.AuditLog).filter_by(case_id=self.cid,event_type='manual_imaging_invalidate').count(),2)

    def test_missing_corrupt_or_withdrawn_source_rejects_and_allows_withdrawal(self):
        item,_,row=self.save_image();req=self.image_review(self.image_body(old=row,operation='correct'))
        storage.Store().path(item['id'],'.blob').write_bytes(b'corrupt')
        self.assertEqual(self.image_state()['reports'][0]['state'],'source_unavailable')
        self.assertEqual(self.image_commit(req).status_code,409)
        self.assertEqual(self.image_commit(self.image_review(self.image_body(old=row,operation='withdraw'))).status_code,200)

    def test_history_change_does_not_modify_imaging(self):
        _,_,row=self.save_image();self.client.put(f'/api/cases/{self.cid}',headers=self.owner_headers,json={'history':'普通病史更正'})
        self.assertEqual(self.image_state()['reports'],[row])

    def test_legacy_lists_review_summary_and_kpi_exclude_versions(self):
        item,_,_=self.attach();routes=[f'/api/diagnostic-data/cases/{self.cid}/'+s for s in ('summary','imaging-studies')]
        before={url:self.client.get(url,headers=self.owner_headers).json() for url in routes}
        row=self.image_commit(self.image_review(self.image_body(item))).json()['report']
        self.image_commit(self.image_review(self.image_body(old=row,operation='correct')))
        for url in routes:
            r=self.client.get(url,headers=self.owner_headers);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json(),before[url])
        url=f'/api/diagnostic-data/imaging-studies/{row["id"]}/review-workflow/apply'
        self.assertEqual(self.client.post(url,headers=self.owner_headers,json={}).status_code,409)
        self.assertEqual(self.client.post(url,headers=self.other_headers,json={}).status_code,404)
        import kpi_api
        with f.db.SessionLocal() as db:self.assertEqual(kpi_api._owned_imaging_studies(db,SimpleNamespace(id=self.owner_id),datetime(2020,1,1),datetime(2030,1,1)),[])


if __name__=='__main__':unittest.main(verbosity=2)

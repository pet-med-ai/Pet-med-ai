"""CW-B15 real JWT, original plan/date/provenance, complete DOCX and read-only proof."""
import copy
import io
import json
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch
from uuid import uuid4
import zipfile
from xml.etree import ElementTree as ET
from sqlalchemy import event
from sqlalchemy.exc import OperationalError

SAMPLES_OUT = os.getenv('PMAI_CWB15_DOC_SAMPLES')
from test_clinical_lab_comparison_documents import ComparisonDocumentFixture, f, storage, doc_text
import clinical_followup_plan_documents as documents
import clinical_docs_api as api

FIXTURE = json.loads((Path(__file__).parent/'fixtures/clinical_followup_plan_documents_cw_b15_cases.json').read_text())
FLAGS = {'FOLLOWUP_PLANS_ENABLED':'1', 'FOLLOWUP_PLANS_SYNTHETIC_ONLY':'1',
         'FOLLOWUP_PLAN_DOCUMENTS_ENABLED':'1', 'FOLLOWUP_PLAN_DOCUMENTS_SYNTHETIC_ONLY':'1'}


class PlanDocumentFixture(ComparisonDocumentFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        f.db.Base.metadata.create_all(f.db.engine, tables=[f.models.FollowUp.__table__])

    def setUp(self):
        super().setUp()
        enabled = patch.dict(os.environ, FLAGS); enabled.start(); self.addCleanup(enabled.stop)
        self.change_case(**FIXTURE['case'])
        self.plan_root = f'/api/cases/{self.cid}/followup-plan'

    def plan_call(self, suffix='', body=None, expected=200):
        r = self.client.request('GET' if body is None else 'POST', self.plan_root+suffix,
                                headers=self.owner_headers, **({'json':body} if body is not None else {}))
        self.assertEqual(r.status_code, expected, r.text)
        return r.json()

    def plan_body(self, operation='create', row=None, data=None):
        listing = self.plan_call()
        b = {'request_id':uuid4().hex, 'operation':operation, 'plan_id':row['id'] if row else None,
             'expected_plan_token':row['token'] if row else '', 'expected_case_token':listing['case_token'],
             'expected_state_token':listing['state_token'], 'reason':'' if operation=='create' else ' 合成更正或撤销\n原文 ',
             'data':None if operation=='withdraw' else copy.deepcopy(data if data is not None else FIXTURE['plan'])}
        return {**b, 'preview_token':self.plan_call('/preview',b)['preview_token'], 'reviewed':True}

    def save_plan(self, operation='create', row=None, data=None):
        return self.plan_call('/confirm',self.plan_body(operation,row,data))['plan']

    @staticmethod
    def choice(row): return {k:row[k] for k in ('id','version','token')}

    def document(self, choice, endpoint='render-preview', snapshot=None, headers=None, **extra):
        return self.client.post('/api/clinical-docs/'+endpoint, headers=self.owner_headers if headers is None else headers,
                                json={'case_id':self.cid,'template_id':'outpatient_record_zh','manual_followup_plan':choice,
                                      **({'expected_content_snapshot':snapshot} if snapshot else {}),**extra})

    def all_business(self):
        with f.db.SessionLocal() as db:
            plans = [{c.key:getattr(row,c.key) for c in row.__table__.columns} for row in db.query(f.models.FollowUp).order_by(f.models.FollowUp.id)]
        return self.business(), plans


class PlanDocumentTests(PlanDocumentFixture):
    def test_literal_selection_and_stable_snapshot_bind_raw_version_account_without_writes(self):
        row = self.save_plan(); choice = self.choice(row); before = self.all_business(); writes=[]
        def capture(_c,_cur,sql,*_):
            if sql.lstrip().split()[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'}: writes.append(sql)
        event.listen(f.db.engine,'before_cursor_execute',capture)
        try:
            with patch.object(storage.Store,'cleanup',side_effect=AssertionError('read must not clean originals')):
                p, raw = self.rendered(choice)
        finally: event.remove(f.db.engine,'before_cursor_execute',capture)
        self.assertEqual(writes,[]); self.assertEqual(self.all_business(),before)
        self.assertEqual(p['manual_followup_plan']['plan'],row)
        self.assertEqual(p['manual_followup_plan']['plan']['data'],FIXTURE['plan'])
        text=doc_text(raw)
        for value in [*FIXTURE['plan']['items'],FIXTURE['plan']['purpose'],FIXTURE['plan']['note'],FIXTURE['plan']['return_conditions'],row['token'],row['reviewed_at'],documents.SCHEMA]:
            self.assertIn(value,text)
        self.assertIn('尚未签署',text); self.assertIn('计划不代表已复查',text)
        f.db.engine.dispose()
        with patch.object(documents.plans,'today',return_value='2030-01-01'), patch.object(api,'_utc_timestamp',return_value='2030-02-01T00:00:00Z'):
            self.assertEqual(self.checked(choice)['content_snapshot'],p['content_snapshot'])

    def test_default_off_no_plan_table_reads_or_inference_for_unselected_document(self):
        row=self.save_plan(); choice=self.choice(row)
        with patch.dict(os.environ,{k:'0' for k in FLAGS}), patch.object(documents.plans,'records',side_effect=AssertionError('unselected must not query plans')):
            for endpoint in ('render-preview','render'):
                r=self.client.post('/api/clinical-docs/'+endpoint,headers=self.owner_headers,json={'case_id':self.cid,'template_id':'outpatient_record_zh'})
                self.assertEqual(r.status_code,200)
                if endpoint=='render-preview':
                    self.assertEqual(r.json()['context']['visit.follow_up'],FIXTURE['expected_no_selection']);self.assertNotIn('manual_followup_plan',r.json())
                else:self.assertIn(FIXTURE['expected_no_selection'],doc_text(r.content));self.assertNotIn('复查计划附节',doc_text(r.content))
        with patch.dict(os.environ,{'CASE_ATTACHMENTS_ENABLED':'0','MANUAL_LAB_RESULTS_ENABLED':'0','LAB_COMPARISON_ENABLED':'0'}):
            self.rendered(choice)

    def test_real_auth_case_isolation_gates_errors_and_deleted_case(self):
        choice=self.choice(self.save_plan());snapshot=self.checked(choice)['content_snapshot']
        for endpoint in ('render-preview','render'):
            self.assertEqual(self.document(choice,endpoint,snapshot,headers={}).status_code,401)
            self.assertEqual(self.document(choice,endpoint,snapshot,headers=self.other_headers).status_code,404)
            for name in FLAGS:
                with patch.dict(os.environ,{name:'0'}):
                    r=self.document(choice,endpoint,snapshot);self.assertEqual(r.status_code,503,name);self.assertEqual(r.headers['cache-control'],'private, no-store')
            for env in ({'ENVIRONMENT':'production'},{'RENDER':'true'}):
                with patch.dict(os.environ,env):self.assertEqual(self.document(choice,endpoint,snapshot).status_code,503)
            with patch.object(documents.plans,'records',side_effect=OperationalError('synthetic',{},Exception('offline'))):
                r=self.document(choice,endpoint,snapshot);self.assertEqual(r.status_code,503);self.assertEqual(r.headers['cache-control'],'private, no-store')
        cid=self.client.post('/api/cases',headers=self.owner_headers,json=FIXTURE['cat_case']).json()['id']
        self.assertEqual(self.document(choice,case_id=cid).status_code,404)
        self.client.delete(f'/api/cases/{self.cid}',headers=self.owner_headers)
        self.assertEqual(self.document(choice).status_code,404)

    def test_strict_selection_no_coercion_null_extra_or_client_originals(self):
        choice=self.choice(self.save_plan())
        variants=[None,[],{},True,'1',{**choice,'data':FIXTURE['plan']},{**choice,'token':'x'*64},
                  {**choice,'token':True},{**choice,'token':'a'*63},{**choice,'version':51}]
        for key in ('id','version'):
            variants += [{**choice,key:v} for v in (True,False,1.0,'1',0,-1,2**53,None)]
        for value in variants:
            r=self.document(value);self.assertEqual(r.status_code,422,str(value));self.assertEqual(r.headers['cache-control'],'private, no-store')
        for template in ('owner_visit_summary_zh','admission_hospitalization_record_bilingual','discharge_summary_bilingual'):
            for value in (choice,None):self.assertEqual(self.document(value,template_id=template).status_code,422)
        self.assertEqual(self.document(choice,include_diagnostic_data=True).status_code,422)
        self.assertEqual(self.document(choice,'render').status_code,409)
        self.assertEqual(self.document(choice,'render','0'*64).status_code,409)

    def test_old_withdrawn_replaced_and_needs_review_are_never_substituted(self):
        first=self.save_plan();old=self.choice(first);snapshot=self.checked(old)['content_snapshot']
        second=self.save_plan('correct',first,FIXTURE['corrected_plan'])
        for endpoint in ('render-preview','render'):self.assertEqual(self.document(old,endpoint,snapshot).status_code,409)
        choice=self.choice(second);snapshot=self.checked(choice)['content_snapshot']
        self.save_plan('withdraw',second);self.save_plan()
        for endpoint in ('render-preview','render'):self.assertEqual(self.document(choice,endpoint,snapshot).status_code,409)
        current=self.plan_call()['plans'][-1];choice=self.choice(current)
        self.change_case(history='病例正文已变化')
        self.assertEqual(self.document(choice).status_code,409)

    def test_corrupt_chain_stays_failure_without_repairs(self):
        row=self.save_plan();choice=self.choice(row)
        with f.db.SessionLocal() as db:original=db.get(f.models.FollowUp,row['id']).note
        meta=json.loads(original)
        for value in ('broken',json.dumps({**meta,'version':2}),json.dumps({**meta,'data':{}}),json.dumps({**meta,'reviewed_by':'2'})):
            with f.db.SessionLocal() as db:db.get(f.models.FollowUp,row['id']).note=value;db.commit()
            before=self.all_business();r=self.document(choice);self.assertEqual(r.status_code,409);self.assertEqual(self.all_business(),before)

    def test_dates_cross_utc_day_month_end_leap_and_past_remain_calendar_literals(self):
        row=None
        for case in FIXTURE['date_cases']:
            row=self.save_plan('correct' if row else 'create',row,{**FIXTURE['short_plan'],'planned_date':case['date']})
            with f.db.SessionLocal() as db:self.assertEqual(db.get(f.models.FollowUp,row['id']).due_date.isoformat(),case['utc'])
            for zone in ('UTC','America/Los_Angeles','Asia/Shanghai'):
                with patch.dict(os.environ,{'TZ':zone}):
                    time.tzset();p,raw=self.rendered(self.choice(row));self.assertEqual(p['manual_followup_plan']['plan']['data']['planned_date'],case['date']);self.assertIn(case['date'],doc_text(raw))
        time.tzset()

    def test_full_snapshot_binds_template_body_selection_and_mixed_sections(self):
        sources,rows=self.save_pair();row=self.save_plan();choice=self.choice(row);snapshot=self.checked(choice)['content_snapshot']
        self.assertEqual(self.document(choice,'render',snapshot,manual_lab_report_ids=[rows[0]['id']]).status_code,409)
        original=api.Path.read_bytes
        def changed(path):
            raw=original(path);return raw+b'changed-template' if str(path).endswith('outpatient_record_zh.docx') else raw
        with patch.object(api.Path,'read_bytes',changed):self.assertEqual(self.document(choice,'render',snapshot).status_code,409)
        self.change_case(owner_name='更正宠主')
        self.assertEqual(self.document(choice,'render',snapshot).status_code,409)

    def test_mixed_transactions_all_subsections_and_sources_bound(self):
        sources,rows=self.save_pair();self.meta={**self.meta,'kind':'dr'};_,_,image=self.save_image()
        row=self.save_plan();choice=self.choice(row)
        combinations=[{'manual_lab_report_ids':[rows[0]['id']]},{'manual_imaging_report_ids':[image['id']]},
                      {'manual_lab_comparison':self.request_body(index=3)},
                      {'manual_lab_comparison':self.request_body(index=3),'manual_lab_report_ids':[rows[0]['id']],'manual_imaging_report_ids':[image['id']]}]
        for extra in combinations:
            before=self.all_business()
            with patch.object(documents.plans,'transaction',side_effect=AssertionError('no nested plan transaction')):
                p,raw=self.rendered(choice,**extra)
            self.assertEqual(p['manual_followup_plan']['plan'],row);self.assertIn(FIXTURE['plan']['purpose'],doc_text(raw));self.assertEqual(self.all_business(),before)
        blob=storage.Store().path(sources[0]['id'],'.blob');blob.write_bytes(b'broken')
        self.assertEqual(self.document(choice,**combinations[-1]).status_code,409)

    def test_four_docx_samples_with_full_long_originals_and_repeating_headers(self):
        row=self.save_plan(data=FIXTURE['short_plan']);samples={'short':self.rendered(self.choice(row))[1]}
        self.change_case(**FIXTURE['cat_case'])
        row=self.save_plan('correct',row,FIXTURE['long_plan']);samples['maximum-length']=self.rendered(self.choice(row))[1]
        row=self.save_plan('correct',row,{**FIXTURE['short_plan'],'planned_date':'2000-02-29'});samples['date-boundary']=self.rendered(self.choice(row))[1]
        _,rows=self.save_pair();self.meta={**self.meta,'kind':'dr'};_,_,image=self.save_image()
        choice=self.choice(row);samples['mixed']=self.rendered(choice,manual_lab_report_ids=[rows[0]['id']],manual_imaging_report_ids=[image['id']],manual_lab_comparison=self.request_body(index=3))[1]
        for title in ('检验结果附节','影像','检验前后对照附节','复查计划附节'):self.assertIn(title,doc_text(samples['mixed']))
        for value in [FIXTURE['long_plan']['purpose'],FIXTURE['long_plan']['note'],FIXTURE['long_plan']['return_conditions'],*FIXTURE['long_plan']['items']]:self.assertIn(value,doc_text(samples['maximum-length']))
        for name,raw in samples.items():
            with zipfile.ZipFile(io.BytesIO(raw)) as z:root=ET.fromstring(z.read('word/document.xml'))
            self.assertEqual(root.find(documents.labs.W+'body')[-1].tag,documents.labs.W+'sectPr')
            self.assertTrue(all(t.find('.//'+documents.labs.W+'tblHeader') is not None for t in root.iter(documents.labs.W+'tbl')))
            if SAMPLES_OUT:
                out=Path(SAMPLES_OUT);out.mkdir(parents=True,exist_ok=True);(out/(name+'.docx')).write_bytes(raw)


if __name__=='__main__':unittest.main(verbosity=2)

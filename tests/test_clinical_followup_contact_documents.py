"""CW-B21 real auth, literal historical facts and complete unsigned DOCX."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
SAMPLES_OUT=os.getenv('PMAI_CWB21_DOC_SAMPLES')
from test_clinical_followup_plan_documents import PlanDocumentFixture, f, storage, doc_text, api
from test_clinical_followup_contacts import ContactFixture, contacts
import clinical_followup_contact_documents as documents

FIXTURE=json.loads((Path(__file__).parent/'fixtures/clinical_followup_contact_documents_cw_b21_cases.json').read_text())
FLAGS={k:'1' for k in ('FOLLOWUP_CONTACTS_ENABLED','FOLLOWUP_CONTACTS_SYNTHETIC_ONLY','FOLLOWUP_CONTACT_DOCUMENTS_ENABLED','FOLLOWUP_CONTACT_DOCUMENTS_SYNTHETIC_ONLY')}

class ContactDocumentFixture(PlanDocumentFixture):
    contact=ContactFixture.contact
    contact_body=ContactFixture.contact_body
    contact_review=ContactFixture.contact_review
    contact_save=ContactFixture.contact_save
    def setUp(self):
        super().setUp()
        flags=patch.dict(os.environ,FLAGS);flags.start();self.addCleanup(flags.stop)
        self.change_case(**FIXTURE['case']);self.source=self.save_plan(data=FIXTURE['plan'])
        self.contact_root=f'/api/cases/{self.cid}/followup-contacts'
    def choice(self,row):
        value=self.contact();source=next(p for p in value['plans'] if p['id']==row['source']['id'])
        return {**{k:row[k] for k in ('id','version','token')},'source_token':source['token'],'case_token':value['case_token']}
    def document(self,choice,endpoint='render-preview',snapshot=None,headers=None,**extra):
        return self.client.post('/api/clinical-docs/'+endpoint,headers=self.owner_headers if headers is None else headers,
            json={'case_id':self.cid,'template_id':'outpatient_record_zh','manual_followup_contact':choice,
                  **({'expected_content_snapshot':snapshot} if snapshot else {}),**extra})
    def all_business(self):
        with f.db.SessionLocal() as db:
            audits=[{c.name:str(getattr(r,'extra_data' if c.name=='metadata' else c.key)) for c in f.models.AuditLog.__table__.columns} for r in db.query(f.models.AuditLog).order_by(f.models.AuditLog.log_id)]
        return super().all_business(),audits

class ContactDocumentTests(ContactDocumentFixture):
    def test_exact_fact_source_and_audit_digest_export_without_writes_or_cleanup(self):
        row=self.contact_save(data=FIXTURE['contact']);choice=self.choice(row);before=self.all_business();writes=[]
        def capture(_c,_cur,sql,*_):
            if sql.lstrip().split()[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'}:writes.append(sql)
        event.listen(f.db.engine,'before_cursor_execute',capture)
        try:
            with patch.object(storage.Store,'cleanup',side_effect=AssertionError('No cleanup')):
                preview,raw=self.rendered(choice)
        finally:event.remove(f.db.engine,'before_cursor_execute',capture)
        self.assertEqual(writes,[]);self.assertEqual(before,self.all_business())
        self.assertEqual(preview['manual_followup_contact']['record'],row)
        self.assertRegex(preview['manual_followup_contact']['audit_token'],r'^[a-f0-9]{64}$')
        text=doc_text(raw)
        for value in [row['data']['occurred_at'],row['data']['note'],row['data']['next_action'],'电话','未取得联系',*row['source']['data']['items'],row['source']['data']['purpose'],row['token'],row['recorded_at'],documents.SCHEMA]:
            self.assertIn(value,text)
        self.assertIn('历史原文',text);self.assertIn('不自动作为本次文书的当前复查安排',text)
        self.assertEqual(preview['context']['visit.follow_up'],FIXTURE['expected_no_selection'])
        f.db.engine.dispose();self.assertEqual(self.checked(choice)['content_snapshot'],preview['content_snapshot'])
        for method,method_label,outcome,outcome_label in [('phone','电话','reached','已取得联系'),('wechat','微信','not_reached','未取得联系'),('in_person','当面','declined','对方拒绝沟通'),('other','其他','other','其他')]:
            record=self.contact_save(data={**FIXTURE['contact'],'method':method,'outcome':outcome})
            _,raw=self.rendered(self.choice(record));self.assertIn('联系方式：'+method_label+'；实际结果：'+outcome_label,doc_text(raw))

    def test_all_gates_real_auth_and_case_access(self):
        choice=self.choice(self.contact_save());snap=self.checked(choice)['content_snapshot']
        for endpoint in ('render-preview','render'):
            self.assertEqual(self.document(choice,endpoint,snap,headers={}).status_code,401)
            self.assertEqual(self.document(choice,endpoint,snap,headers=self.other_headers).status_code,404)
            for flag in [*FLAGS,'FOLLOWUP_PLANS_ENABLED','FOLLOWUP_PLANS_SYNTHETIC_ONLY']:
                with patch.dict(os.environ,{flag:'0'}):
                    r=self.document(choice,endpoint,snap);self.assertEqual(r.status_code,503);self.assertEqual(r.headers['cache-control'],'private, no-store')
            for env in ({'ENVIRONMENT':'production'},{'RENDER':'true'}):
                with patch.dict(os.environ,env):self.assertEqual(self.document(choice,endpoint,snap).status_code,503)
        self.assertEqual(self.document(choice,case_id=999999).status_code,404)
        self.client.delete(f'/api/cases/{self.cid}',headers=self.owner_headers)
        self.assertEqual(self.document(choice).status_code,404)

    def test_strict_selection_template_and_snapshot_preconditions(self):
        choice=self.choice(self.contact_save())
        variants=[None,False,[],{},'1',{**choice,'original':'client forged'}, {k:v for k,v in choice.items() if k!='case_token'}]
        for k in ('id','version'):variants.extend({**choice,k:v} for v in (True,False,0,-1,'1',1.0,None,2**53))
        for k in ('token','source_token','case_token'):variants.extend({**choice,k:v} for v in (True,None,'a'*63,'A'*64,'x'*64))
        variants.append({**choice,'version':51})
        for value in variants:
            with self.subTest(value=value):self.assertEqual(self.document(value).status_code,422)
        for template in ('owner_visit_summary_zh','admission_hospitalization_record_bilingual','discharge_summary_bilingual'):
            for value in (choice,None):self.assertEqual(self.document(value,template_id=template).status_code,422)
        self.assertEqual(self.document(choice,include_diagnostic_data=True).status_code,422)
        self.assertEqual(self.document(choice,'render').status_code,409)
        self.assertEqual(self.document(choice,'render','0'*64).status_code,409)
        for key in ('token','source_token','case_token'):
            self.assertEqual(self.document({**choice,key:'0'*64}).status_code,409)

    def test_current_version_only_no_implicit_substitution(self):
        first=self.contact_save();old=self.choice(first);snapshot=self.checked(old)['content_snapshot']
        second=self.contact_save('correct',first,FIXTURE['corrected']);self.contact_save()
        self.assertEqual(self.document(old).status_code,409)
        current=self.choice(second);self.checked(current);self.contact_save('withdraw',second)
        self.assertEqual(self.document(current,'render',snapshot).status_code,409)
        self.assertEqual(self.document({**current,'id':999999}).status_code,404)

    def test_history_survives_plan_correction_withdrawal_and_case_change_explicitly(self):
        row=self.contact_save(data=FIXTURE['contact']);old=self.choice(row);p=self.checked(old)
        self.change_case(owner_name='CW21 当前更正宠主',history='CW21 当前病史')
        self.assertEqual(self.document(old).status_code,409)
        preview,raw=self.rendered(self.choice(row));self.assertEqual(preview['manual_followup_contact']['record']['source_state'],'needs_review')
        self.assertIn('CW21 当前更正宠主',doc_text(raw));self.assertIn(row['case_snapshot']['owner_name'],doc_text(raw))
        self.save_plan('correct',self.source,FIXTURE['corrected_plan'])
        self.assertEqual(self.document(self.choice(row),'render',p['content_snapshot']).status_code,409)
        preview,raw=self.rendered(self.choice(row));self.assertEqual(preview['manual_followup_contact']['record']['source_state'],'superseded')
        self.assertEqual(preview['manual_followup_contact']['record']['source'],row['source']);self.assertIn('来源计划已更正',doc_text(raw))
        latest=self.plan_call()['plans'][-1];self.source=latest;other=self.contact_save();self.save_plan('withdraw',latest)
        preview,raw=self.rendered(self.choice(other));self.assertEqual(preview['manual_followup_contact']['record']['source_state'],'withdrawn');self.assertIn('来源计划已撤销',doc_text(raw))

    def test_full_snapshot_binds_template_audit_and_other_sections(self):
        sources,rows=self.save_pair();row=self.contact_save();choice=self.choice(row);p=self.checked(choice)
        self.assertEqual(self.document(choice,'render',p['content_snapshot'],manual_lab_report_ids=[rows[0]['id']]).status_code,409)
        original=api.Path.read_bytes
        def changed(path):
            raw=original(path);return raw+b'changed' if str(path).endswith('outpatient_record_zh.docx') else raw
        with patch.object(api.Path,'read_bytes',changed):self.assertEqual(self.document(choice,'render',p['content_snapshot']).status_code,409)
        with f.db.SessionLocal() as db:
            audit=db.query(f.models.AuditLog).filter_by(case_id=self.cid,source=contacts.SOURCE).first();audit.extra_data={**audit.extra_data,'fingerprint':'0'*64};db.commit()
        self.assertEqual(self.document(choice,'render',p['content_snapshot']).status_code,409)
        self.rendered(choice)

    def test_corrupt_chain_source_and_audit_fail_without_repair(self):
        row=self.contact_save();choice=self.choice(row)
        with f.db.SessionLocal() as db:old=db.get(f.models.FollowUp,row['id']).note
        for value in ('broken',json.dumps({**json.loads(old),'version':2})):
            with f.db.SessionLocal() as db:db.get(f.models.FollowUp,row['id']).note=value;db.commit()
            before=self.all_business();self.assertEqual(self.document(choice).status_code,409);self.assertEqual(self.all_business(),before)
        with f.db.SessionLocal() as db:
            db.get(f.models.FollowUp,row['id']).note=old;audit=db.query(f.models.AuditLog).filter_by(case_id=self.cid,source=contacts.SOURCE).first();db.delete(audit);db.commit()
        self.assertEqual(self.document(choice).status_code,409)
        with patch.object(contacts,'records',side_effect=OperationalError('synthetic',{},Exception('unavailable'))):
            r=self.document(choice);self.assertEqual(r.status_code,503);self.assertEqual(r.headers['cache-control'],'private, no-store')

    def test_complete_50_versions_and_cap_plus_one(self):
        row=None
        for i in range(50):row=self.contact_save('correct' if row else 'create',row,{**FIXTURE['contact'],'note':f'合成联系版本{i+1}'})
        self.rendered(self.choice(row))
        with f.db.SessionLocal() as db:
            db.add(f.models.FollowUp(case_id=self.cid,due_date=documents.plans.due_date(FIXTURE['plan']['planned_date']),status=contacts.RECORDED,channel=contacts.SOURCE,note='broken'))
            db.commit()
        self.assertEqual(self.document({'id':row['id'],'version':row['version'],'token':row['token'],'source_token':'a'*64,'case_token':'a'*64}).status_code,409)

    def test_mixed_sources_one_transaction_and_four_docx_samples(self):
        row=self.contact_save(data=FIXTURE['contact']);samples={'short':self.rendered(self.choice(row))[1]}
        self.change_case(**FIXTURE['cat_case']);row=self.contact_save('correct',row,FIXTURE['long_contact']);samples['maximum-length']=self.rendered(self.choice(row))[1]
        self.source=self.save_plan('correct',self.source,FIXTURE['short_plan']);row=self.contact_save(data={**FIXTURE['contact'],'occurred_at':'2000-02-29T00:01+08:00'})
        self.save_plan('withdraw',self.source);samples['historical-source-date']=self.rendered(self.choice(row))[1]
        self.source=self.save_plan(data=FIXTURE['short_plan']);sources,rows=self.save_pair();self.meta={**self.meta,'kind':'dr'};_,_,image=self.save_image()
        row=self.contact_save();extra={'manual_lab_report_ids':[rows[0]['id']],'manual_imaging_report_ids':[image['id']],'manual_lab_comparison':self.request_body(index=3),'manual_followup_plan':PlanDocumentFixture.choice(self.source)}
        choice=self.choice(row)
        with patch.object(documents.plans,'transaction',side_effect=AssertionError('No nested case session')):
            samples['complete-mixed']=self.rendered(choice,**extra)[1]
        for name,raw in samples.items():
            text=doc_text(raw);self.assertIn('人工随访记录附节',text);self.assertIn('尚未签署',text)
        self.assertIn(FIXTURE['long_contact']['note'],doc_text(samples['maximum-length']))
        self.assertIn(FIXTURE['long_contact']['next_action'],doc_text(samples['maximum-length']))
        self.assertIn('2000-02-29T00:01+08:00',doc_text(samples['historical-source-date']))
        out=SAMPLES_OUT
        if out:
            Path(out).mkdir(parents=True,exist_ok=True)
            for name,raw in samples.items():(Path(out)/(name+'.docx')).write_bytes(raw)

if __name__=='__main__':unittest.main(verbosity=2)

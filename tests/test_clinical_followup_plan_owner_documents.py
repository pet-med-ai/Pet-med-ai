"""CW-B16: real authenticated owner documents, template isolation and literal bytes."""
import copy
import io
import json
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch
import zipfile
from xml.etree import ElementTree as ET
from sqlalchemy import event
from sqlalchemy.exc import OperationalError

SAMPLES_OUT = os.getenv('PMAI_CWB16_DOC_SAMPLES')
from test_clinical_followup_plan_documents import PlanDocumentFixture, FLAGS, f, documents, api, storage, doc_text

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/clinical_followup_plan_owner_documents_cw_b16_cases.json').read_text())
OWNER_FLAGS = {'FOLLOWUP_PLAN_OWNER_DOCUMENTS_ENABLED':'1', 'FOLLOWUP_PLAN_OWNER_DOCUMENTS_SYNTHETIC_ONLY':'1'}
OWNER = FIXTURE['owner_template']
DOCTOR = FIXTURE['doctor_template']


class OwnerPlanDocumentFixture(PlanDocumentFixture):
    def setUp(self):
        super().setUp()
        enabled = patch.dict(os.environ, OWNER_FLAGS); enabled.start(); self.addCleanup(enabled.stop)
        self.change_case(**FIXTURE['case'])

    def plan_body(self, operation='create', row=None, data=None):
        return super().plan_body(operation, row, data if data is not None else FIXTURE['plan'])

    def document(self, choice, endpoint='render-preview', snapshot=None, headers=None, **extra):
        return super().document(choice, endpoint, snapshot, headers, **{'template_id':OWNER, **extra})

    def mixed(self):
        sources, rows = self.save_pair()
        self.meta = {**self.meta, 'kind':'dr'}; _, _, image = self.save_image()
        return sources, rows, image, {'manual_lab_report_ids':[rows[0]['id']], 'manual_imaging_report_ids':[image['id']]}


class OwnerPlanDocumentTests(OwnerPlanDocumentFixture):
    def test_originals_provenance_and_stable_template_bound_snapshot_without_writes(self):
        row = self.save_plan(); choice = self.choice(row); before = self.all_business(); writes = []
        def capture(_c, _cur, sql, *_):
            if sql.lstrip().split()[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'}: writes.append(sql)
        event.listen(f.db.engine, 'before_cursor_execute', capture)
        try:
            with patch.object(storage.Store, 'cleanup', side_effect=AssertionError('No cleanup on document reads')):
                p, raw = self.rendered(choice)
        finally: event.remove(f.db.engine, 'before_cursor_execute', capture)
        self.assertEqual(writes, []); self.assertEqual(self.all_business(), before)
        self.assertEqual(p['template_id'], OWNER); self.assertEqual(p['manual_followup_plan']['plan'], row)
        text = doc_text(raw)
        for literal in [*FIXTURE['plan']['items'], FIXTURE['plan']['purpose'], FIXTURE['plan']['return_conditions'],
                        FIXTURE['plan']['note'], row['token'], row['reviewed_at'], row['reviewed_by'], documents.SCHEMA]:
            self.assertIn(literal, text)
        self.assertIn('宠主', text); self.assertIn('尚未签署', text); self.assertIn('计划不代表已复查', text)
        self.assertNotIn(FIXTURE['expected_forbidden_section'], text)
        f.db.engine.dispose()
        with patch.object(documents.plans, 'today', return_value='2030-01-01'), patch.object(api, '_utc_timestamp', return_value='2030-02-01T00:00:00Z'):
            self.assertEqual(self.checked(choice)['content_snapshot'], p['content_snapshot'])

    def test_unselected_defaults_neutral_and_never_reads_plan_table_with_flags_off(self):
        self.save_plan()
        with patch.dict(os.environ, {k:'0' for k in {**FLAGS, **OWNER_FLAGS}}), patch.object(documents.plans, 'records', side_effect=AssertionError('No implicit plan read')):
            for template in (OWNER, DOCTOR):
                body = {'case_id':self.cid, 'template_id':template}
                p = self.client.post('/api/clinical-docs/render-preview', headers=self.owner_headers, json=body)
                self.assertEqual(p.status_code, 200); p = p.json()
                self.assertEqual(p['context']['visit.follow_up'], FIXTURE['expected_no_selection']); self.assertNotIn('manual_followup_plan', p)
                r = self.client.post('/api/clinical-docs/render', headers=self.owner_headers, json={**body, 'expected_content_snapshot':p['content_snapshot']})
                self.assertEqual(r.status_code, 200); self.assertIn(FIXTURE['expected_no_selection'], doc_text(r.content))
                self.assertNotIn('复查计划附节', doc_text(r.content))

    def test_owner_flags_independent_and_all_parent_gates_enforced(self):
        choice = self.choice(self.save_plan()); snapshot = self.checked(choice)['content_snapshot']
        for endpoint in ('render-preview','render'):
            for name in OWNER_FLAGS:
                with patch.dict(os.environ, {name:'0'}):
                    r = self.document(choice, endpoint, snapshot)
                    self.assertEqual(r.status_code, 503); self.assertEqual(r.json()['detail'], 'followup_plan_owner_documents_disabled')
                    self.assertEqual(r.headers['cache-control'], 'private, no-store')
                    self.rendered(choice, template_id=DOCTOR)
            for name in FLAGS:
                with patch.dict(os.environ, {name:'0'}): self.assertEqual(self.document(choice, endpoint, snapshot).status_code, 503)
            for env in ({'ENVIRONMENT':'production'}, {'RENDER':'true'}):
                with patch.dict(os.environ, env): self.assertEqual(self.document(choice, endpoint, snapshot).status_code, 503)
        with patch.dict(os.environ, {'CASE_ATTACHMENTS_ENABLED':'0','MANUAL_LAB_RESULTS_ENABLED':'0','LAB_COMPARISON_ENABLED':'0'}): self.rendered(choice)

    def test_real_auth_ownership_deleted_case_and_read_failure(self):
        choice = self.choice(self.save_plan()); snapshot = self.checked(choice)['content_snapshot']
        for endpoint in ('render-preview','render'):
            self.assertEqual(self.document(choice, endpoint, snapshot, headers={}).status_code, 401)
            self.assertEqual(self.document(choice, endpoint, snapshot, headers=self.other_headers).status_code, 404)
            with patch.object(documents.plans, 'records', side_effect=OperationalError('synthetic', {}, Exception('offline'))):
                r = self.document(choice, endpoint, snapshot); self.assertEqual(r.status_code, 503)
                self.assertEqual(r.headers['cache-control'], 'private, no-store')
        cid = self.client.post('/api/cases', headers=self.owner_headers, json=FIXTURE['cat_case']).json()['id']
        self.assertEqual(self.document(choice, case_id=cid).status_code, 404)
        self.assertEqual(self.client.delete(f'/api/cases/{self.cid}', headers=self.owner_headers).status_code, 204)
        self.assertEqual(self.document(choice).status_code, 404)

    def test_malformed_plan_choices_and_other_templates_are_rejected(self):
        choice = self.choice(self.save_plan())
        variants = [None, [], {}, True, '1', {**choice,'data':FIXTURE['plan']}, {**choice,'token':'x'*64}, {**choice,'version':51}]
        for key in ('id','version'):
            variants += [{**choice,key:value} for value in (True,False,1.0,'1',0,-1,2**53,None)]
        for endpoint in ('render-preview','render'):
            for value in variants:
                r = self.document(value, endpoint, '0'*64); self.assertEqual(r.status_code, 422, str(value))
                self.assertEqual(r.headers['cache-control'], 'private, no-store')
            for template in ('admission_hospitalization_record_bilingual','discharge_summary_bilingual'):
                self.assertEqual(self.document(choice, endpoint, '0'*64, template_id=template).status_code, 422)
            self.assertEqual(self.document(choice, endpoint, '0'*64, include_diagnostic_data=True).status_code, 422)
        self.assertEqual(self.document(choice, 'render').status_code, 409)

    def test_comparison_never_bypasses_owner_restriction_with_or_without_plan(self):
        _, rows = self.save_pair(); choice = self.choice(self.save_plan())
        comparison = self.request_body(index=3)
        for endpoint in ('render-preview','render'):
            for value in (None, {}, comparison):
                for include_plan in (False, True):
                    body = {'case_id':self.cid,'template_id':OWNER,'manual_lab_comparison':value,'expected_content_snapshot':'0'*64}
                    if include_plan: body['manual_followup_plan'] = choice
                    with patch.object(documents, 'snapshot', side_effect=AssertionError('Reject before transaction')):
                        r = self.client.post('/api/clinical-docs/'+endpoint, headers=self.owner_headers, json=body)
                    self.assertEqual(r.status_code, 422)
        # The same valid pair remains allowed in the clinician document.
        self.rendered(choice, template_id=DOCTOR, manual_lab_comparison=comparison, manual_lab_report_ids=[rows[0]['id']])

    def test_template_snapshot_swap_changed_asset_and_changed_selections(self):
        _, _, _, extra = self.mixed(); choice = self.choice(self.save_plan())
        owner = self.checked(choice); doctor = self.checked(choice, template_id=DOCTOR)
        self.assertNotEqual(owner['content_snapshot'], doctor['content_snapshot'])
        self.assertEqual(self.document(choice,'render',doctor['content_snapshot']).status_code,409)
        self.assertEqual(self.document(choice,'render',owner['content_snapshot'],template_id=DOCTOR).status_code,409)
        self.assertEqual(self.document(choice,'render',owner['content_snapshot'],**extra).status_code,409)
        original = api.Path.read_bytes
        def changed(path):
            raw = original(path)
            return raw+b'changed-template' if str(path).endswith('owner_visit_summary_zh.docx') else raw
        with patch.object(api.Path,'read_bytes',side_effect=changed): self.assertEqual(self.document(choice,'render',owner['content_snapshot']).status_code,409)
        self.change_case(history='CW-B16 changed saved body')
        self.assertEqual(self.document(choice,'render',owner['content_snapshot']).status_code,409)

    def test_old_withdrawn_replaced_needs_review_and_corrupt_chain_are_not_substituted(self):
        first=self.save_plan(); choice=self.choice(first); snapshot=self.checked(choice)['content_snapshot']
        current=self.save_plan('correct',first,FIXTURE['corrected_plan'])
        self.assertEqual(self.document(choice,'render',snapshot).status_code,409)
        choice=self.choice(current); snapshot=self.checked(choice)['content_snapshot']; self.save_plan('withdraw',current)
        current=self.save_plan(); self.assertEqual(self.document(choice,'render',snapshot).status_code,409)
        choice=self.choice(current)
        with f.db.SessionLocal() as db: original=db.get(f.models.FollowUp,current['id']).note
        meta=json.loads(original)
        for bad in ('broken',json.dumps({**meta,'version':2}),json.dumps({**meta,'data':{}}),json.dumps({**meta,'reviewed_by':'2'})):
            with f.db.SessionLocal() as db: db.get(f.models.FollowUp,current['id']).note=bad; db.commit()
            before=self.all_business(); self.assertEqual(self.document(choice).status_code,409); self.assertEqual(self.all_business(),before)
        with f.db.SessionLocal() as db: db.get(f.models.FollowUp,current['id']).note=original; db.commit()
        self.change_case(history='CW-B16 requires plan review'); self.assertEqual(self.document(choice).status_code,409)

    def test_calendar_dates_are_unchanged_across_server_timezones(self):
        row=None
        for case in FIXTURE['date_cases']:
            row=self.save_plan('correct' if row else 'create',row,{**FIXTURE['short_plan'],'planned_date':case['date']})
            with f.db.SessionLocal() as db: self.assertEqual(db.get(f.models.FollowUp,row['id']).due_date.isoformat(),case['utc'])
            for zone in ('UTC','Asia/Shanghai','America/Los_Angeles'):
                try:
                    with patch.dict(os.environ,{'TZ':zone}):
                        time.tzset(); p,raw=self.rendered(self.choice(row))
                        self.assertEqual(p['manual_followup_plan']['plan']['data']['planned_date'],case['date']); self.assertIn(case['date'],doc_text(raw))
                finally: time.tzset()

    def test_mixed_lab_and_imaging_use_one_transaction_and_all_sources_are_bound(self):
        sources,rows,image,extra=self.mixed(); choice=self.choice(self.save_plan())
        combinations=[{'manual_lab_report_ids':extra['manual_lab_report_ids']},{'manual_imaging_report_ids':extra['manual_imaging_report_ids']},extra]
        for selected in combinations:
            before=self.all_business()
            with patch.object(documents.plans,'transaction',side_effect=AssertionError('No nested case transaction')):
                p,raw=self.rendered(choice,**selected)
            self.assertEqual(self.all_business(),before); self.assertNotIn('manual_lab_comparison',p)
            self.assertNotIn(FIXTURE['expected_forbidden_section'],doc_text(raw)); self.assertIn(FIXTURE['plan']['purpose'],doc_text(raw))
        storage.Store().path(sources[0]['id'],'.blob').write_bytes(b'broken')
        self.assertEqual(self.document(choice,**extra).status_code,409)

    def test_four_docx_samples_full_originals_and_repeating_table_headers(self):
        row=self.save_plan(data=FIXTURE['short_plan']); samples={'short':self.rendered(self.choice(row))[1]}
        self.change_case(**FIXTURE['cat_case'])
        row=self.save_plan('correct',row,FIXTURE['long_plan']); samples['maximum-length']=self.rendered(self.choice(row))[1]
        row=self.save_plan('correct',row,{**FIXTURE['short_plan'],'planned_date':'2000-02-29'}); samples['date-boundary']=self.rendered(self.choice(row))[1]
        _,_,_,extra=self.mixed(); samples['mixed']=self.rendered(self.choice(row),**extra)[1]
        for title in ('检验结果附节','影像','复查计划附节'): self.assertIn(title,doc_text(samples['mixed']))
        for literal in [FIXTURE['long_plan']['purpose'],FIXTURE['long_plan']['note'],FIXTURE['long_plan']['return_conditions'],*FIXTURE['long_plan']['items']]: self.assertIn(literal,doc_text(samples['maximum-length']))
        for name,raw in samples.items():
            self.assertNotIn(FIXTURE['expected_forbidden_section'],doc_text(raw))
            with zipfile.ZipFile(io.BytesIO(raw)) as z: root=ET.fromstring(z.read('word/document.xml'))
            self.assertEqual(root.find(documents.labs.W+'body')[-1].tag,documents.labs.W+'sectPr')
            self.assertTrue(all(t.find('.//'+documents.labs.W+'tblHeader') is not None for t in root.iter(documents.labs.W+'tbl')))
            if SAMPLES_OUT:
                out=Path(SAMPLES_OUT); out.mkdir(parents=True,exist_ok=True); (out/(name+'.docx')).write_bytes(raw)


if __name__=='__main__': unittest.main(verbosity=2)

"""Independent old KPI, inventory, queue, complete document and namespace controls."""
from datetime import datetime
import os
import unittest
from unittest.mock import patch
from test_clinical_followup_plan_overview import PlanOverviewFixture, f
from test_clinical_followup_contacts import ContactFixture,contacts,FIXTURE
from test_clinical_lab_comparison_documents import doc_text


class ContactIsolation(PlanOverviewFixture):
    contact=ContactFixture.contact
    contact_body=ContactFixture.contact_body
    contact_review=ContactFixture.contact_review
    contact_save=ContactFixture.contact_save

    def setUp(self):
        super().setUp()
        flags=patch.dict(os.environ,FOLLOWUP_CONTACTS_ENABLED='1',FOLLOWUP_CONTACTS_SYNTHETIC_ONLY='1',
            FOLLOWUP_PLAN_QUEUE_ENABLED='1',FOLLOWUP_PLAN_QUEUE_SYNTHETIC_ONLY='1',
            FOLLOWUP_PLAN_OWNER_DOCUMENTS_ENABLED='1',FOLLOWUP_PLAN_OWNER_DOCUMENTS_SYNTHETIC_ONLY='1')
        flags.start();self.addCleanup(flags.stop)
        self.source=self.save_plan(data=FIXTURE['plan']);self.contact_root=f'/api/cases/{self.cid}/followup-contacts'
        with f.db.SessionLocal() as db:
            for i,done in enumerate([datetime(2024,2,29,12),datetime(2024,3,2),None]):
                db.add(f.models.FollowUp(case_id=self.cid,due_date=datetime(2024,2,29),done_at=done,status='legacy-'+str(i),channel='phone',note='合成旧自由文本'))
            db.commit()

    def snapshots(self):
        def get(url,**kw):
            r=self.client.get(url,headers=self.owner_headers,**kw);self.assertEqual(r.status_code,200,r.text)
            data=r.json();data.pop('read_at',None);return data
        result={'plans':self.plan_call(),'overview':get(self.overview_url,params={'include_followup_plan':'true'}),
                'queue':get('/api/followup-plan-queue',params={'range':'all'}),
                'kpi':get('/api/kpi/followups?start=2024-02-01&end=2024-03-31'),
                'case':get(f'/api/cases/{self.cid}')}
        with patch('clinical_docs_api._utc_timestamp',return_value='2026-10-09T03:00:00Z'):
            for template in ['outpatient_record_zh','owner_visit_summary_zh']:
                p=self.document(self.choice(self.source),template_id=template);self.assertEqual(p.status_code,200,p.text)
                d=p.json();raw=self.document(self.choice(self.source),'render',d['content_snapshot'],template_id=template)
                self.assertEqual(raw.status_code,200,raw.text[:200] if raw.status_code!=200 else '')
                result[template]={'snapshot':d['content_snapshot'],'context':d['context'],'text':doc_text(raw.content)}
        return result

    def test_all_contact_states_and_broken_namespace_leave_old_payloads_exact(self):
        for species in ['dog','cat']:
            if species=='cat':
                self.change_case(species='cat',patient_name='CW-B19 合成猫')
                self.source=self.save_plan('correct',self.source,FIXTURE['plan'])
            before=self.snapshots();metric=before['kpi']['metrics']['followup_compliance']
            self.assertEqual(metric['due_total'],3);self.assertEqual(metric['done_within_due_plus_minus_1_day'],1)
            row=self.contact_save();self.assertEqual(self.snapshots(),before)
            row=self.contact_save('correct',row,FIXTURE['corrected']);self.assertEqual(self.snapshots(),before)
            self.contact_save('withdraw',row);self.assertEqual(self.snapshots(),before)
        with f.db.SessionLocal() as db:
            for status,channel in [('cw-b19-broken',''),('corrupt',contacts.SOURCE),('cw-b19-',None)]:
                db.add(f.models.FollowUp(case_id=self.cid,due_date=datetime(2024,2,29),done_at=datetime(2024,2,29),status=status,channel=channel,note='broken'))
            db.commit()
        self.contact(expected=409);self.assertEqual(self.snapshots(),before)


if __name__=='__main__':unittest.main(verbosity=2)

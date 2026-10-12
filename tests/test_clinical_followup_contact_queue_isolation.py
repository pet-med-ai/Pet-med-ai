"""Compare the frozen CW-B22 validator and complete historical payloads around new GETs."""
import ast
import copy
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
FROZEN = subprocess.check_output(['git','show','21a2afaa100807842dd42a4967e24b771e362d12:backend/clinical_followup_contacts.py'],cwd=Path(__file__).resolve().parents[1],text=True)
from test_clinical_followup_contact_isolation import ContactIsolation
from test_clinical_followup_contact_queue import ContactQueueFixture, f, contacts, service


class QueueIsolation(ContactIsolation):
    all_business=ContactQueueFixture.all_business

    def test_historical_payloads_docs_kpi_and_audits_unchanged(self):
        with patch.dict(os.environ,FOLLOWUP_CONTACT_QUEUE_ENABLED='1',FOLLOWUP_CONTACT_QUEUE_SYNTHETIC_ONLY='1',
                        FOLLOWUP_CONTACT_OVERVIEW_ENABLED='1',FOLLOWUP_CONTACT_OVERVIEW_SYNTHETIC_ONLY='1'):
            for species in ('dog','cat'):
                if species=='cat':
                    self.change_case(species='cat');self.source=self.save_plan('correct',self.source)
                row=self.contact_save()
                for action in ('read','correct','withdraw'):
                    if action!='read':row=self.contact_save(action,row)
                    original=self.snapshots();saved=self.contact();business=self.all_business()
                    overview=self.client.get(self.overview_url,headers=self.owner_headers,params={'include_followup_plan':'true','include_followup_contacts':'true'}).json();overview.pop('read_at')
                    for state in ('all','current','historical_only','none'):
                        r=self.client.get('/api/followup-plan-queue',headers=self.owner_headers,params={'range':'all','include_followup_contacts':'true','contact_state':state})
                        self.assertEqual(r.status_code,200,r.text)
                    self.assertEqual(self.snapshots(),original);self.assertEqual(self.contact(),saved);self.assertEqual(self.all_business(),business)
                    again=self.client.get(self.overview_url,headers=self.owner_headers,params={'include_followup_plan':'true','include_followup_contacts':'true'}).json();again.pop('read_at');self.assertEqual(again,overview)


    def test_frozen_validator_and_pure_extraction_agree_for_valid_and_corrupt_inputs(self):
        old=FROZEN
        function=next(n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef) and n.name=='records')
        scope=dict(contacts.__dict__);exec(compile(ast.Module(body=[function],type_ignores=[]),'<frozen CW-B22 records>','exec'),scope)
        row=self.contact_save();self.contact_save('correct',row)
        with f.db.SessionLocal() as db:
            case=db.get(f.models.Case,self.cid);sources=contacts.plans.listing_data(db,case)['plans']
            rows=db.query(f.models.FollowUp).filter(contacts.namespace(f.models.FollowUp.status,f.models.FollowUp.channel),f.models.FollowUp.case_id==self.cid).order_by(f.models.FollowUp.id).all()
            audits=db.query(f.models.AuditLog).filter_by(case_id=self.cid,source=contacts.SOURCE).order_by(f.models.AuditLog.log_id).all()
            def outcome(fn):
                try:return [(r.id,m) for r,m in fn()]
                except contacts.Error as exc:return (exc.code,exc.status)
            def compare():
                expected=outcome(lambda:scope['records'](db,case,sources))
                with patch.object(service,'prefetched_contacts',side_effect=AssertionError('pure')),patch.object(contacts.plans,'SessionLocal',side_effect=AssertionError('pure')):
                    self.assertEqual(outcome(lambda:contacts.validated_records(rows,audits,case,sources)),expected)
            compare();original=rows[-1].note;meta=json.loads(original)
            for changes in ({'schema':'bad'},{'root_id':999999},{'version':7},{'withdrawal':{}},{'recorded_by':'other'},
                            {'data':{**meta['data'],'outcome':'complete'}},{'source':{**meta['source'],'id':999999}}):
                rows[-1].note=json.dumps({**meta,**changes});compare()
            rows[-1].note=original
            for changes in ({'operation':'bad'},{'content_hash':'b'*64},{'record_id':999999}):
                original_audit=copy.deepcopy(audits[0].extra_data);audits[0].extra_data={**original_audit,**changes};compare();audits[0].extra_data=original_audit
            # Extra guards required only because the new caller can pass prefetched groups.
            audits[0].case_id=999999
            with self.assertRaises(contacts.Error):contacts.validated_records(rows,audits,case,sources)
            db.rollback()


if __name__=='__main__':
    suite=unittest.TestSuite([QueueIsolation('test_historical_payloads_docs_kpi_and_audits_unchanged'),QueueIsolation('test_frozen_validator_and_pure_extraction_agree_for_valid_and_corrupt_inputs')])
    result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(not result.wasSuccessful())

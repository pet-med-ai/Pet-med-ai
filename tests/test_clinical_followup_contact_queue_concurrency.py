"""Independent WAL writer commits between each bulk read; never a mixed snapshot."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Event
import unittest
from unittest.mock import patch
from sqlalchemy import text
from test_clinical_followup_contact_queue import ContactQueueFixture, FIXTURE, f, contacts, queue, service

ACTIONS=('create','correct','withdraw','plan_correct','plan_withdraw','body','identity','owner','delete','audit','bad_audit','missing_audit')


class ContactQueueConcurrency(ContactQueueFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with f.db.engine.connect() as conn:conn.execute(text('PRAGMA journal_mode=WAL'))

    def race(self, action, stage):
        row=self.contact_save();self.seed_plan(self.add_case())
        before=self.get_queue({'page_size':'1'})
        def mutate():
            if action=='create':self.contact_save()
            elif action in ('correct','withdraw'):self.contact_save(action,row,FIXTURE['corrected'])
            elif action.startswith('plan_'):self.save(action.removeprefix('plan_'),self.source,data=FIXTURE['corrected_plan'])
            elif action in ('body','identity'):self.change_case(**({'history':'CW23 并发正文'} if action=='body' else {'patient_name':'CW23 并发身份'}))
            elif action=='delete':self.assertEqual(self.client.delete(f'/api/cases/{self.cid}',headers=self.owner_headers).status_code,204)
            else:
                with f.db.SessionLocal() as db:
                    if action=='owner':db.get(f.models.Case,self.cid).owner_id=db.query(f.models.User).filter_by(email='other@example.com').one().id
                    else:
                        audit=db.query(f.models.AuditLog).filter_by(case_id=self.cid,source=contacts.SOURCE).one()
                        if action=='audit':audit.model_version='CW23 审计元数据'
                        elif action=='bad_audit':audit.extra_data={**audit.extra_data,'content_hash':'b'*64}
                        else:db.delete(audit)
                    db.commit()
        module=queue if stage=='prefetched_rows' else service
        entered,release=Event(),Event();normal=getattr(module,stage)
        def held(*args):entered.set();self.assertTrue(release.wait(20));return normal(*args)
        with ThreadPoolExecutor(2) as pool,patch.object(module,stage,side_effect=held):
            reading=pool.submit(self.get_queue,{'page_size':'1'})
            try:self.assertTrue(entered.wait(10));pool.submit(mutate).result(15)
            finally:release.set()
            result=reading.result(15)
        for key in ('snapshot','items','total'):self.assertEqual(result[key],before[key])
        if action in ('bad_audit','missing_audit'):self.get_queue(expected=409)
        else:self.assertNotEqual(self.get_queue({'page_size':'1'})['snapshot'],before['snapshot'])
        self.get_queue({'page':'2','page_size':'1','snapshot':before['snapshot']},409)

    def test_midnight_snapshot_cannot_continue(self):
        self.contact_save();before=self.get_queue({'page_size':'1'})
        class Tomorrow(datetime):
            @classmethod
            def now(cls,tz=None):return datetime.fromisoformat('2028-02-29T16:00:00+00:00')
        with patch.object(queue,'datetime',Tomorrow):self.get_queue({'page':'2','page_size':'1','snapshot':before['snapshot']},409)


for index,action in enumerate(ACTIONS):
    stage=('prefetched_rows','prefetched_contacts','prefetched_audits')[index%3]
    setattr(ContactQueueConcurrency,'test_'+action,lambda self,a=action,s=stage:self.race(a,s))
if __name__=='__main__':unittest.main(verbosity=2)

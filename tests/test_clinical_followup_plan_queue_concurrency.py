"""WAL readers span case and plan queries; committed concurrent writers stay invisible."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Event
import unittest
from unittest.mock import patch
from sqlalchemy import text
from test_clinical_followup_plan_queue import QueueFixture, FIXTURE, f, queue

ACTIONS=('create','correct','withdraw','replace','body','identity','delete','restore','new_case_plan','cross_case')


class QueueConcurrencyTests(QueueFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with f.db.engine.connect() as conn: conn.execute(text('PRAGMA journal_mode=WAL'))

    def race(self, action):
        row=None if action=='create' else self.save(data=FIXTURE['plan'])
        other=self.add_case(); self.seed_plan(other)
        if action=='restore':
            with f.db.SessionLocal() as db:db.get(f.models.Case,self.cid).deleted_at=datetime(2028,2,29);db.commit()
        before=self.get_queue({'range':'all','page_size':'1'})
        if action in ('create','correct','withdraw','replace'):
            request=self.reviewed(self.body('withdraw' if action=='replace' else action,row,{**FIXTURE['plan'],'purpose':'合成并发更正'}))
            def mutation():
                r=self.client.post(self.root+'/confirm',headers=self.owner_headers,json=request);self.assertEqual(r.status_code,200,r.text)
                if action=='replace':self.save(data=FIXTURE['short_plan'])
        elif action=='delete':
            def mutation():self.assertEqual(self.client.delete(f'/api/cases/{self.cid}',headers=self.owner_headers).status_code,204)
        elif action=='restore':
            def mutation():
                with f.db.SessionLocal() as db:db.get(f.models.Case,self.cid).deleted_at=None;db.commit()
        elif action=='new_case_plan':mutation=lambda:self.seed_plan(self.add_case())
        elif action=='cross_case':
            def mutation():
                with f.db.SessionLocal() as db:
                    for cid in (self.cid,other):db.get(f.models.Case,cid).patient_name='合成跨病例更正'
                    db.commit()
        else: mutation=lambda:self.change_case(**({'patient_name':'合成身份更正'} if action=='identity' else {'history':'合成正文更正'}))
        entered, release = Event(),Event(); normal=queue.prefetched_rows
        def held(*args): entered.set();self.assertTrue(release.wait(15));return normal(*args)
        with ThreadPoolExecutor(2) as pool,patch.object(queue,'prefetched_rows',side_effect=held):
            reading=pool.submit(self.get_queue,{'range':'all','page_size':'1'})
            try:
                self.assertTrue(entered.wait(10));writing=pool.submit(mutation);writing.result(15)
            finally:release.set()
            result=reading.result(15)
        self.assertEqual(result['snapshot'],before['snapshot']);self.assertEqual(result['items'],before['items']);self.assertEqual(result['total'],before['total'])
        fresh=self.get_queue({'range':'all','page_size':'1'});self.assertNotEqual(fresh['snapshot'],before['snapshot'])
        self.get_queue({'range':'all','page_size':'1','page':'2','snapshot':before['snapshot']},409)

    def test_shanghai_midnight_invalidates_continuous_page_snapshot(self):
        self.seed_plan();self.seed_plan(self.add_case());first=self.get_queue({'range':'all','page_size':'1'})
        class Tomorrow(datetime):
            @classmethod
            def now(cls,tz=None):return datetime.fromisoformat('2028-02-29T16:00:00+00:00')
        with patch.object(queue,'datetime',Tomorrow):self.get_queue({'range':'all','page_size':'1','page':'2','snapshot':first['snapshot']},409)


for action in ACTIONS:setattr(QueueConcurrencyTests,'test_'+action,lambda self,a=action:self.race(a))
if __name__=='__main__':unittest.main(verbosity=2)

"""Independent SQLite sessions, retries, case invalidation and atomic failure."""
from concurrent.futures import ThreadPoolExecutor
import copy
import unittest
from unittest.mock import patch
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from test_manual_imaging_records import ImagingFixture, f, imaging


class ConcurrencyTests(ImagingFixture):
    def test_duplicate_and_competing_corrections(self):
        item,_,_=self.attach(); req=self.image_review(self.image_body(item))
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(lambda _:self.image_commit(req),range(2)))
        self.assertEqual([r.status_code for r in results],[200,200])
        self.assertEqual(len(self.image_state()['reports']),1)
        row=results[0].json()['report'];bodies=[self.image_body(old=row,operation='correct') for _ in range(2)]
        for i,b in enumerate(bodies): b['data']['findings']='更正原文 '+str(i+1)
        requests=[self.image_review(b) for b in bodies]
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(self.image_commit,requests))
        self.assertEqual(sorted(r.status_code for r in results),[200,409])
        self.assertEqual(len(self.image_state()['reports']),2)

    def test_competing_first_reports_and_correction_versus_withdrawal(self):
        item,_,_=self.attach();requests=[self.image_review(self.image_body(item)) for _ in range(2)]
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(self.image_commit,requests))
        self.assertEqual(sorted(r.status_code for r in results),[200,409])
        row=self.image_state()['reports'][0]
        requests=[self.image_review(self.image_body(old=row,operation=op)) for op in ('correct','withdraw')]
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(self.image_commit,requests))
        self.assertEqual(sorted(r.status_code for r in results),[200,409])

    def test_audit_and_commit_failure_roll_back_every_row_then_recover(self):
        item,_,_=self.attach();req=self.image_review(self.image_body(item))
        with patch.object(imaging,'append_audit',side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError):self.image_commit(req)
        self.assertEqual(self.image_state()['reports'],[])
        with patch.object(Session,'commit',side_effect=OperationalError('synthetic',{},Exception('fail'))):
            self.assertEqual(self.image_commit(req).status_code,503)
        self.assertEqual(self.image_state()['reports'],[])
        with f.db.SessionLocal() as db:
            self.assertEqual(db.query(f.models.ImagingStudy).filter_by(case_id=self.cid).count(),0)
        self.assertEqual(self.client.get(self.image_root+'/requests/'+req['request_id'],headers=self.owner_headers).json()['state'],'not_committed')
        self.assertEqual(self.image_commit(req).status_code,200)
        self.assertEqual(len(self.image_state()['reports']),1)

    def test_source_revision_failure_rolls_back_invalidation_and_source(self):
        item,_,row=self.save_image();self.meta={**self.meta,'title':'原件更正'}
        req=self.reviewed(self.body(item,'update'))
        with patch.object(Session,'commit',side_effect=OperationalError('synthetic',{},Exception('fail'))):
            self.assertEqual(self.commit(req).status_code,503)
        self.assertEqual(self.image_state()['reports'][0],row)
        self.assertEqual(self.listing()['items'][0]['metadata']['title'],item['metadata']['title'])
        self.assertEqual(self.commit(req).status_code,200)
        self.assertEqual(self.image_state()['reports'][0]['state'],'needs_review')

    def test_source_withdrawal_races_first_confirmation(self):
        item,_,_=self.attach(); req=self.image_review(self.image_body(item))
        withdrawal=self.reviewed(self.body(item,'withdraw'))
        with ThreadPoolExecutor(max_workers=2) as pool:
            save=pool.submit(self.image_commit,req); remove=pool.submit(self.commit,withdrawal)
            self.assertIn(save.result().status_code,[200,409]);self.assertEqual(remove.result().status_code,200)
        self.assertTrue(all(row['state']!='confirmed' for row in self.image_state()['reports']))

    def test_identity_change_races_correction_without_deadlock(self):
        _,_,row=self.save_image(); req=self.image_review(self.image_body(old=row,operation='correct'))
        with ThreadPoolExecutor(max_workers=2) as pool:
            save=pool.submit(self.image_commit,req)
            change=pool.submit(self.client.put,f'/api/cases/{self.cid}',headers=self.owner_headers,json={'owner_name':'并发合成宠主'})
            self.assertIn(save.result().status_code,[200,409]);self.assertEqual(change.result().status_code,200)
        self.assertTrue(all(row['state']!='confirmed' for row in self.image_state()['reports']))


if __name__=='__main__':unittest.main(verbosity=2)

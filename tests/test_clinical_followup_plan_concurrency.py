"""SQLite independent transactions: competing writes, rollback and lost replies."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
import unittest
from unittest.mock import patch
from sqlalchemy.exc import OperationalError
from test_clinical_followup_plans import FollowupFixture, f, plans, FIXTURE


class FollowupConcurrencyTests(FollowupFixture):
    def race(self,bodies):
        gate=Barrier(2)
        def send(body):
            gate.wait(timeout=10)
            return self.client.post(self.root+'/confirm',headers=self.owner_headers,json=body)
        with ThreadPoolExecutor(2) as pool:
            futures=[pool.submit(send,b) for b in bodies]
            return [v.result(timeout=15) for v in futures]

    def test_competing_creates_only_one_current_and_one_audit(self):
        a,b=self.reviewed(),self.reviewed();responses=self.race([a,b])
        self.assertEqual(sorted(r.status_code for r in responses),[200,409])
        self.assertEqual(len(self.request()['plans']),1);self.assertEqual(len(self.business()['audit_log']),1)

    def test_identical_request_replay_serializes_without_second_audit(self):
        body=self.reviewed();responses=self.race([body,body])
        self.assertEqual([r.status_code for r in responses],[200,200])
        self.assertEqual(sorted(r.json()['writes_database'] for r in responses),[False,True])
        self.assertEqual(len(self.business()['audit_log']),1)

    def test_correct_vs_withdraw_conflict_keeps_complete_chain(self):
        row=self.save();bodies=[self.reviewed(self.body('correct',row)),self.reviewed(self.body('withdraw',row))]
        responses=self.race(bodies);self.assertEqual(sorted(r.status_code for r in responses),[200,409])
        self.assertEqual(len(self.business()['audit_log']),2)
        listing=self.request();self.assertLessEqual(sum(p['stored_state']=='planned' for p in listing['plans']),1)

    def test_body_correction_waits_for_same_case_lock_then_invalidates_preview(self):
        body=self.reviewed();entered,release=Event(),Event()
        with ThreadPoolExecutor(2) as pool:
            def edit():
                with plans.transaction(self.owner_id,self.cid) as (db,case):
                    case.history='并发修改正文';db.flush();entered.set();assert release.wait(10);db.commit()
            first=pool.submit(edit);self.assertTrue(entered.wait(10))
            second=pool.submit(lambda:self.client.post(self.root+'/confirm',headers=self.owner_headers,json=body))
            self.assertFalse(second.done());release.set();first.result(15)
            self.assertEqual(second.result(15).status_code,409)
        self.assertEqual(self.business()['audit_log'],[])

    def test_audit_and_flush_failures_rollback_create_correct_and_withdraw(self):
        def fail(*args,**kwargs):raise OperationalError('synthetic',{},Exception('rollback'))
        for operation in ['create','correct','withdraw']:
            row=self.save() if operation=='correct' else (self.request()['plans'][-1] if operation=='withdraw' else None)
            body=self.reviewed(self.body(operation,row));before=self.business()
            original=plans.append_audit
            def fail_after(*args):original(*args);args[0].flush();fail()
            for handler in [fail,fail_after]:
                with patch.object(plans,'append_audit',side_effect=handler):self.request('/confirm',body,503)
                self.assertEqual(self.business(),before)
                self.assertEqual(self.request('/requests/'+body['request_id'])['state'],'not_committed')

    def test_lost_reply_result_query_waits_then_readback_and_retry_are_idempotent(self):
        body=self.reviewed();entered,release=Event(),Event();original=plans.append_audit
        def held(*args):original(*args);args[0].flush();entered.set();assert release.wait(10)
        with patch.object(plans,'append_audit',side_effect=held),ThreadPoolExecutor(2) as pool:
            write=pool.submit(lambda:self.client.post(self.root+'/confirm',headers=self.owner_headers,json=body))
            self.assertTrue(entered.wait(10))
            read=pool.submit(lambda:self.client.get(self.root+'/requests/'+body['request_id'],headers=self.owner_headers))
            self.assertFalse(read.done());release.set();self.assertEqual(write.result(15).status_code,200)
            receipt=read.result(15);self.assertEqual(receipt.status_code,200,receipt.text);self.assertEqual(receipt.json()['state'],'committed')
        self.assertEqual(self.request()['plans'][0]['data'],FIXTURE['plan'])
        self.assertFalse(self.request('/confirm',body)['writes_database']);self.assertEqual(len(self.business()['audit_log']),1)


if __name__=='__main__':unittest.main(verbosity=2)

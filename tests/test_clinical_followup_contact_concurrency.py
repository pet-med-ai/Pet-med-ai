"""Independent SQLite writers and receipt readers, including rollback after flush."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier,Event
import unittest
from unittest.mock import patch
from sqlalchemy.exc import OperationalError
from test_clinical_followup_contacts import ContactFixture,contacts,f,plans,FIXTURE


class ContactConcurrency(ContactFixture):
    def race(self,a,b):
        barrier=Barrier(2)
        def worker(body):barrier.wait(10);return self.client.post(self.contact_root+'/confirm',headers=self.owner_headers,json=body)
        with ThreadPoolExecutor(2) as pool:return [j.result(20) for j in [pool.submit(worker,a),pool.submit(worker,b)]]

    def test_two_creates_and_same_request_only_once(self):
        responses=self.race(self.contact_review(),self.contact_review())
        self.assertEqual(sorted(r.status_code for r in responses),[200,409])
        body=self.contact_review();responses=self.race(body,body)
        self.assertEqual([r.status_code for r in responses],[200,200])
        self.assertEqual(sorted(r.json()['writes_database'] for r in responses),[False,True])
        self.assertEqual(len(self.contact()['records']),2)

    def test_correction_and_withdraw_compete(self):
        row=self.contact_save();responses=self.race(self.contact_review(self.contact_body('correct',row)),self.contact_review(self.contact_body('withdraw',row)))
        self.assertEqual(sorted(r.status_code for r in responses),[200,409])

    def test_case_lock_waiting_then_stale(self):
        body=self.contact_review();entered,release=Event(),Event()
        def edit():
            with plans.transaction(self.owner_id,self.cid) as (db,case):
                case.history='并发已保存正文';db.flush();entered.set();assert release.wait(10);db.commit()
        with ThreadPoolExecutor(2) as pool:
            writer=pool.submit(edit);self.assertTrue(entered.wait(10))
            waiter=pool.submit(lambda:self.client.post(self.contact_root+'/confirm',headers=self.owner_headers,json=body))
            self.assertFalse(waiter.done());release.set();writer.result(20);self.assertEqual(waiter.result(20).status_code,409)
        self.assertEqual(self.contact()['records'],[])

    def test_plan_writer_and_contact_writer_use_same_case_lock(self):
        body=self.contact_review();plan_body=self.reviewed(self.body('withdraw',self.source));entered,release=Event(),Event();original=plans.append_audit
        def held(*args):original(*args);args[0].flush();entered.set();assert release.wait(10)
        with patch.object(plans,'append_audit',side_effect=held),ThreadPoolExecutor(2) as pool:
            writer=pool.submit(lambda:self.client.post(self.root+'/confirm',headers=self.owner_headers,json=plan_body));self.assertTrue(entered.wait(10))
            waiter=pool.submit(lambda:self.client.post(self.contact_root+'/confirm',headers=self.owner_headers,json=body))
            self.assertFalse(waiter.done());release.set();self.assertEqual(writer.result(20).status_code,200);self.assertEqual(waiter.result(20).status_code,409)

    def test_audit_flush_and_commit_errors_atomically_rollback_all_operations(self):
        def fail(*args,**kwargs):raise OperationalError('synthetic',{},Exception('rollback'))
        for operation in ['create','correct','withdraw']:
            row=self.contact_save() if operation=='correct' else (self.contact()['records'][-1] if operation=='withdraw' else None)
            body=self.contact_review(self.contact_body(operation,row));before=self.business();original=contacts.append_audit
            def after_flush(*args):original(*args);args[0].flush();fail()
            for handler in [fail,after_flush]:
                with patch.object(contacts,'append_audit',side_effect=handler):self.contact('/confirm',body,503)
                self.assertEqual(self.business(),before)
            with patch('sqlalchemy.orm.Session.commit',side_effect=fail):self.contact('/confirm',body,503)
            self.assertEqual(self.business(),before);self.assertEqual(self.contact('/requests/'+body['request_id'])['state'],'not_committed')

    def test_receipt_query_waits_for_commit_and_replay_does_not_duplicate(self):
        body=self.contact_review();entered,release=Event(),Event();original=contacts.append_audit
        def held(*args):original(*args);args[0].flush();entered.set();assert release.wait(10)
        with patch.object(contacts,'append_audit',side_effect=held),ThreadPoolExecutor(2) as pool:
            writer=pool.submit(lambda:self.client.post(self.contact_root+'/confirm',headers=self.owner_headers,json=body));self.assertTrue(entered.wait(10))
            reader=pool.submit(lambda:self.client.get(self.contact_root+'/requests/'+body['request_id'],headers=self.owner_headers));self.assertFalse(reader.done())
            release.set();self.assertEqual(writer.result(20).status_code,200)
            receipt=reader.result(20);self.assertEqual(receipt.status_code,200);self.assertEqual(receipt.json()['state'],'committed')
        self.assertFalse(self.contact('/confirm',body)['writes_database']);self.assertEqual(len(self.contact()['records']),1)


if __name__=='__main__':unittest.main(verbosity=2)

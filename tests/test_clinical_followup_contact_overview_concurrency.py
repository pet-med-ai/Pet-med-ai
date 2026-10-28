"""CW-B20 SQLite: the case lock covers original reports, plans, contacts and digest."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from test_clinical_followup_contact_overview import ContactOverviewFixture, FIXTURE, extension, contacts, f

ACTIONS = ('contact_create', 'contact_correct', 'contact_withdraw', 'plan_correct', 'plan_withdraw', 'plan_replace',
           'body', 'identity', 'delete', 'owner', 'source', 'source_metadata', 'lab', 'lab_correct', 'imaging', 'imaging_correct')


class ContactOverviewConcurrencyTests(ContactOverviewFixture):
    def race(self, action):
        sources, labs, _, image = self.mixed_sources()
        row = self.contact_save(data=FIXTURE['contact'])
        before = self.inventory()
        if action.startswith('contact_'):
            operation = action.removeprefix('contact_')
            body = self.contact_review(self.contact_body(operation, None if operation == 'create' else row, FIXTURE['corrected']))
            mutation = lambda: self.client.post(self.contact_root+'/confirm', headers=self.owner_headers, json=body)
        elif action.startswith('plan_'):
            operation = 'withdraw' if action == 'plan_replace' else action.removeprefix('plan_')
            body = self.plan_body(operation, self.source, FIXTURE['corrected_plan'])
            def mutation():
                result = self.client.post(self.plan_root+'/confirm', headers=self.owner_headers, json=body)
                if action == 'plan_replace': self.source = self.save_plan(data=FIXTURE['short_plan'])
                return result
        elif action in ('source', 'source_metadata'):
            self.meta = {**sources[0]['metadata'], 'title': 'CW-B20 合成来源更正'}
            body = self.reviewed(self.body(sources[0], 'withdraw' if action == 'source' else 'update'))
            mutation = lambda: self.commit(body)
        elif action in ('lab', 'lab_correct'):
            body = self.lab_body(old=labs[0], operation='correct' if action == 'lab_correct' else 'withdraw')
            if action == 'lab_correct': body['data']['items'][0]['value'] = '1.500'
            request = self.lab_review(body); mutation = lambda: self.lab_commit(request)
        elif action in ('imaging', 'imaging_correct'):
            body = self.image_body(old=image, operation='correct' if action == 'imaging_correct' else 'withdraw')
            if action == 'imaging_correct': body['data']['findings'] += ' CW-B20 合成更正'
            request = self.image_review(body); mutation = lambda: self.image_commit(request)
        elif action == 'owner':
            uid = before['groups']['contacts']['case']['owner_id']
            with f.db.SessionLocal() as db: other_id = db.query(f.models.User).filter_by(email='other@example.com').one().id
            def mutation():
                with contacts.plans.transaction(uid, self.cid) as (db, case):
                    case.owner_id = other_id; db.commit()
                return SimpleNamespace(status_code=200)
        elif action == 'delete': mutation = lambda: self.client.delete(f'/api/cases/{self.cid}', headers=self.owner_headers)
        else: mutation = lambda: self.client.put(f'/api/cases/{self.cid}', headers=self.owner_headers,
                       json={'owner_name': 'CW-B20 并发身份'} if action == 'identity' else {'history': 'CW-B20 并发正文'})
        entered, release, attempted = Event(), Event(), Event(); normal = extension.group
        def held(*args): entered.set(); self.assertTrue(release.wait(15)); return normal(*args)
        def mutate(): attempted.set(); return mutation()
        with ThreadPoolExecutor(2) as pool, patch.object(extension, 'group', side_effect=held):
            reading = pool.submit(self.inventory)
            try:
                self.assertTrue(entered.wait(10)); writing = pool.submit(mutate)
                self.assertTrue(attempted.wait(10)); self.assertFalse(writing.done())
            finally: release.set()
            result = reading.result(20)
            self.assertEqual(result['snapshot'], before['snapshot']); self.assertEqual(result['groups'], before['groups'])
            self.assertEqual(writing.result(20).status_code, 204 if action == 'delete' else 200)
        if action in ('delete', 'owner'): self.inventory(expected=404)
        else: self.assertNotEqual(self.inventory()['snapshot'], before['snapshot'])


for action in ACTIONS:
    setattr(ContactOverviewConcurrencyTests, 'test_'+action, lambda self, a=action: self.race(a))

if __name__ == '__main__': unittest.main(verbosity=2)

"""CW-B17 SQLite: the shared case lock spans all inventory groups and snapshot."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import unittest
from unittest.mock import patch
from test_clinical_followup_plan_overview import PlanOverviewFixture, FIXTURE, extension

ACTIONS = ('create', 'correct', 'withdraw', 'replace', 'body', 'identity', 'delete',
           'source', 'source_metadata', 'lab', 'lab_correct', 'imaging', 'imaging_correct')


class PlanOverviewConcurrencyTests(PlanOverviewFixture):
    def race(self, action):
        sources, labs, _, image = self.mixed_sources()
        row = None if action == 'create' else self.save_plan()
        before = self.overview()
        if action in ('create', 'correct', 'withdraw', 'replace'):
            request = self.plan_body('withdraw' if action == 'replace' else action, row, FIXTURE['corrected_plan'])
            def mutation():
                r = self.client.post(self.plan_root+'/confirm', headers=self.owner_headers, json=request)
                if action == 'replace': self.save_plan(data=FIXTURE['short_plan'])
                return r
        elif action in ('source', 'source_metadata'):
            self.meta = {**sources[0]['metadata'], 'title': '并发来源更正'}
            request = self.reviewed(self.body(sources[0], 'withdraw' if action == 'source' else 'update'))
            mutation = lambda: self.commit(request)
        elif action in ('lab', 'lab_correct'):
            body = self.lab_body(old=labs[0], operation='correct' if action == 'lab_correct' else 'withdraw')
            if action == 'lab_correct': body['data']['items'][0]['value'] = '1.500'
            request = self.lab_review(body); mutation = lambda: self.lab_commit(request)
        elif action in ('imaging', 'imaging_correct'):
            body = self.image_body(old=image, operation='correct' if action == 'imaging_correct' else 'withdraw')
            if action == 'imaging_correct': body['data']['findings'] += ' CW-B17 更正原文'
            request = self.image_review(body); mutation = lambda: self.image_commit(request)
        elif action == 'delete': mutation = lambda: self.client.delete(f'/api/cases/{self.cid}', headers=self.owner_headers)
        else: mutation = lambda: self.client.put(f'/api/cases/{self.cid}', headers=self.owner_headers,
                    json={'owner_name': '并发更正宠主'} if action == 'identity' else {'history': '并发更正正文'})
        entered, release, attempted = Event(), Event(), Event(); normal = extension.group
        def held(*args): entered.set(); self.assertTrue(release.wait(15)); return normal(*args)
        def mutate(): attempted.set(); return mutation()
        with ThreadPoolExecutor(2) as pool, patch.object(extension, 'group', side_effect=held):
            reading = pool.submit(self.overview)
            try:
                self.assertTrue(entered.wait(10)); writing = pool.submit(mutate)
                self.assertTrue(attempted.wait(10)); self.assertFalse(writing.done())
            finally: release.set()
            result = reading.result(20); self.assertEqual(result['snapshot'], before['snapshot'])
            self.assertEqual(result['groups'], before['groups'])
            self.assertEqual(writing.result(20).status_code, 204 if action == 'delete' else 200)
        if action == 'delete': self.overview(404)
        else: self.assertNotEqual(self.overview()['snapshot'], before['snapshot'])


for action in ACTIONS:
    setattr(PlanOverviewConcurrencyTests, 'test_'+action, lambda self, a=action: self.race(a))

if __name__ == '__main__': unittest.main(verbosity=2)

"""CW-B11: result/source/identity mutations cannot split a read snapshot."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import unittest
from unittest.mock import patch
from test_clinical_lab_range_review import RangeFixture, service


class RangeConcurrencyTests(RangeFixture):
    def race(self, scenario):
        source, row = self.saved_range(); before = self.ranges()
        if scenario in {'correct', 'withdraw'}:
            body = self.lab_body(old=row, operation=scenario)
            if scenario == 'correct': body['data']['items'][0]['value'] = '1.500'
            request = self.lab_review(body); mutate = lambda: self.lab_commit(request)
        elif scenario in {'source', 'source_metadata'}:
            if scenario == 'source_metadata': self.meta = {**self.meta, 'title': '并发来源更正'}
            request = self.reviewed(self.body(source, 'withdraw' if scenario == 'source' else 'update'))
            mutate = lambda: self.commit(request)
        else: mutate = lambda: self.client.put(f'/api/cases/{self.cid}', headers=self.owner_headers, json={'owner_name': '并发身份更正'})
        entered, release, attempted = Event(), Event(), Event(); normal = service.assemble
        def held(*args): entered.set(); self.assertTrue(release.wait(10)); return normal(*args)
        def change(): attempted.set(); return mutate()
        with ThreadPoolExecutor(max_workers=2) as pool, patch.object(service, 'assemble', side_effect=held):
            reading = pool.submit(self.ranges)
            try:
                self.assertTrue(entered.wait(5)); changing = pool.submit(change)
                self.assertTrue(attempted.wait(5)); self.assertFalse(changing.done())
            finally: release.set()
            self.assertEqual(reading.result(10)['snapshot'], before['snapshot'])
            self.assertEqual(changing.result(10).status_code, 200)
        after = self.ranges(); self.assertNotEqual(after['snapshot'], before['snapshot'])
        if scenario == 'correct':
            self.assertEqual(after['reports'][0]['version'], 2)
            self.assertEqual(after['reports'][0]['items'][0]['value'], '1.500')
        else: self.assertEqual(after['reports'], [])

    def test_correct(self): self.race('correct')
    def test_withdraw(self): self.race('withdraw')
    def test_source_withdraw(self): self.race('source')
    def test_source_metadata(self): self.race('source_metadata')
    def test_identity(self): self.race('identity')


if __name__ == '__main__': unittest.main(verbosity=2)

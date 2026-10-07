"""SQLite serialization and stale-selection refusal for both GET and preview POST."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import unittest
from unittest.mock import patch
from test_clinical_lab_comparison import ComparisonFixture, service


class ComparisonConcurrencyTests(ComparisonFixture):
    def race(self, scenario, previewing):
        sources, rows = self.save_pair(); before = self.read_comparison(); choice = self.request_body(before)
        if scenario in {'correct', 'withdraw'}:
            body = self.lab_body(old=rows[0], operation=scenario)
            if scenario == 'correct': body['data']['items'][0]['value'] = '1.500'
            request = self.lab_review(body); mutation = lambda: self.lab_commit(request)
        elif scenario in {'source', 'source_metadata'}:
            if scenario == 'source_metadata': self.meta = {**self.meta, 'title': '并发来源更正'}
            request = self.reviewed(self.body(sources[0], 'withdraw' if scenario == 'source' else 'update'))
            mutation = lambda: self.commit(request)
        else: mutation = lambda: self.client.put(f'/api/cases/{self.cid}', headers=self.owner_headers, json={'owner_name': '并发身份更正'})
        entered, release, attempted = Event(), Event(), Event(); normal = service.assemble
        def held(*args): entered.set(); self.assertTrue(release.wait(10)); return normal(*args)
        def change(): attempted.set(); return mutation()
        with ThreadPoolExecutor(max_workers=2) as pool, patch.object(service, 'assemble', side_effect=held):
            reading = pool.submit(self.preview, choice) if previewing else pool.submit(self.read_comparison)
            try:
                self.assertTrue(entered.wait(5)); changing = pool.submit(change)
                self.assertTrue(attempted.wait(5)); self.assertFalse(changing.done())
            finally: release.set()
            result = reading.result(10); self.assertEqual(result['snapshot'], before['snapshot'])
            if previewing: self.assertEqual(result['delta']['value'], '0')
            self.assertEqual(changing.result(10).status_code, 200)
        after = self.read_comparison(); self.assertNotEqual(before['snapshot'], after['snapshot']); self.preview(choice, 409)
        if scenario == 'correct':
            current = next(r for r in after['reports'] if r['root_id'] == rows[0]['root_id'])
            self.assertEqual(current['version'], 2); self.assertEqual(current['items'][0]['value'], '1.500')
        else: self.assertEqual(len(after['reports']), 0 if scenario == 'identity' else 1)


for scenario in ('correct', 'withdraw', 'source', 'source_metadata', 'identity'):
    for previewing in (False, True):
        def test(self, scenario=scenario, previewing=previewing): self.race(scenario, previewing)
        setattr(ComparisonConcurrencyTests, f'test_{scenario}_{"preview" if previewing else "get"}', test)


if __name__ == '__main__': unittest.main(verbosity=2)

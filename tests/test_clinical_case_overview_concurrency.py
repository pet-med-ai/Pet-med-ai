"""CW-B10: a view and concurrent original/report/case mutations cannot mix versions."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import unittest
from unittest.mock import patch
from test_clinical_case_overview import OverviewFixture, overview


class OverviewConcurrencyTests(OverviewFixture):
    def race(self, scenario):
        source, image, _, lab = self.both_reports()
        before = self.overview()
        if scenario in {'imaging', 'withdraw'}:
            req = self.image_review(self.image_body(old=image, operation='correct' if scenario == 'imaging' else 'withdraw'))
            mutate = lambda: self.image_commit(req)
        elif scenario == 'lab':
            req = self.lab_review(self.lab_body(old=lab, operation='correct'))
            mutate = lambda: self.lab_commit(req)
        elif scenario == 'source':
            req = self.reviewed(self.body(source, 'withdraw'))
            mutate = lambda: self.commit(req)
        else:
            mutate = lambda: self.client.put(f'/api/cases/{self.cid}', headers=self.owner_headers, json={scenario: '并发合成更正'})
        entered, release, attempted = Event(), Event(), Event()
        normal = overview.assemble
        def held(*args):
            entered.set(); self.assertTrue(release.wait(10)); return normal(*args)
        def change(): attempted.set(); return mutate()
        with ThreadPoolExecutor(max_workers=2) as pool, patch.object(overview, 'assemble', side_effect=held):
            reading = pool.submit(self.overview)
            try:
                self.assertTrue(entered.wait(5))
                changing = pool.submit(change); self.assertTrue(attempted.wait(5)); self.assertFalse(changing.done())
            finally: release.set()
            result = reading.result(10); self.assertEqual(changing.result(10).status_code, 200)
        self.assertEqual(result['snapshot'], before['snapshot'])
        self.assertNotEqual(self.overview()['snapshot'], before['snapshot'])

    def test_concurrent_imaging_correction(self): self.race('imaging')
    def test_concurrent_lab_correction(self): self.race('lab')
    def test_concurrent_report_withdrawal(self): self.race('withdraw')
    def test_concurrent_source_withdrawal(self): self.race('source')
    def test_concurrent_identity_change(self): self.race('owner_name')
    def test_concurrent_saved_text_change(self): self.race('history')


if __name__ == '__main__': unittest.main(verbosity=2)

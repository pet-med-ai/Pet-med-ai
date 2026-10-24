"""Render and mutation ordering using independent SQLite sessions and real routes."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import unittest
from unittest.mock import patch
from test_manual_lab_documents import LabDocumentFixture, doc_text, f
import clinical_docs_api as api


class LabDocumentConcurrencyTests(LabDocumentFixture):
    def test_render_holds_snapshot_while_correction_waits(self):
        _,_,row=self.save_lab();ids=[row['id']];snap=self.checked(ids)
        body=self.lab_body(old=row,operation='correct');body['data']['items'][0]['value']='0.0900';req=self.lab_review(body)
        entered,release,attempted=Event(),Event(),Event();normal=api._render_docx
        def slow(*a,**k):
            entered.set();assert release.wait(5);return normal(*a,**k)
        def change():attempted.set();return self.lab_commit(req)
        with ThreadPoolExecutor(max_workers=2) as pool,patch.object(api,'_render_docx',side_effect=slow):
            download=pool.submit(self.document,ids,endpoint='render',snapshot=snap)
            self.assertTrue(entered.wait(5));mutation=pool.submit(change);self.assertTrue(attempted.wait(5));self.assertFalse(mutation.done());release.set()
            r=download.result(10);self.assertEqual(r.status_code,200);self.assertIn('0.0100',doc_text(r.content));self.assertNotIn('0.0900',doc_text(r.content))
            self.assertEqual(mutation.result(10).status_code,200)
        self.assertEqual(self.document(ids,endpoint='render',snapshot=snap).status_code,409)

    def race(self, action):
        item,_,row=self.save_lab();ids=[row['id']];snap=self.checked(ids)
        if action=='withdraw':req=self.lab_review(self.lab_body(old=row,operation='withdraw'));change=lambda:self.lab_commit(req)
        elif action=='source':req=self.reviewed(self.body(item,'withdraw'));change=lambda:self.commit(req)
        else:change=lambda:self.client.put(f'/api/cases/{self.cid}',headers=self.owner_headers,json={('owner_name' if action=='identity' else 'history'):'并发更新合成'})
        with ThreadPoolExecutor(max_workers=2) as pool:
            r=pool.submit(self.document,ids,endpoint='render',snapshot=snap);c=pool.submit(change)
            result=r.result(10);self.assertIn(result.status_code,[200,409]);self.assertEqual(c.result(10).status_code,200)
            if result.status_code==200:self.assertIn('0.0100',doc_text(result.content));self.assertNotIn('并发更新合成',doc_text(result.content))
        self.assertEqual(self.document(ids,endpoint='render',snapshot=snap).status_code,409)

    def test_withdraw_race(self):self.race('withdraw')
    def test_source_race(self):self.race('source')
    def test_identity_race(self):self.race('identity')
    def test_history_race(self):self.race('history')

    def test_render_failure_does_not_write_or_change_report(self):
        _,_,row=self.save_lab();snap=self.checked([row['id']])
        with patch.object(api,'_render_docx',side_effect=OSError('synthetic rendering failure')):
            self.assertEqual(self.document([row['id']],endpoint='render',snapshot=snap).status_code,409)
        self.assertEqual(self.lab_state()['reports'],[row]);self.assertEqual(self.checked([row['id']]),snap)


if __name__=='__main__':unittest.main(verbosity=2)

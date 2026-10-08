"""CW-B13 independent SQLite sessions: lock spans preview and complete DOCX bytes."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import unittest
from unittest.mock import patch
from test_clinical_lab_comparison_documents import ComparisonDocumentFixture, doc_text, documents
import clinical_docs_api as api


class ComparisonDocumentConcurrencyTests(ComparisonDocumentFixture):
    def race(self, action, rendering):
        sources,rows=self.save_pair();extras={}
        if action=='imaging':
            self.meta={**self.meta,'kind':'dr'};_,_,image=self.save_image();extras={'manual_imaging_report_ids':[image['id']]}
            req=self.image_review(self.image_body(old=image,operation='withdraw'));change=lambda:self.image_commit(req)
        elif action in ('correct','withdraw'):
            body=self.lab_body(old=rows[0],operation=action)
            if action=='correct':body['data']['items'][0]['value']='1.500'
            req=self.lab_review(body);change=lambda:self.lab_commit(req)
        elif action in ('source','source_metadata'):
            self.meta={**self.meta,'title':'并发来源更正'};req=self.reviewed(self.body(sources[0],'withdraw' if action=='source' else 'update'));change=lambda:self.commit(req)
        else:change=lambda:self.client.put(f'/api/cases/{self.cid}',headers=self.owner_headers,json={('owner_name' if action=='identity' else 'history'):'并发正文或身份更正'})
        choice=self.request_body(index=3);before=self.checked(choice,**extras)
        entered,release,attempted=Event(),Event(),Event()
        module=api if rendering else documents;method='_render_docx' if rendering else 'read_selected';normal=getattr(module,method)
        def hold(*args,**kwargs):entered.set();assert release.wait(10);return normal(*args,**kwargs)
        def mutate():attempted.set();return change()
        with ThreadPoolExecutor(max_workers=2) as pool,patch.object(module,method,side_effect=hold):
            read=pool.submit(self.document,choice,'render' if rendering else 'render-preview',before['content_snapshot'] if rendering else None,**extras)
            try:
                self.assertTrue(entered.wait(10));write=pool.submit(mutate);self.assertTrue(attempted.wait(10));self.assertFalse(write.done())
            finally:release.set()
            r=read.result(10);self.assertEqual(r.status_code,200,r.text if not rendering else '')
            if rendering:self.assertIn('差值 B−A：0.00000000000000000000000000001',doc_text(r.content));self.assertNotIn('并发正文或身份更正',doc_text(r.content))
            else:self.assertEqual(r.json()['content_snapshot'],before['content_snapshot'])
            self.assertEqual(write.result(10).status_code,200)
        self.assertEqual(self.document(choice,'render',before['content_snapshot'],**extras).status_code,409)

for action in ('correct','withdraw','source','source_metadata','identity','body','imaging'):
    for rendering in (False,True):
        setattr(ComparisonDocumentConcurrencyTests,f'test_{action}_{"render" if rendering else "preview"}',lambda self,a=action,r=rendering:self.race(a,r))

if __name__=='__main__':unittest.main(verbosity=2)

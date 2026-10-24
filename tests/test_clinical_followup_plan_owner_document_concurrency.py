"""CW-B16 owner SQLite: independent mutation waits through the entire document read."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import unittest
from unittest.mock import patch
from test_clinical_followup_plan_owner_documents import OwnerPlanDocumentFixture, FIXTURE, documents, api, doc_text


class OwnerPlanDocumentConcurrencyTests(OwnerPlanDocumentFixture):
    def race(self, action, rendering, mixed):
        extra={}
        if mixed:
            sources,rows=self.save_pair();self.meta={**self.meta,'kind':'dr'};_,_,image=self.save_image()
            extra={'manual_lab_report_ids':[rows[0]['id']],'manual_imaging_report_ids':[image['id']]}
        row=self.save_plan();choice=self.choice(row);before=self.checked(choice,**extra)
        if action in ('correct','withdraw','replace'):
            request=self.plan_body('correct' if action == 'correct' else 'withdraw',row,FIXTURE['corrected_plan'])
            def mutation():
                r=self.client.post(self.plan_root+'/confirm',headers=self.owner_headers,json=request)
                if action=='replace':self.save_plan(data=FIXTURE['short_plan'])
                return r
        elif action in ('source','source_metadata'):
            self.meta={**sources[0]['metadata'],'title':'并发来源更正'}
            request=self.reviewed(self.body(sources[0],'withdraw' if action=='source' else 'update'))
            mutation=lambda:self.commit(request)
        elif action in ('lab','lab_correct'):
            body=self.lab_body(old=rows[0],operation='correct' if action=='lab_correct' else 'withdraw')
            if action=='lab_correct':body['data']['items'][0]['value']='1.500'
            request=self.lab_review(body);mutation=lambda:self.lab_commit(request)
        elif action in ('imaging','imaging_correct'):
            body=self.image_body(old=image,operation='correct' if action=='imaging_correct' else 'withdraw')
            if action=='imaging_correct':body['data']['findings']+=' CW-B16 更正影像原文'
            request=self.image_review(body);mutation=lambda:self.image_commit(request)
        elif action=='delete':mutation=lambda:self.client.delete(f'/api/cases/{self.cid}',headers=self.owner_headers)
        else:mutation=lambda:self.client.put(f'/api/cases/{self.cid}',headers=self.owner_headers,json={'owner_name':'更正宠主身份'} if action=='identity' else {'history':'并发更正正文'})
        entered,release,attempted=Event(),Event(),Event()
        module,method=(api,'_render_docx') if rendering else (documents,'read_selected');normal=getattr(module,method)
        def hold(*args,**kwargs):entered.set();assert release.wait(15);return normal(*args,**kwargs)
        def mutate():attempted.set();return mutation()
        with ThreadPoolExecutor(2) as pool,patch.object(module,method,side_effect=hold):
            reading=pool.submit(self.document,choice,'render' if rendering else 'render-preview',before['content_snapshot'] if rendering else None,**extra)
            try:
                self.assertTrue(entered.wait(10));writing=pool.submit(mutate);self.assertTrue(attempted.wait(10));self.assertFalse(writing.done())
            finally:release.set()
            r=reading.result(20);self.assertEqual(r.status_code,200,r.text if not rendering else '')
            if rendering:self.assertIn(FIXTURE['plan']['purpose'],doc_text(r.content));self.assertNotIn('并发更正正文',doc_text(r.content))
            else:self.assertEqual(r.json()['content_snapshot'],before['content_snapshot'])
            self.assertEqual(writing.result(20).status_code,204 if action=='delete' else 200)
        self.assertEqual(self.document(choice,'render',before['content_snapshot'],**extra).status_code,404 if action=='delete' else 409)


for mixed in (False,True):
    actions=('correct','withdraw','replace','body','identity','delete')+ (('source','source_metadata','lab','lab_correct','imaging','imaging_correct') if mixed else ())
    for action in actions:
        for rendering in (False,True):
            setattr(OwnerPlanDocumentConcurrencyTests,f'test_{action}_{"mixed" if mixed else "plan_only"}_{"render" if rendering else "preview"}',lambda self,a=action,r=rendering,m=mixed:self.race(a,r,m))

if __name__=='__main__':unittest.main(verbosity=2)

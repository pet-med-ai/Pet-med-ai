"""Old payloads, all templates and saved business facts stay unchanged."""
import unittest
from unittest.mock import patch
import os
from test_clinical_followup_contact_isolation import ContactIsolation
from test_clinical_followup_contact_documents import ContactDocumentFixture,FLAGS,FIXTURE,contacts,api,doc_text

class ContactDocumentIsolation(ContactIsolation):
    def test_legacy_snapshots_and_default_documents_remain_exact(self):
        with patch.dict(os.environ,FLAGS):
            for species in ('dog','cat'):
                if species=='cat':
                    self.change_case(species='cat');self.source=self.save_plan('correct',self.source,FIXTURE['plan'])
                row=self.contact_save();choice=ContactDocumentFixture.choice(self,row)
                before=self.snapshots();business=self.all_business();listing=self.contact()
                p=ContactDocumentFixture.document(self,choice);self.assertEqual(p.status_code,200,p.text)
                r=ContactDocumentFixture.document(self,choice,'render',p.json()['content_snapshot']);self.assertEqual(r.status_code,200)
                self.assertIn('人工随访记录附节',doc_text(r.content))
                self.assertEqual(self.snapshots(),before);self.assertEqual(self.all_business(),business);self.assertEqual(self.contact(),listing)
                with patch.object(api,'_utc_timestamp',return_value='2026-10-09T07:00:00Z'):
                    for template in ('outpatient_record_zh','owner_visit_summary_zh','admission_hospitalization_record_bilingual','discharge_summary_bilingual'):
                        body={'case_id':self.cid,'template_id':template}
                        expected=self.client.post('/api/clinical-docs/render-preview',headers=self.owner_headers,json=body).json()
                        baseline=self.client.post('/api/clinical-docs/render',headers=self.owner_headers,json=body)
                        self.assertEqual(baseline.status_code,500 if template=='discharge_summary_bilingual' else 200)
                        with patch.dict(os.environ,{k:'0' for k in FLAGS}),patch.object(contacts,'records',side_effect=AssertionError('Unselected does not read contacts')):
                            actual=self.client.post('/api/clinical-docs/render-preview',headers=self.owner_headers,json=body)
                            self.assertEqual(actual.status_code,200);self.assertEqual(actual.json(),expected)
                            doc=self.client.post('/api/clinical-docs/render',headers=self.owner_headers,json=body);self.assertEqual(doc.status_code,baseline.status_code)
                            if doc.status_code==200:
                                self.assertEqual(doc_text(doc.content),doc_text(baseline.content));self.assertNotIn('人工随访记录附节',doc_text(doc.content))
                            else:self.assertEqual(doc.json(),baseline.json())
                    # Also prove successful unchanged exports for both legacy templates.
                    self.change_case(history='CW21 clean synthetic historical text')
                    for template in ('admission_hospitalization_record_bilingual','discharge_summary_bilingual'):
                        body={'case_id':self.cid,'template_id':template}
                        baseline=self.client.post('/api/clinical-docs/render',headers=self.owner_headers,json=body);self.assertEqual(baseline.status_code,200,baseline.text)
                        with patch.dict(os.environ,{k:'0' for k in FLAGS}),patch.object(contacts,'records',side_effect=AssertionError('Legacy does not read contacts')):
                            doc=self.client.post('/api/clinical-docs/render',headers=self.owner_headers,json=body);self.assertEqual(doc.status_code,200);self.assertEqual(doc_text(doc.content),doc_text(baseline.content))
                    self.change_case(history=FIXTURE['case']['history'])

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([ContactDocumentIsolation('test_legacy_snapshots_and_default_documents_remain_exact')]))
    raise SystemExit(not result.wasSuccessful())

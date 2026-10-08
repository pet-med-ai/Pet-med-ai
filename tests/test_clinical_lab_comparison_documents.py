"""CW-B13 real JWT, literal DOCX, stable full-document snapshot and no business writes."""
import copy
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile
from xml.etree import ElementTree as ET
from sqlalchemy import event
from sqlalchemy.exc import OperationalError
SAMPLES_OUT = os.getenv('PMAI_CWB13_DOC_SAMPLES')
from test_clinical_lab_comparison import ComparisonFixture, f, storage
from test_manual_lab_documents import doc_text
import clinical_lab_comparison_documents as documents
import clinical_docs_api as api

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/clinical_lab_comparison_documents_cw_b13_cases.json').read_text())


class ComparisonDocumentFixture(ComparisonFixture):
    def setUp(self):
        super().setUp()
        env = patch.dict(os.environ, {'LAB_COMPARISON_DOCUMENTS_ENABLED': '1', 'LAB_COMPARISON_DOCUMENTS_SYNTHETIC_ONLY': '1',
                                     'MANUAL_LAB_DOCUMENTS_ENABLED': '1', 'MANUAL_LAB_DOCUMENTS_SYNTHETIC_ONLY': '1'})
        env.start(); self.addCleanup(env.stop)

    def document(self, choice, endpoint='render-preview', snapshot=None, headers=None, **extra):
        return self.client.post('/api/clinical-docs/' + endpoint, headers=self.owner_headers if headers is None else headers,
                               json={'case_id': self.cid, 'template_id': 'outpatient_record_zh', 'manual_lab_comparison': choice,
                                     **({'expected_content_snapshot': snapshot} if snapshot else {}), **extra})

    def checked(self, choice, **extra):
        r = self.document(choice, **extra); self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.headers['cache-control'], 'private, no-store')
        return r.json()

    def rendered(self, choice, **extra):
        preview = self.checked(choice, **extra)
        r = self.document(choice, 'render', preview['content_snapshot'], **extra)
        self.assertEqual(r.status_code, 200, r.text if r.status_code != 200 else '')
        self.assertEqual(r.headers['x-pmai-content-snapshot'], preview['content_snapshot'])
        self.assertEqual(r.headers['cache-control'], 'private, no-store')
        return preview, r.content


class ComparisonDocumentTests(ComparisonDocumentFixture):
    def test_all_exact_differences_raw_provenance_and_stable_readback(self):
        sources, rows = self.save_pair(); saved = self.read_comparison()
        for index, delta in enumerate(FIXTURE['expected_deltas']):
            choice = self.request_body(saved, index)
            preview, raw = self.rendered(choice); payload = preview['manual_lab_comparison']; text = doc_text(raw)
            self.assertEqual(payload['result']['delta']['value'], delta)
            self.assertIn('差值 B−A：' + delta, text)
            for key, i in [('a', 0), ('b', 1)]:
                side = payload[key]
                self.assertEqual(side['item'], saved['reports'][i]['items'][index])
                for literal in [side['item']['value'], side['source']['sha256'], side['report']['collected_at'], side['token']]: self.assertIn(literal, text)
                self.assertEqual(side['source']['sha256'], sources[i]['sha256']); self.assertEqual(side['version'], rows[i]['version'])
            self.assertIn('参考范围不同', text); self.assertIn('尚未签署', text); self.assertIn(documents.comparison.RULES, text)
            f.db.engine.dispose(); self.assertEqual(self.checked(choice)['content_snapshot'], preview['content_snapshot'])

    def test_no_sql_audit_original_cleanup_or_persistent_export_writes(self):
        self.save_pair(); choice = self.request_body(); before = self.business(); writes = []
        def capture(_c, _cur, sql, *_):
            if sql.lstrip().split()[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'}: writes.append(sql)
        event.listen(f.db.engine, 'before_cursor_execute', capture)
        try:
            with patch.object(storage.Store, 'cleanup', side_effect=AssertionError('No cleanup on document reads')):
                self.rendered(choice)
        finally: event.remove(f.db.engine, 'before_cursor_execute', capture)
        self.assertEqual(writes, []); self.assertEqual(self.business(), before)

    def test_auth_other_case_deleted_case_gates_and_read_failure(self):
        self.save_pair(); choice = self.request_body(); snap = self.checked(choice)['content_snapshot']
        for endpoint in ('render-preview', 'render'):
            self.assertEqual(self.document(choice, endpoint, snap, headers={}).status_code, 401)
            self.assertEqual(self.document(choice, endpoint, snap, headers=self.other_headers).status_code, 404)
            for name in ('LAB_COMPARISON_DOCUMENTS_ENABLED','LAB_COMPARISON_DOCUMENTS_SYNTHETIC_ONLY','LAB_COMPARISON_ENABLED','LAB_COMPARISON_SYNTHETIC_ONLY','MANUAL_LAB_DOCUMENTS_ENABLED','MANUAL_LAB_DOCUMENTS_SYNTHETIC_ONLY','MANUAL_LAB_RESULTS_ENABLED','CASE_ATTACHMENTS_ENABLED'):
                with patch.dict(os.environ, {name:'0'}): self.assertEqual(self.document(choice, endpoint, snap).status_code, 503, name)
            for env in ({'ENVIRONMENT':'production'}, {'RENDER':'true'}):
                with patch.dict(os.environ, env): self.assertEqual(self.document(choice, endpoint, snap).status_code, 503)
            with patch.object(documents.comparison, 'assemble', side_effect=OperationalError('synthetic', {}, Exception('offline'))):
                r = self.document(choice, endpoint, snap); self.assertEqual(r.status_code,503); self.assertEqual(r.headers['cache-control'],'private, no-store')
        cid = self.client.post('/api/cases', headers=self.owner_headers, json=FIXTURE['case']).json()['id']
        self.assertEqual(self.document(choice, case_id=cid).status_code, 409)
        self.client.delete(f'/api/cases/{self.cid}', headers=self.owner_headers)
        self.assertEqual(self.document(choice).status_code,404)

    def test_strict_choice_noncomparable_and_unsupported_templates(self):
        self.save_pair(); saved=self.read_comparison(); choice=self.request_body(saved)
        variants=[None, [], {**choice,'value':'99'}, {**choice,'delta':'9'}, {**choice,'doctor_confirmed':1}, {**choice,'a':{**choice['a'],'id':True}}, {**choice,'a':{**choice['a'],'unit':'mg'}}]
        for value in variants: self.assertEqual(self.document(value).status_code,422,str(value))
        for i in range(7,11): self.assertEqual(self.document(self.request_body(saved,i)).status_code,422)
        for change in ({'doctor_confirmed':False}, {'b':choice['a']}, {'a':choice['b'],'b':choice['a']}): self.assertEqual(self.document({**choice,**change}).status_code,422)
        for template in ('owner_visit_summary_zh','admission_hospitalization_record_bilingual','discharge_summary_bilingual'):
            self.assertEqual(self.document(choice,template_id=template).status_code,422)
            self.assertEqual(self.document(None,template_id=template).status_code,422)
        self.assertEqual(self.document(choice,include_diagnostic_data=True).status_code,422)
        self.assertEqual(self.document(choice,'render').status_code,409)
        self.assertEqual(self.document(choice,'render','0'*64).status_code,409)

    def test_full_snapshot_binds_body_template_pair_and_mixed_selections(self):
        self.save_pair(); choice=self.request_body(); snap=self.checked(choice)['content_snapshot']
        self.change_case(history='更正正文 {{literal}}')
        self.assertEqual(self.document(choice,'render',snap).status_code,409)
        choice=self.request_body(); snap=self.checked(choice)['content_snapshot']
        original=api.Path.read_bytes
        def changed(path):
            result=original(path)
            return result+b'asset-change' if str(path).endswith('outpatient_record_zh.docx') else result
        with patch.object(api.Path,'read_bytes',changed): self.assertEqual(self.document(choice,'render',snap).status_code,409)
        other=self.request_body(index=1)
        self.assertEqual(self.document(other,'render',snap).status_code,409)
        self.assertEqual(self.document(choice,'render',snap,manual_lab_report_ids=[choice['a']['id']]).status_code,409)

    def test_stale_version_source_loss_and_corrupt_saved_structure(self):
        sources,rows=self.save_pair(); choice=self.request_body(); snap=self.checked(choice)['content_snapshot']
        blob=storage.Store().path(sources[0]['id'],'.blob'); original=blob.read_bytes()
        for missing in (False,True):
            blob.unlink() if missing else blob.write_bytes(b'corrupted')
            self.assertEqual(self.document(choice).status_code,409)
            self.assertEqual(self.document(choice,'render',snap).status_code,409)
        blob.write_bytes(original)
        with f.db.SessionLocal() as db:
            row=db.get(f.models.DiagnosticReport,rows[0]['id']); value=copy.deepcopy(row.metadata_json);value['version']=100;row.metadata_json=value;db.commit()
        self.assertEqual(self.document(choice).status_code,409)

    def test_four_docx_sample_categories_literal_text_and_table_structure(self):
        _,rows=self.save_pair(); choice=self.request_body(index=0)
        samples={'short':self.rendered(choice)[1]}
        samples['precise-changed-reference']=self.rendered(self.request_body(index=5))[1]
        old=rows[0]; body=self.lab_body(old=old,operation='correct')
        body['data']['report']['note']=FIXTURE['literal_note']*12
        changed=self.lab_commit(self.lab_review(body));self.assertEqual(changed.status_code,200,changed.text)
        choice=self.request_body(index=3)
        samples['long-unicode-braces']=self.rendered(choice)[1]
        self.assertIn(FIXTURE['literal_note']*12,doc_text(samples['long-unicode-braces']))
        self.meta={**self.meta,'kind':'dr'};_,_,image=self.save_image()
        choice=self.request_body(index=3)
        labs=[choice['a']['id']]
        samples['mixed-lab-imaging']=self.rendered(choice,manual_lab_report_ids=labs,manual_imaging_report_ids=[image['id']])[1]
        text=doc_text(samples['mixed-lab-imaging'])
        for title in ('检验结果附节','影像','检验前后对照附节'):self.assertIn(title,text)
        w=documents.labs.W
        for name,raw in samples.items():
            with zipfile.ZipFile(io.BytesIO(raw)) as z:root=ET.fromstring(z.read('word/document.xml'))
            tables=list(root.iter(w+'tbl'));self.assertTrue(tables)
            self.assertTrue(all(t.find('.//'+w+'tblHeader') is not None for t in tables))
            self.assertEqual(root.find(w+'body')[-1].tag,w+'sectPr')
            if SAMPLES_OUT:
                out=Path(SAMPLES_OUT);out.mkdir(parents=True,exist_ok=True);(out/(name+'.docx')).write_bytes(raw)


if __name__=='__main__':unittest.main(verbosity=2)

"""Whole-image reports, mixed snapshots, literal DOCX output and mutation races."""
import copy
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import unittest
from unittest.mock import patch
from sqlalchemy import event
SAMPLES_OUT=os.getenv('PMAI_CWB9_DOC_SAMPLES')
from test_manual_imaging_records import ImagingFixture, DATA, f, storage
from test_manual_lab_documents import LabDocumentFixture, doc_text, TEMPLATES
import manual_imaging_documents as documents
import clinical_docs_api as api

LITERAL='原文 <tag> & "引号"\n第二行\t{{visit.history}} 😀 未提供'


class ImagingDocumentTests(ImagingFixture):
    def setUp(self):
        super().setUp()
        env=patch.dict(os.environ,{'MANUAL_LAB_DOCUMENTS_ENABLED':'1','MANUAL_LAB_DOCUMENTS_SYNTHETIC_ONLY':'1'})
        env.start();self.addCleanup(env.stop)

    def document(self,ids,template=TEMPLATES[0],endpoint='render-preview',snapshot=None,labs=None,headers=None,**extra):
        return self.client.post('/api/clinical-docs/'+endpoint,headers=self.owner_headers if headers is None else headers,
            json={'case_id':self.cid,'template_id':template,'manual_imaging_report_ids':ids,'manual_lab_report_ids':labs or [],
                  **({'expected_content_snapshot':snapshot} if snapshot else {}),**extra})

    def checked(self,ids,template=TEMPLATES[0],labs=None):
        r=self.document(ids,template,labs=labs);self.assertEqual(r.status_code,200,r.text);return r.json()['content_snapshot']

    def second_image(self,index=1,data=None):
        import struct,zlib
        from test_case_attachments import png
        raw=png();text=f'Synthetic CW-B9 {index}'.encode();kind=b'tEXt'
        raw=raw[:-12]+struct.pack('>I',len(text))+kind+text+struct.pack('>I',zlib.crc32(kind+text)&0xffffffff)+raw[-12:]
        data=copy.deepcopy(data or DATA);self.meta={**self.meta,'kind':data['modality']}
        item,_,_=self.attach(data=raw);b=self.image_body(item);b['data']=data
        r=self.image_commit(self.image_review(b));self.assertEqual(r.status_code,200,r.text);return item,r.json()['report']

    def lab_report(self,index=1):
        self.meta={**self.meta,'kind':'lab'}
        result=LabDocumentFixture.second_report(self,index)
        self.meta={**self.meta,'kind':'dr'};return result[1]

    def test_both_templates_exact_fields_and_no_writes_mixed(self):
        _,_,row=self.save_image();lab=self.lab_report();ids=[row['id']];labs=[lab['id']];writes=[]
        def sql(_c,_cur,statement,*_):
            if statement.lstrip().split(' ',1)[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'}:writes.append(statement)
        event.listen(f.db.engine,'before_cursor_execute',sql)
        try:
            for template in TEMPLATES:
                snap=self.checked(ids,template,labs);r=self.document(ids,template,'render',snap,labs=labs)
                self.assertEqual(r.status_code,200,r.text if r.status_code!=200 else '')
                text=doc_text(r.content)
                for value in [*map(DATA.get,documents.BODY_FIELDS),DATA['taken_at'],DATA['position'],row['source']['sha256'],'影像报告附节','检验结果附节','0.0100','尚未签署']:
                    self.assertIn(value,text)
                self.assertEqual(r.headers['x-pmai-content-snapshot'],snap)
                self.assertEqual(r.headers['x-pmai-writes-database'],'false')
        finally:event.remove(f.db.engine,'before_cursor_execute',sql)
        self.assertEqual(writes,[])

    def test_selection_bound_and_no_default_inclusion(self):
        _,_,a=self.save_image();_,b=self.second_image();lab=self.lab_report();snap=self.checked([a['id']],labs=[lab['id']])
        for ids,labs in [([b['id']],[lab['id']]),([a['id']],[]),([],[lab['id']]),([],[])]:
            self.assertEqual(self.document(ids,endpoint='render',snapshot=snap,labs=labs).status_code,409)
        self.assertEqual(self.document([a['id']],endpoint='render').status_code,409)
        r=self.document([],endpoint='render',snapshot=self.checked([]));self.assertNotIn('影像报告附节',doc_text(r.content))
        for ids in [[a['id'],a['id']],[True],['1'],[-1],list(range(1,7))]:self.assertEqual(self.document(ids).status_code,422)
        self.assertEqual(self.document([a['id']],include_diagnostic_data=True).status_code,422)
        self.assertEqual(self.document([a['id']],'discharge_summary_bilingual').status_code,422)

    def test_permission_foreign_case_feature_flags_and_deletion(self):
        _,_,r=self.save_image();ids=[r['id']];snap=self.checked(ids)
        for headers,code in [({},401),(self.other_headers,404)]:self.assertEqual(self.document(ids,headers=headers).status_code,code)
        for env in [{'MANUAL_IMAGING_ENABLED':'0'},{'MANUAL_IMAGING_SYNTHETIC_ONLY':'0'},{'ENVIRONMENT':'production'},{'RENDER':'true'}]:
            with patch.dict(os.environ,env):
                self.assertEqual(self.document(ids,endpoint='render',snapshot=snap).status_code,503)
                self.assertEqual(self.document([]).status_code,200)
        original=self.cid;self.cid=self.client.post('/api/cases',headers=self.owner_headers,json={'patient_name':'另一合成病例','species':'cat','chief_complaint':'合成'}).json()['id']
        self.assertEqual(self.document(ids).status_code,404);self.cid=original
        self.client.delete(f'/api/cases/{self.cid}',headers=self.owner_headers);self.assertEqual(self.document(ids).status_code,404)

    def test_corruption_source_update_identity_and_history_invalidate(self):
        item,_,row=self.save_image();ids=[row['id']];snap=self.checked(ids)
        path=storage.Store().path(item['id'],'.blob');raw=path.read_bytes();path.write_bytes(b'corrupt')
        self.assertEqual(self.document(ids,endpoint='render',snapshot=snap).status_code,409)
        path.unlink();self.assertEqual(self.document(ids).status_code,409);path.write_bytes(raw)
        self.client.put(f'/api/cases/{self.cid}',headers=self.owner_headers,json={'history':'病史已更正'})
        self.assertEqual(self.document(ids,endpoint='render',snapshot=snap).status_code,409);snap=self.checked(ids)
        self.meta={**self.meta,'title':'原件已更正'};self.commit(self.reviewed(self.body(item,'update')))
        self.assertEqual(self.document(ids,endpoint='render',snapshot=snap).status_code,409)
        row=self.image_commit(self.image_review(self.image_body(old=self.image_state()['reports'][0],operation='correct'))).json()['report']
        snap=self.checked([row['id']]);self.client.put(f'/api/cases/{self.cid}',headers=self.owner_headers,json={'owner_name':'新合成宠主'})
        self.assertEqual(self.document([row['id']],endpoint='render',snapshot=snap).status_code,409)

    def test_twenty_thousand_unicode_characters_never_truncated(self):
        data={**DATA,'findings':'😀'*5000,'impression':'原'*5000,'limitations':'','note':''}
        _,a=self.second_image(1,data);_,b=self.second_image(2,data);_,c=self.second_image(3)
        ids=[a['id'],b['id']];snap=self.checked(ids);self.assertEqual(snap,self.checked(ids[::-1]))
        out=self.document(ids,endpoint='render',snapshot=snap);text=doc_text(out.content)
        self.assertEqual(text.count('😀'),10000)
        self.assertEqual(self.document(ids+[c['id']]).status_code,422)

    def test_mixed_snapshot_holds_one_lock_through_render_for_both_mutations(self):
        _,_,row=self.save_image();lab=self.lab_report();ids=[row['id']];labs=[lab['id']];snap=self.checked(ids,labs=labs)
        image_req=self.image_review(self.image_body(old=row,operation='withdraw'))
        lab_req=self.lab_review(self.lab_body(old=lab,operation='withdraw'))
        entered,release=Event(),Event();normal=api._render_docx
        def slow(*a,**k):entered.set();assert release.wait(5);return normal(*a,**k)
        with ThreadPoolExecutor(max_workers=3) as pool,patch.object(api,'_render_docx',side_effect=slow):
            export=pool.submit(self.document,ids,endpoint='render',snapshot=snap,labs=labs)
            self.assertTrue(entered.wait(5));image_change=pool.submit(self.image_commit,image_req);lab_change=pool.submit(self.lab_commit,lab_req)
            self.assertFalse(image_change.done());self.assertFalse(lab_change.done());release.set()
            out=export.result(10);self.assertEqual(out.status_code,200)
            self.assertIn(DATA['findings'],doc_text(out.content));self.assertIn('0.0100',doc_text(out.content))
            self.assertEqual(image_change.result(10).status_code,200);self.assertEqual(lab_change.result(10).status_code,200)
        self.assertEqual(self.document(ids,endpoint='render',snapshot=snap,labs=labs).status_code,409)

    def test_correction_withdrawal_and_render_failure(self):
        _,_,old=self.save_image();snap=self.checked([old['id']]);b=self.image_body(old=old,operation='correct');b['data']['findings']=LITERAL
        new=self.image_commit(self.image_review(b)).json()['report'];ids=[new['id']]
        self.assertEqual(self.document([old['id']],endpoint='render',snapshot=snap).status_code,409)
        snap=self.checked(ids)
        with patch.object(api,'_render_docx',side_effect=OSError('synthetic failure')):
            self.assertEqual(self.document(ids,endpoint='render',snapshot=snap).status_code,409)
        self.assertEqual(self.checked(ids),snap)
        for template in TEMPLATES:
            out=self.document(ids,template,'render',self.checked(ids,template));self.assertIn(LITERAL,doc_text(out.content))
        self.image_commit(self.image_review(self.image_body(old=new,operation='withdraw')))
        self.assertEqual(self.document(ids,endpoint='render',snapshot=snap).status_code,409)

    def test_options_restart_and_synthetic_visual_samples(self):
        for i,shape in enumerate(['short','long','special','mixed']):
            data=copy.deepcopy(DATA)
            if shape=='long':data.update(findings=('所见原文，保持段落和限定语。\n'*180),impression=('结论原文，需结合临床资料。\n'*120))
            if shape=='special':data.update(findings=LITERAL,impression='',limitations='',note='')
            if shape=='mixed':data.update(modality='ultrasound',title='合成超声报告',body_part='腹部')
            _,row=self.second_image(i+1,data);ids=[row['id']];labs=[self.lab_report(i+1)['id']] if shape=='mixed' else []
            url=f'/api/clinical-docs/cases/{self.cid}/manual-imaging-options'
            self.assertIn(row,self.client.get(url,headers=self.owner_headers).json()['reports'])
            snap=self.checked(ids,labs=labs);f.db.engine.dispose();self.assertEqual(self.checked(ids,labs=labs),snap)
            for template in TEMPLATES:
                out=self.document(ids,template,'render',self.checked(ids,template,labs),labs=labs);self.assertEqual(out.status_code,200,out.text if out.status_code!=200 else '')
                self.assertEqual(doc_text(out.content).count('影像报告附节'),1)
                if SAMPLES_OUT:
                    target=Path(SAMPLES_OUT);target.mkdir(parents=True,exist_ok=True);(target/f'{template}-{shape}.docx').write_bytes(out.content)


if __name__=='__main__':unittest.main(verbosity=2)

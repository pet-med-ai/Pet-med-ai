"""CW-B8 authenticated export, exact literals, source lifecycle and no-write checks."""
import copy
import io
import json
import os
import struct
import zlib
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile
from xml.etree import ElementTree as ET
from sqlalchemy import event
SAMPLES_OUT=os.getenv('PMAI_CWB8_DOC_SAMPLES')
from test_manual_lab_results import ManualLabFixture, DATA, f, storage
from test_case_attachments import png
import manual_lab_documents as documents

FIXTURES=json.loads((Path(__file__).parent/'fixtures/manual_lab_cw_b8_cases.json').read_text())
TEMPLATES=FIXTURES['templates']
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def doc_text(content):
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        root=ET.fromstring(z.read('word/document.xml'))
    return '\n'.join(''.join(n.text or '' if n.tag==W+'t' else '\n' if n.tag==W+'br' else '\t' if n.tag==W+'tab' else '' for n in p.iter()) for p in root.iter(W+'p'))


class LabDocumentFixture(ManualLabFixture):
    def setUp(self):
        super().setUp()
        self.docenv=patch.dict(os.environ,{'MANUAL_LAB_DOCUMENTS_ENABLED':'1','MANUAL_LAB_DOCUMENTS_SYNTHETIC_ONLY':'1'})
        self.docenv.start();self.addCleanup(self.docenv.stop)

    def document(self, ids, template=TEMPLATES[0], endpoint='render-preview', snapshot=None, headers=None, **extra):
        return self.client.post('/api/clinical-docs/'+endpoint,headers=self.owner_headers if headers is None else headers,
            json={'case_id':self.cid,'template_id':template,'manual_lab_report_ids':ids,
                  **({'expected_content_snapshot':snapshot} if snapshot else {}),**extra})

    def checked(self, ids, template=TEMPLATES[0]):
        r=self.document(ids,template);self.assertEqual(r.status_code,200,r.text)
        return r.json()['content_snapshot']

    def second_report(self, index=1, data=None):
        # A valid ancillary PNG chunk gives each synthetic original unique bytes.
        text=f'Synthetic CW-B8 {index}'.encode();kind=b'tEXt';raw=png()
        raw=raw[:-12]+struct.pack('>I',len(text))+kind+text+struct.pack('>I',zlib.crc32(kind+text)&0xffffffff)+raw[-12:]
        item,_,_=self.attach(data=raw)
        b=self.lab_body(item);b['data']=copy.deepcopy(data or DATA)
        r=self.lab_commit(self.lab_review(b));self.assertEqual(r.status_code,200,r.text)
        return item,r.json()['report']


class LabDocumentTests(LabDocumentFixture):
    def test_selected_values_both_documents_and_zero_database_writes(self):
        _,_,row=self.save_lab();ids=[row['id']];writes=[]
        def sql(_c,_cur,statement,*_):
            if statement.lstrip().split(' ',1)[0].upper() in {'INSERT','UPDATE','DELETE','CREATE','ALTER','DROP'}:writes.append(statement)
        event.listen(f.db.engine,'before_cursor_execute',sql)
        try:
            for template in TEMPLATES:
                snapshot=self.checked(ids,template)
                r=self.document(ids,template,'render',snapshot)
                self.assertEqual(r.status_code,200,r.text if r.status_code!=200 else '')
                self.assertEqual(r.headers['x-pmai-content-snapshot'],snapshot)
                text=doc_text(r.content)
                for value in ['0.0100','0.0010','未测','未提供','检验结果附节',row['source']['sha256'],row['source']['name']]:self.assertIn(value,text)
                for item in DATA['items']:
                    if item['value']:self.assertIn(item['value'],text)
                    self.assertIn(item['position'],text)
                self.assertEqual(r.headers['X-PMAI-Writes-Database'],'false')
        finally:event.remove(f.db.engine,'before_cursor_execute',sql)
        self.assertEqual(writes,[])
        self.assertEqual(self.lab_state()['reports'],[row])

    def test_selected_export_requires_snapshot_and_rejects_selection_tampering(self):
        _,_,row=self.save_lab();_,second=self.second_report()
        one=self.checked([row['id']]);self.assertEqual(self.document([row['id']],endpoint='render').status_code,409)
        for ids in ([second['id']],[row['id'],second['id']],[]):
            self.assertEqual(self.document(ids,endpoint='render',snapshot=one).status_code,409)
        for ids in ([row['id'],row['id']], [True], ['1'], [1.2], [-1], list(range(1,7))):
            self.assertEqual(self.document(ids).status_code,422,(ids,self.document(ids).text))

    def test_default_documents_unchanged_and_legacy_cannot_include(self):
        _,_,row=self.save_lab()
        for template in TEMPLATES:
            p=self.document([],template).json();r=self.document([],template,'render',p['content_snapshot'])
            self.assertNotIn('检验结果附节',doc_text(r.content))
            self.assertNotIn('manual_lab_reports',p)
            self.assertEqual(self.document([row['id']],template,include_diagnostic_data=True).status_code,422)
        self.assertEqual(self.document([row['id']],'discharge_summary_bilingual').status_code,422)

    def test_permissions_deleted_and_feature_environment(self):
        _,_,row=self.save_lab();ids=[row['id']];snap=self.checked(ids)
        for headers,code in [({},401),(self.other_headers,404)]:
            self.assertEqual(self.document(ids,headers=headers).status_code,code)
            self.assertEqual(self.document(ids,endpoint='render',snapshot=snap,headers=headers).status_code,code)
        for env in [{'MANUAL_LAB_DOCUMENTS_ENABLED':'0'},{'MANUAL_LAB_DOCUMENTS_SYNTHETIC_ONLY':'0'},{'ENVIRONMENT':'production'},{'RENDER':'true'}]:
            with patch.dict(os.environ,env):
                self.assertEqual(self.document(ids).status_code,503)
                self.assertEqual(self.document(ids,endpoint='render',snapshot=snap).status_code,503)
                self.assertEqual(self.document([]).status_code,200)
        self.client.delete(f'/api/cases/{self.cid}',headers=self.owner_headers)
        self.assertEqual(self.document(ids).status_code,404)

    def test_foreign_report_id_never_reads_other_case(self):
        _,_,row=self.save_lab();own=self.cid
        new=self.client.post('/api/cases',headers=self.owner_headers,json={'patient_name':'其他合成犬','species':'dog','chief_complaint':'合成'}).json()['id']
        self.cid=new;self.assertEqual(self.document([row['id']]).status_code,404);self.cid=own

    def test_correction_and_withdrawal_reject_old_preview(self):
        _,_,row=self.save_lab();snap=self.checked([row['id']]);b=self.lab_body(old=row,operation='correct');b['data']['items'][0]['value']='0.0200'
        new=self.lab_commit(self.lab_review(b)).json()['report']
        self.assertEqual(self.document([row['id']],endpoint='render',snapshot=snap).status_code,409)
        snap2=self.checked([new['id']]);out=self.document([new['id']],endpoint='render',snapshot=snap2)
        self.assertIn('0.0200',doc_text(out.content));self.assertNotEqual(snap,snap2)
        self.lab_commit(self.lab_review(self.lab_body(old=new,operation='withdraw')))
        self.assertEqual(self.document([new['id']],endpoint='render',snapshot=snap2).status_code,409)

    def test_source_changed_or_lost_rejects_selected_export(self):
        item,_,row=self.save_lab();snap=self.checked([row['id']])
        path=storage.Store().path(item['id'],'.blob');raw=path.read_bytes();path.write_bytes(b'corrupt')
        self.assertEqual(self.document([row['id']],endpoint='render',snapshot=snap).status_code,409)
        path.unlink();self.assertEqual(self.document([row['id']]).status_code,409);path.write_bytes(raw)
        self.meta={**self.meta,'title':'changed original'};self.commit(self.reviewed(self.body(item,'update')))
        self.assertEqual(self.document([row['id']],endpoint='render',snapshot=snap).status_code,409)

    def test_identity_and_document_field_changes_invalidate(self):
        _,_,row=self.save_lab();snap=self.checked([row['id']])
        self.client.put(f'/api/cases/{self.cid}',headers=self.owner_headers,json={'history':'更正已保存病史'})
        self.assertEqual(self.document([row['id']],endpoint='render',snapshot=snap).status_code,409)
        snap=self.checked([row['id']])
        self.client.put(f'/api/cases/{self.cid}',headers=self.owner_headers,json={'owner_name':'更正宠主'})
        self.assertEqual(self.document([row['id']],endpoint='render',snapshot=snap).status_code,409)

    def test_missing_units_reference_and_literal_template_tokens(self):
        data=copy.deepcopy(DATA);data['report']['note']=FIXTURES['literal']
        data['items']=[{**data['items'][0],'name':'原文 {{visit.history}}','result_type':'text','value':FIXTURES['literal'],'unit':'','reference':'','reference_low':'','reference_high':'','reference_unit':''}]
        _,row=self.second_report(data=data)
        for template in TEMPLATES:
            r=self.document([row['id']],template,'render',self.checked([row['id']],template))
            self.assertEqual(r.status_code,200);text=doc_text(r.content)
            self.assertIn(FIXTURES['literal'],text);self.assertIn('原文 {{visit.history}}',text);self.assertGreaterEqual(text.count('未提供'),2)

    def test_two_hundred_items_and_order_without_truncation(self):
        data=copy.deepcopy(DATA);data['items']=[{**data['items'][0],'name':f'合成项目 {i:03d}'} for i in range(100)]
        _,a=self.second_report(1,data);_,b=self.second_report(2,data);_,c=self.second_report(3)
        ids=[a['id'],b['id']]
        snap=self.checked(ids);self.assertEqual(snap,self.checked(ids[::-1]))
        r=self.document(ids,endpoint='render',snapshot=snap)
        self.assertEqual(doc_text(r.content).count('合成项目 '),200)
        self.assertEqual(self.document(ids+[c['id']]).status_code,422)

    def test_options_fresh_states_and_restart_readback(self):
        _,_,row=self.save_lab();url=f'/api/clinical-docs/cases/{self.cid}/manual-lab-options'
        self.assertEqual(self.client.get(url,headers=self.owner_headers).json()['reports'],[row])
        snapshot=self.checked([row['id']]);f.db.engine.dispose();self.assertEqual(self.checked([row['id']]),snapshot)
        self.lab_commit(self.lab_review(self.lab_body(old=row,operation='withdraw')))
        self.assertEqual(self.client.get(url,headers=self.owner_headers).json()['reports'],[])

    def test_synthetic_document_samples_for_visual_acceptance(self):
        out=SAMPLES_OUT
        for index,shape in enumerate(FIXTURES['sample_shapes']):
            data=copy.deepcopy(DATA)
            if shape=='long':data['items']=[{**data['items'][0],'name':f'长报告项目 {i:03d}','reference':'参考范围原文 '+('未提供更多说明。'*18)} for i in range(60)]
            if shape=='limit200':data['items']=[{**data['items'][0],'name':f'上限项目 {i:03d}'} for i in range(100)]
            if shape=='special':data['report']['note']=FIXTURES['literal']
            _,row=self.second_report(index*2+1,data);ids=[row['id']]
            if shape=='limit200':_,r2=self.second_report(index*2+2,data);ids.append(r2['id'])
            for template in TEMPLATES:
                r=self.document(ids,template,'render',self.checked(ids,template));self.assertEqual(r.status_code,200,r.text if r.status_code!=200 else '')
                self.assertEqual(doc_text(r.content).count('检验结果附节'),len(ids))
                if out:
                    target=Path(out);target.mkdir(parents=True,exist_ok=True);(target/f'{template}-{shape}.docx').write_bytes(r.content)


if __name__=='__main__':unittest.main(verbosity=2)

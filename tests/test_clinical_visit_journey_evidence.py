"""Reject false completion receipts; no application/database fixture is mocked here."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('journey_readback', ROOT/'tests/acceptance/clinical_visit_journey_readback.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='cwb24-evidence-negative-')
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        self.fixture = json.loads(check.FIXTURE.read_text())
        self.head = '1'*40
        f = self.fixture
        self.report = {'schema':check.SCHEMA, 'head':self.head, 'fixture_sha256':check.sha(check.FIXTURE.read_bytes()),
                       'status':'PASS', 'errors':[], 'external':[], 'doctor_acceptance':'pending', 'merged':False,
                       'deployed':False, 'passed':f['scenarios'][:], 'backend':'postgresql', 'cases':[],
                       'faults':{'lost_write_response':{'status':'PASS','confirm_posts':1},
                                 'stale_document_source':{'status':'PASS','rejected_status':409},
                                 'late_case_account_response':{'status':'PASS','modes':['case','account']},
                                 'failed_cancelled_download':{'status':'PASS','downloads':0}}}
        for index, data in enumerate(f['cases'],1):
            case={'species':data['species'], 'case_id':index, 'saved_case':{'id':index,**data}, 'steps':f['steps'][:],
                  'requests':{'create':1,'attachments':2,'lab':2,'imaging':1,'plan':1,'contact':1},
                  'readonly_before':{'case_id':index},'readonly_after':{'case_id':index},
                  'lab':{'reports':[{'state':'superseded','data':deepcopy(f['lab'])},{'version':2,'data':deepcopy(f['lab'])}]},
                  'plans':{'plans':[{'id':10+index,'data':f['plan']}]},
                  'contacts':{'records':[{'id':20+index,'token':'synthetic-version-token','source':{'id':10+index},'data':f['contact']}]},
                  'documents':[],'screenshots':[],'originals':[]}
            case['lab']['reports'][1]['data']['items'][0]['value']=f['corrected_lab_value']
            literals=[data['patient_name'],data['history'],data['treatment'],f['lab']['report']['title'],f['corrected_lab_value'],
                      f['imaging']['findings'],f['plan']['purpose'],*f['plan']['items'],f['plan']['note'],f['contact']['note'],
                      f['contact']['next_action'],'尚未签署','待医生核对','synthetic-version-token']
            for template in ['outpatient_record_zh','owner_visit_summary_zh']:
                name=f'{index}-{template}.docx'
                with zipfile.ZipFile(self.out/name,'w') as z:
                    z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+''.join('<w:p><w:r><w:t xml:space="preserve">'+escape(v)+'</w:t></w:r></w:p>' for v in literals)+'</w:body></w:document>')
                case['documents'].append(self.receipt(name,template=template,case_id=index,plan_id=10+index,contact_id=20+index))
            for viewport in ['wide','narrow']:
                name=f'{index}-{viewport}.png';(self.out/name).write_bytes(b'negative-test-only')
                case['screenshots'].append(self.receipt(name,viewport=viewport))
            for kind in ['lab','dr']:
                name=f'{index}-{kind}.bin';(self.out/name).write_bytes(b'synthetic source bytes')
                case['originals'].append(self.receipt(name,attachment_id=f'{index}-{kind}'))
            self.report['cases'].append(case)

    def receipt(self,name,**extra):
        b=(self.out/name).read_bytes()
        return {'file':name,'bytes':len(b),'sha256':check.sha(b),**extra}

    def validate(self):
        return check.validate_evidence(self.report,self.out,self.head)

    def test_complete_structural_receipt_is_not_doctor_signoff(self):
        self.assertEqual(len(self.validate()),12)
        self.assertEqual(self.report['doctor_acceptance'],'pending')

    def test_wrong_head_schema_fixture_and_unknown_backend_are_refused(self):
        for key,value in [('head','2'*40),('schema','old'),('fixture_sha256','0'*64),('backend','production')]:
            with self.subTest(key=key):
                original=self.report[key];self.report[key]=value
                with self.assertRaises(ValueError):self.validate()
                self.report[key]=original

    def test_missing_duplicate_or_reordered_steps_and_scenarios(self):
        row=self.report['cases'][0]
        for value in [row['steps'][:-1],row['steps']+row['steps'][:1],list(reversed(row['steps']))]:
            old=row['steps'];row['steps']=value
            with self.assertRaises(ValueError):self.validate()
            row['steps']=old
        self.report['passed'].pop()
        with self.assertRaises(ValueError):self.validate()

    def test_wrong_identity_source_version_or_repeated_save(self):
        row=self.report['cases'][0]
        pairs=[(row,'case_id',999),(row['saved_case'],'history','changed'),(row['contacts']['records'][0]['source'],'id',999),
               (row['lab']['reports'][1],'version',1),(row['requests'],'contact',2),(row['readonly_after'],'case_id',999)]
        for obj,key,value in pairs:
            with self.subTest(key=key):
                old=obj[key];obj[key]=value
                with self.assertRaises(ValueError):self.validate()
                obj[key]=old

    def test_missing_changed_or_escaped_files(self):
        item=self.report['cases'][0]['documents'][0]
        for key,value in [('sha256','0'*64),('bytes',0),('file','../escape.docx'),('file','missing.docx')]:
            old=item[key];item[key]=value
            with self.assertRaises(ValueError):self.validate()
            item[key]=old

    def test_success_label_cannot_hide_errors_or_claim_acceptance(self):
        for key,value in [('status','INCOMPLETE'),('errors',['real error']),('external',['blocked request']),
                          ('doctor_acceptance','passed'),('merged',True),('deployed',True)]:
            old=self.report[key];self.report[key]=value
            with self.assertRaises(ValueError):self.validate()
            self.report[key]=old

    def test_wrong_download_selection_and_missing_literal(self):
        item=self.report['cases'][0]['documents'][0];item['contact_id']=999
        with self.assertRaises(ValueError):self.validate()
        item['contact_id']=21
        with zipfile.ZipFile(self.out/item['file'],'w') as z:
            z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>wrong case</w:t></w:r></w:p></w:document>')
        item.update(self.receipt(item['file']))
        with self.assertRaises(ValueError):self.validate()

    def test_fault_results_cannot_be_silently_downgraded(self):
        for name,key,value in [('lost_write_response','confirm_posts',2),('stale_document_source','rejected_status',200),
                               ('late_case_account_response','modes',['case']),('failed_cancelled_download','downloads',1)]:
            target=self.report['faults'][name];old=target[key];target[key]=value
            with self.assertRaises(ValueError):self.validate()
            target[key]=old


if __name__=='__main__':unittest.main(verbosity=2)

"""B4 authenticated API/save/readback/DOCX on disposable SQLite only."""
import unittest
import test_consult_update_preview as fixture
from test_clinical_doc_lifecycle import paragraphs, DRAFTS
import chief_complaint_intake as intake
main, db = fixture.main, fixture.db


class ConsultEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ConsultUpdatePreviewTests.setUpClass()
        cls.client=fixture.ConsultUpdatePreviewTests.client
        cls.auth=fixture.ConsultUpdatePreviewTests.owner_headers
        cls.other=fixture.ConsultUpdatePreviewTests.other_headers

    @classmethod
    def tearDownClass(cls):fixture.ConsultUpdatePreviewTests.tearDownClass()

    def call(self, method, url, body=None, status=200, auth=None):
        r=self.client.request(method,url,headers=self.auth if auth is None else auth,**({'json':body} if body is not None else {}))
        self.assertEqual(r.status_code,status,r.text if r.status_code!=status else '')
        return r

    def test_normal_and_dynamic_endpoints_exclude_questions(self):
        for animal in ['dog','cat']:
            r=self.call('POST','/api/ai/consult',{'text':'未见黑便','species':animal}).json()
            self.assertEqual(r['diseases']['diseases'],[])
            r=self.call('POST','/api/ai/consult/dynamic',{'text':'常规体检','species':animal,'answers':[{'question':'黑便或干呕、腹胀？','answer':'没有'}]}).json()
            self.assertEqual(r['risk_level'],'待核对')
            self.assertEqual(r['diseases']['diseases'],[])

    def test_structured_labels_unknown_and_inactive_branches_not_findings(self):
        for animal in ['dog','cat']:
            for key in intake.TEMPLATES:
                t=intake.get_template(key,animal)
                presence=next(q for q in t['questions'] if q['kind']=='presence')['key']
                branch=next(q for q in t['questions'] if q.get('when'))
                answers={'notes':{'state':'observed','text':'未见黑便'},presence:{'state':'uncertain','text':'不知道'},
                         branch['when']:{'state':'absent','text':''},branch['key']:{'state':'observed','text':'黑便；干呕；腹胀'}}
                snapshot=intake.build_snapshot(key,{'version':t['version'],'fingerprint':t['fingerprint'],'species':animal,'answers':answers})
                r=self.call('POST','/api/ai/consult/session',{'text':'常规体检','species':animal,'structured_intake_answers':snapshot}).json()
                self.assertEqual(r['result']['diseases']['diseases'],[],key)
                self.assertEqual(r['result']['risk_level'],'待核对')
                records=r['result']['input_evidence']['records']
                self.assertFalse(any(row['source'].endswith('/'+branch['key']) for row in records))
                self.assertTrue(any(row['raw']=='未见黑便' and row['state']=='negative' for row in records))

    def test_positive_presence_without_text_requires_single_unambiguous_subject(self):
        # Text-free compound questions must not turn every named sign positive.
        t=intake.get_template('fever_lethargy','dog')
        p=next(q for q in t['questions'] if q['kind']=='presence')['key']
        snapshot=intake.build_snapshot('fever_lethargy',{'version':t['version'],'fingerprint':t['fingerprint'],'species':'dog','answers':{p:{'state':'observed','text':''}}})
        result=self.call('POST','/api/ai/consult/session',{'text':'常规体检','species':'dog','structured_intake_answers':snapshot}).json()['result']
        self.assertTrue(result['input_evidence']['needs_review'])

    def test_followup_save_relogin_readback_and_actual_documents(self):
        for animal in ['dog','cat']:
            raw='  没有黑便🐾\n原文保留 <literal>  '
            created=self.call('POST','/api/ai/consult/session',{'text':'常规体检','species':animal}).json()
            route='/api/ai/consult/session/'+created['session_id']
            updated=self.call('POST',route+'/answer',{'question':'是否有黑便、干呕或腹胀？','answer':raw,'expected_answers_token':created['answers_token']}).json()
            self.assertEqual(updated['result']['diseases']['diseases'],[])
            before=updated['result']['input_evidence']
            body={'patient_name':'B4合成'+animal,'species':animal,'chief_complaint':'常规体检','history':'医生原病史🐾\n','owner_name':'B4合成宠主','coat_color':'黑白'}
            p=self.call('POST',route+'/preview-case',body).json()
            saved=self.call('POST',route+'/save-case',{**body,'expected_preview_token':p['preview_token']}).json()
            self.call('GET',route,auth=self.other,status=404)
            db.engine.dispose()
            login=self.client.post('/auth/login',data={'username':'owner@example.com','password':'synthetic-test-password'})
            self.assertEqual(login.status_code,200)
            auth={'Authorization':'Bearer '+login.json()['access_token']}
            self.assertEqual(self.call('GET',route,auth=auth).json()['result']['input_evidence'],before)
            cid=saved['case_id'];case=self.call('GET',f'/api/cases/{cid}',auth=auth).json()
            self.assertIn(raw,case['history']);self.assertNotIn('扭转',case['analysis'])
            self.assertIn('待核对',case['treatment'])
            for template in DRAFTS:
                preview=self.call('POST','/api/clinical-docs/render-preview',{'case_id':cid,'template_id':template},auth=auth).json()
                rendered=self.call('POST','/api/clinical-docs/render',{'case_id':cid,'template_id':template,'expected_content_snapshot':preview['content_snapshot']},auth=auth)
                text='\n'.join(paragraphs(rendered.content))
                self.assertIn(raw,text);self.assertIn('待核对',text)
                self.assertNotIn('胃扩张/扭转',text)
                self.assertEqual(self.call('GET',f'/api/cases/{cid}',auth=auth).json(),case)

    def test_absent_field_with_positive_raw_is_visible_conflict(self):
        t=intake.get_template('cough_breathing','dog')
        key=next(q for q in t['questions'] if q['kind']=='presence')['key']
        snap=intake.build_snapshot('cough_breathing',{'version':t['version'],'fingerprint':t['fingerprint'],'species':'dog','answers':{key:{'state':'absent','text':'出现呼吸困难'}}})
        r=self.call('POST','/api/ai/consult/session',{'text':'常规体检','species':'dog','structured_intake_answers':snap}).json()['result']
        self.assertTrue(any(row['state']=='conflict' for row in r['input_evidence']['records']))
        self.assertEqual(r['risk_level'],'待核对')


if __name__=='__main__':unittest.main()

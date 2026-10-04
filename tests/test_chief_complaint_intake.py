"""B1 real auth/SQLite routes, canonical templates and literal clinical drafts."""
import unittest
import json
from copy import deepcopy
from unittest.mock import patch
import test_consult_update_preview as fixture
import chief_complaint_intake as intake
from test_clinical_doc_lifecycle import paragraphs, DRAFTS

main, db, models = fixture.main, fixture.db, fixture.models


def request(key, species='dog', **answers):
    t = intake.get_template(key, species)
    return {'version':t['version'],'fingerprint':t['fingerprint'],'species':species,'answers':answers}


class ChiefComplaintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ConsultUpdatePreviewTests.setUpClass()
        for name in ['client','owner_headers','other_headers','owner_id']:
            setattr(cls,name,getattr(fixture.ConsultUpdatePreviewTests,name))

    @classmethod
    def tearDownClass(cls):
        fixture.ConsultUpdatePreviewTests.tearDownClass()

    def call(self, method, url, body=None, status=200, headers=None):
        r = self.client.request(method,url,headers=self.owner_headers if headers is None else headers,**({'json':body} if body is not None else {}))
        self.assertEqual(r.status_code,status,r.text if r.status_code!=200 else '')
        return r

    def test_templates_defaults_states_bounds_and_species(self):
        for key in intake.TEMPLATES:
            for animal in ['dog','cat']:
                with self.subTest(key=key,animal=animal):
                    t=intake.get_template(key,animal)
                    self.assertEqual(t['review_status'],'clinical_draft')
                    s=intake.build_snapshot(key,request(key,animal))
                    self.assertEqual(intake.validate_snapshot(s),s)
                    self.assertTrue(all(':unfilled:' in a['answer_type'] for a in s['sections'][0]['answers']))
                    self.assertEqual(intake.ai_context(s),'')
                    self.assertNotIn('正常',main._structured_snapshot_text(s))
                    p=next(q for q in t['questions'] if q['kind']=='presence')['key']
                    for state in intake.STATES:
                        s=intake.build_snapshot(key,request(key,animal,**{p:{'state':state,'text':'原文'}}))
                        self.assertIn('状态：'+intake.STATES[state],main._structured_snapshot_text(s))
            for answers in [{'onset':{'state':'observed','text':' \n'}},{'onset':{'state':'absent','text':''}},{'notes':{'state':'observed','text':'x'*6001}},{'unknown':{'state':'unfilled','text':''}}, {q['key']:{'state':'uncertain','text':'x'*3000} for q in t['questions']}]:
                with self.assertRaises(intake.IntakeError):intake.build_snapshot(key,request(key,**answers))
            with self.assertRaises(intake.IntakeError):intake.get_template(key,'other')

    def test_conditional_originals_and_negative_states_do_not_enter_keyword_engine(self):
        for key in intake.TEMPLATES:
            q=next(q for q in intake.get_template(key,'dog')['questions'] if q.get('when'))
            raw='  旧分支🐾\r\n<5 & {{literal}}\t尾部  \n'
            body=request(key,**{q['when']:{'state':'observed','text':''},q['key']:{'state':'observed','text':raw}})
            self.assertIn(raw,intake.ai_context(intake.build_snapshot(key,body)))
            body['answers'][q['when']]['state']='absent'
            s=intake.build_snapshot(key,body)
            self.assertEqual(intake.ai_context(s),'')
            self.assertIn(raw,main._structured_snapshot_text(s))
            self.assertIn('当前不适用',main._structured_snapshot_text(s))

    def test_tampered_families_labels_flags_and_stale_templates_rejected(self):
        for key in intake.TEMPLATES:
            original=intake.build_snapshot(key,request(key))
            edits=[lambda s:s.update(version=key+'-intake-old+old'),lambda s:s.update(label='自动确认正常'),
                   lambda s:s['sections'][0].update(key='diarrhea'),lambda s:s['sections'][0]['answers'][0].update(answer_type=key+':unfilled:0'),
                   lambda s:s['sections'][0]['answers'][0].update(label='被替换'),lambda s:s['sections'][0]['answers'].pop()]
            for edit in edits:
                changed=deepcopy(original);edit(changed)
                with self.assertRaises(Exception):main._clean_structured_snapshot(changed)
            for other in intake.TEMPLATES:
                if other!=key:
                    self.call('POST','/api/ai/consult/intake/'+other+'/preview',request(key),status=409)
            old=deepcopy(original);old['version']=key+'-intake-old+old'
            self.assertEqual(main._stored_structured_snapshot({main.STRUCTURED_SNAPSHOT_KEY:json.dumps(old)}),old)
            self.assertEqual(intake.ai_context(old),'')

    def test_auth_preview_and_unknown_template_never_write(self):
        with db.SessionLocal() as s:before=s.query(models.ConsultSession).count()
        for key in intake.TEMPLATES:
            url='/api/ai/consult/intake/'+key
            self.call('GET',url+'?species=dog',headers={},status=401)
            self.call('POST',url+'/preview',request(key),headers={},status=401)
            self.call('GET',url+'?species=dog')
            preview=self.call('POST',url+'/preview',request(key)).json()
            self.assertIn('临床草稿',preview['history_block'])
            self.call('POST',url+'/preview',{**request(key),'fingerprint':'0'*64},status=409)
        self.call('GET','/api/ai/consult/intake/unknown?species=dog',status=404)
        with db.SessionLocal() as s:self.assertEqual(s.query(models.ConsultSession).count(),before)

    def test_species_and_anonymous_rejected_before_ai(self):
        for key in intake.TEMPLATES:
            s=intake.build_snapshot(key,request(key))
            with patch.object(main,'run_agent') as agent:
                for auth,animal,status in [({},'dog',401),(self.owner_headers,'cat',409),(self.owner_headers,'other',409)]:
                    self.call('POST','/api/ai/consult/session',{'text':'合成','species':animal,'structured_intake_answers':s},headers=auth,status=status)
                agent.assert_not_called()

    def test_saved_history_edit_tokens_and_both_documents_preserve_original(self):
        for key in intake.TEMPLATES:
            for animal in ['dog','cat']:
                raw='  '+key+' 医生原文🐾\n<5 & {{literal}}\t尾部  \n'
                snap=intake.build_snapshot(key,request(key,animal,notes={'state':'observed','text':raw}))
                with patch.object(main,'run_agent',return_value={'risk_level':'low'}) as agent:
                    created=self.call('POST','/api/ai/consult/session',{'text':'合成问诊','species':animal,'structured_intake_answers':snap}).json()
                    self.assertIn(raw,agent.call_args.args[0])
                    self.assertNotIn('是否观察',agent.call_args.args[0])
                route='/api/ai/consult/session/'+created['session_id']
                self.call('GET',route,headers=self.other_headers,status=404)
                body={'patient_name':'B1合成'+animal,'species':animal,'chief_complaint':'合成主诉','history':'  原病史\n','owner_name':'合成宠主','coat_color':'合成毛色','structured_intake_answers':snap}
                preview=self.call('POST',route+'/preview-case',body).json()
                self.call('POST',route+'/save-case',{**body,'history':'changed','expected_preview_token':preview['preview_token']},status=409)
                saved=self.call('POST',route+'/save-case',{**body,'expected_preview_token':preview['preview_token']}).json()
                repeated=self.call('POST',route+'/save-case',{**body,'expected_preview_token':preview['preview_token']}).json()
                self.assertEqual(saved['case_id'],repeated['case_id'])
                caseurl='/api/cases/'+str(saved['case_id'])
                case=self.call('GET',caseurl).json()
                self.assertEqual(case['history'].count(raw),1)
                self.assertTrue(case['history'].startswith(body['history']))
                for template in DRAFTS:
                    doc={'case_id':case['id'],'template_id':template,'output':'docx'}
                    old=self.call('POST','/api/clinical-docs/render-preview',doc).json()
                    state=self.call('GET',caseurl+'/edit-state').json()
                    edit={'changes':{'history':case['history']+'\n医生更正'},'expected_case_token':state['case_token']}
                    ep=self.call('POST',caseurl+'/preview-edit',edit).json()
                    self.call('POST',caseurl+'/confirm-edit',{**edit,'expected_preview_token':ep['preview_token']})
                    self.call('POST','/api/clinical-docs/render',{**doc,'expected_content_snapshot':old['content_snapshot']},status=409)
                    case=self.call('GET',caseurl).json()
                    current=self.call('POST','/api/clinical-docs/render-preview',doc).json()
                    result=self.call('POST','/api/clinical-docs/render',{**doc,'expected_content_snapshot':current['content_snapshot']})
                    self.assertIn(case['history'],'\n'.join(paragraphs(result.content)))
                    self.assertEqual(self.call('GET',caseurl).json(),case)
                    if template=='outpatient_record_zh':
                        self.assertEqual(current['context']['visit.owner_name'],'合成宠主')
                        self.assertEqual(current['context']['visit.coat_color'],'合成毛色')

    def test_pupd_keeps_amount_frequency_units_and_uncertainty_separate(self):
        key='polyuria_polydipsia'
        raw={'water_amount':{'state':'uncertain','text':'  0.4 L / 12 h；仅一次估测，未完整测量  '},
             'urine_frequency':{'state':'observed','text':'白天4次；夜间不确定'},
             'urine_volume':{'state':'unobservable','text':'多宠家庭，无法归属；没有测量值'}}
        snapshot=intake.build_snapshot(key,request(key,**raw))
        text=main._structured_snapshot_text(snapshot)
        for value in raw.values():self.assertIn(value['text'],text)
        context=intake.ai_context(snapshot)
        self.assertIn('白天4次',context)
        self.assertNotIn('0.4 L',context)
        self.assertNotIn('无法归属',context)
        self.assertNotIn('ml/kg',text)
        self.assertEqual(intake.validate_snapshot(snapshot),snapshot)

    def test_cough_and_breathing_observations_are_independent(self):
        key='cough_breathing'
        raw={'cough':{'state':'absent','text':'医生明确否定咳嗽'},
             'cough_detail':{'state':'observed','text':'旧咳嗽分支原文保留'},
             'breathing':{'state':'observed','text':'医生记录呼吸表现'},
             'breathing_detail':{'state':'observed','text':'  休息时呼吸用力；活动时未观察  '},
             'respiratory_rate':{'state':'uncertain','text':'约 20 次 / 30 秒，估测；状态不确定'}}
        snapshot=intake.build_snapshot(key,request(key,**raw))
        text=main._structured_snapshot_text(snapshot)
        for value in raw.values():self.assertIn(value['text'],text)
        context=intake.ai_context(snapshot)
        self.assertIn(raw['breathing_detail']['text'],context)
        self.assertNotIn('咳嗽',context)
        self.assertNotIn('20',context)
        self.assertEqual(intake.validate_snapshot(snapshot),snapshot)

    def test_syncope_records_independent_observations_without_event_classification(self):
        key='syncope_seizure'
        raw={'consciousness':{'state':'uncertain','text':'当时未回应是否代表意识变化无法判断'},
             'consciousness_detail':{'state':'observed','text':'旧分支：曾怀疑意识变化'},
             'posture':{'state':'observed','text':'  左侧卧地🐾；目击者口述  '},
             'limb_movements':{'state':'unobservable','text':'被遮挡，未看到肢体'},
             'duration':{'state':'uncertain','text':'约 20 秒；未计时'},
             'after_episode':{'state':'observed','text':'事件后行走；恢复时间未记录'}}
        for animal in ['dog','cat']:
            snapshot=intake.build_snapshot(key,request(key,animal,**raw))
            text=main._structured_snapshot_text(snapshot)
            for value in raw.values():self.assertIn(value['text'],text)
            context=intake.ai_context(snapshot)
            self.assertIn(raw['posture']['text'],context)
            self.assertIn(raw['after_episode']['text'],context)
            for field in ['consciousness','consciousness_detail','limb_movements','duration']:
                self.assertNotIn(raw[field]['text'],context)
            self.assertEqual(intake.validate_snapshot(snapshot),snapshot)
            self.assertNotIn('risk_level',snapshot)

    def test_urinary_frequency_volume_and_last_observed_void_remain_independent_of_pupd(self):
        key='urinary_abnormality'
        raw={'urine_frequency':{'state':'observed','text':'  尝试 5 次 / 2 小时，确见排尿 1 次🐾  '},
             'per_void_volume':{'state':'uncertain','text':'估计 3 mL / 次；非测量值'},
             'last_urination':{'state':'observed','text':'2026-10-04 08:10；宠主目击，随后未观察'},
             'straining':{'state':'observed','text':'蹲姿反复'},
             'straining_detail':{'state':'observed','text':'有尝试，是否每次排出无法判断'},
             'pain':{'state':'absent','text':'医生明确否定疼痛相关表现'},
             'pain_detail':{'state':'observed','text':'先前疼痛分支保留'}}
        for animal in ['dog','cat']:
            body=request(key,animal,**raw)
            snapshot=intake.build_snapshot(key,body)
            text=main._structured_snapshot_text(snapshot)
            for value in raw.values():self.assertIn(value['text'],text)
            context=intake.ai_context(snapshot)
            self.assertIn(raw['urine_frequency']['text'],context)
            self.assertIn(raw['last_urination']['text'],context)
            self.assertIn(raw['straining_detail']['text'],context)
            for field in ['per_void_volume','pain','pain_detail']:self.assertNotIn(raw[field]['text'],context)
            self.assertEqual(intake.validate_snapshot(snapshot),snapshot)
            self.call('POST','/api/ai/consult/intake/polyuria_polydipsia/preview',body,status=409)
            self.call('POST','/api/ai/consult/intake/'+key+'/preview',request('polyuria_polydipsia',animal),status=409)

    def test_ai_failure_keeps_manual_history_with_no_session_write(self):
        for key in intake.TEMPLATES:
            snap=intake.build_snapshot(key,request(key,'cat',notes={'state':'observed','text':'原文🐾'}))
            with db.SessionLocal() as s:before=s.query(models.ConsultSession).count()
            with patch.object(main,'run_agent',side_effect=RuntimeError('synthetic unavailable')):
                with fixture.TestClient(main.app,raise_server_exceptions=False) as c:
                    self.assertEqual(c.post('/api/ai/consult/session',headers=self.owner_headers,json={'text':'合成','species':'cat','structured_intake_answers':snap}).status_code,500)
            history=main._structured_snapshot_text(snap)
            case=self.call('POST','/api/cases',{'patient_name':'B1手工猫','species':'cat','chief_complaint':'合成主诉','history':history},status=201).json()
            self.assertEqual(self.call('GET','/api/cases/'+str(case['id'])).json()['history'],history)
            with db.SessionLocal() as s:self.assertEqual(s.query(models.ConsultSession).count(),before)


if __name__=='__main__':unittest.main()

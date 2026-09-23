"""Document lifecycle on disposable SQLite and real auth; network denied by fixture."""
import io
import unittest
import zipfile
from xml.etree import ElementTree as ET
from test_consult_update_preview import main, db, models, feature_flags, TestClient, FIXTURE


LEGACY = ['admission_hospitalization_record_bilingual', 'discharge_summary_bilingual']
DRAFTS = ['outpatient_record_zh', 'owner_visit_summary_zh']
ALL_TEMPLATES = LEGACY + DRAFTS
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def paragraphs(content):
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        root = ET.fromstring(z.read('word/document.xml'))
    return [''.join(node.text or '' if node.tag == W+'t' else '\n' if node.tag == W+'br' else '\t' if node.tag == W+'tab' else '' for node in p.iter()) for p in root.iter(W+'p')]


class ClinicalDocLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert not main.app.dependency_overrides
        assert feature_flags.dangerous_enabled_flags() == []
        db.Base.metadata.create_all(db.engine, tables=[models.User.__table__, models.Case.__table__, models.ConsultSession.__table__])
        cls.client = TestClient(main.app)
        for name in ['owner', 'other']:
            email = name + '@example.com'
            assert cls.client.post('/auth/signup', json={'email': email, 'password': 'synthetic-test-password'}).status_code == 200
            r = cls.client.post('/auth/login', data={'username': email, 'password': 'synthetic-test-password'})
            setattr(cls, name, {'Authorization': 'Bearer ' + r.json()['access_token']})

    @classmethod
    def tearDownClass(cls):
        cls.client.close(); db.engine.dispose(); FIXTURE.cleanup()

    def create(self):
        r = self.client.post('/api/cases', headers=self.owner, json={'patient_name': '文书合成犬', 'chief_complaint': '合成主诉', 'history': '合成病史', 'treatment': '更正后处理🐾', 'prognosis': '合成随访'})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def render(self, cid, template, endpoint='render', headers=None):
        return self.client.post('/api/clinical-docs/' + endpoint, headers=self.owner if headers is None else headers,
                                json={'case_id': cid, 'template_id': template, 'output': 'docx'})

    def test_both_docx_templates_read_current_case_without_modifying_it(self):
        case = self.create()
        for template in ALL_TEMPLATES:
            r = self.render(case['id'], template)
            self.assertEqual(r.status_code, 200, r.text if r.status_code != 200 else '')
            self.assertEqual(r.headers['X-PMAI-Writes-Database'], 'false')
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                xml = ET.fromstring(z.read('word/document.xml'))
                text = ''.join(xml.itertext())
            for value in ['文书合成犬', '更正后处理🐾']:
                self.assertIn(value, text)
            self.assertNotIn('{{', text)
            self.assertEqual(self.client.get(f"/api/cases/{case['id']}", headers=self.owner).json(), case)

    def test_deleted_case_refuses_both_preview_and_download(self):
        case = self.create()
        self.assertEqual(self.client.delete(f"/api/cases/{case['id']}", headers=self.owner).status_code, 204)
        for endpoint in ['render', 'render-preview']:
            for template in ALL_TEMPLATES:
                self.assertEqual(self.render(case['id'], template, endpoint).status_code, 404)
        with db.SessionLocal() as session:
            self.assertIsNotNone(session.get(models.Case, case['id']).deleted_at)

    def test_other_owner_and_anonymous_cannot_export(self):
        cid = self.create()['id']
        for endpoint in ['render', 'render-preview']:
            for headers, status in [(self.other, 404), ({}, 401)]:
                for template in ALL_TEMPLATES:
                    self.assertEqual(self.render(cid, template, endpoint, headers).status_code, status)


    def test_template_list_keeps_legacy_and_adds_both_drafts(self):
        result = self.client.get('/api/clinical-docs/templates').json()
        self.assertEqual({t['template_id'] for t in result['templates']}, set(ALL_TEMPLATES))
        self.assertTrue(all(t['exists'] for t in result['templates']))

    def test_new_drafts_preserve_literal_multiline_text_and_no_write(self):
        case = self.create()
        raw = '  未见呕吐，不排除异物。\n复核 <5 & >2 \"引号\"；原文 {{visit.plan}} {{literal}}。\n\t保持缩进  '
        with db.SessionLocal() as session:
            row = session.get(models.Case, case['id']); row.history = raw
            row.weight = '7.2 kg'; row.analysis = '评估待核对，尚未确诊'; row.exam_findings = '查体记录 & 原文'
            session.commit()
        saved = self.client.get(f"/api/cases/{case['id']}", headers=self.owner).json()
        for template in DRAFTS:
            r = self.render(case['id'], template)
            self.assertEqual(r.status_code, 200, r.text if r.status_code != 200 else '')
            ps = paragraphs(r.content)
            self.assertIn(raw, ps)
            self.assertIn('体重：7.2 kg', ''.join(ps))
            self.assertIn(saved['analysis'], ps)
            self.assertIn(saved['exam_findings'], ps)
            self.assertIn(saved['treatment'], ps)
            self.assertIn('未单独记录复查安排，请医生补充确认', ps)
            self.assertNotIn('最终诊断', ''.join(ps))
            self.assertNotIn('电子章', ''.join(ps))
            self.assertEqual(self.client.get(f"/api/cases/{case['id']}", headers=self.owner).json(), saved)

    def test_new_blank_fields_stay_explicitly_missing(self):
        case = self.create()
        with db.SessionLocal() as session:
            row = session.get(models.Case, case['id'])
            for key in ['history', 'exam_findings', 'analysis', 'treatment', 'prognosis']:
                setattr(row, key, ' \t\n')
            row.weight = '0'; session.commit()
        for template in DRAFTS:
            preview = self.render(case['id'], template, 'render-preview').json()
            for key in ['visit.history', 'visit.exam', 'visit.assessment', 'visit.plan', 'visit.notes']:
                self.assertEqual(preview['context'][key], '未填写')
            self.assertEqual(preview['context']['visit.weight'], '0')
            self.assertEqual(preview['missing_required_keys'], [])
            r = self.render(case['id'], template); self.assertEqual(r.status_code, 200)
            text = ''.join(paragraphs(r.content))
            self.assertGreaterEqual(text.count('未填写'), 5)
            self.assertNotIn('无异常', text)

    def test_new_account_is_authenticated_and_follow_up_is_not_inferred(self):
        case = self.create()
        for template in DRAFTS:
            r = self.client.post('/api/clinical-docs/render-preview', headers=self.owner, json={
                'case_id': case['id'], 'template_id': template, 'clinician_id': 'forged-id',
                'clinician_name': 'forged-name', 'generator': 'forged-generator'})
            self.assertEqual(r.status_code, 200)
            ctx = r.json()['context']
            self.assertNotIn('forged', str(ctx))
            with db.SessionLocal() as session:
                expected = session.query(models.User).filter_by(email='owner@example.com').one().id
            self.assertEqual(ctx['export.account_id'], str(expected))
            self.assertEqual(ctx['visit.notes'], case['prognosis'])
            self.assertNotEqual(ctx['visit.follow_up'], case['prognosis'])

    def test_new_drafts_do_not_truncate_long_history(self):
        case = self.create()
        raw = ('否认腹泻；已记录情况仍需医生核对。\n' * 180) + '末行不可丢失'
        with db.SessionLocal() as session:
            session.get(models.Case, case['id']).history = raw; session.commit()
        for template in DRAFTS:
            r = self.render(case['id'], template); self.assertEqual(r.status_code, 200)
            self.assertIn(raw, paragraphs(r.content))

    def test_new_drafts_reject_unapproved_diagnostic_append(self):
        case = self.create()
        for template in DRAFTS:
            for endpoint in ['render', 'render-preview']:
                r = self.client.post('/api/clinical-docs/'+endpoint, headers=self.owner, json={
                    'case_id': case['id'], 'template_id': template, 'include_diagnostic_data': True})
                self.assertEqual(r.status_code, 422)
                self.assertIn('不支持附加诊断数据合并', r.json()['detail'])

    def test_new_hash_and_document_follow_current_saved_correction(self):
        case = self.create()
        for template in DRAFTS:
            before = self.render(case['id'], template)
            new = '本次更正原文-'+template
            r = self.client.put(f"/api/cases/{case['id']}", headers=self.owner, json={'treatment': new})
            self.assertEqual(r.status_code, 200)
            after = self.render(case['id'], template); self.assertEqual(after.status_code, 200)
            self.assertIn(new, paragraphs(after.content))
            self.assertNotEqual(before.headers['x-pmai-document-hash'], after.headers['x-pmai-document-hash'])

    def test_new_invalid_xml_control_refuses_instead_of_silently_changing_text(self):
        case = self.create()
        with db.SessionLocal() as session:
            session.get(models.Case, case['id']).history = '内容\x01未改'; session.commit()
        for template in DRAFTS:
            self.assertEqual(self.render(case['id'], template).status_code, 422)
        with db.SessionLocal() as session:
            self.assertEqual(session.get(models.Case, case['id']).history, '内容\x01未改')


if __name__ == '__main__':
    unittest.main(verbosity=2)

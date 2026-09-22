"""Document lifecycle on disposable SQLite and real auth; network denied by fixture."""
import io
import unittest
import zipfile
from xml.etree import ElementTree as ET
from test_consult_update_preview import main, db, models, feature_flags, TestClient, FIXTURE


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
        for template in ['admission_hospitalization_record_bilingual', 'discharge_summary_bilingual']:
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
            for template in ['admission_hospitalization_record_bilingual', 'discharge_summary_bilingual']:
                self.assertEqual(self.render(case['id'], template, endpoint).status_code, 404)
        with db.SessionLocal() as session:
            self.assertIsNotNone(session.get(models.Case, case['id']).deleted_at)

    def test_other_owner_and_anonymous_cannot_export(self):
        cid = self.create()['id']
        for endpoint in ['render', 'render-preview']:
            for headers, status in [(self.other, 404), ({}, 401)]:
                self.assertEqual(self.render(cid, 'discharge_summary_bilingual', endpoint, headers).status_code, status)


if __name__ == '__main__':
    unittest.main(verbosity=2)

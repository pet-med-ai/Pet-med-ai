"""Real authenticated manual creation and persistence in a disposable SQLite DB.

Reuse the existing network-denying fixture, without running its consultation tests.
No external requests, migrations, production data or deployed services are used.
"""
import unittest
from test_consult_update_preview import main, db, models, feature_flags, TestClient, FIXTURE


class ManualCaseCreateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert not main.app.dependency_overrides
        assert feature_flags.dangerous_enabled_flags() == []
        db.Base.metadata.create_all(db.engine, tables=[models.User.__table__, models.Case.__table__, models.ConsultSession.__table__])
        cls.client = TestClient(main.app)
        for name in ["owner", "other"]:
            email = name + "@example.com"
            r = cls.client.post("/auth/signup", json={"email": email, "password": "synthetic-test-password"})
            assert r.status_code == 200, r.text
            r = cls.client.post("/auth/login", data={"username": email, "password": "synthetic-test-password"})
            assert r.status_code == 200, r.text
            setattr(cls, name + "_headers", {"Authorization": "Bearer " + r.json()["access_token"]})

    @classmethod
    def tearDownClass(cls):
        cls.client.close(); db.engine.dispose(); FIXTURE.cleanup()

    def payload(self):
        return {"patient_name": "合成手工病例🐾", "species": "dog", "sex": "M", "age_info": "2y",
                "breed": "虚构品种", "weight": "5.2kg", "coat_color": None, "owner_name": "虚构主人",
                "owner_phone": None, "chief_complaint": "  合成主诉\r\n ", "history": "  原始病史🐾\r\n\t ",
                "exam_findings": "合成体检", "analysis": "  手工分析\r\n ",
                "treatment": "手工处理 <script>literal</script>", "prognosis": "  手工随访\n "}

    def count(self):
        with db.SessionLocal() as session:
            return session.query(models.Case).count()

    def test_create_and_new_connection_readback_preserve_all_fifteen_fields(self):
        body = self.payload(); before = self.count()
        r = self.client.post("/api/cases", headers=self.owner_headers, json=body)
        self.assertEqual(r.status_code, 201, r.text); cid = r.json()["id"]
        db.engine.dispose()
        r = self.client.get(f"/api/cases/{cid}", headers=self.owner_headers)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual({k: r.json()[k] for k in body}, body)
        self.assertEqual(self.count(), before + 1)
        with db.SessionLocal() as session:
            self.assertEqual(session.query(models.ConsultSession).count(), 0)

    def test_legacy_minimal_payload_remains_supported(self):
        r = self.client.post("/api/cases", headers=self.owner_headers,
                             json={"patient_name": "兼容合成病例", "chief_complaint": "仅两个必填项"})
        self.assertEqual(r.status_code, 201, r.text)
        for field in ["analysis", "treatment", "prognosis", "history"]:
            self.assertIsNone(r.json()[field])

    def test_invalid_clinical_field_types_are_rejected_without_creating(self):
        for field in ["analysis", "treatment", "prognosis"]:
            with self.subTest(field=field):
                before = self.count()
                r = self.client.post("/api/cases", headers=self.owner_headers, json={**self.payload(), field: ["invalid"]})
                self.assertEqual(r.status_code, 422); self.assertEqual(self.count(), before)

    def test_anonymous_create_is_rejected_without_writes(self):
        before = self.count()
        r = self.client.post("/api/cases", json=self.payload())
        self.assertEqual(r.status_code, 401); self.assertEqual(self.count(), before)

    def test_new_creation_does_not_modify_existing_case_and_other_user_cannot_read(self):
        original = self.client.post("/api/cases", headers=self.owner_headers, json=self.payload()).json()
        r = self.client.post("/api/cases", headers=self.owner_headers, json={**self.payload(), "history": "另一份合成病史"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.client.get(f"/api/cases/{original['id']}", headers=self.owner_headers).json(), original)
        self.assertEqual(self.client.get(f"/api/cases/{r.json()['id']}", headers=self.other_headers).status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""First-save route acceptance. Reuses only the isolated fixture bootstrap.
Run separately: python tests/test_consult_first_save.py
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4
import unittest
import test_consult_update_preview as fixture

main, db, models = fixture.main, fixture.db, fixture.models


class ConsultFirstSaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ConsultUpdatePreviewTests.setUpClass()
        for name in ["client", "owner_headers", "other_headers", "owner_id"]:
            setattr(cls, name, getattr(fixture.ConsultUpdatePreviewTests, name))

    @classmethod
    def tearDownClass(cls):
        fixture.ConsultUpdatePreviewTests.tearDownClass()

    def setUp(self):
        self.sid = uuid4().hex
        self.url = f"/api/ai/consult/session/{self.sid}"
        with db.SessionLocal() as session:
            session.add(models.ConsultSession(session_uid=self.sid, owner_id=self.owner_id, text="原始合成问诊", answers=[{"question": "多久", "answer": "两天"}], result={"risk_level": "low"}))
            session.commit()
        self.initial_count = self.count()
        self.body = {
            "patient_name": " 合成犬A ", "species": "dog", "sex": "M", "age_info": "4岁",
            "breed": "合成品种", "weight": "5kg", "coat_color": "白", "owner_name": "合成主人", "owner_phone": "synthetic-only",
            "chief_complaint": "医生核对后的主诉", "history": "  医生补记🐾\r\n保留原文和尾部空白。  \n\t",
            "exam_findings": "合成体检记录", "structured_intake_answers": {"sections": [{"title": "用药史", "answers": [{"label": "此前用药", "answer": "合成补充内容"}]}]},
        }

    def count(self):
        with db.SessionLocal() as session:
            return session.query(models.Case).count()

    def preview(self, body=None):
        response = self.client.post(self.url + "/preview-case", headers=self.owner_headers, json=self.body if body is None else body)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def save(self, body=None):
        return self.client.post(self.url + "/save-case", headers=self.owner_headers, json=self.body if body is None else body)

    def session(self):
        response = self.client.get(self.url, headers=self.owner_headers)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def read(self, case_id):
        response = self.client.get(f"/api/cases/{case_id}", headers=self.owner_headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_preview_no_write_and_all_fifteen_fields_match_persisted_readback(self):
        before = self.session()
        preview = self.preview()
        self.assertEqual(self.count(), self.initial_count)
        self.assertEqual(self.session(), before)
        self.assertEqual(preview, self.preview())
        self.assertTrue(preview["history"].startswith(self.body["history"]))
        self.assertIn("合成补充内容", preview["history"])
        self.assertIn("两天", preview["history"])
        response = self.save({**self.body, "expected_preview_token": preview["preview_token"]})
        self.assertEqual(response.status_code, 200, response.text)
        case_id = response.json()["case_id"]
        db.engine.dispose()
        record = self.read(case_id)
        for name in main.CONSULT_SAVE_FIELDS:
            self.assertEqual(record[name], preview[name], name)
        self.assertEqual(record["chief_complaint"], self.body["chief_complaint"])
        self.assertEqual(self.session()["case_id"], case_id)
        self.assertEqual(self.count(), self.initial_count + 1)

    def test_editing_each_input_invalidates_confirmation_without_writes(self):
        preview = self.preview()
        for name in self.body:
            with self.subTest(field=name):
                changed = {**self.body, name: {} if name == "structured_intake_answers" else "修改后的内容", "expected_preview_token": preview["preview_token"]}
                response = self.save(changed)
                self.assertEqual(response.status_code, 409, response.text)
                self.assertEqual(self.count(), self.initial_count)
                self.assertIsNone(self.session()["case_id"])

    def test_followup_after_preview_requires_new_confirmation(self):
        preview = self.preview()
        response = self.client.post(self.url + "/answer", headers=self.owner_headers, json={"question": "合成补问", "answer": "新的回答"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.save({**self.body, "expected_preview_token": preview["preview_token"]}).status_code, 409)
        new_preview = self.preview()
        self.assertEqual(self.save({**self.body, "expected_preview_token": new_preview["preview_token"]}).status_code, 200)

    def test_repeated_save_after_lost_response_returns_same_case_and_keeps_content(self):
        preview = self.preview()
        request = {**self.body, "expected_preview_token": preview["preview_token"]}
        first = self.save(request).json()
        record = self.read(first["case_id"])
        second = self.save(request)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["message"], "already_saved")
        self.assertEqual(second.json()["case_id"], first["case_id"])
        self.assertEqual(self.save({**request, "history": "后来的不同输入"}).json()["case_id"], first["case_id"])
        self.assertEqual(self.read(first["case_id"]), record)
        self.assertEqual(self.count(), self.initial_count + 1)

    def test_unowned_session_preview_does_not_claim_ownership(self):
        with db.SessionLocal() as session:
            row = session.query(models.ConsultSession).filter_by(session_uid=self.sid).one()
            row.owner_id = None; session.commit()
        preview = self.preview()
        with db.SessionLocal() as session:
            self.assertIsNone(session.query(models.ConsultSession).filter_by(session_uid=self.sid).one().owner_id)
        response = self.save({**self.body, "expected_preview_token": preview["preview_token"]})
        self.assertEqual(response.status_code, 200, response.text)
        with db.SessionLocal() as session:
            self.assertEqual(session.query(models.ConsultSession).filter_by(session_uid=self.sid).one().owner_id, self.owner_id)

    def test_old_client_without_token_or_new_fields_retains_compatibility(self):
        preview = self.preview({"patient_name": "旧客户端合成犬"})
        response = self.save({"patient_name": "旧客户端合成犬"})
        self.assertEqual(response.status_code, 200, response.text)
        record = self.read(response.json()["case_id"])
        self.assertEqual(record["chief_complaint"], "原始合成问诊")
        self.assertTrue(record["history"].startswith("【动态问诊追问记录】"))
        for name in main.CONSULT_SAVE_FIELDS:
            self.assertEqual(record[name], preview[name])

    def test_auth_and_foreign_ownership_reject_both_routes_without_writes(self):
        for route in ["/preview-case", "/save-case"]:
            self.assertEqual(self.client.post(self.url + route, json=self.body).status_code, 401)
            self.assertEqual(self.client.post(self.url + route, json=self.body, headers=self.other_headers).status_code, 404)
        self.assertEqual(self.count(), self.initial_count)

    def test_invalid_or_wrong_token_cannot_create_a_case(self):
        for token, status in [("x", 422), ("测" * 64, 422), ("0" * 64, 409)]:
            self.assertEqual(self.save({**self.body, "expected_preview_token": token}).status_code, status)
        self.assertEqual(self.count(), self.initial_count)

    def simultaneous_saves(self, headers):
        original = main._consult_save_snapshot
        barrier = Barrier(2, timeout=10)
        def synchronized_snapshot(*args):
            snapshot = original(*args)
            barrier.wait()  # Force both real routes to observe the initially unbound session.
            return snapshot
        def worker(auth):
            with fixture.TestClient(main.app) as client:
                return client.post(self.url + "/save-case", headers=auth, json=self.body)
        # The only application patch is this fixture scheduling barrier. All route,
        # authentication, transaction and DB operations remain the real implementation.
        with patch.object(main, "_consult_save_snapshot", side_effect=synchronized_snapshot):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(worker, auth) for auth in headers]
                return [future.result(timeout=20) for future in futures]

    def test_two_simultaneous_saves_bind_one_case_without_orphans(self):
        responses = self.simultaneous_saves([self.owner_headers, self.owner_headers])
        self.assertEqual([r.status_code for r in responses], [200, 200])
        self.assertEqual(len({r.json()["case_id"] for r in responses}), 1)
        self.assertEqual({r.json()["message"] for r in responses}, {"saved", "already_saved"})
        self.assertEqual(self.count(), self.initial_count + 1)

    def test_competing_owners_cannot_claim_or_read_another_owners_case(self):
        with db.SessionLocal() as session:
            row = session.query(models.ConsultSession).filter_by(session_uid=self.sid).one()
            row.owner_id = None; session.commit()
        responses = self.simultaneous_saves([self.owner_headers, self.other_headers])
        self.assertEqual(sorted(r.status_code for r in responses), [200, 404])
        self.assertEqual(self.count(), self.initial_count + 1)
        self.assertNotIn("case_id", next(r for r in responses if r.status_code == 404).json())


if __name__ == "__main__":
    unittest.main(verbosity=2)

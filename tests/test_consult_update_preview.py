"""Real ASGI routes and JWT against a disposable SQLite fixture; no migrations.
Run in its own process: python tests/test_consult_update_preview.py
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = tempfile.TemporaryDirectory(prefix="pmai-update-preview-")
DATABASE = Path(FIXTURE.name) / "synthetic.sqlite3"
os.environ.clear()
os.environ.update({
    "DATABASE_URL": "sqlite:///" + str(DATABASE),
    "SECRET_KEY": "synthetic-update-preview-test-key",
    "ENVIRONMENT": "test", "RENDER": "false", "PYTHONDONTWRITEBYTECODE": "1",
})
sys.dont_write_bytecode = True
# Use the same flat import layout as `cd backend && uvicorn main:app`.
sys.path[:] = [str(ROOT / "backend")] + [p for p in sys.path if Path(p or os.getcwd()).resolve() != ROOT]


def isolation(event, args):
    if event in {"socket.connect", "socket.connect_ex", "socket.bind", "socket.getaddrinfo", "subprocess.Popen", "os.system"}:
        raise RuntimeError("Networking and subprocesses are forbidden in this fixture")
    if event == "sqlite3.connect" and Path(str(args[0])).resolve() != DATABASE:
        raise RuntimeError("Unexpected database")


sys.addaudithook(isolation)
from fastapi.testclient import TestClient
import main
import db
import models
import feature_flags


class ConsultUpdatePreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert not main.app.dependency_overrides
        assert feature_flags.dangerous_enabled_flags() == []
        db.Base.metadata.create_all(db.engine, tables=[models.User.__table__, models.Case.__table__, models.ConsultSession.__table__])
        cls.client = TestClient(main.app)
        for name in ["owner", "other"]:
            email = name + "@example.com"
            response = cls.client.post("/auth/signup", json={"email": email, "password": "synthetic-test-password"})
            assert response.status_code == 200, response.text
            response = cls.client.post("/auth/login", data={"username": email, "password": "synthetic-test-password"})
            assert response.status_code == 200, response.text
            setattr(cls, name + "_headers", {"Authorization": "Bearer " + response.json()["access_token"]})
        with db.SessionLocal() as session:
            cls.owner_id = session.query(models.User).filter_by(email="owner@example.com").one().id

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        db.engine.dispose()
        FIXTURE.cleanup()

    def setUp(self):
        self.sid = uuid4().hex
        self.history = "  医生已保存原文🐾\r\n既往用药待核对。  \n\t"
        with db.SessionLocal() as session:
            case = models.Case(owner_id=self.owner_id, patient_name="合成犬", species="dog", chief_complaint="原主诉", history=self.history,
                               exam_findings="合成体检记录", analysis="原分析", treatment="原处理", prognosis="原风险")
            session.add(case); session.flush(); self.cid = case.id
            session.add(models.ConsultSession(owner_id=self.owner_id, case_id=case.id, session_uid=self.sid, text="合成问诊主诉",
                answers=[{"question": "合成追问", "answer": "合成回答"}], result={"risk_level": "low", "actions": ["合成建议"]}))
            session.commit()
        self.url = f"/api/ai/consult/session/{self.sid}"

    def preview(self):
        response = self.client.post(self.url + "/preview-update-case", headers=self.owner_headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def update(self, preview):
        return self.client.post(self.url + "/update-case", headers=self.owner_headers,
                                json={"expected_preview_token": preview["preview_token"]})

    def read(self):
        response = self.client.get(f"/api/cases/{self.cid}", headers=self.owner_headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def change_case(self, **fields):
        response = self.client.put(f"/api/cases/{self.cid}", headers=self.owner_headers, json=fields)
        self.assertEqual(response.status_code, 200, response.text)

    def test_preview_is_read_only_and_save_readback_matches_all_six_fields(self):
        before = self.read()
        preview = self.preview()
        self.assertEqual(self.read(), before)
        self.assertEqual(self.preview(), preview)
        self.assertEqual(set(preview["proposed"]), set(main.CONSULT_UPDATE_FIELDS))
        self.assertTrue(preview["proposed"]["history"].startswith(self.history))
        self.assertEqual(preview["before"]["history"], self.history)
        self.assertEqual(self.update(preview).status_code, 200)
        db.engine.dispose()  # force persisted read on a new database connection
        actual = self.read()
        for field in main.CONSULT_UPDATE_FIELDS:
            self.assertEqual(actual[field], preview["proposed"][field], field)

    def test_case_change_rejects_stale_preview_without_writes(self):
        for field in main.CONSULT_UPDATE_FIELDS:
            with self.subTest(field=field):
                preview = self.preview()
                self.change_case(**{field: "医生后续补充"})
                current = self.read()
                self.assertEqual(self.update(preview).status_code, 409)
                self.assertEqual(self.read(), current)

    def test_patient_identity_change_invalidates_preview(self):
        preview = self.preview()
        self.change_case(patient_name="修改后的合成犬")
        self.assertEqual(self.update(preview).status_code, 409)

    def test_answer_change_rejects_stale_preview_without_writes(self):
        preview = self.preview()
        response = self.client.post(self.url + "/answer", headers=self.owner_headers, json={"question": "合成补问", "answer": "新的补充"})
        self.assertEqual(response.status_code, 200, response.text)
        current = self.read()
        self.assertEqual(self.update(preview).status_code, 409)
        self.assertEqual(self.read(), current)
        refreshed = self.preview()
        self.assertEqual(self.update(refreshed).status_code, 200)

    def test_result_change_invalidates_preview(self):
        preview = self.preview()
        with db.SessionLocal() as session:
            consult = session.query(models.ConsultSession).filter_by(session_uid=self.sid).one()
            consult.result = {"risk_level": "high"}
            session.commit()
        self.assertEqual(self.update(preview).status_code, 409)

    def test_preview_token_cannot_be_reused_after_save(self):
        preview = self.preview()
        self.assertEqual(self.update(preview).status_code, 200)
        first = self.read()
        self.assertEqual(self.update(preview).status_code, 409)
        self.assertEqual(self.read(), first)
        self.assertEqual(self.update(self.preview()).status_code, 200)
        self.assertEqual(self.read()["history"], first["history"])

    def test_legacy_bodyless_update_still_matches_preview(self):
        preview = self.preview()
        response = self.client.post(self.url + "/update-case", headers=self.owner_headers)
        self.assertEqual(response.status_code, 200, response.text)
        actual = self.read()
        for field in main.CONSULT_UPDATE_FIELDS:
            self.assertEqual(actual[field], preview["proposed"][field])

    def test_authentication_and_ownership_on_both_routes(self):
        for route in ["/preview-update-case", "/update-case"]:
            self.assertEqual(self.client.post(self.url + route).status_code, 401)
            self.assertEqual(self.client.post(self.url + route, headers=self.other_headers).status_code, 404)
        self.assertEqual(self.read()["history"], self.history)

    def test_missing_and_unbound_sessions(self):
        for route in ["/preview-update-case", "/update-case"]:
            self.assertEqual(self.client.post("/api/ai/consult/session/missing" + route, headers=self.owner_headers).status_code, 404)
        with db.SessionLocal() as session:
            consult = session.query(models.ConsultSession).filter_by(session_uid=self.sid).one()
            consult.case_id = None; session.commit()
        for route in ["/preview-update-case", "/update-case"]:
            self.assertEqual(self.client.post(self.url + route, headers=self.owner_headers).status_code, 400)

    def test_bound_case_owned_by_another_user_is_rejected(self):
        with db.SessionLocal() as session:
            other = session.query(models.User).filter_by(email="other@example.com").one()
            case = session.get(models.Case, self.cid); case.owner_id = other.id; session.commit()
        for route in ["/preview-update-case", "/update-case"]:
            self.assertEqual(self.client.post(self.url + route, headers=self.owner_headers).status_code, 404)

    def test_invalid_token_does_not_write(self):
        before = self.read()
        for body, status in [({}, 422), ({"expected_preview_token": "short"}, 422), ({"expected_preview_token": "测" * 64}, 422), ({"expected_preview_token": "0" * 64}, 409)]:
            response = self.client.post(self.url + "/update-case", headers=self.owner_headers, json=body)
            self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(self.read(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)

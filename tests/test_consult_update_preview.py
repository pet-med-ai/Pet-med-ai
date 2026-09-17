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

    def note_preview(self, note):
        response = self.client.post(self.url + "/preview-update-case", headers=self.owner_headers, json={"history_addendum": note})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def note_update(self, note, preview):
        return self.client.post(self.url + "/update-case", headers=self.owner_headers,
                                json={"history_addendum": note, "expected_preview_token": preview["preview_token"]})

    def test_addendum_preview_and_readback_preserve_exact_old_and_new_text(self):
        note = "  复诊补记🐾\r\n用药经过。  \n"
        before = self.read(); preview = self.note_preview(note)
        self.assertEqual(self.read(), before)
        self.assertEqual(preview["history_addendum"], note)
        self.assertTrue(preview["proposed"]["history"].startswith(self.history))
        self.assertTrue(preview["proposed"]["history"].endswith("【医生病史补记】\n" + note))
        self.assertEqual(self.note_update(note, preview).status_code, 200)
        self.assertEqual(self.read()["history"], preview["proposed"]["history"])

    def test_addendum_changed_or_omitted_invalidates_confirmation_without_write(self):
        note = "reviewed note"; preview = self.note_preview(note); before = self.read()
        for changed in ["changed note", "", note + " "]:
            self.assertEqual(self.note_update(changed, preview).status_code, 409)
            self.assertEqual(self.read(), before)
        self.assertEqual(self.update(preview).status_code, 409)
        response = self.client.post(self.url + "/update-case", headers=self.owner_headers, json={"history_addendum": note})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.read(), before)

    def test_identical_addendum_is_not_duplicated_and_blank_addendum_is_noop(self):
        note = "补记原文"
        self.assertEqual(self.note_update(note, self.note_preview(note)).status_code, 200)
        once = self.read()["history"]
        self.assertEqual(self.note_update(note, self.note_preview(note)).status_code, 200)
        self.assertEqual(self.read()["history"], once)
        self.assertEqual(self.note_update(" \n\t", self.note_preview(" \n\t")).status_code, 200)
        self.assertEqual(self.read()["history"], once)

    def test_addendum_authentication_shape_and_length_are_validated(self):
        before = self.read()
        for suffix in ["/preview-update-case", "/update-case"]:
            body = {"history_addendum": "note", "expected_preview_token": "0" * 64}
            self.assertEqual(self.client.post(self.url+suffix, json=body).status_code, 401)
            self.assertEqual(self.client.post(self.url+suffix, headers=self.other_headers, json=body).status_code, 404)
            for invalid in ["x" * 20001, 12, None, {}]:
                self.assertEqual(self.client.post(self.url+suffix, headers=self.owner_headers, json={**body, "history_addendum": invalid}).status_code, 422)
        self.assertEqual(self.read(), before)

    def test_intervening_doctor_history_rejects_stale_addendum_and_is_preserved_after_repreview(self):
        note = "当前补记"; preview = self.note_preview(note)
        changed = self.history + "\n另一医生新记载"
        self.change_case(history=changed)
        self.assertEqual(self.note_update(note, preview).status_code, 409)
        self.assertEqual(self.read()["history"], changed)
        self.assertEqual(self.note_update(note, self.note_preview(note)).status_code, 200)
        self.assertTrue(self.read()["history"].startswith(changed))

    def scoped_preview(self, note, mode):
        r = self.client.post(self.url + "/preview-update-case", headers=self.owner_headers, json={"history_addendum": note, "update_mode": mode})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def scoped_update(self, note, mode, preview):
        return self.client.post(self.url + "/update-case", headers=self.owner_headers,
                                json={"history_addendum": note, "update_mode": mode, "expected_preview_token": preview["preview_token"]})

    def test_history_only_changes_exactly_history_not_other_doctor_fields(self):
        before = self.read(); note = "  新增补记🐾\r\n保留空格。  "
        p = self.scoped_preview(note, "history_only")
        self.assertEqual(p["update_mode"], "history_only")
        self.assertEqual(self.read(), before)
        for key in main.CONSULT_UPDATE_FIELDS:
            if key != "history": self.assertEqual(p["proposed"][key], before[key])
        self.assertNotIn("合成回答", p["proposed"]["history"])
        self.assertEqual(self.scoped_update(note, "history_only", p).status_code, 200)
        after = self.read()
        self.assertEqual(after["history"], p["proposed"]["history"])
        self.assertEqual({k:v for k,v in after.items() if k != "history"}, {k:v for k,v in before.items() if k != "history"})

    def test_sync_keeps_chief_and_exam_bytes_including_empty_values(self):
        for chief, exam in [("  医生确认主诉🐾\r\n ", "  确认体检\r\n "), ("", "")]:
            self.change_case(chief_complaint=chief, exam_findings=exam)
            p = self.scoped_preview("", "consult_sync")
            self.assertEqual(p["proposed"]["chief_complaint"], chief)
            self.assertEqual(p["proposed"]["exam_findings"], exam)
            self.assertEqual(self.scoped_update("", "consult_sync", p).status_code, 200)
            current = self.read()
            self.assertEqual(current["chief_complaint"], chief)
            self.assertEqual(current["exam_findings"], exam)
            self.assertIn("合成回答", current["history"])

    def test_scope_changed_or_omitted_cannot_reuse_history_only_confirmation(self):
        note = "本次补记"; p = self.scoped_preview(note, "history_only"); before = self.read()
        self.assertEqual(self.scoped_update(note, "consult_sync", p).status_code, 409)
        self.assertEqual(self.note_update(note, p).status_code, 409)
        self.assertEqual(self.read(), before)
        other = self.scoped_preview(note, "consult_sync")
        self.assertNotEqual(other["preview_token"], p["preview_token"])
        self.assertEqual(self.scoped_update(note, "history_only", other).status_code, 409)

    def test_invalid_scope_and_blank_history_only_cannot_write(self):
        before = self.read()
        for suffix in ["/preview-update-case", "/update-case"]:
            for mode in ["unknown", None, 1, {}]:
                r = self.client.post(self.url+suffix, headers=self.owner_headers, json={"history_addendum":"note", "update_mode":mode, "expected_preview_token":"0"*64})
                self.assertEqual(r.status_code, 422)
            r = self.client.post(self.url+suffix, headers=self.owner_headers, json={"history_addendum":" \n\t", "update_mode":"history_only", "expected_preview_token":"0"*64})
            self.assertEqual(r.status_code, 400)
        self.assertEqual(self.read(), before)

    def test_history_only_repeated_note_never_imports_pending_consult_summary(self):
        note = "只补记一次"
        for index in range(2):
            p = self.scoped_preview(note, "history_only")
            self.assertEqual(self.scoped_update(note, "history_only", p).status_code, 200)
        current = self.read()
        self.assertEqual(current["history"].count(note), 1)
        self.assertNotIn("合成回答", current["history"])
        self.assertEqual(current["analysis"], "原分析")

    def test_history_only_detects_intervening_change_to_preserved_fields(self):
        note = "本次补记"; p = self.scoped_preview(note, "history_only")
        self.change_case(treatment="另一医生更新治疗")
        current = self.read()
        self.assertEqual(self.scoped_update(note, "history_only", p).status_code, 409)
        self.assertEqual(self.read(), current)
        p = self.scoped_preview(note, "history_only")
        self.assertEqual(self.scoped_update(note, "history_only", p).status_code, 200)
        self.assertEqual(self.read()["treatment"], current["treatment"])


    def edit_state(self):
        r = self.client.get(f"/api/cases/{self.cid}/edit-state", headers=self.owner_headers)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def edit_preview(self, changes, state=None):
        request = {"changes": changes, "expected_case_token": (state or self.edit_state())["case_token"]}
        r = self.client.post(f"/api/cases/{self.cid}/preview-edit", headers=self.owner_headers, json=request)
        self.assertEqual(r.status_code, 200, r.text)
        return request, r.json()

    def edit_confirm(self, request, preview):
        return self.client.post(f"/api/cases/{self.cid}/confirm-edit", headers=self.owner_headers,
                                json={**request, "expected_preview_token": preview["preview_token"]})

    def test_editor_only_changed_treatment_writes_and_preserves_all_other_fields(self):
        before = self.read(); state = self.edit_state()
        self.assertEqual(set(state["before"]), set(main.CASE_EDIT_FIELDS))
        request, preview = self.edit_preview({"treatment": "  医生治疗🐾\r\n保留空格  "}, state)
        self.assertEqual(self.read(), before)
        self.assertEqual(set(preview["changes"]), {"treatment"})
        self.assertEqual(self.edit_confirm(request, preview).status_code, 200)
        after = self.read()
        self.assertEqual(after["treatment"], request["changes"]["treatment"])
        self.assertEqual({k:v for k,v in after.items() if k != "treatment"}, {k:v for k,v in before.items() if k != "treatment"})

    def test_editor_exact_fifteen_field_changes_and_intentional_history_replacement(self):
        changes = {key: "  修订"+key+"🐾\r\n " for key in main.CASE_EDIT_FIELDS}
        changes.update(species="cat", owner_phone="", prognosis=None)
        request, preview = self.edit_preview(changes)
        self.assertEqual(self.edit_confirm(request, preview).status_code, 200)
        actual = self.read()
        for key, value in changes.items(): self.assertEqual(actual[key], value, key)
        self.assertEqual(actual["history"], changes["history"])

    def test_editor_opened_stale_case_cannot_preview_without_reloading(self):
        state = self.edit_state(); self.change_case(history=self.history+"医生新增")
        before = self.read()
        r = self.client.post(f"/api/cases/{self.cid}/preview-edit", headers=self.owner_headers,
                             json={"changes":{"treatment":"新治疗"},"expected_case_token":state["case_token"]})
        self.assertEqual(r.status_code, 409); self.assertEqual(self.read(), before)
        request, preview = self.edit_preview({"treatment":"新治疗"})
        self.assertEqual(self.edit_confirm(request, preview).status_code, 200)
        self.assertEqual(self.read()["history"], before["history"])

    def test_editor_all_saved_field_changes_expire_preview(self):
        for key in main.CASE_EDIT_FIELDS:
            with self.subTest(key=key):
                request, preview = self.edit_preview({"history":"本次病史修订"})
                self.change_case(**{key:"其他医生新值"})
                before = self.read()
                self.assertEqual(self.edit_confirm(request, preview).status_code, 409)
                self.assertEqual(self.read(), before)

    def test_editor_changed_payload_or_wrong_confirmation_never_writes(self):
        request, preview = self.edit_preview({"treatment":"新治疗"}); before = self.read()
        self.assertEqual(self.edit_confirm({**request,"changes":{"treatment":"不同治疗"}},preview).status_code,409)
        self.assertEqual(self.edit_confirm(request,{**preview,"preview_token":"0"*64}).status_code,409)
        self.assertEqual(self.read(),before)

    def test_editor_auth_ownership_and_deleted_visibility_remain_enforced(self):
        from datetime import datetime
        request, preview = self.edit_preview({"treatment":"新治疗"}); before = self.read()
        for headers, code in [({},401),(self.other_headers,404)]:
            r=self.client.get(f"/api/cases/{self.cid}/edit-state",headers=headers)
            self.assertEqual(r.status_code,code)
            for suffix in ["preview-edit","confirm-edit"]:
                body=request if suffix=="preview-edit" else {**request,"expected_preview_token":preview["preview_token"]}
                r=self.client.post(f"/api/cases/{self.cid}/{suffix}",headers=headers,json=body)
                self.assertEqual(r.status_code,code)
        self.assertEqual(self.read(),before)
        with db.SessionLocal() as session:
            session.get(models.Case,self.cid).deleted_at=datetime.utcnow();session.commit()
        self.assertEqual(self.client.get(f"/api/cases/{self.cid}/edit-state",headers=self.owner_headers).status_code,404)
        self.assertEqual(self.edit_confirm(request,preview).status_code,404)

    def test_editor_rejects_unknown_fields_bad_types_blank_required_and_empty_patch(self):
        before=self.read();state=self.edit_state()
        for changes, code in [({"owner_id":7},422),({"treatment":42},422),({"chief_complaint":None},400),({"patient_name":"  "},400),({},400),({"history":self.history},400)]:
            request={"changes":changes,"expected_case_token":state["case_token"]}
            for suffix in ["preview-edit","confirm-edit"]:
                body=request if suffix=="preview-edit" else {**request,"expected_preview_token":"0"*64}
                r=self.client.post(f"/api/cases/{self.cid}/{suffix}",headers=self.owner_headers,json=body)
                self.assertEqual(r.status_code,code,r.text)
        self.assertEqual(self.read(),before)

    def test_editor_repeat_confirmation_cannot_overwrite_again(self):
        request,preview=self.edit_preview({"treatment":"新治疗"})
        self.assertEqual(self.edit_confirm(request,preview).status_code,200);before=self.read()
        self.assertEqual(self.edit_confirm(request,preview).status_code,409)
        self.assertEqual(self.read(),before)

    def test_editor_and_consultation_previews_expire_each_other(self):
        consult=self.scoped_preview("新补记","history_only")
        request,preview=self.edit_preview({"treatment":"新治疗"})
        self.assertEqual(self.edit_confirm(request,preview).status_code,200)
        self.assertEqual(self.scoped_update("新补记","history_only",consult).status_code,409)
        request,preview=self.edit_preview({"chief_complaint":"修订主诉"})
        consult=self.scoped_preview("新补记","history_only")
        self.assertEqual(self.scoped_update("新补记","history_only",consult).status_code,200)
        before=self.read()
        self.assertEqual(self.edit_confirm(request,preview).status_code,409)
        self.assertEqual(self.read(),before)


if __name__ == "__main__":
    unittest.main(verbosity=2)

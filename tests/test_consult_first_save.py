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
import json
from copy import deepcopy
import dynamic_consult


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

    def structured(self, raw="  否认用药🐾\r\n<literal> & 保留。  \n\t", key="dog"):
        return {"version": "synthetic-v1", "template_key": key, "label": "合成模板", "category": "companion" if key == "dog" else "exotic",
                "sections": [{"key": "history", "title": "原始记录", "answers": [{"key": "meds", "label": "用药原文", "answer": raw, "answer_type": "text", "required": False, "triggered": True}]}]}

    def answer(self, snapshot, token=None, headers=None):
        body = {"question": "合成普通追问", "answer": "普通回答", "structured_intake_answers": snapshot}
        if token is not None: body["expected_answers_token"] = token
        return self.client.post(self.url + "/answer", headers=self.owner_headers if headers is None else headers, json=body)

    def test_retained_rounds_reach_next_context_get_preview_and_actual_case(self):
        a, b = self.structured(), self.structured("第二轮原文，没有呕吐🐱\n  ", "rabbit")
        original = dynamic_consult.run_dynamic_consult
        with patch.object(dynamic_consult, "run_dynamic_consult", wraps=original) as ai:
            first = self.answer(a, self.session()["answers_token"])
            self.assertEqual(first.status_code, 200, first.text)
            second = self.answer(b, first.json()["answers_token"])
            self.assertEqual(second.status_code, 200, second.text)
            self.assertEqual(ai.call_count, 2)
            context = ai.call_args.args[1]
            for snapshot in [a, b]:
                raw = snapshot["sections"][0]["answers"][0]["answer"]
                self.assertEqual(sum(raw in item["answer"] for item in context), 1)
        db.engine.dispose()
        rounds = self.session()["answers"]
        self.assertEqual(rounds[0], {"question": "多久", "answer": "两天"})
        for item, snapshot in zip(rounds[1:], [a, b]):
            self.assertEqual(item["answer"], "普通回答")
            self.assertEqual(json.loads(item["structured_intake_snapshot"]), snapshot)
        legacy = deepcopy(b); legacy.pop("category")
        body = {**self.body, "structured_intake_answers": legacy}
        preview = self.preview(body)
        saved = self.save({**body, "expected_preview_token": preview["preview_token"]})
        self.assertEqual(saved.status_code, 200, saved.text)
        record = self.read(saved.json()["case_id"])
        self.assertEqual(record["history"], preview["history"])
        self.assertTrue(record["history"].startswith(self.body["history"]))
        for n, snapshot in enumerate([a, b], 2):
            self.assertIn(f"第 {n} 轮", record["history"])
            self.assertEqual(record["history"].count(snapshot["sections"][0]["answers"][0]["answer"]), 1)
        self.assertEqual(record["history"].count("模板版本：synthetic-v1"), 2)

    def test_invalid_snapshot_is_rejected_before_ai_and_write(self):
        samples = [[], {"unexpected": "x"}, {"sections": {}}, {"sections": [{}] * 61}]
        for value in [True, 12, None, "x" * 100001]:
            sample = self.structured(); sample["sections"][0]["answers"][0]["answer"] = value; samples.append(sample)
        sample = self.structured(); sample["sections"][0]["answers"][0]["required"] = "true"; samples.append(sample)
        sample = self.structured(); sample["sections"][0]["answers"] *= 201; samples.append(sample)
        sample = self.structured("x" * 90000); sample["sections"][0]["answers"] *= 3; samples.append(sample)
        before = self.session()
        with patch.object(dynamic_consult, "run_dynamic_consult") as ai:
            for sample in samples:
                with self.subTest(sample=str(sample)[:80]):
                    self.assertEqual(self.answer(sample).status_code, 422)
                    self.assertEqual(self.session(), before)
            ai.assert_not_called()

    def test_answer_token_stops_replay_and_stale_client_without_second_ai(self):
        token = self.session()["answers_token"]
        response = self.answer(self.structured(), token)
        self.assertEqual(response.status_code, 200, response.text)
        before = self.session()
        with patch.object(dynamic_consult, "run_dynamic_consult") as ai:
            self.assertEqual(self.answer(self.structured(), token).status_code, 409)
            self.assertEqual(self.answer(self.structured("different"), token).status_code, 409)
            ai.assert_not_called()
        self.assertEqual(self.session(), before)

    def test_blank_long_and_identical_round_text_is_preserved_not_collapsed(self):
        for raw in [" \r\n\t", "否认异常🐾" * 500, "重复原文", "重复原文"]:
            response = self.answer(self.structured(raw))
            self.assertEqual(response.status_code, 200, response.text)
            item = json.loads(response.json()["answers"][-1]["structured_intake_snapshot"])
            self.assertEqual(item["sections"][0]["answers"][0]["answer"], raw)
        history = self.preview({**self.body, "structured_intake_answers": None})["history"]
        self.assertEqual(history.count("重复原文"), 2)
        self.assertIn("第 4 轮", history); self.assertIn("第 5 轮", history)
        self.assertIn(" \r\n\t", history)

    def test_snapshot_auth_and_corrupt_stored_record_fail_closed(self):
        before = self.session()
        self.assertIn(self.answer(self.structured(), headers={}).status_code, (401, 404))
        self.assertEqual(self.answer(self.structured(), headers=self.other_headers).status_code, 404)
        self.assertEqual(self.client.get(self.url, headers=self.other_headers).status_code, 404)
        self.assertEqual(self.session(), before)
        with db.SessionLocal() as session:
            row = session.query(models.ConsultSession).filter_by(session_uid=self.sid).one()
            row.answers = [{"question": "old", "answer": "old", "structured_intake_snapshot": "{broken"}]; session.commit()
        self.assertEqual(self.client.post(self.url + "/preview-case", headers=self.owner_headers, json=self.body).status_code, 409)
        self.assertEqual(self.save().status_code, 409)
        self.assertEqual(self.count(), self.initial_count)

    def test_snapshot_only_change_invalidates_save_preview(self):
        self.assertEqual(self.answer(self.structured()).status_code, 200)
        preview = self.preview()
        with db.SessionLocal() as session:
            row = session.query(models.ConsultSession).filter_by(session_uid=self.sid).one()
            items = deepcopy(row.answers); items[-1]["structured_intake_snapshot"] = json.dumps(self.structured("更正"), ensure_ascii=False)
            row.answers = items; session.commit()
        self.assertEqual(self.save({**self.body, "expected_preview_token": preview["preview_token"]}).status_code, 409)
        self.assertEqual(self.count(), self.initial_count)


if __name__ == "__main__":
    unittest.main(verbosity=2)

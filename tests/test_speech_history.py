"""Doctor confirmation, source integrity, atomic save and both document outputs."""
import io
import json
import unittest
import zipfile
from unittest.mock import patch
from test_speech_transcription import SpeechFixture, db, models, api, budget


class HistoryTests(SpeechFixture):
    def voice(self):
        response, _, _ = self.transcribe(); self.assertEqual(response.status_code, 200, response.text)
        r = response.json()
        return {"receipt": r["receipt"], "original_text": r["text"], "edited_text": "未见呕吐，药物 0.5 毫升。", "reviewed": True}

    def body(self, entry):
        return {"patient_name": "合成犬", "species": "dog", "history": "原始手写病史\n\n" + entry["edited_text"], "voice_confirmations": [entry]}

    def post(self, endpoint, body):
        return self.client.post(self.url + endpoint, headers=self.owner_headers, json=body)

    def audit(self):
        with db.SessionLocal() as session:
            return [r.extra_data for r in session.query(models.AuditLog).filter_by(event_type="speech_confirm")]

    def save(self, body):
        p = self.post("/preview-case", body); self.assertEqual(p.status_code, 200, p.text)
        r = self.post("/save-case", {**body, "expected_preview_token": p.json()["preview_token"]})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()["case_id"]

    def test_confirmed_history_and_audit_saved_once(self):
        entry = self.voice(); body = self.body(entry); cid = self.save(body)
        self.assertEqual(len(self.audit()), 1); self.assertEqual(self.audit()[0]["original_text"], entry["original_text"])
        self.assertEqual(self.audit()[0]["edited_text"], entry["edited_text"])
        self.assertEqual(self.post("/save-case", body).json()["case_id"], cid)
        db.engine.dispose(); self.assertEqual(len(self.audit()), 1)
        record = self.client.get(f"/api/cases/{cid}", headers=self.owner_headers).json()
        self.assertTrue(record["history"].startswith(body["history"]))

    def test_forged_expired_or_moved_sources_rejected(self):
        entry = self.voice(); body = self.body(entry)
        for bad in ({**entry, "original_text": "伪造原文"}, {**entry, "receipt": entry["receipt"][:-1] + "x"}, {**entry, "edited_text": "病史中没有此句"}):
            self.assertEqual(self.post("/preview-case", {**body, "voice_confirmations": [bad]}).status_code, 409)
        for changed in ({"patient_name": "另一只犬"}, {"species": "cat"}, {"voice_confirmations": [entry, entry]}):
            self.assertEqual(self.post("/preview-case", {**body, **changed}).status_code, 409)
        with patch.object(api.time, "time", return_value=10 ** 12):
            self.assertEqual(self.post("/preview-case", body).status_code, 409)
        self.assertEqual(self.audit(), [])

    def test_preview_confirmation_binds_edits_and_doctor_check(self):
        entry = self.voice(); body = self.body(entry)
        self.assertEqual(self.post("/save-case", body).status_code, 409)
        p = self.post("/preview-case", body).json()
        bad = {**body, "voice_confirmations": [{**entry, "reviewed": False}]}
        self.assertEqual(self.post("/save-case", bad).status_code, 422)
        self.assertEqual(self.post("/save-case", {**body, "history": "已改变", "expected_preview_token": p["preview_token"]}).status_code, 409)
        self.assertEqual(self.audit(), [])

    def test_explicit_source_review_after_session_change_has_no_second_asr(self):
        entry = self.voice(); body = self.body(entry)
        with db.SessionLocal() as session:
            row = session.query(models.ConsultSession).filter_by(session_uid=self.sid).one()
            row.answers = [{"question": "补充", "answer": "新的原文"}]; session.commit()
        self.assertEqual(self.post("/preview-case", body).status_code, 409)
        context = self.client.get("/api/speech/context/" + self.sid, headers=self.owner_headers).json()
        binding = {**context, "patient_name": "合成犬", "species": "dog", "draft_version": "c" * 64}
        r = self.client.post("/api/speech/review", headers=self.owner_headers, json={"binding": binding, "confirmation": entry})
        self.assertEqual(r.status_code, 200, r.text)
        revised = {**entry, "receipt": r.json()["receipt"]}
        self.save(self.body(revised)); self.assertEqual(budget.budget_status()["attempts"], 1)
        self.assertEqual(self.client.post("/api/speech/review", headers=self.owner_headers, json={"binding": binding, "confirmation": revised}).status_code, 409)

    def test_audit_failure_rolls_back_case_and_session_binding(self):
        entry = self.voice(); body = self.body(entry)
        with patch.object(api.budget, "row", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError): self.save(body)
        with db.SessionLocal() as session:
            row = session.query(models.ConsultSession).filter_by(session_uid=self.sid).one()
            self.assertIsNone(row.case_id)
        self.assertEqual(self.audit(), [])

    def test_addendum_preserves_prior_history_and_consumes_source_once(self):
        cid = self.save(self.body(self.voice()))
        before = self.client.get(f"/api/cases/{cid}", headers=self.owner_headers).json()
        context = self.client.get("/api/speech/context/" + self.sid, headers=self.owner_headers).json()
        self.binding = {**context, "draft_version": "b" * 64}
        entry = self.voice(); body = {"history_addendum": entry["edited_text"], "update_mode": "history_only", "voice_confirmations": [entry]}
        p = self.post("/preview-update-case", body); self.assertEqual(p.status_code, 200, p.text)
        req = {**body, "expected_preview_token": p.json()["preview_token"]}
        self.assertEqual(self.post("/update-case", req).status_code, 200)
        self.assertEqual(self.post("/update-case", req).status_code, 409)
        after = self.client.get(f"/api/cases/{cid}", headers=self.owner_headers).json()
        self.assertTrue(after["history"].startswith(before["history"])); self.assertEqual(len(self.audit()), 2)
        self.assertEqual(self.post("/preview-update-case", body).status_code, 409)

    def test_both_docx_use_confirmed_history_and_old_confirmation_expires(self):
        import xml.etree.ElementTree as ET
        cid = self.save(self.body(self.voice()))
        old = {}
        for template in ("outpatient_record_zh", "owner_visit_summary_zh"):
            body = {"case_id": cid, "template_id": template}
            preview = self.client.post("/api/clinical-docs/render-preview", headers=self.owner_headers, json=body)
            self.assertEqual(preview.status_code, 200, preview.text)
            old[template] = preview.json()["content_snapshot"]
            rendered = self.client.post("/api/clinical-docs/render", headers=self.owner_headers, json={**body, "expected_content_snapshot": old[template]})
            self.assertEqual(rendered.status_code, 200)
            with zipfile.ZipFile(io.BytesIO(rendered.content)) as z:
                text = "".join(ET.fromstring(z.read("word/document.xml")).itertext())
            self.assertIn("未见呕吐，药物 0.5 毫升。", text)
        self.binding = {**self.client.get("/api/speech/context/" + self.sid, headers=self.owner_headers).json(), "draft_version": "c" * 64}
        entry = self.voice(); entry["edited_text"] = "补记：已向医生核对单位。"
        body = {"history_addendum": entry["edited_text"], "update_mode": "history_only", "voice_confirmations": [entry]}
        p = self.post("/preview-update-case", body).json()
        self.assertEqual(self.post("/update-case", {**body, "expected_preview_token": p["preview_token"]}).status_code, 200)
        for template, snapshot in old.items():
            response = self.client.post("/api/clinical-docs/render", headers=self.owner_headers, json={"case_id": cid, "template_id": template, "expected_content_snapshot": snapshot})
            self.assertEqual(response.status_code, 409)


if __name__ == "__main__": unittest.main(verbosity=2)

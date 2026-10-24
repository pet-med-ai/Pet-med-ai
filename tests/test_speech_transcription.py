"""Real authenticated routes, bounded audio, mocked vendor; egress forbidden."""
import asyncio
import base64
import io
import json
import os
import unittest
import wave
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import test_consult_update_preview as fixture
import speech_transcription as provider
import speech_transcription_api as api
import speech_budget as budget

main, db, models = fixture.main, fixture.db, fixture.models


def wav(seconds=1, rate=16000, channels=1):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(channels); writer.setsampwidth(2); writer.setframerate(rate)
        writer.writeframes(b"\x00\x00" * int(seconds * rate) * channels)
    return buffer.getvalue()


class SpeechFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ConsultUpdatePreviewTests.setUpClass()
        for name in ("client", "owner_headers", "other_headers", "owner_id"):
            setattr(cls, name, getattr(fixture.ConsultUpdatePreviewTests, name))
        models.AuditLog.__table__.create(db.engine)

    @classmethod
    def tearDownClass(cls):
        fixture.ConsultUpdatePreviewTests.tearDownClass()

    def setUp(self):
        # This fixture creates a disposable database; no application reset route.
        with db.SessionLocal() as session:
            session.query(models.AuditLog).delete(); session.commit()
        budget.initialize_ledger()
        self.sid = uuid4().hex
        with db.SessionLocal() as session:
            session.add(models.ConsultSession(session_uid=self.sid, owner_id=self.owner_id, text="合成犬", answers=[], result={}))
            session.commit()
        self.url = "/api/ai/consult/session/" + self.sid
        self.context = self.client.get("/api/speech/context/" + self.sid, headers=self.owner_headers).json()
        self.binding = {**self.context, "patient_name": "合成犬", "species": "dog", "draft_version": "a" * 64}

    def transcribe(self, **changes):
        body = {"request_id": uuid4().hex, "binding": self.binding, "synthetic_only": True, "audio_base64": base64.b64encode(wav()).decode(), **changes}
        with patch.object(provider, "ensure_enabled"), patch.object(provider, "recognize", AsyncMock(return_value={"text": "未见呕吐，药物零点五毫升", "provider_request_id": "synthetic-only"})) as mock:
            response = self.client.post("/api/speech/transcribe", headers=self.owner_headers, json=body)
        return response, body, mock


class SpeechTests(SpeechFixture):
    def test_auth_disabled_and_production_fail_closed(self):
        self.assertEqual(self.client.get("/api/speech/availability").status_code, 401)
        self.assertFalse(self.client.get("/api/speech/availability", headers=self.owner_headers).json()["enabled"])
        for environment in ({"ENVIRONMENT": "production"}, {"RENDER": "true"}):
            with patch.dict(os.environ, environment), self.assertRaises(provider.SpeechError):
                provider.ensure_development()
        self.assertEqual(budget.budget_status()["attempts"], 0)

    def test_wav_boundaries_and_corruption(self):
        self.assertEqual(provider.validate_wav(wav(30)), 30)
        for audio in (wav(30.1), wav(.05), wav(rate=8000), wav(channels=2), b"x" * (provider.MAX_AUDIO_BYTES + 1), wav()[:-2], wav() + b"junk", b"not audio"):
            with self.subTest(size=len(audio)), self.assertRaises(provider.SpeechError):
                provider.validate_wav(audio)

    def test_transcribe_hash_only_ledger_and_replay_never_egresses(self):
        response, body, mock = self.transcribe()
        self.assertEqual(response.status_code, 200, response.text); mock.assert_awaited_once()
        data = response.json()
        self.assertEqual(api.parse_receipt(data["receipt"])["binding"], self.binding)
        with db.SessionLocal() as session:
            records = [r.extra_data for r in session.query(models.AuditLog)]
        self.assertNotIn(data["text"], json.dumps(records, ensure_ascii=False))
        self.assertNotIn(body["audio_base64"], json.dumps(records))
        repeated, _, mock = self.transcribe(**body)
        self.assertEqual(repeated.status_code, 409); mock.assert_not_awaited()
        self.assertEqual(budget.budget_status()["attempts"], 1)

    def test_bad_context_and_audio_do_not_reserve(self):
        for binding in ({**self.binding, "case_id": 90000}, {**self.binding, "session_version": "0" * 64}):
            r, _, mock = self.transcribe(binding=binding); self.assertEqual(r.status_code, 409); mock.assert_not_awaited()
        for extra in ({"synthetic_only": False}, {"audio_base64": "bad==="}, {"binding": {**self.binding, "extra": 1}}):
            r, _, mock = self.transcribe(**extra); self.assertEqual(r.status_code, 422); mock.assert_not_awaited()
        self.assertEqual(budget.budget_status()["attempts"], 0)

    def test_cross_account_context_and_request_status(self):
        r, body, _ = self.transcribe(); self.assertEqual(r.status_code, 200)
        path = "/api/speech/requests/" + body["request_id"]
        self.assertEqual(self.client.get(path, headers=self.other_headers).status_code, 404)
        self.assertEqual(self.client.get("/api/speech/context/" + self.sid, headers=self.other_headers).status_code, 404)
        data = self.client.get(path, headers=self.owner_headers).json()
        self.assertFalse(data["retry_allowed"]); self.assertNotIn("text", data)

    def test_vendor_timeout_keeps_reservation(self):
        body = {"request_id": uuid4().hex, "binding": self.binding, "synthetic_only": True, "audio_base64": base64.b64encode(wav()).decode()}
        with patch.object(provider, "ensure_enabled"), patch.object(provider, "recognize", AsyncMock(side_effect=provider.SpeechError("provider_timeout_unknown", 504))) as mock:
            response = self.client.post("/api/speech/transcribe", headers=self.owner_headers, json=body)
        self.assertEqual(response.status_code, 504); mock.assert_awaited_once()
        self.assertEqual(budget.budget_status()["reserved_fen"], 1)

    def test_tc3_signature_payload_and_no_auto_rewriting(self):
        with patch.dict(os.environ, {"TENCENTCLOUD_SECRET_ID": "synthetic-id", "TENCENTCLOUD_SECRET_KEY": "synthetic-key"}):
            body, headers = provider.signed_request(wav(), "test", timestamp=1551113065)
            second = provider.signed_request(wav(), "test", timestamp=1551113065)
        self.assertEqual((body, headers), second)
        params = json.loads(body)
        self.assertEqual(params["DataLen"], len(wav())); self.assertEqual(base64.b64decode(params["Data"]), wav())
        self.assertEqual([params[k] for k in ["FilterModal", "FilterDirty", "ConvertNumMode"]], [0, 0, 0])
        self.assertNotIn("Url", params); self.assertNotIn("HotwordList", params)
        self.assertIn("/2019-02-25/asr/tc3_request", headers["Authorization"])

    def test_adapter_errors_sanitized_single_attempt(self):
        import httpx
        class Client:
            calls = 0
            def __init__(self, **kw):
                assert kw["follow_redirects"] is False and kw["trust_env"] is False
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            def stream(self, *args, **kw):
                Client.calls += 1
                raise httpx.ReadTimeout("SECRET-AUDIO-PAYLOAD")
        with patch.object(provider, "ensure_enabled"), patch.object(provider, "signed_request", return_value=(b"synthetic", {})), patch.object(provider.httpx, "AsyncClient", Client):
            with self.assertRaises(provider.SpeechError) as raised:
                asyncio.run(provider.recognize(wav(), "synthetic"))
        self.assertEqual(str(raised.exception), "provider_timeout_unknown"); self.assertEqual(Client.calls, 1)


if __name__ == "__main__": unittest.main(verbosity=2)

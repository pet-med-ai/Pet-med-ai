"""Real authenticated attachment routes, disposable DB/files; egress prohibited."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import quote
from uuid import uuid4
import test_consult_update_preview as f
import case_attachment_service as service
import case_attachment_store as storage
sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
from build_attachment_cw_b6_fixtures import samples, png


class AttachmentFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        f.ConsultUpdatePreviewTests.setUpClass()
        for name in ("client", "owner_headers", "other_headers", "owner_id"):
            setattr(cls, name, getattr(f.ConsultUpdatePreviewTests, name))
        f.models.AuditLog.__table__.create(f.db.engine, checkfirst=True)

    @classmethod
    def tearDownClass(cls): f.ConsultUpdatePreviewTests.tearDownClass()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cw6-store-")
        self.env = patch.dict(os.environ, {"CASE_ATTACHMENTS_ENABLED": "1", "CASE_ATTACHMENTS_SYNTHETIC_ONLY": "1", "CASE_ATTACHMENTS_DIR": self.temp.name})
        self.env.start()
        f.ConsultUpdatePreviewTests.setUp(self)
        self.base = f"/api/cases/{self.cid}/attachments"
        self.meta = {"title": "合成报告", "kind": "lab", "taken_at": "2026-10-06T10:00:00+08:00", "reported_at": "", "source": "合成实验室", "note": "未记录项保持空白"}

    def tearDown(self): self.env.stop(); self.temp.cleanup()

    def listing(self):
        r = self.client.get(self.base, headers=self.owner_headers)
        self.assertEqual(r.status_code, 200, r.text); return r.json()

    def upload(self, name="sample.png", mime="image/png", data=None, rid=None, token=None, headers=None):
        rid = rid or uuid4().hex
        r = self.client.post(self.base + "/uploads/" + rid, headers={**(headers or self.owner_headers),
            "Content-Type": mime, "X-Attachment-Filename": quote(name), "X-Case-Token": token or self.listing()["case_token"]}, content=png() if data is None else data)
        return r, rid

    def body(self, item, operation="confirm"):
        return {"operation": operation, "attachment_id": item["id"], "request_id": uuid4().hex,
                "expected_case_token": self.listing()["case_token"], "metadata": self.meta, "reason": "错误关联合成病例" if operation == "withdraw" else ""}

    def reviewed(self, body):
        r = self.client.post(self.base + "/preview", headers=self.owner_headers, json=body)
        self.assertEqual(r.status_code, 200, r.text)
        return {**body, "preview_token": r.json()["preview_token"], "reviewed": True}

    def commit(self, request):
        return self.client.post(self.base + "/confirm", headers=self.owner_headers, json=request)

    def attach(self, *args, **kwargs):
        r, rid = self.upload(*args, **kwargs); self.assertEqual(r.status_code, 200, r.text)
        body = self.reviewed(self.body(r.json()["attachment"]))
        c = self.commit(body); self.assertEqual(c.status_code, 200, c.text)
        return c.json()["attachment"], body, rid

    def get_content(self, item, headers=None, preview=False):
        return self.client.get(self.base + f'/{item["id"]}/content', headers=headers or self.owner_headers,
                               params={"request_id": uuid4().hex, "preview": str(preview).lower()})


class AttachmentTests(AttachmentFixture):
    def test_all_formats_original_bytes_metadata_and_restart(self):
        for name, mime, data in samples():
            item, request, rid = self.attach(name, mime, data)
            self.assertEqual(item["metadata"], self.meta)
            self.assertEqual(item["uploaded_by"], str(self.owner_id)); self.assertTrue(item["uploaded_at"])
            self.assertEqual(self.commit(request).status_code, 200)
            r = self.get_content(item); self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(r.content, data); self.assertEqual(r.headers["cache-control"], "private, no-store")
            self.assertNotIn(self.temp.name, r.text)
        f.db.engine.dispose()
        self.assertEqual(len(self.listing()["items"]), 3)
        with f.db.SessionLocal() as db:
            self.assertEqual(db.query(f.models.AuditLog).filter_by(case_id=self.cid, event_type="attachment_confirm").count(), 3)

    def test_pending_not_listed_and_duplicate_recovery(self):
        r, rid = self.upload(); self.assertEqual(r.status_code, 200)
        self.assertEqual(self.listing()["items"], [])
        status = self.client.get(self.base+"/uploads/"+rid, headers=self.owner_headers).json()
        req = self.reviewed(self.body(status["attachment"]))
        self.assertEqual(self.commit(req).status_code, 200)
        self.assertEqual(self.commit(req).status_code, 200)
        again, _ = self.upload(); self.assertEqual(again.json()["state"], "already_attached")
        self.assertEqual(len(self.listing()["items"]), 1)
        result = self.client.get(self.base+"/requests/"+req["request_id"], headers=self.owner_headers).json()
        self.assertEqual(result["state"], "committed")
        self.assertEqual(self.commit({**req, "reason": "changed"}).status_code, 409)

    def test_foreign_account_case_deleted_and_disabled(self):
        item, _, _ = self.attach()
        self.assertEqual(self.client.get(self.base).status_code, 401)
        self.assertEqual(self.client.get(self.base, headers=self.other_headers).status_code, 404)
        self.assertEqual(self.get_content(item, self.other_headers).status_code, 404)
        with f.db.SessionLocal() as db:
            case = db.get(f.models.Case, self.cid); case.deleted_at = f.main.datetime.utcnow(); db.commit()
        self.assertEqual(self.get_content(item).status_code, 404)
        for change in ({"CASE_ATTACHMENTS_ENABLED":"0"},{"ENVIRONMENT":"production"},{"RENDER":"true"}):
            with patch.dict(os.environ, change):
                self.assertEqual(self.client.get(self.base, headers=self.owner_headers).status_code, 503)

    def test_stale_review_unchecked_and_switched_case(self):
        r, _ = self.upload(); body = self.body(r.json()["attachment"]); req = self.reviewed(body)
        self.assertEqual(self.commit({**req, "reviewed":False}).status_code, 422)
        self.assertEqual(self.commit({**req, "metadata":{**self.meta,"title":"changed"}}).status_code, 409)
        old = self.cid
        f.ConsultUpdatePreviewTests.setUp(self)
        r = self.client.post(f"/api/cases/{self.cid}/attachments/preview", headers=self.owner_headers, json=body)
        self.assertEqual(r.status_code, 409)
        self.cid = old
        self.client.put(f"/api/cases/{old}", headers=self.owner_headers, json={"patient_name":"已变化"})
        self.assertEqual(self.commit(req).status_code, 409)
        self.assertEqual(self.listing()["items"], [])

    def test_update_withdraw_preserves_original_legacy_and_history(self):
        legacy = {"url":"https://invalid.example/never-fetch","unknown":[1,2]}
        with f.db.SessionLocal() as db:
            c=db.get(f.models.Case,self.cid);c.attachments=[legacy];db.commit()
        item, _, _ = self.attach()
        before=self.client.get(f"/api/cases/{self.cid}",headers=self.owner_headers).json()
        self.meta={**self.meta,"title":"更正标题"}
        r=self.commit(self.reviewed(self.body(item,"update")));self.assertEqual(r.status_code,200)
        self.assertEqual(self.get_content(item).content,png())
        r=self.commit(self.reviewed(self.body(item,"withdraw")));self.assertEqual(r.status_code,200)
        self.assertEqual(self.get_content(item).status_code,404)
        self.assertTrue(storage.Store().path(item["id"],".blob").exists())
        after=self.client.get(f"/api/cases/{self.cid}",headers=self.owner_headers).json();self.assertEqual(before,after)
        with f.db.SessionLocal() as db:
            self.assertEqual(db.get(f.models.Case,self.cid).attachments[0],legacy)
        self.assertEqual(self.listing()["legacy_count"],1)

    def test_cancel_expiry_integrity_and_atomic_audit_failure(self):
        r,rid=self.upload();aid=r.json()["attachment"]["id"]
        self.assertEqual(self.client.post(self.base+"/uploads/"+rid+"/cancel",headers=self.owner_headers).status_code,200)
        self.assertFalse(storage.Store().path(aid,".blob").exists())
        self.assertEqual(self.client.get(self.base+"/uploads/"+rid,headers=self.owner_headers).json()["state"],"cancelled")
        r,rid=self.upload();req=self.reviewed(self.body(r.json()["attachment"]))
        with patch.object(service,"audit",side_effect=RuntimeError("synthetic audit fail")):
            with self.assertRaises(RuntimeError):self.commit(req)
        self.assertEqual(self.listing()["items"],[])
        self.assertEqual(self.commit(req).status_code,200)
        item=self.listing()["items"][0];storage.Store().path(item["id"],".blob").write_bytes(b"damaged")
        self.assertEqual(self.get_content(item).status_code,409)

    def test_types_limits_and_expiration(self):
        for name,mime,data in [("../escape.png","image/png",png()),("test.pdf","image/png",png()),("test.png","image/png",png()[:-2]),("test.png","image/png",b"")]:
            r,_=self.upload(name,mime,data);self.assertEqual(r.status_code,422,r.text)
        with patch.object(service,"MAX_CASE_FILES",0):
            self.assertEqual(self.upload()[0].status_code,413)
        with patch.object(service,"MAX_CASE_BYTES",1):
            self.assertEqual(self.upload()[0].status_code,413)
        r,rid=self.upload();body=self.body(r.json()["attachment"])
        with patch.object(service.time,"time",return_value=10**12):
            p=self.client.post(self.base+"/preview",headers=self.owner_headers,json=body);self.assertEqual(p.status_code,409)
            self.listing()  # cleanup may already remove the pending manifest
            status=self.client.get(self.base+"/uploads/"+rid,headers=self.owner_headers)
            self.assertEqual(status.status_code,200);self.assertEqual(status.json()["state"],"expired")

    def test_both_documents_do_not_absorb_unreviewed_files(self):
        for template in ("outpatient_record_zh","owner_visit_summary_zh"):
            body={"case_id":self.cid,"template_id":template}
            before=self.client.post("/api/clinical-docs/render-preview",headers=self.owner_headers,json=body).json()
            if not self.listing()["items"]: self.attach(name=template+".png")
            after=self.client.post("/api/clinical-docs/render-preview",headers=self.owner_headers,json=body).json()
            self.assertEqual(before["content_snapshot"],after["content_snapshot"])
            r=self.client.post("/api/clinical-docs/render",headers=self.owner_headers,json={**body,"expected_content_snapshot":before["content_snapshot"]})
            self.assertEqual(r.status_code,200)


if __name__ == "__main__": unittest.main(verbosity=2)

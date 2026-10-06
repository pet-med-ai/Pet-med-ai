from concurrent.futures import ThreadPoolExecutor
import tempfile
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4
from test_case_attachments import AttachmentFixture, f, service, storage, png
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from verify_case_attachment_storage import backup_readback


def exercise_sqlite(factory, uid, cid, directory):
    """SQLite concurrency on real DB/service; PostgreSQL has a separate isolated CI fixture."""
    before=service.listing(uid,cid)
    rid=uuid4().hex
    with ThreadPoolExecutor(max_workers=2) as pool:
        uploaded=list(pool.map(lambda _:service.upload(uid,cid,rid,before["case_token"],png(),"concurrent.png","image/png"),range(2)))
    assert uploaded[0]["attachment"]["id"]==uploaded[1]["attachment"]["id"]
    item=uploaded[0]["attachment"]
    meta={"title":"并发合成报告","kind":"lab","taken_at":"","reported_at":"","source":"","note":""}
    body={"request_id":uuid4().hex,"attachment_id":item["id"],"operation":"confirm","expected_case_token":before["case_token"],"metadata":meta,"reason":""}
    token=service.preview(uid,cid,body)["preview_token"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:service.commit(uid,cid,body,token),range(2)))
    assert len({r["attachment"]["id"] for r in results})==1
    listing=service.listing(uid,cid);assert len(listing["items"])==1
    with factory() as db:
        assert db.query(f.models.AuditLog).filter_by(case_id=cid,event_type="attachment_confirm").count()==1
    original=results[0]["attachment"]
    base={**body,"operation":"update","expected_case_token":listing["case_token"]}
    bodies=[{**base,"request_id":uuid4().hex,"metadata":{**meta,"title":str(i)}} for i in range(2)]
    tokens=[service.preview(uid,cid,b)["preview_token"] for b in bodies]
    def worker(i):
        try:service.commit(uid,cid,bodies[i],tokens[i]);return 200
        except storage.AttachmentError as e:return e.status
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(worker,range(2)))==[200,409]
    with factory() as db:
        case=db.get(f.models.Case,cid)
        report=backup_readback(storage.Store(),[{"case_id":cid,"owner_id":uid,"attachments":case.attachments}],Path(directory)/"restored")
    assert report["verified"] and report["files"]==1 and not report["database_restored"]
    return {"case_id":cid,"attachment":service.listing(uid,cid)["items"][0],"backup":report,"confirm_request":body["request_id"]}


class ConcurrencyTests(AttachmentFixture):
    def test_simultaneous_upload_confirm_update_and_backup(self):
        with tempfile.TemporaryDirectory(prefix="cwb6-backup-") as directory:
            exercise_sqlite(f.db.SessionLocal,self.owner_id,self.cid,directory)

    def test_database_commit_failure_can_recover_without_duplicate_file(self):
        r,rid=self.upload();item=r.json()["attachment"];req=self.reviewed(self.body(item))
        from sqlalchemy.orm import Session
        from sqlalchemy.exc import OperationalError
        with patch.object(Session,"commit",side_effect=OperationalError("synthetic",{},Exception("fail"))):
            r=self.commit(req);self.assertEqual(r.status_code,503)
        self.assertEqual(self.listing()["items"],[])
        self.assertEqual(self.commit(req).status_code,200)
        self.assertEqual(len(self.listing()["items"]),1)
        self.assertEqual(len(list(Path(self.temp.name).glob("*.blob"))),1)


if __name__=="__main__":unittest.main(verbosity=2)

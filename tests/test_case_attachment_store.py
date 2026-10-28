import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "tests" / "fixtures")]
import case_attachment_store as s
from build_attachment_cw_b6_fixtures import samples, png


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cw6-files-")
        self.env=patch.dict(os.environ,{"ENVIRONMENT":"test","RENDER":"false","CASE_ATTACHMENTS_ENABLED":"1","CASE_ATTACHMENTS_SYNTHETIC_ONLY":"1","CASE_ATTACHMENTS_DIR":self.temp.name});self.env.start()
        self.store=s.Store();self.key="a"*64

    def tearDown(self):self.env.stop();self.temp.cleanup()

    def test_original_formats_and_truncations(self):
        for name,mime,data in samples():
            value=s.validate_file(data,name,mime);self.assertEqual(value["size"],len(data))
            for bad in (data[:-4],b"not an image",b""):
                with self.assertRaises(s.AttachmentError):s.validate_file(bad,name,mime)
        with patch.object(s,"MAX_FILE",len(png())):
            s.validate_file(png(),"a.png","image/png")
            with self.assertRaises(s.AttachmentError):s.validate_file(png()+b"x","a.png","image/png")

    def test_path_escape_symlink_and_quota_fail_closed(self):
        with self.assertRaises(s.AttachmentError):self.store.path("../outside",".blob")
        outside=Path(self.temp.name)/"outside";outside.write_bytes(b"keep")
        self.store.path(self.key,".blob").symlink_to(outside)
        with self.assertRaises(s.AttachmentError):self.store.read(self.key,".blob")
        with self.assertRaises(s.AttachmentError):self.store.write(self.key,".blob",b"overwrite")
        self.assertEqual(outside.read_bytes(),b"keep")
        self.store.path(self.key,".blob").unlink()
        with patch.object(s,"MAX_TOTAL",2),self.assertRaises(s.AttachmentError):self.store.write(self.key,".blob",b"large")
        with self.assertRaises(s.AttachmentError):s.Store(ROOT/"private")

    def test_atomic_write_failure_cleanup_and_committed_protection(self):
        with self.store.locked():
            with patch.object(s.os,"replace",side_effect=OSError("synthetic disk failure")),self.assertRaises(OSError):self.store.write(self.key,".blob",b"original")
            self.assertFalse(self.store.path(self.key,".blob").exists());self.assertFalse(self.store.path(self.key,".tmp").exists())
            self.store.write(self.key,".blob",b"keep")
            other="b"*64;self.store.write(other,".blob",b"orphan")
            removed=self.store.cleanup({self.key},now=time.time()+s.TTL+1)
            self.assertEqual(removed,[other+".blob"]);self.assertEqual(self.store.read(self.key,".blob"),b"keep")


if __name__ == "__main__":unittest.main(verbosity=2)

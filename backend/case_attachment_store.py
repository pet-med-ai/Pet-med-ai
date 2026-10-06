"""CW-B6 private, bounded synthetic-file store. No public mount or remote fetch."""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import threading
import time
import zlib

MAX_FILE = 10 * 1024 * 1024
MAX_TOTAL = 500 * 1024 * 1024
TTL = 3600
SCHEMA = "case-attachment-cw-b6-v1"
_THREAD_LOCK = threading.RLock()
_KEY = re.compile(r"[a-f0-9]{64}\Z")


class AttachmentError(Exception):
    def __init__(self, code, status=409):
        self.code, self.status = code, status
        super().__init__(code)


def ensure_enabled():
    if (os.getenv("ENVIRONMENT") not in {"test", "development"}
            or os.getenv("RENDER", "").lower() == "true"
            or os.getenv("CASE_ATTACHMENTS_ENABLED") != "1"
            or os.getenv("CASE_ATTACHMENTS_SYNTHETIC_ONLY") != "1"):
        raise AttachmentError("attachments_disabled", 503)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def validate_file(data, name, mime):
    if not isinstance(name, str) or not name or len(name) > 255 or any(ord(c) < 32 for c in name) or any(c in name for c in "/\\\x7f"):
        raise AttachmentError("invalid_filename", 422)
    suffix = Path(name).suffix.lower()
    expected = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(suffix)
    if not expected or mime != expected or not data or len(data) > MAX_FILE:
        raise AttachmentError("invalid_file_type_or_size", 422)
    try:
        if mime == "application/pdf":
            # Deliberately only structural recognition; never render/execute PDF.
            assert re.match(rb"%PDF-1\.[0-9][\r\n]", data)
            tail = re.search(rb"startxref\s+(\d+)\s+%%EOF\s*\Z", data)
            assert tail and 0 < int(tail[1]) < tail.start()
            target = data[int(tail[1]):]
            assert target.startswith(b"xref") or re.match(rb"\d+\s+\d+\s+obj", target)
            assert b"/Type /Catalog" in data or b"/Type/Catalog" in data
        elif mime == "image/png":
            assert data.startswith(b"\x89PNG\r\n\x1a\n")
            pos, first, image_data, ended = 8, True, False, False
            while pos < len(data):
                length = struct.unpack(">I", data[pos:pos + 4])[0]
                kind, payload = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + length]
                assert len(payload) == length and pos + length + 12 <= len(data)
                assert zlib.crc32(kind + payload) & 0xffffffff == struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])[0]
                if first:
                    assert kind == b"IHDR" and length == 13
                    width, height = struct.unpack(">II", payload[:8])
                    assert 0 < width <= 10000 and 0 < height <= 10000 and width * height <= 25000000
                    first = False
                if kind == b"IDAT": image_data = True
                pos += length + 12
                if kind == b"IEND":
                    assert length == 0 and pos == len(data)
                    ended = True
                    break
            assert image_data and ended
        else:
            assert data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9")
            pos, dimensions, scan = 2, False, False
            while pos < len(data) - 2:
                assert data[pos] == 255
                while data[pos] == 255: pos += 1
                marker = data[pos]; pos += 1
                assert marker not in (0, 0xd8, 0xd9)
                length = int.from_bytes(data[pos:pos + 2], "big")
                assert length >= 2 and pos + length <= len(data) - 2
                if marker in {0xc0, 0xc1, 0xc2}:
                    assert length >= 8
                    height, width = struct.unpack(">HH", data[pos + 3:pos + 7])
                    assert 0 < width <= 10000 and 0 < height <= 10000 and width * height <= 25000000
                    dimensions = True
                pos += length
                if marker == 0xda:
                    scan = True
                    break
            assert dimensions and scan and pos < len(data) - 2
    except (AssertionError, IndexError, ValueError, struct.error):
        raise AttachmentError("invalid_file_structure", 422) from None
    return {"name": name, "mime": mime, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class Store:
    def __init__(self, root=None):
        ensure_enabled()
        path = Path(root or os.getenv("CASE_ATTACHMENTS_DIR", ""))
        repo = Path(__file__).resolve().parents[1]
        if not path.is_absolute() or path == repo or repo in path.parents or path == Path("/"):
            raise AttachmentError("private_store_not_configured", 503)
        if any(p.is_symlink() for p in [path, *path.parents]):
            raise AttachmentError("unsafe_store_path", 503)
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not path.is_dir() or path.stat().st_uid != os.getuid():
            raise AttachmentError("unsafe_store_path", 503)
        os.chmod(path, 0o700)
        self.root = path

    @contextlib.contextmanager
    def locked(self):
        with _THREAD_LOCK:
            fd = os.open(self.root / ".cw-b6.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            try:
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    raise AttachmentError("unsafe_store_path", 503)
                fcntl.flock(fd, fcntl.LOCK_EX)
                yield self
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)

    def path(self, key, suffix):
        if not _KEY.fullmatch(key) or suffix not in {".json", ".blob", ".tmp"}:
            raise AttachmentError("invalid_attachment_id", 422)
        return self.root / (key + suffix)

    def read(self, key, suffix, limit=MAX_FILE):
        try:
            fd = os.open(self.path(key, suffix), os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode): raise OSError()
                data = stream.read(limit + 1)
                if len(data) > limit: raise OSError()
                return data
        except OSError:
            raise AttachmentError("attachment_file_unavailable", 409) from None

    def metadata(self, key):
        try:
            value = json.loads(self.read(key, ".json", 16384))
            if value.get("schema") != SCHEMA or value.get("id") != key: raise ValueError()
            return value
        except (ValueError, TypeError):
            raise AttachmentError("attachment_metadata_invalid", 409) from None

    def usage(self):
        total = 0
        for path in self.root.iterdir():
            if path.is_symlink(): raise AttachmentError("unsafe_store_path", 503)
            if path.is_file(): total += path.stat().st_size
        return total

    def write(self, key, suffix, data):
        target = self.path(key, suffix)
        if target.is_symlink(): raise AttachmentError("unsafe_store_path", 503)
        if self.usage() + len(data) > MAX_TOTAL:
            raise AttachmentError("attachment_storage_full", 413)
        temporary = self.path(key, ".tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, target)
            directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
            try: os.fsync(directory)
            finally: os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)

    def write_metadata(self, item):
        self.write(item["id"], ".json", json.dumps(item, ensure_ascii=False, sort_keys=True).encode())

    def verified(self, item):
        data = self.read(item["id"], ".blob")
        if len(data) != item["size"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise AttachmentError("attachment_integrity_failed")
        return data

    def cleanup(self, protected, now=None):
        """Caller holds store lock and derives protected IDs from ALL cases."""
        now = time.time() if now is None else now
        removed = []
        for path in self.root.iterdir():
            if path.suffix not in {".json", ".blob", ".tmp"} or not _KEY.fullmatch(path.stem) or path.stem in protected: continue
            if path.is_symlink(): raise AttachmentError("unsafe_store_path", 503)
            if now - path.stat().st_mtime >= TTL:
                path.unlink(); removed.append(path.name)
        return removed

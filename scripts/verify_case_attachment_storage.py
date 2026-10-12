"""Synthetic-only raw-file/reference backup readback; never restores a database."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from case_attachment_store import Store, SCHEMA, AttachmentError
from case_attachment_service import known


def backup_readback(store, cases, destination):
    target = Path(destination)
    if not target.is_absolute() or target.exists() or any(p.is_symlink() for p in target.parents):
        raise AttachmentError("backup_requires_new_private_directory")
    if target == ROOT or ROOT in target.parents or target == store.root or store.root in target.parents:
        raise AttachmentError("invalid_backup_directory")
    # No source mutation. Entire operation is under the same cross-process lock.
    with store.locked():
        rows = [{"case_id": row["case_id"], "owner_id": row["owner_id"],
                 "attachments": [a for a in row["attachments"] if known(a)]} for row in cases]
        entries = [a for row in rows for a in row["attachments"]]
        if len({a["id"] for a in entries}) != len(entries): raise AttachmentError("duplicate_reference")
        data = [(a, store.verified(a)) for a in entries]
        target.mkdir(mode=0o700, parents=True)
        for a, raw in data:
            if not re.fullmatch(r"[a-f0-9]{64}", a["id"]): raise AttachmentError("invalid_attachment_id")
            with (target / (a["id"] + ".blob")).open("xb") as f: f.write(raw)
        manifest = {"schema": SCHEMA, "synthetic_only": True, "database_restored": False, "cases": rows}
        (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    restored = json.loads((target / "manifest.json").read_text())
    assert restored == manifest
    for row in restored["cases"]:
        for a in row["attachments"]:
            raw = (target / (a["id"] + ".blob")).read_bytes()
            assert len(raw) == a["size"] and hashlib.sha256(raw).hexdigest() == a["sha256"]
    return {"verified": True, "files": len(entries), "cases": len(rows), "database_restored": False, "synthetic_only": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    from db import SessionLocal
    from models import Case
    store = Store()  # Production/default-disabled guard before database access.
    with SessionLocal() as db:
        rows = [{"case_id": c.id, "owner_id": c.owner_id, "attachments": c.attachments or []} for c in db.query(Case)]
        result = backup_readback(store, rows, args.destination)
    print(json.dumps(result))

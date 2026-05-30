#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate KPI data model V1 wiring.

Scope:
- Imports backend SQLAlchemy models.
- Confirms expected KPI tables/columns are registered on Base.metadata.
- Confirms Alembic 0002 migration exists and chains from 0001_baseline.
- Does not connect to the database.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from db import Base  # type: ignore
    import models  # noqa: F401  # registers tables on Base.metadata
except Exception as exc:
    raise SystemExit(f"ERROR: failed to import backend models: {exc}")

EXPECTED = {
    "imaging_studies": {
        "id", "case_id", "modality", "body_part", "taken_at", "is_planned_review",
        "tag", "report_url", "viewer_url", "thumbnail_url", "metadata", "created_at",
    },
    "imaging_billing": {
        "id", "case_id", "imaging_id", "fee", "tag", "bill_date", "created_at",
    },
    "followups": {
        "id", "case_id", "due_date", "done_at", "channel", "owner", "status",
        "note", "created_at", "updated_at",
    },
    "qa_audit": {
        "id", "case_id", "auditor", "audit_type", "findings", "severity",
        "status", "metadata", "created_at",
    },
}

errors = []
for table_name, expected_columns in EXPECTED.items():
    table = Base.metadata.tables.get(table_name)
    if table is None:
        errors.append(f"missing table on metadata: {table_name}")
        continue
    columns = set(table.columns.keys())
    missing = expected_columns - columns
    if missing:
        errors.append(f"{table_name} missing columns: {sorted(missing)}")

migration = ROOT / "backend" / "migrations" / "versions" / "0002_kpi_data_models.py"
if not migration.exists():
    errors.append("missing Alembic migration: 0002_kpi_data_models.py")
else:
    text = migration.read_text(encoding="utf-8")
    if 'revision = "0002_kpi_data_models"' not in text:
        errors.append("0002 migration revision id mismatch")
    if 'down_revision = "0001_baseline"' not in text:
        errors.append("0002 migration must chain from 0001_baseline")
    for table_name in EXPECTED:
        if f'"{table_name}"' not in text:
            errors.append(f"0002 migration does not mention table {table_name}")

models_path = ROOT / "backend" / "models.py"
models_text = models_path.read_text(encoding="utf-8")
for class_name in ("ImagingStudy", "ImagingBilling", "FollowUp", "QaAudit"):
    if not re.search(rf"class\s+{class_name}\s*\(", models_text):
        errors.append(f"models.py missing class {class_name}")

if errors:
    print("KPI data model validation failed:")
    for error in errors:
        print(f"  - {error}")
    raise SystemExit(2)

print("OK KPI data models: ORM metadata and Alembic 0002 migration are present")

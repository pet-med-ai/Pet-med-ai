#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Map a validated legacy cases CSV into Pet-Med-AI CaseCreate JSONL payloads.

Scope:
- Dry-run only.
- Does not connect to the database.
- Does not call Pet-Med-AI APIs.
- Reuses scripts/validate_legacy_cases_csv.py before producing payloads.

Usage:
  python3 scripts/legacy_cases_to_case_payloads.py docs/migrations/LEGACY_CASES_IMPORT_TEMPLATE.csv
  python3 scripts/legacy_cases_to_case_payloads.py legacy_cases.csv \
    --jsonl-out legacy_case_payloads.jsonl \
    --errors-out migration_errors.csv \
    --report-out legacy_case_payload_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    import validate_legacy_cases_csv as validator
except Exception as exc:  # pragma: no cover - fatal CLI setup guard
    raise SystemExit(f"ERROR: failed to import validate_legacy_cases_csv.py: {exc}")


CASE_CREATE_FIELDS = [
    "patient_name",
    "species",
    "sex",
    "age_info",
    "breed",
    "weight",
    "coat_color",
    "owner_name",
    "owner_phone",
    "chief_complaint",
    "history",
    "exam_findings",
]

SPECIES_NORMALIZATION = {
    "avian": "bird",
    "mouse": "rat",
    "mice": "rat",
    "guinea pig": "guinea_pig",
    "guinea-pig": "guinea_pig",
    "sugar glider": "sugar_glider",
    "sugar-glider": "sugar_glider",
}


def clean(value: Any) -> str:
    return str(value if value is not None else "").strip()


def normalize_species(value: Any) -> str:
    text = clean(value).lower().replace(" ", "_").replace("-", "_")
    text = SPECIES_NORMALIZATION.get(text, text)
    return text or "other"


def format_weight(value: Any) -> Optional[str]:
    text = clean(value)
    if not text:
        return None
    return f"{text}kg"


def date_line(label: str, value: Any) -> str:
    text = clean(value)
    return f"{label}：{text or '未记录'}"


def build_history(row: Dict[str, str]) -> str:
    lines = [
        "【旧系统迁移记录】",
        date_line("旧病例ID", row.get("case_id")),
        date_line("就诊日期", row.get("visit_date")),
        date_line("旧系统状态", row.get("status")),
        date_line("临床医生", row.get("clinician")),
        date_line("旧系统主要诊断", row.get("primary_dx")),
        date_line("回访到期日", row.get("follow_up_due")),
        date_line("回访完成状态", row.get("follow_up_done")),
        date_line("旧系统创建时间", row.get("created_at")),
        date_line("旧系统更新时间", row.get("updated_at")),
        date_line("迁移幂等键", row.get("idempotency_key")),
    ]
    return "\n".join(lines)


def build_exam_findings(row: Dict[str, str]) -> str:
    imaging_count = clean(row.get("imaging_count")) or "0"
    imaging_repeat_count = clean(row.get("imaging_repeat_count")) or "0"
    return "\n".join([
        "【旧系统影像/附件元数据】",
        f"影像数量：{imaging_count}",
        f"影像复拍数量：{imaging_repeat_count}",
        "说明：dry-run V1 只映射影像元数据，不搬迁原始影像大文件。",
    ])


def build_chief_complaint(row: Dict[str, str]) -> str:
    primary_dx = clean(row.get("primary_dx"))
    visit_date = clean(row.get("visit_date"))
    if primary_dx:
        return f"旧系统导入病例：{primary_dx}（就诊日期：{visit_date or '未记录'}）"
    return f"旧系统导入病例（就诊日期：{visit_date or '未记录'}）"


def build_case_create_payload(row: Dict[str, str]) -> Dict[str, Any]:
    payload = {
        "patient_name": clean(row.get("pet_name")) or "未命名病例",
        "species": normalize_species(row.get("species")),
        "sex": None,
        "age_info": None,
        "breed": None,
        "weight": format_weight(row.get("weight_kg")),
        "coat_color": None,
        "owner_name": None,
        "owner_phone": None,
        "chief_complaint": build_chief_complaint(row),
        "history": build_history(row),
        "exam_findings": build_exam_findings(row),
    }
    return {field: payload.get(field) for field in CASE_CREATE_FIELDS}


def build_jsonl_record(row: Dict[str, str], source_file: Path, row_number: int) -> Dict[str, Any]:
    case_create = build_case_create_payload(row)
    return {
        "operation": "case_create",
        "dry_run": True,
        "source": "legacy_cases_csv",
        "source_file": str(source_file),
        "source_row_number": row_number,
        "legacy_case_id": clean(row.get("case_id")),
        "idempotency_key": clean(row.get("idempotency_key")),
        "case_create": case_create,
        "legacy": {
            "case_id": clean(row.get("case_id")),
            "visit_date": clean(row.get("visit_date")),
            "clinician": clean(row.get("clinician")),
            "primary_dx": clean(row.get("primary_dx")),
            "status": clean(row.get("status")),
            "imaging_count": clean(row.get("imaging_count")),
            "imaging_repeat_count": clean(row.get("imaging_repeat_count")),
            "follow_up_due": clean(row.get("follow_up_due")),
            "follow_up_done": clean(row.get("follow_up_done")),
            "created_at": clean(row.get("created_at")),
            "updated_at": clean(row.get("updated_at")),
        },
    }


def default_jsonl_path(csv_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return csv_path.parent / f"legacy_case_payloads_{timestamp}.jsonl"


def default_errors_path(csv_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return csv_path.parent / f"migration_errors_{timestamp}.csv"


def default_report_path(jsonl_path: Path) -> Path:
    return jsonl_path.with_suffix(".report.json")


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=False) + "\n")
            count += 1
    return count


def write_report(path: Path, csv_path: Path, jsonl_path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    species_counts = Counter(record["case_create"].get("species") or "other" for record in records)
    status_counts = Counter(record["legacy"].get("status") or "" for record in records)
    report = {
        "status": "PASS",
        "mode": "dry_run",
        "source_file": str(csv_path),
        "jsonl_out": str(jsonl_path),
        "payload_rows": len(records),
        "operation": "case_create",
        "writes_database": False,
        "calls_api": False,
        "species_counts": dict(sorted(species_counts.items())),
        "legacy_status_counts": dict(sorted(status_counts.items())),
        "case_create_fields": CASE_CREATE_FIELDS,
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_failed_report(path: Path, csv_path: Path, errors_out: Path, error_count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "FAILED",
        "mode": "dry_run",
        "source_file": str(csv_path),
        "errors_out": str(errors_out),
        "error_count": error_count,
        "payload_rows": 0,
        "writes_database": False,
        "calls_api": False,
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_and_validate(csv_path: Path, strict_header: bool):
    header, rows = validator.read_csv(csv_path)
    errors = validator.validate_header(header, strict_header=strict_header)
    if errors:
        return header, rows, errors, []
    row_errors, normalized_rows = validator.validate_rows(rows)
    return header, rows, row_errors, normalized_rows


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry-run map legacy case CSV to Pet-Med-AI CaseCreate JSONL payloads.")
    parser.add_argument("csv_file", help="Path to legacy cases CSV.")
    parser.add_argument("--jsonl-out", default="", help="Output JSONL path. Default: legacy_case_payloads_YYYYMMDD_HHMMSS.jsonl next to input.")
    parser.add_argument("--errors-out", default="", help="Output validation error CSV path. Default: migration_errors_YYYYMMDD_HHMMSS.csv next to input.")
    parser.add_argument("--report-out", default="", help="Output JSON dry-run report path. Default: JSONL path with .report.json suffix.")
    parser.add_argument("--strict-header", action="store_true", help="Require exact template header order before mapping.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}", file=sys.stderr)
        return 1

    jsonl_out = Path(args.jsonl_out) if args.jsonl_out else default_jsonl_path(csv_path)
    errors_out = Path(args.errors_out) if args.errors_out else default_errors_path(csv_path)
    report_out = Path(args.report_out) if args.report_out else default_report_path(jsonl_out)

    try:
        header, rows, errors, normalized_rows = load_and_validate(csv_path, bool(args.strict_header))
    except Exception as exc:
        print(f"ERROR: failed to validate CSV: {exc}", file=sys.stderr)
        return 1

    validator.write_errors(errors_out, errors)

    if errors:
        write_failed_report(report_out, csv_path, errors_out, len(errors))
        print("Legacy case payload dry-run")
        print(f"  file: {csv_path}")
        print(f"  rows: {len(rows)}")
        print(f"  errors: {len(errors)}")
        print(f"  errors_out: {errors_out}")
        print(f"  report_out: {report_out}")
        print("  status: FAILED")
        return 2

    records = [
        build_jsonl_record(row, source_file=csv_path, row_number=index)
        for index, row in enumerate(normalized_rows, start=2)
    ]
    count = write_jsonl(jsonl_out, records)
    write_report(report_out, csv_path, jsonl_out, records)

    print("Legacy case payload dry-run")
    print(f"  file: {csv_path}")
    print(f"  rows: {len(rows)}")
    print(f"  payload_rows: {count}")
    print(f"  jsonl_out: {jsonl_out}")
    print(f"  errors_out: {errors_out}")
    print(f"  report_out: {report_out}")
    print("  writes_database: false")
    print("  calls_api: false")
    print("  status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

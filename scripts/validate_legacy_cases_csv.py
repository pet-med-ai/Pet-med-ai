#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legacy case CSV pre-validator for Pet-Med-AI.

Scope:
- Dry-run validation only.
- Does not connect to the database.
- Does not write Pet-Med-AI records.
- Writes a machine-readable error CSV for failed rows.

Usage:
  python3 scripts/validate_legacy_cases_csv.py docs/migrations/LEGACY_CASES_IMPORT_TEMPLATE.csv
  python3 scripts/validate_legacy_cases_csv.py legacy_cases.csv --errors-out migration_errors.csv --report-out migration_report.json
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


EXPECTED_COLUMNS = [
    "case_id",
    "visit_date",
    "pet_name",
    "species",
    "weight_kg",
    "clinician",
    "primary_dx",
    "imaging_count",
    "imaging_repeat_count",
    "follow_up_due",
    "follow_up_done",
    "status",
    "created_at",
    "updated_at",
]

REQUIRED_COLUMNS = list(EXPECTED_COLUMNS)

REQUIRED_NON_EMPTY = {
    "case_id",
    "visit_date",
    "pet_name",
    "species",
    "status",
    "created_at",
    "updated_at",
}

ALLOWED_SPECIES = {
    "dog",
    "cat",
    "rabbit",
    "bird",
    "avian",
    "reptile",
    "turtle",
    "snake",
    "lizard",
    "amphibian",
    "ferret",
    "rodent",
    "guinea_pig",
    "hamster",
    "chinchilla",
    "rat",
    "mouse",
    "hedgehog",
    "sugar_glider",
    "fish",
    "other",
}

ALLOWED_STATUS = {
    "active",
    "closed",
    "archived",
    "inactive",
    "deleted",
    "draft",
}

BOOLEAN_LIKE = {
    "",
    "0",
    "1",
    "true",
    "false",
    "yes",
    "no",
    "y",
    "n",
    "done",
    "pending",
    "completed",
    "not_done",
    "未完成",
    "已完成",
    "是",
    "否",
}

CASE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{1,80}$")


@dataclass
class ValidationError:
    row_number: int
    case_id: str
    field: str
    original_value: str
    error_code: str
    error_reason: str
    suggestion: str


def clean(value: object) -> str:
    return str(value if value is not None else "").strip()


def parse_date(value: str) -> Optional[date]:
    value = clean(value)
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_datetime(value: str) -> Optional[datetime]:
    value = clean(value)
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def parse_non_negative_int(value: str) -> Optional[int]:
    value = clean(value)
    if value == "":
        return 0
    if not re.fullmatch(r"\d+", value):
        return None
    return int(value)


def parse_positive_float(value: str) -> Optional[float]:
    value = clean(value)
    if value == "":
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    if number <= 0:
        return None
    return number


def idempotency_key(case_id: str, updated_at: str) -> str:
    payload = f"{clean(case_id)}|{clean(updated_at)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def add_error(
    errors: List[ValidationError],
    row_number: int,
    row: Dict[str, str],
    field: str,
    code: str,
    reason: str,
    suggestion: str,
) -> None:
    errors.append(
        ValidationError(
            row_number=row_number,
            case_id=clean(row.get("case_id")),
            field=field,
            original_value=clean(row.get(field)),
            error_code=code,
            error_reason=reason,
            suggestion=suggestion,
        )
    )


def read_csv(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row.")
        rows = [dict(row) for row in reader]
        return [clean(name) for name in reader.fieldnames], rows


def validate_header(header: List[str], strict_header: bool) -> List[ValidationError]:
    errors: List[ValidationError] = []
    header_set = set(header)

    for column in REQUIRED_COLUMNS:
        if column not in header_set:
            errors.append(
                ValidationError(
                    row_number=1,
                    case_id="",
                    field=column,
                    original_value="",
                    error_code="missing_column",
                    error_reason=f"Missing required column: {column}",
                    suggestion=f"Add column {column} to the CSV header.",
                )
            )

    if strict_header and header != EXPECTED_COLUMNS:
        errors.append(
            ValidationError(
                row_number=1,
                case_id="",
                field="__header__",
                original_value=",".join(header),
                error_code="header_mismatch",
                error_reason="Header does not exactly match LEGACY_CASES_IMPORT_TEMPLATE.csv.",
                suggestion="Use the template header exactly, with the same order and spelling.",
            )
        )

    return errors


def validate_rows(rows: List[Dict[str, str]]) -> Tuple[List[ValidationError], List[Dict[str, str]]]:
    errors: List[ValidationError] = []
    normalized_rows: List[Dict[str, str]] = []
    seen_case_ids: Dict[str, int] = {}

    for index, row in enumerate(rows, start=2):
        normalized = {key: clean(value) for key, value in row.items() if key is not None}
        case_id = normalized.get("case_id", "")

        for field in REQUIRED_NON_EMPTY:
            if not normalized.get(field):
                add_error(
                    errors,
                    index,
                    normalized,
                    field,
                    "required",
                    f"{field} is required.",
                    f"Fill {field} before import.",
                )

        if case_id:
            if not CASE_ID_PATTERN.match(case_id):
                add_error(
                    errors,
                    index,
                    normalized,
                    "case_id",
                    "invalid_case_id",
                    "case_id contains unsupported characters or length.",
                    "Use stable ASCII identifiers such as HS-2026-000123.",
                )
            if case_id in seen_case_ids:
                add_error(
                    errors,
                    index,
                    normalized,
                    "case_id",
                    "duplicate_case_id",
                    f"case_id already appears on row {seen_case_ids[case_id]}.",
                    "Deduplicate rows or assign a stable unique case_id.",
                )
            else:
                seen_case_ids[case_id] = index

        visit_date = parse_date(normalized.get("visit_date", ""))
        if normalized.get("visit_date") and visit_date is None:
            add_error(
                errors,
                index,
                normalized,
                "visit_date",
                "invalid_date",
                "visit_date must be YYYY-MM-DD.",
                "Convert visit_date to ISO date, e.g. 2026-05-25.",
            )

        follow_up_due = parse_date(normalized.get("follow_up_due", ""))
        if normalized.get("follow_up_due") and follow_up_due is None:
            add_error(
                errors,
                index,
                normalized,
                "follow_up_due",
                "invalid_date",
                "follow_up_due must be blank or YYYY-MM-DD.",
                "Convert follow_up_due to ISO date or leave blank.",
            )

        if visit_date and follow_up_due and follow_up_due < visit_date:
            add_error(
                errors,
                index,
                normalized,
                "follow_up_due",
                "business_rule",
                "follow_up_due is earlier than visit_date.",
                "Set follow_up_due on or after visit_date.",
            )

        created_at = parse_datetime(normalized.get("created_at", ""))
        updated_at = parse_datetime(normalized.get("updated_at", ""))

        if normalized.get("created_at") and created_at is None:
            add_error(
                errors,
                index,
                normalized,
                "created_at",
                "invalid_datetime",
                "created_at must be ISO 8601 datetime with timezone.",
                "Use e.g. 2026-05-25T10:12:30+08:00.",
            )

        if normalized.get("updated_at") and updated_at is None:
            add_error(
                errors,
                index,
                normalized,
                "updated_at",
                "invalid_datetime",
                "updated_at must be ISO 8601 datetime with timezone.",
                "Use e.g. 2026-05-25T10:12:30+08:00.",
            )

        if created_at and updated_at and updated_at < created_at:
            add_error(
                errors,
                index,
                normalized,
                "updated_at",
                "business_rule",
                "updated_at is earlier than created_at.",
                "Verify timestamps and normalize timezone before import.",
            )

        species = normalized.get("species", "").lower()
        if species and species not in ALLOWED_SPECIES:
            add_error(
                errors,
                index,
                normalized,
                "species",
                "invalid_species",
                f"Unsupported species: {species}",
                "Map species to Pet-Med-AI internal values such as dog, cat, rabbit, bird, reptile, ferret, rodent, other.",
            )

        status = normalized.get("status", "").lower()
        if status and status not in ALLOWED_STATUS:
            add_error(
                errors,
                index,
                normalized,
                "status",
                "invalid_status",
                f"Unsupported status: {status}",
                "Map status to active, closed, archived, inactive, deleted, or draft.",
            )

        weight_raw = normalized.get("weight_kg", "")
        weight = parse_positive_float(weight_raw)
        if weight_raw and weight is None:
            add_error(
                errors,
                index,
                normalized,
                "weight_kg",
                "invalid_number",
                "weight_kg must be a positive number in kg.",
                "Convert weight to kg and keep numeric value only, e.g. 3.20.",
            )
        elif weight is not None and weight > 300:
            add_error(
                errors,
                index,
                normalized,
                "weight_kg",
                "out_of_range",
                "weight_kg is unusually high for companion animal records.",
                "Verify unit conversion. If this is not kg, convert before import.",
            )

        imaging_count = parse_non_negative_int(normalized.get("imaging_count", ""))
        imaging_repeat_count = parse_non_negative_int(normalized.get("imaging_repeat_count", ""))

        if imaging_count is None:
            add_error(
                errors,
                index,
                normalized,
                "imaging_count",
                "invalid_integer",
                "imaging_count must be a non-negative integer.",
                "Use 0 if no imaging exists.",
            )

        if imaging_repeat_count is None:
            add_error(
                errors,
                index,
                normalized,
                "imaging_repeat_count",
                "invalid_integer",
                "imaging_repeat_count must be a non-negative integer.",
                "Use 0 if no repeat imaging exists.",
            )

        if imaging_count is not None and imaging_repeat_count is not None and imaging_repeat_count > imaging_count:
            add_error(
                errors,
                index,
                normalized,
                "imaging_repeat_count",
                "business_rule",
                "imaging_repeat_count cannot exceed imaging_count.",
                "Verify imaging counters before import.",
            )

        follow_up_done = normalized.get("follow_up_done", "").lower()
        if follow_up_done not in BOOLEAN_LIKE:
            add_error(
                errors,
                index,
                normalized,
                "follow_up_done",
                "invalid_boolean",
                "follow_up_done must be blank or a boolean-like value.",
                "Use blank, true/false, yes/no, 1/0, done/pending, 已完成/未完成.",
            )

        normalized["idempotency_key"] = idempotency_key(normalized.get("case_id", ""), normalized.get("updated_at", ""))
        normalized_rows.append(normalized)

    return errors, normalized_rows


def write_errors(path: Path, errors: List[ValidationError]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "row_number",
        "case_id",
        "field",
        "original_value",
        "error_code",
        "error_reason",
        "suggestion",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for error in errors:
            writer.writerow(error.__dict__)


def write_normalized(path: Path, rows: List[Dict[str, str]], header: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(header + ["idempotency_key"]))
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, csv_path: Path, rows: List[Dict[str, str]], errors: List[ValidationError]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    total = len(rows)
    error_rows = {error.row_number for error in errors if error.row_number >= 2}
    by_code: Dict[str, int] = {}
    by_field: Dict[str, int] = {}
    for error in errors:
        by_code[error.error_code] = by_code.get(error.error_code, 0) + 1
        by_field[error.field] = by_field.get(error.field, 0) + 1

    report = {
        "source_file": str(csv_path),
        "total_rows": total,
        "valid_rows": max(0, total - len(error_rows)),
        "invalid_rows": len(error_rows),
        "error_count": len(errors),
        "errors_by_code": dict(sorted(by_code.items())),
        "errors_by_field": dict(sorted(by_field.items())),
        "passed": not errors,
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def default_error_path(csv_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return csv_path.parent / f"migration_errors_{timestamp}.csv"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate legacy case CSV before Pet-Med-AI import.")
    parser.add_argument("csv_file", help="Path to legacy case CSV.")
    parser.add_argument("--errors-out", default="", help="Path for error CSV. Default: migration_errors_YYYYMMDD_HHMMSS.csv next to input.")
    parser.add_argument("--report-out", default="", help="Optional JSON validation report output path.")
    parser.add_argument("--normalized-out", default="", help="Optional normalized CSV output path with idempotency_key.")
    parser.add_argument("--strict-header", action="store_true", help="Require exact template column order.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    csv_path = Path(args.csv_file)

    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}", file=sys.stderr)
        return 1

    try:
        header, rows = read_csv(csv_path)
    except Exception as exc:
        print(f"ERROR: failed to read CSV: {exc}", file=sys.stderr)
        return 1

    errors = validate_header(header, strict_header=bool(args.strict_header))
    if not errors:
        row_errors, normalized_rows = validate_rows(rows)
        errors.extend(row_errors)
    else:
        normalized_rows = []

    errors_out = Path(args.errors_out) if args.errors_out else default_error_path(csv_path)
    write_errors(errors_out, errors)

    if args.normalized_out:
        write_normalized(Path(args.normalized_out), normalized_rows, header)

    if args.report_out:
        write_report(Path(args.report_out), csv_path, rows, errors)

    print("Legacy cases CSV validation")
    print(f"  file: {csv_path}")
    print(f"  rows: {len(rows)}")
    print(f"  errors: {len(errors)}")
    print(f"  errors_out: {errors_out}")

    if errors:
        print("  status: FAILED")
        return 2

    print("  status: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

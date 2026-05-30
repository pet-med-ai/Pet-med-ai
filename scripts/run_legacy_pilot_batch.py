#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legacy case pilot batch runner for Pet-Med-AI.

Scope:
- Runs CSV validation.
- Maps valid legacy CSV rows to CaseCreate JSONL payloads.
- Optionally calls /api/migrations/legacy-cases/dry-run to get backend batch report.
- Generates a clinical review checklist CSV.
- Never writes database records.
- Never calls /api/cases.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    import validate_legacy_cases_csv as validator
    import legacy_cases_to_case_payloads as mapper
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"ERROR: failed to import legacy migration scripts: {exc}")


def clean(value: Any) -> str:
    return str(value if value is not None else "").strip()


def now_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if text:
                records.append(json.loads(text))
    return records


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def call_api_dry_run(
    *,
    base_url: str,
    token: str,
    batch_id: str,
    records: List[Dict[str, Any]],
    chunk_size: int,
    sample_size: int,
    include_items: bool,
    timeout: int = 120,
) -> Dict[str, Any]:
    base = base_url.rstrip("/")
    url = f"{base}/api/migrations/legacy-cases/dry-run"
    body = {
        "batch_id": batch_id,
        "records": records,
        "options": {
            "chunk_size": chunk_size,
            "sample_limit": sample_size,
            "include_items": include_items,
        },
    }
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API dry-run failed HTTP {exc.code}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"API dry-run connection failed: {exc}") from exc


def build_review_rows(*, records: List[Dict[str, Any]], api_report: Optional[Dict[str, Any]], sample_size: int) -> List[Dict[str, str]]:
    status_by_index: Dict[int, str] = {}
    if isinstance(api_report, dict):
        for item in api_report.get("items") or []:
            try:
                index = int(item.get("index"))
            except Exception:
                continue
            status_by_index[index] = clean(item.get("status")) or "unknown"

    rows: List[Dict[str, str]] = []
    for idx, record in enumerate(records[:sample_size], start=1):
        case_create = record.get("case_create") if isinstance(record.get("case_create"), dict) else {}
        legacy = record.get("legacy") if isinstance(record.get("legacy"), dict) else {}
        rows.append({
            "review_id": f"pilot-{idx:04d}",
            "source_row_number": clean(record.get("source_row_number")),
            "legacy_case_id": clean(record.get("legacy_case_id") or legacy.get("case_id")),
            "idempotency_key": clean(record.get("idempotency_key")),
            "pet_name": clean(case_create.get("patient_name")),
            "species": clean(case_create.get("species")),
            "visit_date": clean(legacy.get("visit_date")),
            "primary_dx": clean(legacy.get("primary_dx")),
            "case_create_patient_name": clean(case_create.get("patient_name")),
            "case_create_species": clean(case_create.get("species")),
            "case_create_chief_complaint": clean(case_create.get("chief_complaint")),
            "has_history": "yes" if clean(case_create.get("history")) else "no",
            "has_exam_findings": "yes" if clean(case_create.get("exam_findings")) else "no",
            "api_status": status_by_index.get(idx, "not_called"),
            "ready_for_review": "yes",
            "clinical_reviewer": "",
            "clinical_result": "",
            "notes": "",
        })
    return rows


def write_review_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "review_id", "source_row_number", "legacy_case_id", "idempotency_key", "pet_name", "species",
        "visit_date", "primary_dx", "case_create_patient_name", "case_create_species",
        "case_create_chief_complaint", "has_history", "has_exam_findings", "api_status", "ready_for_review",
        "clinical_reviewer", "clinical_result", "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def quality_gate(api_report: Optional[Dict[str, Any]], records: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    if api_report is None:
        return True, ["API dry-run was not requested; local artifacts generated only."]
    if api_report.get("writes_database") is not False:
        reasons.append("API dry-run report does not explicitly state writes_database=false.")
    if api_report.get("calls_case_create_api") is not False:
        reasons.append("API dry-run report does not explicitly state calls_case_create_api=false.")
    if api_report.get("accepted") != len(records):
        reasons.append(f"Accepted count mismatch: expected {len(records)}, actual {api_report.get('accepted')}.")
    if api_report.get("rejected") not in (0, "0"):
        reasons.append(f"Rejected count is not zero: {api_report.get('rejected')}.")
    if api_report.get("ready_for_import") is not True:
        reasons.append("API report ready_for_import is not true.")
    return not reasons, reasons


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a legacy case pilot batch dry-run.")
    parser.add_argument("csv_file", help="Legacy case CSV file.")
    parser.add_argument("--work-dir", default="", help="Directory for pilot artifacts. Default: docs/migrations/pilot_runs/pilot_YYYYMMDD_HHMMSS")
    parser.add_argument("--batch-id", default="", help="Batch id for reports/API dry-run.")
    parser.add_argument("--sample-size", type=int, default=200, help="Number of rows to include in clinical review checklist.")
    parser.add_argument("--chunk-size", type=int, default=1000, help="API dry-run chunk size hint.")
    parser.add_argument("--strict-header", action="store_true", help="Require exact template header order.")
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", ""), help="Optional Pet-Med-AI base URL for API dry-run.")
    parser.add_argument("--token", default=os.getenv("PETMED_TOKEN", ""), help="Optional bearer token for API dry-run.")
    parser.add_argument("--include-items", action="store_true", help="Request full per-record items from API dry-run report.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}", file=sys.stderr)
        return 1
    if bool(args.base_url) ^ bool(args.token):
        print("ERROR: --base-url and --token must be provided together for API dry-run.", file=sys.stderr)
        return 1

    batch_id = args.batch_id or f"pilot-{now_id()}"
    work_dir = Path(args.work_dir) if args.work_dir else Path("docs/migrations/pilot_runs") / batch_id
    work_dir.mkdir(parents=True, exist_ok=True)

    errors_out = work_dir / "migration_errors.csv"
    jsonl_out = work_dir / "legacy_case_payloads.jsonl"
    mapper_report_out = work_dir / "legacy_case_payload_report.json"
    api_request_out = work_dir / "api_dry_run_request.json"
    api_report_out = work_dir / "api_dry_run_report.json"
    review_csv_out = work_dir / "pilot_review_checklist.csv"
    signoff_out = work_dir / "clinical_signoff.md"
    pilot_report_out = work_dir / "pilot_report.json"

    exit_code = mapper.main([
        str(csv_path),
        "--jsonl-out", str(jsonl_out),
        "--errors-out", str(errors_out),
        "--report-out", str(mapper_report_out),
        *(["--strict-header"] if args.strict_header else []),
    ])
    if exit_code != 0:
        report = {
            "status": "FAILED",
            "mode": "legacy_pilot_batch_v1",
            "batch_id": batch_id,
            "source_file": str(csv_path),
            "work_dir": str(work_dir),
            "writes_database": False,
            "calls_case_create_api": False,
            "failure_stage": "csv_validation_or_payload_mapping",
            "artifacts": {"errors_csv": str(errors_out), "mapper_report": str(mapper_report_out)},
        }
        write_json(pilot_report_out, report)
        print("Legacy pilot batch V1")
        print(f"  batch_id: {batch_id}")
        print(f"  work_dir: {work_dir}")
        print("  status: FAILED")
        return 2

    records = read_jsonl(jsonl_out)
    api_report: Optional[Dict[str, Any]] = None
    if args.base_url and args.token:
        request_body = {
            "batch_id": batch_id,
            "records": records,
            "options": {"chunk_size": args.chunk_size, "sample_limit": min(max(args.sample_size, 0), 100), "include_items": bool(args.include_items)},
        }
        write_json(api_request_out, request_body)
        api_report = call_api_dry_run(
            base_url=args.base_url,
            token=args.token,
            batch_id=batch_id,
            records=records,
            chunk_size=args.chunk_size,
            sample_size=min(max(args.sample_size, 0), 100),
            include_items=bool(args.include_items),
        )
        write_json(api_report_out, api_report)

    review_rows = build_review_rows(records=records, api_report=api_report, sample_size=max(0, args.sample_size))
    write_review_csv(review_csv_out, review_rows)

    signoff_text = (
        f"# Legacy Pilot Batch Clinical Sign-off\n\n"
        f"Batch ID: {batch_id}\n"
        f"Source CSV: {csv_path}\n"
        f"Work dir: {work_dir}\n"
        f"Payload rows: {len(records)}\n"
        f"Review checklist: {review_csv_out}\n\n"
        "## Review requirement\n\n"
        "- Review all rows in `pilot_review_checklist.csv` for this pilot batch, or at least the agreed sample size.\n"
        "- Confirm patient name, species, visit date, diagnosis summary, history, and imaging metadata display correctly.\n"
        "- This pilot does not write database records and does not call `/api/cases`.\n\n"
        "## Sign-off\n\n"
        "Clinical reviewer:\n"
        "Date:\n"
        "Result: PASS / FAIL\n"
        "Notes:\n"
    )
    write_text(signoff_out, signoff_text)

    gate_ok, gate_reasons = quality_gate(api_report, records)
    report = {
        "status": "PASS" if gate_ok else "FAILED",
        "mode": "legacy_pilot_batch_v1",
        "batch_id": batch_id,
        "source_file": str(csv_path),
        "work_dir": str(work_dir),
        "writes_database": False,
        "calls_case_create_api": False,
        "api_dry_run_called": api_report is not None,
        "source_rows": len(records),
        "payload_rows": len(records),
        "review_rows": len(review_rows),
        "quality_gate": {"passed": gate_ok, "reasons": gate_reasons},
        "api_summary": (api_report or {}).get("summary") if isinstance(api_report, dict) else None,
        "api_ready_for_import": (api_report or {}).get("ready_for_import") if isinstance(api_report, dict) else None,
        "artifacts": {
            "errors_csv": str(errors_out),
            "payload_jsonl": str(jsonl_out),
            "payload_report": str(mapper_report_out),
            "api_request": str(api_request_out) if api_report is not None else "",
            "api_report": str(api_report_out) if api_report is not None else "",
            "review_checklist": str(review_csv_out),
            "clinical_signoff": str(signoff_out),
            "pilot_report": str(pilot_report_out),
        },
        "next_gate": "clinical sign-off before any real import implementation.",
    }
    write_json(pilot_report_out, report)

    print("Legacy pilot batch V1")
    print(f"  batch_id: {batch_id}")
    print(f"  source_file: {csv_path}")
    print(f"  work_dir: {work_dir}")
    print(f"  payload_rows: {len(records)}")
    print(f"  review_rows: {len(review_rows)}")
    print("  writes_database: false")
    print("  calls_case_create_api: false")
    print(f"  api_dry_run_called: {str(api_report is not None).lower()}")
    print(f"  pilot_report: {pilot_report_out}")
    print(f"  status: {'PASS' if gate_ok else 'FAILED'}")
    if not gate_ok:
        for reason in gate_reasons:
            print(f"  gate_reason: {reason}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

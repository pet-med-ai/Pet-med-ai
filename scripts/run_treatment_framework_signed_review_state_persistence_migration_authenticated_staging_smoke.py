#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Guarded PMAI-P0-03 authenticated staging smoke runner.

Python 3.9+. Standard library only.

The runner refuses the production backend, requires an isolated staging
hostname and explicit execution confirmation, and writes only synthetic
staging users, one synthetic staging case, and one append-only audit row.
It never runs Alembic, never creates revision 0010, never writes
Case.treatment or prescription data, and never emits medication amount,
route, or frequency.

It is deliberately not invoked by CI or scripts/smoke_petmed.sh.
"""
from __future__ import print_function

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

STAGE_ID = "PMAI-P0-03"
BASELINE_COMMIT = "b37362a2a343b068926edce4862b6f7d7c62a19d"
EXECUTION_CONFIRMATION = "PMAI-P0-03-AUTHENTICATED-STAGING-SMOKE"
PRODUCTION_HOST = "pet-med-ai-backend.onrender.com"
DEFAULT_PRODUCTION_URL = "https://" + PRODUCTION_HOST
EXPECTED_REVISION = "0009_diag_data"
AUDIT_APPEND_CONFIRMATION = (
    "I_UNDERSTAND_THIS_APPENDS_TREATMENT_FRAMEWORK_AUDIT_LOG_ONLY"
)
DANGEROUS_FLAGS = [
    "ENABLE_EMR_REAL_IMPORT",
    "ENABLE_EMR_IMPORT_CASE_UPDATE",
    "ENABLE_EMR_ATTACHMENT_DOWNLOAD",
    "ENABLE_PREVENTIVE_AUTO_DELIVERY",
    "ENABLE_PREVENTIVE_SMS_DELIVERY",
    "ENABLE_PREVENTIVE_WECHAT_DELIVERY",
    "ENABLE_PREVENTIVE_EMAIL_DELIVERY",
    "ENABLE_PRESCRIPTION_STRUCTURED_WRITE",
    "ENABLE_DEVICE_REAL_INGEST",
    "ENABLE_BILLING_REAL_WRITE",
]

BUILD_PATH = (
    "/api/diagnostic-data/dry-run/confirmed-diagnosis/"
    "treatment-framework/build"
)
REVIEW_PATH = (
    "/api/diagnostic-data/dry-run/confirmed-diagnosis/"
    "treatment-framework/review"
)
AUDIT_PATH = (
    "/api/diagnostic-data/confirmed-diagnosis/"
    "treatment-framework/audit-log/append"
)
SIGNED_PATH = (
    "/api/diagnostic-data/dry-run/confirmed-diagnosis/"
    "treatment-framework/signed-review-state/build"
)
PERSISTENCE_PATH = (
    "/api/diagnostic-data/dry-run/confirmed-diagnosis/"
    "treatment-framework/signed-review-state/persistence/prepare"
)
MIGRATION_PATH = (
    "/api/diagnostic-data/dry-run/confirmed-diagnosis/"
    "treatment-framework/signed-review-state/persistence/migration/dry-run"
)

FORBIDDEN_EVIDENCE_PATTERNS = [
    re.compile(r"(?i)(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)\b(?:password|passwd|access[_-]?token|api[_-]?key|secret)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
]


class SmokeFailure(RuntimeError):
    pass


def fail(message: str) -> None:
    raise SmokeFailure(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def canonical_hash(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def pseudonymize(label: str, value: Any, run_id: str) -> str:
    raw = ("%s:%s:%s" % (label, value, run_id)).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def run_git(repo_root: Path, args: Sequence[str], check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git"] + list(args),
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if check and result.returncode != 0:
        fail(
            "git command failed: git %s: %s"
            % (" ".join(args), result.stderr.strip() or result.stdout.strip())
        )
    return result


def repo_preflight(repo_root: Path) -> str:
    if not (repo_root / ".git").exists():
        fail("repo root is not a Git worktree")
    dirty = run_git(repo_root, ["status", "--short"]).stdout.strip()
    if dirty:
        fail("Git worktree must be clean before external staging smoke")
    if run_git(
        repo_root,
        ["merge-base", "--is-ancestor", BASELINE_COMMIT, "HEAD"],
        check=False,
    ).returncode != 0:
        fail("PMAI-P0-02 completion commit is not an ancestor of HEAD")
    active = sorted(
        (repo_root / "backend" / "migrations" / "versions").glob("0010*.py")
    )
    if active:
        fail("active backend/migrations/versions/0010*.py is forbidden")
    return run_git(repo_root, ["rev-parse", "--short", "HEAD"]).stdout.strip()


def normalize_base_url(raw: str) -> str:
    value = str(raw or "").strip().rstrip("/")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        fail("staging base URL must be an HTTPS URL")
    host = parsed.hostname.lower()
    if host == PRODUCTION_HOST or value == DEFAULT_PRODUCTION_URL:
        fail("production backend URL is forbidden")
    if "staging" not in host:
        fail("staging base URL hostname must contain the staging marker")
    return value


def request_json(
    base_url: str,
    method: str,
    path: str,
    *,
    body: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None,
    form: Optional[Dict[str, str]] = None,
    timeout: int = 90,
) -> Tuple[int, Dict[str, Any]]:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    elif form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urllib.parse.urlencode(form).encode("utf-8")
    if token:
        headers["Authorization"] = "Bearer " + token

    request = urllib.request.Request(
        base_url + path,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            raw = response.read()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        raw = exc.read()
    except Exception as exc:
        fail("HTTP request failed for %s %s: %s" % (method, path, exc))

    if not raw:
        return status, {}
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception:
        parsed = {"_non_json_body": raw.decode("utf-8", errors="replace")[:500]}
    if not isinstance(parsed, dict):
        parsed = {"_json_value": parsed}
    return status, parsed


def expect(status: int, expected: int, label: str, payload: Dict[str, Any]) -> None:
    if status != expected:
        detail = payload.get("detail") or payload.get("message") or payload
        fail("%s: expected HTTP %s, got %s: %r" % (label, expected, status, detail))


def check_version(base_url: str, label: str) -> Dict[str, Any]:
    status, data = request_json(base_url, "GET", "/api/system/version")
    expect(status, 200, label + " version", data)
    expected = {
        "database_revision": EXPECTED_REVISION,
        "alembic_head": EXPECTED_REVISION,
        "schema_ok": True,
        "writes_database": False,
        "exposes_database_url": False,
    }
    errors = [
        "%s=%r" % (key, data.get(key))
        for key, value in expected.items()
        if data.get(key) != value
    ]
    if data.get("migration_errors") != []:
        errors.append("migration_errors=%r" % data.get("migration_errors"))
    if errors:
        fail(label + " hard gate mismatch: " + ", ".join(errors))
    return data


def check_flags(base_url: str, label: str) -> Dict[str, Any]:
    status, data = request_json(base_url, "GET", "/api/system/feature-flags")
    expect(status, 200, label + " feature flags", data)
    flags = data.get("flags") if isinstance(data.get("flags"), dict) else {}
    bad = []
    for key in DANGEROUS_FLAGS:
        value = flags.get(key)
        enabled = value.get("enabled") if isinstance(value, dict) else value
        if enabled is not False:
            bad.append(key)
    if bad or data.get("all_dangerous_features_disabled") is not True:
        fail(label + " dangerous feature flags are not all disabled: " + ",".join(bad))
    return data


def signup(base_url: str, email: str, password: str, full_name: str) -> Dict[str, Any]:
    status, data = request_json(
        base_url,
        "POST",
        "/auth/signup",
        body={"email": email, "password": password, "full_name": full_name},
    )
    expect(status, 200, "signup " + full_name, data)
    return data


def login(base_url: str, email: str, password: str) -> str:
    status, data = request_json(
        base_url,
        "POST",
        "/auth/login",
        form={"username": email, "password": password},
    )
    expect(status, 200, "login", data)
    token = str(data.get("access_token") or "").strip()
    if not token:
        fail("login response has no access token")
    return token


def audit_rows_for_case(base_url: str, token: str, case_id: int) -> List[Dict[str, Any]]:
    status, data = request_json(
        base_url,
        "GET",
        "/api/diagnostic-data/clinical-qa-dashboard/v2/summary?case_id=%s"
        % case_id,
        token=token,
    )
    expect(status, 200, "owner-scoped audit readback", data)
    rows = data.get("audit_logs")
    if not isinstance(rows, list):
        fail("audit readback has no audit_logs list")
    return [item for item in rows if isinstance(item, dict)]


def require_bool(data: Dict[str, Any], key: str, expected: bool, label: str) -> None:
    if data.get(key) is not expected:
        fail("%s: %s expected %s, got %r" % (label, key, expected, data.get(key)))


def check_safe_preview_response(data: Dict[str, Any], label: str) -> None:
    require_bool(data, "writes_database", False, label)
    require_bool(data, "writes_case_treatment", False, label)
    require_bool(data, "writes_prescription", False, label)
    require_bool(data, "returns_drug_dose", False, label)
    require_bool(data, "returns_drug_route", False, label)
    require_bool(data, "returns_drug_frequency", False, label)
    require_bool(data, "not_client_facing", True, label)


def run_readonly_chain(
    base_url: str,
    token: str,
    *,
    case_id: int,
    diagnosis: str,
    clinician_id: str,
    audit_log_id: str,
) -> Dict[str, Any]:
    base_payload = {
        "case_id": case_id,
        "confirmed_diagnosis_label": diagnosis,
        "confirmed_by": clinician_id,
        "confirmation_source": "clinician_confirmed",
        "ai_generated": False,
    }
    status, build = request_json(base_url, "POST", BUILD_PATH, body=base_payload, token=token)
    expect(status, 200, "treatment framework build", build)
    check_safe_preview_response(build, "treatment framework build")
    preview = build.get("treatment_framework_preview")
    if not isinstance(preview, dict) or not preview:
        fail("treatment framework preview is missing")

    review_payload = dict(base_payload)
    review_payload.update(
        {
            "treatment_framework_preview": preview,
            "reviewed_by": clinician_id,
            "review_decision": "approve_for_clinician_use",
            "review_note": "Synthetic internal clinician review.",
        }
    )
    status, review = request_json(base_url, "POST", REVIEW_PATH, body=review_payload, token=token)
    expect(status, 200, "clinician review", review)
    check_safe_preview_response(review, "clinician review")

    signed_payload = dict(review_payload)
    signed_payload.update(
        {
            "signed_by": clinician_id,
            "signoff_decision": "sign_internal_review",
            "audit_log_id": audit_log_id,
        }
    )
    status, signed = request_json(base_url, "POST", SIGNED_PATH, body=signed_payload, token=token)
    expect(status, 200, "signed review state preview", signed)
    check_safe_preview_response(signed, "signed review state preview")
    signed_preview = signed.get("signed_review_state_preview")
    if not isinstance(signed_preview, dict) or not signed_preview:
        fail("signed review state preview is missing")
    if int(signed_preview.get("case_id") or -1) != case_id:
        fail("signed review state preview case link mismatch")
    if signed_preview.get("persisted") is not False:
        fail("signed review state preview unexpectedly persisted")

    persistence_payload = dict(signed_payload)
    persistence_payload.update(
        {
            "signed_review_state_preview": signed_preview,
            "persistence_requested_by": clinician_id,
        }
    )
    status, persistence = request_json(
        base_url,
        "POST",
        PERSISTENCE_PATH,
        body=persistence_payload,
        token=token,
    )
    expect(status, 200, "persistence prepare preview", persistence)
    check_safe_preview_response(persistence, "persistence prepare preview")
    persistence_preview = persistence.get("persistence_dry_run_preview")
    if not isinstance(persistence_preview, dict) or not persistence_preview:
        fail("persistence dry-run preview is missing")

    migration_payload = dict(persistence_payload)
    migration_payload.update(
        {
            "persistence_dry_run_preview": persistence_preview,
            "migration_design_acknowledged": True,
            "migration_readiness_review_completed": True,
            "migration_dry_run_requested_by": clinician_id,
        }
    )
    status, migration = request_json(
        base_url,
        "POST",
        MIGRATION_PATH,
        body=migration_payload,
        token=token,
    )
    expect(status, 200, "migration path preview", migration)
    check_safe_preview_response(migration, "migration path preview")
    if migration.get("migration_enabled") is not False:
        fail("migration path preview unexpectedly enables migration")
    if migration.get("migration_file_created") is not False:
        fail("migration path preview unexpectedly creates a migration file")

    return {
        "build_hash": canonical_hash(preview),
        "review_hash": canonical_hash(
            {
                "preview": review.get("treatment_framework_preview"),
                "workflow": review.get("review_workflow"),
            }
        ),
        "signed_hash": canonical_hash(signed_preview),
        "persistence_hash": canonical_hash(persistence_preview),
        "migration_hash": canonical_hash(migration.get("migration_plan_preview")),
        "preview": preview,
        "review_payload": review_payload,
        "signed_payload": signed_payload,
        "persistence_payload": persistence_payload,
        "migration_payload": migration_payload,
        "signed_preview": signed_preview,
        "persistence_preview": persistence_preview,
    }


def sanitize_and_write(workspace: Path, evidence: Dict[str, Any]) -> Tuple[Path, str]:
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        workspace.chmod(0o700)
    except OSError:
        pass
    text = json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    for pattern in FORBIDDEN_EVIDENCE_PATTERNS:
        if pattern.search(text):
            fail("sanitized evidence contains a forbidden secret or identity pattern")
    path = workspace / (
        "PMAI_P0_03_AUTHENTICATED_STAGING_SMOKE_V1.json"
    )
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(text, encoding="utf-8")
    temp.chmod(0o600)
    temp.replace(path)
    path.chmod(0o600)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, digest


def execute(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).expanduser().resolve()
    repo_head = repo_preflight(repo_root)
    staging_url = normalize_base_url(args.base_url)
    production_url = str(args.production_base_url or DEFAULT_PRODUCTION_URL).strip().rstrip("/")
    if urllib.parse.urlsplit(production_url).hostname != PRODUCTION_HOST:
        fail("production hard-gate URL must be the canonical production backend")

    if not args.execute:
        check_version(staging_url, "staging")
        check_flags(staging_url, "staging")
        check_version(production_url, "production")
        check_flags(production_url, "production")
        print("stage_id=" + STAGE_ID)
        print("repo_head=" + repo_head)
        print("network_preflight=PASS")
        print("write_performed=false")
        print("PASS: PMAI-P0-03 authenticated staging smoke network preflight")
        return 0

    if args.confirm != EXECUTION_CONFIRMATION:
        fail("execution confirmation is missing")

    started_at = utc_now()
    check_version(staging_url, "staging")
    check_flags(staging_url, "staging")
    check_version(production_url, "production")
    check_flags(production_url, "production")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + secrets.token_hex(4)
    password = secrets.token_urlsafe(24)
    email_a = "p0-03-a-%s@%s" % (run_id, "example.com")
    email_b = "p0-03-b-%s@%s" % (run_id, "example.com")

    user_a = signup(staging_url, email_a, password, "P0-03 Synthetic A")
    user_b = signup(staging_url, email_b, password, "P0-03 Synthetic B")
    token_a = login(staging_url, email_a, password)
    token_b = login(staging_url, email_b, password)

    case_body = {
        "patient_name": "P0-03-SYNTHETIC-CASE",
        "species": "dog",
        "sex": None,
        "age_info": None,
        "breed": None,
        "weight": None,
        "coat_color": None,
        "owner_name": None,
        "owner_phone": None,
        "chief_complaint": "Synthetic authenticated staging smoke; no clinical use.",
        "history": None,
        "exam_findings": None,
    }
    status, created_case = request_json(
        staging_url,
        "POST",
        "/api/cases",
        body=case_body,
        token=token_a,
    )
    expect(status, 201, "synthetic case create", created_case)
    case_id = int(created_case.get("id") or 0)
    if case_id <= 0:
        fail("synthetic case create returned no case ID")
    if created_case.get("treatment") not in (None, ""):
        fail("synthetic case unexpectedly contains treatment")

    status, case_before = request_json(
        staging_url,
        "GET",
        "/api/cases/%s" % case_id,
        token=token_a,
    )
    expect(status, 200, "owner case read", case_before)
    case_before_hash = canonical_hash(case_before)

    status, denied_case = request_json(
        staging_url,
        "GET",
        "/api/cases/%s" % case_id,
        token=token_b,
    )
    expect(status, 404, "cross-user case denial", denied_case)

    diagnosis = "P0-03 synthetic clinician confirmed diagnosis"
    clinician_id = "p0-03-clinician-a"
    base_payload = {
        "case_id": case_id,
        "confirmed_diagnosis_label": diagnosis,
        "confirmed_by": clinician_id,
        "confirmation_source": "clinician_confirmed",
        "ai_generated": False,
    }

    status, unauth = request_json(
        staging_url,
        "POST",
        BUILD_PATH,
        body=base_payload,
    )
    expect(status, 401, "unauthenticated framework denial", unauth)

    status, cross_build = request_json(
        staging_url,
        "POST",
        BUILD_PATH,
        body=base_payload,
        token=token_b,
    )
    expect(status, 404, "cross-user framework denial", cross_build)

    status, build = request_json(
        staging_url,
        "POST",
        BUILD_PATH,
        body=base_payload,
        token=token_a,
    )
    expect(status, 200, "initial framework build", build)
    check_safe_preview_response(build, "initial framework build")
    preview = build.get("treatment_framework_preview")
    if not isinstance(preview, dict) or not preview:
        fail("initial treatment framework preview is missing")

    review_payload = dict(base_payload)
    review_payload.update(
        {
            "treatment_framework_preview": preview,
            "reviewed_by": clinician_id,
            "review_decision": "approve_for_clinician_use",
            "review_note": "Synthetic internal clinician review.",
        }
    )
    status, review = request_json(
        staging_url,
        "POST",
        REVIEW_PATH,
        body=review_payload,
        token=token_a,
    )
    expect(status, 200, "initial clinician review", review)
    check_safe_preview_response(review, "initial clinician review")

    before_audit_rows = audit_rows_for_case(staging_url, token_a, case_id)
    if before_audit_rows:
        fail("new P0-03 synthetic case unexpectedly has audit rows")

    request_id = "p0-03-treatment-audit-" + run_id
    audit_dry_body = dict(review_payload)
    audit_dry_body.update(
        {
            "dry_run": True,
            "request_id": request_id,
        }
    )
    status, audit_dry_1 = request_json(
        staging_url,
        "POST",
        AUDIT_PATH,
        body=audit_dry_body,
        token=token_a,
    )
    expect(status, 200, "audit dry-run first", audit_dry_1)
    status, audit_dry_2 = request_json(
        staging_url,
        "POST",
        AUDIT_PATH,
        body=audit_dry_body,
        token=token_a,
    )
    expect(status, 200, "audit dry-run replay", audit_dry_2)
    if canonical_hash(audit_dry_1) != canonical_hash(audit_dry_2):
        fail("audit dry-run replay is not deterministic")

    audit_write_body = dict(audit_dry_body)
    audit_write_body.update(
        {
            "dry_run": False,
            "audit_log_confirmation": AUDIT_APPEND_CONFIRMATION,
        }
    )
    status, audit_write = request_json(
        staging_url,
        "POST",
        AUDIT_PATH,
        body=audit_write_body,
        token=token_a,
    )
    expect(status, 200, "single append-only audit write", audit_write)
    result = audit_write.get("audit_log_result")
    if not isinstance(result, dict) or result.get("persisted") is not True:
        fail("append-only audit write was not persisted")
    audit_log_id = str(result.get("audit_log_id") or "").strip()
    if not audit_log_id:
        fail("append-only audit write returned no audit log ID")
    if audit_write.get("writes_case_treatment") is not False:
        fail("audit endpoint unexpectedly wrote Case.treatment")
    if audit_write.get("writes_prescription") is not False:
        fail("audit endpoint unexpectedly wrote prescription data")

    first_chain = run_readonly_chain(
        staging_url,
        token_a,
        case_id=case_id,
        diagnosis=diagnosis,
        clinician_id=clinician_id,
        audit_log_id=audit_log_id,
    )
    second_chain = run_readonly_chain(
        staging_url,
        token_a,
        case_id=case_id,
        diagnosis=diagnosis,
        clinician_id=clinician_id,
        audit_log_id=audit_log_id,
    )
    hash_keys = [
        "build_hash",
        "review_hash",
        "signed_hash",
        "persistence_hash",
        "migration_hash",
    ]
    if any(first_chain[key] != second_chain[key] for key in hash_keys):
        fail("read-only treatment chain replay is not deterministic")

    status, denied_signed = request_json(
        staging_url,
        "POST",
        SIGNED_PATH,
        body=first_chain["signed_payload"],
        token=token_b,
    )
    expect(status, 404, "cross-user signed-state denial", denied_signed)

    signed_without_audit = dict(first_chain["signed_payload"])
    for key in (
        "audit_log_id",
        "audit_request_id",
        "audit_event_id",
        "request_id",
        "audit_log_result",
        "audit_event",
    ):
        signed_without_audit.pop(key, None)
    status, missing_audit = request_json(
        staging_url,
        "POST",
        SIGNED_PATH,
        body=signed_without_audit,
        token=token_a,
    )
    expect(status, 422, "missing audit reference failure", missing_audit)

    migration_missing_ack = dict(first_chain["migration_payload"])
    migration_missing_ack.pop("migration_design_acknowledged", None)
    status, missing_ack = request_json(
        staging_url,
        "POST",
        MIGRATION_PATH,
        body=migration_missing_ack,
        token=token_a,
    )
    expect(status, 422, "missing migration acknowledgement failure", missing_ack)

    forbidden_payload = dict(base_payload)
    forbidden_payload["confirmed_diagnosis_label"] = (
        "P0-03 forbidden synthetic detail 10 mg"
    )
    status, forbidden = request_json(
        staging_url,
        "POST",
        BUILD_PATH,
        body=forbidden_payload,
        token=token_a,
    )
    expect(status, 422, "forbidden medication detail failure", forbidden)

    status, case_after = request_json(
        staging_url,
        "GET",
        "/api/cases/%s" % case_id,
        token=token_a,
    )
    expect(status, 200, "final owner case read", case_after)
    case_after_hash = canonical_hash(case_after)
    if case_before_hash != case_after_hash:
        fail("case snapshot changed during dry-run treatment chain")
    if case_after.get("treatment") not in (None, ""):
        fail("case treatment field was written")

    audit_rows = audit_rows_for_case(staging_url, token_a, case_id)
    matched = [
        item
        for item in audit_rows
        if str(item.get("log_id") or "") == audit_log_id
    ]
    if len(audit_rows) != 1 or len(matched) != 1:
        fail("expected exactly one linked audit row")
    audit_row = matched[0]
    if int(audit_row.get("case_id") or -1) != case_id:
        fail("audit readback case link mismatch")
    if audit_row.get("event_type") != "treatment_framework_review":
        fail("audit readback event type mismatch")

    status, denied_dashboard = request_json(
        staging_url,
        "GET",
        "/api/diagnostic-data/clinical-qa-dashboard/v2/summary?case_id=%s"
        % case_id,
        token=token_b,
    )
    expect(status, 404, "cross-user audit readback denial", denied_dashboard)

    # Recheck production after all staging writes.
    production_version = check_version(production_url, "production post-smoke")
    check_flags(production_url, "production post-smoke")
    staging_version = check_version(staging_url, "staging post-smoke")
    check_flags(staging_url, "staging post-smoke")

    completed_at = utc_now()
    evidence = {
        "stage_id": STAGE_ID,
        "status": "PASS",
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "service_label": args.service_label,
        "repo_head": repo_head,
        "staging_revision": staging_version.get("database_revision"),
        "production_revision": production_version.get("database_revision"),
        "test_results": {
            "authentication_verified": True,
            "unauthenticated_request_blocked": True,
            "owner_scope_verified": True,
            "cross_user_denial_verified": True,
            "treatment_framework_build_verified": True,
            "clinician_review_verified": True,
            "append_only_audit_link_verified": True,
            "signed_review_state_preview_verified": True,
            "persistence_prepare_verified": True,
            "migration_path_preview_verified": True,
            "readback_verified": True,
            "dry_run_replay_deterministic": True,
            "actual_audit_append_count": 1,
            "missing_audit_reference_blocked": True,
            "missing_migration_ack_blocked": True,
            "forbidden_medication_detail_blocked": True,
            "no_partial_write_after_failures": True,
            "case_snapshot_unchanged": True,
            "production_hard_gate_preserved": True,
        },
        "write_scope": {
            "synthetic_users_created": 2,
            "synthetic_cases_created": 1,
            "append_only_audit_rows_created": 1,
            "signed_review_state_rows_created": 0,
            "case_treatment_write": False,
            "prescription_write": False,
            "medication_detail_output": False,
            "production_database_write": False,
            "active_0010_created": False,
            "migration_executed": False,
        },
        "idempotency_strategy": {
            "name": (
                "write_once_audit_append_plus_deterministic_"
                "read_only_replay"
            ),
            "audit_dry_run_repeated": True,
            "actual_audit_append_replayed": False,
            "read_only_chain_repeated": True,
            "server_unique_request_constraint_claimed": False,
        },
        "pseudonymous_identifiers": {
            "run_token": pseudonymize("run", run_id, run_id),
            "user_a_token": pseudonymize(
                "user-a", user_a.get("id"), run_id
            ),
            "user_b_token": pseudonymize(
                "user-b", user_b.get("id"), run_id
            ),
            "case_token": pseudonymize("case", case_id, run_id),
            "audit_token": pseudonymize("audit", audit_log_id, run_id),
        },
        "governance": {
            "operator_role": args.operator_role,
            "incident_owner_role": args.incident_owner_role,
            "decision": (
                "GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
                "PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1"
            ),
        },
    }
    evidence_path, digest = sanitize_and_write(
        Path(args.evidence_workspace).expanduser().resolve(),
        evidence,
    )

    print("stage_id=" + STAGE_ID)
    print("authenticated_staging_smoke=PASS")
    print("authentication_verified=true")
    print("owner_scope_verified=true")
    print("cross_user_denial_verified=true")
    print("append_only_audit_write_count=1")
    print("dry_run_replay_deterministic=true")
    print("failure_no_partial_write_verified=true")
    print("case_treatment_write=false")
    print("prescription_write=false")
    print("medication_detail_output=false")
    print("signed_review_0010_staging_migration_executed=false")
    print("production_database_write=false")
    print("evidence_file=" + str(evidence_path))
    print("evidence_sha256=" + digest)
    print(
        "decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_"
        "PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1"
    )
    print("PASS: PMAI-P0-03 Authenticated Staging Smoke")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run guarded PMAI-P0-03 authenticated staging smoke"
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument(
        "--production-base-url",
        default=DEFAULT_PRODUCTION_URL,
    )
    parser.add_argument(
        "--service-label",
        default="pet-med-ai-backend-staging-ohio",
    )
    parser.add_argument("--evidence-workspace", required=True)
    parser.add_argument("--operator-role", default="release_operator")
    parser.add_argument("--incident-owner-role", default="backend_owner")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    return parser


def main() -> int:
    try:
        return execute(build_parser().parse_args())
    except SmokeFailure as exc:
        print("NO-GO: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
